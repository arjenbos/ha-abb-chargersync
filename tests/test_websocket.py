"""Local cloud emulator; no account or physical charger involved."""

import asyncio
import functools
import json
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest
from aiohttp import web

from custom_components.abb_chargersync import websocket
from custom_components.abb_chargersync.api import ChargerSyncError, UnsupportedError
from custom_components.abb_chargersync.protocol import DeviceRejectedError, FrameDecoder, encode
from custom_components.abb_chargersync.websocket import (
    ReconnectPostponedError,
    RemoteCharger,
    RemoteError,
)

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.mark.parametrize("reply_code", [0, "0"])
async def test_cloud_handshake_fragmentation_and_cleanup(aiohttp_client, monkeypatch, reply_code):
    commands = []

    async def handler(request):
        assert request.query["t"] == "vendor-session"
        assert request.query["e"] == "test+charger@example.com"
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({"method": "login", "code": reply_code})
        async for msg in ws:
            data = json.loads(msg.data)
            if data["method"] == "ping":
                continue
            assert data["to"] == "TEST"
            frame = FrameDecoder().feed(bytes.fromhex(data["data"]))[0]
            commands.append(frame.command)
            if frame.command == 254:
                body = bytes(26) + b"12345678"
            elif frame.command == 176:
                body = bytes(4)
            else:
                body = b"\0"
            reply = encode(frame.command, body)
            for part in (reply[:7], reply[7:]):
                await ws.send_json(
                    {
                        "method": "remote_control",
                        "code": reply_code,
                        "data": {"deviceNumber": "TEST", "raw": part.hex()},
                    }
                )
        return ws

    app = web.Application()
    app.router.add_get("/ws/login", handler)
    server = await aiohttp_client(app)
    monkeypatch.setattr(
        "custom_components.abb_chargersync.websocket.WS_URL",
        str(server.make_url("/ws/login")).replace("http:", "ws:"),
    )
    client = Mock(
        session=server.session,
        token={"access_token": "access"},
        ensure_token=AsyncMock(),
        remote_credentials=AsyncMock(return_value=("test+charger@example.com", "vendor-session")),
    )
    remote = RemoteCharger(client, "TEST")
    assert await remote.command(181, b"\0") == b"\0"
    assert await remote.command(181, b"\0") == b"\0"
    assert commands == [254, 176, 181, 181]
    await remote.close()
    assert remote._ping_task is None and remote._ws is None


async def test_mutation_timeout_does_not_retry_and_closes():
    remote = RemoteCharger(Mock(), "TEST")
    remote._connect = AsyncMock()
    remote._exchange = AsyncMock(side_effect=TimeoutError)
    remote.close = AsyncMock()
    with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
        await remote.command(180, b"\0\0")
    remote._exchange.assert_awaited_once()
    remote.close.assert_awaited_once()


@pytest.mark.parametrize(
    "failure",
    [RemoteError("login_rejected", 401), RemoteError("connection_closed", 1008), TimeoutError()],
)
async def test_failed_login_refreshes_profile_without_replaying_commands(failure):
    client = Mock()
    remote = RemoteCharger(client, "TEST")

    async def connect():
        remote.stage = "cloud_login"
        raise failure

    remote._connect = connect
    remote._exchange = AsyncMock()
    remote.close = AsyncMock()
    with pytest.raises(ChargerSyncError):
        await remote.command(180)
    client.invalidate_remote_credentials.assert_called_once()
    remote._exchange.assert_not_awaited()
    remote.close.assert_awaited_once()
    assert remote.last_error["stage"] == "cloud_login"
    if isinstance(failure, RemoteError):
        assert remote.last_error["reason"] == failure.reason
        assert remote.last_error["result_code"] == failure.result_code


