"""Local cloud emulator; no account or physical charger involved."""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

from custom_components.abb_chargersync.api import ChargerSyncError
from custom_components.abb_chargersync.protocol import FrameDecoder, encode
from custom_components.abb_chargersync.websocket import RemoteCharger

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