async def _emulator(aiohttp_client, monkeypatch, on_command=None):
    """Cloud emulator; `on_command(frame, ws)` may return a reply body, an int code or None."""
    state = {"commands": [], "logins": 0, "sockets": []}

    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        state["logins"] += 1
        state["sockets"].append(ws)
        await ws.send_json({"method": "login", "code": 0})
        async for msg in ws:
            data = json.loads(msg.data)
            if data["method"] == "ping":
                continue
            frame = FrameDecoder().feed(bytes.fromhex(data["data"]))[0]
            state["commands"].append(frame.command)
            code = 0
            if frame.command == 254:
                body = bytes(26) + b"12345678"
            elif frame.command == 176:
                body = bytes(4)
            else:
                body = b"\0"
                if on_command is not None:
                    outcome = await on_command(frame, ws)
                    if outcome == "cloud_reject":
                        await ws.send_json({"method": "remote_control", "code": 5})
                        continue
                    if isinstance(outcome, int):
                        code = outcome
                    elif isinstance(outcome, bytes):
                        body = outcome
            raw = bytearray(encode(frame.command, body))
            if code:
                raw[2] = code
                raw[7] = 0
                raw[7] = functools.reduce(int.__xor__, raw, 0)
            await ws.send_json(
                {
                    "method": "remote_control",
                    "code": 0,
                    "data": {"deviceNumber": "TEST", "raw": bytes(raw).hex()},
                }
            )
        return ws

    app = web.Application()
    app.router.add_get("/ws/login", handler)
    server = await aiohttp_client(app)
    monkeypatch.setattr(
        "custom_components.abb_chargersync.websocket.WS_URL",
        str(server.make_url("/ws/login")).replace("http:", "ws:"),
    )
    client = Mock(
        session=server.session,
        token={"access_token": "access"},
        ensure_token=AsyncMock(),
        remote_credentials=AsyncMock(return_value=("authen", "vendor-session")),
    )
    return RemoteCharger(client, "TEST"), state


async def test_token_refresh_reuses_the_logged_in_connection(aiohttp_client, monkeypatch):
    remote, state = await _emulator(aiohttp_client, monkeypatch)
    await remote.command(181, b"\0")
    remote.client.token = {"access_token": "rotated"}
    await remote.command(181, b"\0")
    assert state["logins"] == 1 and remote.connects == 1
    assert state["commands"] == [254, 176, 181, 181]
    await remote.close()


@pytest.mark.parametrize(
    ("outcome", "error"), [(1, DeviceRejectedError), (20, UnsupportedError), ("cloud_reject", None)]
)
async def test_clean_rejection_keeps_the_connection(aiohttp_client, monkeypatch, outcome, error):
    async def on_command(frame, ws):
        return outcome if frame.command == 240 else None

    remote, state = await _emulator(aiohttp_client, monkeypatch, on_command)
    await remote.command(181, b"\0")
    with pytest.raises(error or RemoteError):
        await remote.command(240, b"\x09\0", 9)
    assert remote.connected
    assert await remote.command(181, b"\0") == b"\0"
    assert state["logins"] == 1
    await remote.close()


async def test_idle_server_close_is_detected_and_reconnects_once(aiohttp_client, monkeypatch):
    remote, state = await _emulator(aiohttp_client, monkeypatch)
    await remote.command(181, b"\0")
    await state["sockets"][0].close()
    for _ in range(100):
        if not remote.connected:
            break
        await asyncio.sleep(0.01)
    assert not remote.connected
    assert remote.last_disconnect == "connection_closed"
    assert await remote.command(181, b"\0") == b"\0"
    assert state["logins"] == 2 and remote.connects == 2
    await remote.close()


async def test_idle_device_disconnect_status_ends_connection(aiohttp_client, monkeypatch):
    remote, state = await _emulator(aiohttp_client, monkeypatch)
    await remote.command(181, b"\0")
    await state["sockets"][0].send_json({"method": "update_device_status", "data": {"status": 1}})
    for _ in range(100):
        if not remote.connected:
            break
        await asyncio.sleep(0.01)
    assert remote.last_disconnect == "device_disconnected"
    await remote.close()


async def test_timeout_mid_command_drops_connection(aiohttp_client, monkeypatch):
    async def on_command(frame, ws):
        if frame.command == 182:
            await asyncio.sleep(1)
        return None

    monkeypatch.setattr("custom_components.abb_chargersync.websocket.REQUEST_TIMEOUT", 0.2)
    remote, _ = await _emulator(aiohttp_client, monkeypatch, on_command)
    await remote.command(181, b"\0")
    with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
        await remote.command(182, b"\0")
    assert not remote.connected and remote.failures == 1
    await remote.close()


async def test_reconnect_backoff_and_user_override(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(websocket.time, "monotonic", lambda: now[0])
    client = Mock(remote_credentials=AsyncMock(side_effect=TimeoutError))
    remote = RemoteCharger(client, "TEST")
    # The first failure retries at once, like the app; later ones back off exponentially.
    previous = 0
    for expected_delay in (0, 30, 60, 120):
        now[0] += previous
        with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
            await remote.command(181, b"\0")
        assert remote.connection_stats()["reconnect_in"] == expected_delay
        previous = expected_delay
    attempts = client.remote_credentials.await_count
    with pytest.raises(ReconnectPostponedError):
        await remote.command(181, b"\0")
    assert client.remote_credentials.await_count == attempts
    assert remote.last_error["stage"] == "remote_credentials"
    remote.allow_reconnect()
    with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
        await remote.command(181, b"\0")
    assert client.remote_credentials.await_count == attempts + 1
    for _ in range(10):
        remote._retry_at = 0
        with pytest.raises(ChargerSyncError):
            await remote.command(181, b"\0")
    assert remote.connection_stats()["reconnect_in"] == websocket.BACKOFF_MAX


def test_long_lived_connection_resets_backoff(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(websocket.time, "monotonic", lambda: now[0])
    remote = RemoteCharger(Mock(), "TEST")
    remote.failures = 5
    remote._connected_at = now[0]
    now[0] += websocket.STABLE_CONNECTION
    remote._note_lost("connection_closed")
    assert remote.failures == 1 and remote.connection_stats()["reconnect_in"] == 0


async def test_session_takeover_defers_reclaiming(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(websocket.time, "monotonic", lambda: now[0])
    client = Mock(remote_session_changes=0)
    client.remote_credentials = AsyncMock(return_value=("authen", "session"))
    client.session.ws_connect = AsyncMock(side_effect=aiohttp.ClientError)
    remote = RemoteCharger(client, "TEST")
    # First connect records the session generation (the socket open then fails).
    with pytest.raises(ChargerSyncError):
        await remote.command(181)
    remote._retry_at = 0
    client.remote_session_changes = 1
    with pytest.raises(ReconnectPostponedError):
        await remote.command(181)
    assert client.session.ws_connect.await_count == 1
    stats = remote.connection_stats()
    assert stats["session_takeovers"] == 1 and stats["reconnect_in"] == websocket.TAKEOVER_BACKOFF
    assert remote.last_disconnect == "session_taken_over"
    # The same generation after the wait reconnects; another takeover doubles the wait.
    now[0] += websocket.TAKEOVER_BACKOFF
    with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
        await remote.command(181)
    assert client.session.ws_connect.await_count == 2
    remote._retry_at = 0
    client.remote_session_changes = 2
    with pytest.raises(ReconnectPostponedError):
        await remote.command(181)
    assert remote.connection_stats()["reconnect_in"] == 2 * websocket.TAKEOVER_BACKOFF
    # A user action reclaims immediately.
    remote.allow_reconnect()
    with pytest.raises(ChargerSyncError, match="outcome may be unknown"):
        await remote.command(181)
    assert client.session.ws_connect.await_count == 3


async def test_profile_session_change_is_counted_without_exposing_it():
    from custom_components.abb_chargersync.api import ChargerSyncClient

    client = ChargerSyncClient(Mock(), {"access_token": "a", "expires_at": 1e12})
    client.user = AsyncMock(return_value={"id": 1, "authen": "e", "sessionId": "one"})
    await client.remote_credentials()
    client.invalidate_remote_credentials()
    await client.remote_credentials()
    assert client.remote_session_changes == 0
    client.user.return_value = {"id": 1, "authen": "e", "sessionId": "two"}
    client.invalidate_remote_credentials()
    await client.remote_credentials()
    assert client.remote_session_changes == 1
    assert "two" not in repr(vars(client).get("_identity_digest"))
