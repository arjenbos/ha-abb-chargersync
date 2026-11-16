"""Persistent cloud WebSocket per charger; close on ambiguity instead of replaying writes.

Every new connection repeats the cloud login, device identity authentication and time
synchronization, exactly like the Android SDK. Chargers can audibly signal such a login,
so the connection is kept open for as long as the cloud allows: the OAuth token is not
part of the WebSocket session, cleanly rejected commands leave the stream intact, and a
background reader consumes cloud messages between polls, as `WebSocketClientImpl` does.
"""

from __future__ import annotations

import asyncio
import struct
import time
from collections.abc import Callable
from contextlib import suppress

import aiohttp
from yarl import URL

from .api import ChargerSyncClient, ChargerSyncError, UnsupportedError
from .const import REQUEST_TIMEOUT, WS_URL
from .protocol import (
    DeviceRejectedError,
    FrameDecoder,
    ProtocolError,
    check_reply,
    encode,
    identity_body,
    identity_token,
)

PING_INTERVAL = 30
# A connection that lasted this long counts as healthy; its loss restarts the backoff.
STABLE_CONNECTION = 300
BACKOFF_BASE = 30
BACKOFF_MAX = 600


class RemoteError(ChargerSyncError):
    """Remote failure with safe, structured evidence, excluding vendor payloads."""

    def __init__(self, reason: str, result_code: int | None = None) -> None:
        super().__init__(reason.replace("_", " "))
        self.reason = reason
        self.result_code = result_code


class ReconnectPostponedError(ChargerSyncError):
    """Reconnection is deferred after repeated failures to avoid repeated charger logins."""


def _clean_rejection(err: BaseException) -> bool:
    """A complete reply rejected the command; the stream itself is still consistent."""
    return isinstance(err, UnsupportedError | DeviceRejectedError) or (
        isinstance(err, RemoteError) and err.reason == "command_rejected"
    )


class RemoteCharger:
    def __init__(
        self,
        client: ChargerSyncClient,
        number: str,
        timezone_offset: Callable[[], int] | None = None,
    ) -> None:
        self.client = client
        self.number = number
        self.timezone_offset = timezone_offset
        self._lock = asyncio.Lock()
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._token = bytes(8)
        self._decoder = FrameDecoder()
        self._ping_task: asyncio.Task | None = None
        self._reader_task: asyncio.Task | None = None
        self._login: asyncio.Future[int] | None = None
        self._pending: tuple[int, int | None, asyncio.Future[bytes]] | None = None
        self._ready = False
        self.stage = "disconnected"
        self.last_error: dict[str, str | int] | None = None
        # Connection statistics: each connect is one cloud login at the charger.
        self.connects = 0
        self.failures = 0
        self.last_disconnect: str | None = None
        self._connected_at: float | None = None
        self._retry_at = 0.0

    @property
    def connected(self) -> bool:
        return self._ready and self._ws is not None and not self._ws.closed

    def connection_stats(self) -> dict[str, str | int | bool | None]:
        """Credential-free counters for diagnostics and the remote-login sensor."""
        now = time.monotonic()
        return {
            "connected": self.connected,
            "connects": self.connects,
            "consecutive_failures": self.failures,
            "last_disconnect": self.last_disconnect,
            "connection_age": (
                int(now - self._connected_at)
                if self.connected and self._connected_at is not None
                else None
            ),
            "reconnect_in": max(0, int(self._retry_at - now)) if not self.connected else 0,
        }

    def allow_reconnect(self) -> None:
        """User-initiated actions may reconnect immediately despite the backoff."""
        self._retry_at = 0.0

    def _note_lost(self, reason: str) -> None:
        """Record an unplanned disconnect or failed connect and schedule the next attempt."""
        self.last_disconnect = reason
        now = time.monotonic()
        if self._connected_at is not None and now - self._connected_at >= STABLE_CONNECTION:
            self.failures = 0
        self._connected_at = None
        self.failures += 1
        # Like the app, retry once immediately; back off exponentially after that.
        delay = (
            0 if self.failures <= 1 else min(BACKOFF_BASE * 2 ** (self.failures - 2), BACKOFF_MAX)
        )
        self._retry_at = now + delay

    async def close(self) -> None:
        self._ready = False
        current = asyncio.current_task()
        for attr in ("_ping_task", "_reader_task"):
            task = getattr(self, attr)
            setattr(self, attr, None)
            if task and task is not current:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        if self._ws:
            ws, self._ws = self._ws, None
            await ws.close()
        self._fail_waiters(RemoteError("connection_closed"))
        self._decoder = FrameDecoder()
        self._token = bytes(8)
        self._connected_at = None

    def _fail_waiters(self, err: Exception) -> None:
        if self._login is not None and not self._login.done():
            self._login.set_exception(err)
        if self._pending is not None and not self._pending[2].done():
            self._pending[2].set_exception(err)

    @staticmethod
    def _reply_code(response: dict) -> int:
        """Match JSONObject.optInt: accept numeric strings as well as JSON numbers."""
        try:
            return int(response.get("code", -1))
        except ValueError, TypeError:
            return -1

    async def _read_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Consume every cloud message, so pings are answered and closes are seen at once."""
        reason = "connection_closed"
        try:
            while True:
                message = await ws.receive()
                if message.type != aiohttp.WSMsgType.TEXT:
                    self._fail_waiters(RemoteError("connection_closed", ws.close_code))
                    break
                try:
                    data = message.json()
                except ValueError:
                    data = None
                if not isinstance(data, dict):
                    reason = "invalid_message"
                    self._fail_waiters(ProtocolError("Invalid remote envelope"))
                    break
                outcome = self._dispatch(data)
                if outcome is not None:
                    reason = outcome
                    break
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001 - transport failures end this connection
            reason = "receive_failed"
            self._fail_waiters(ChargerSyncError(type(err).__name__))
        if self._ws is ws:
            # A waiting command records the loss itself when its future fails.
            if self._ready and self._pending is None:
                self._note_lost(reason)
            self._ready = False
            await ws.close()

    def _dispatch(self, response: dict) -> str | None:
        """Route one envelope; return a reason when the connection must end."""
        method = response.get("method")
        if method == "login":
            if self._login is not None and not self._login.done():
                self._login.set_result(self._reply_code(response))
            return None
        if method == "update_device_status":
            data = response.get("data")
            status = data.get("status") if isinstance(data, dict) else None
            if status in (1, 3, -1):
                # The SDK disconnects on these statuses as well.
                self._fail_waiters(RemoteError("device_disconnected", status))
                return "device_disconnected"
            return None
        if method != "remote_control":
            return None
        code = self._reply_code(response)
        if code == 401:
            self.client.invalidate_remote_credentials()
            self._fail_waiters(RemoteError("account_session_expired", code))
            return "account_session_expired"
        pending = self._pending
        if code != 0:
            if pending is not None and not pending[2].done():
                pending[2].set_exception(RemoteError("command_rejected", code))
            return None
        data = response.get("data")
        if not isinstance(data, dict) or data.get("deviceNumber") != self.number:
            return None
        try:
            frames = self._decoder.feed(bytes.fromhex(data.get("raw", "")))
        except (ValueError, TypeError, ProtocolError) as err:
            self._fail_waiters(
                err if isinstance(err, ProtocolError) else ProtocolError("Invalid remote frame")
            )
            return "invalid_frame"
        for frame in frames:
            if pending is None or pending[2].done() or frame.command != pending[0]:
                continue
            try:
                reply = check_reply(frame)
            except ChargerSyncError as err:
                pending[2].set_exception(err)
                continue
            subtype = pending[1]
            if subtype is not None and (
                len(reply) < 2 or int.from_bytes(reply[:2], "little") != subtype
            ):
                continue
            pending[2].set_result(reply)
        return None

    async def _connect(self) -> None:
        if self.connected:
            return
        if self._ws is not None or self._reader_task is not None:
            await self.close()
        if time.monotonic() < self._retry_at:
            raise ReconnectPostponedError("Reconnect postponed after repeated failures")
        self.stage = "remote_credentials"
        authen, session_id = await self.client.remote_credentials()
        url = URL(WS_URL).with_query(t=session_id, v=1, e=authen)
        self.stage = "websocket_open"
        self.connects += 1
        ws = await self.client.session.ws_connect(url, max_msg_size=32768)
        self._ws = ws
        self._login = asyncio.get_running_loop().create_future()
        self._reader_task = asyncio.create_task(self._read_loop(ws))
        self.stage = "cloud_login"
        try:
            code = await self._login
        finally:
            self._login = None
        if code != 0:
            raise RemoteError("login_rejected", code)
        self.stage = "device_authentication"
        body = await self._exchange(254, identity_body(self.number))
        self._token = identity_token(body)
        # Match SDK connection initialization; time sync has no charging side effects.
        offset = int(
            (time.localtime().tm_gmtoff if hasattr(time.localtime(), "tm_gmtoff") else 0) / 3600
        )
        if self.timezone_offset is not None:
            offset = self.timezone_offset()
        self.stage = "time_sync"
        await self._exchange(176, struct.pack("<IB", int(time.time()), offset + 12))
        self._ready = True
        self._connected_at = time.monotonic()
        self._ping_task = asyncio.create_task(self._ping())

    async def _ping(self) -> None:
        try:
            while self._ws and not self._ws.closed:
                await asyncio.sleep(PING_INTERVAL)
                if self._ws and not self._ws.closed:
                    await self._ws.send_json({"method": "ping"})
        except aiohttp.ClientError, ConnectionError, RuntimeError:
            if self._ws:
                await self._ws.close()

    async def _exchange(self, command: int, body: bytes = b"", subtype: int | None = None) -> bytes:
        assert self._ws is not None
        future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()
        self._pending = (command, subtype, future)
        try:
            await self._ws.send_json(
                {
                    "method": "remote_control",
                    "to": self.number,
                    "data": encode(command, body, self._token).hex().upper(),
                }
            )
            return await future
        finally:
            self._pending = None

    def _record_failure(self, err: Exception) -> None:
        self.last_error = {"stage": self.stage, "error": type(err).__name__}
        if isinstance(err, RemoteError):
            self.last_error["reason"] = err.reason
            if err.result_code is not None:
                self.last_error["result_code"] = err.result_code
        if self.stage == "cloud_login":
            # A closed login handshake can also indicate a stale profile session.
            # Refresh on the next poll without replaying the requested command.
            self.client.invalidate_remote_credentials()

    async def _drop(self, err: Exception) -> None:
        """End an ambiguous connection; a failed connect also counts toward the backoff."""
        reason = (self.last_error or {}).get("reason") or type(err).__name__
        self._note_lost(str(reason))
        await self.close()

    async def command(self, command: int, body: bytes = b"", subtype: int | None = None) -> bytes:
        async with self._lock:
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    await self._connect()
                    self.stage = f"command_{command:02x}"
                    result = await self._exchange(command, body, subtype)
                    self.stage = "ready"
                    self.last_error = None
                    return result
            except ReconnectPostponedError:
                # Keep the original failure as evidence; nothing was sent.
                raise
            except (aiohttp.ClientError, TimeoutError, ConnectionError, RuntimeError) as err:
                self._record_failure(err)
                if isinstance(err, aiohttp.WSServerHandshakeError):
                    self.last_error["http_status"] = err.status
                await self._drop(err)
                raise ChargerSyncError("Remote command failed; outcome may be unknown") from None
            except asyncio.CancelledError:
                await self.close()
                raise
            except Exception as err:
                self._record_failure(err)
                if self.connected and _clean_rejection(err):
                    # The reply was complete: keep the session instead of logging in again.
                    self.stage = "ready"
                    raise
                await self._drop(err)
                raise

    async def query_configuration(self, kind: int) -> bytes:
        from .protocol import configuration

        return configuration(await self.command(240, struct.pack("<H", kind), kind), kind)

    async def configure(self, kind: int, data: bytes) -> None:
        result = await self.command(167, struct.pack("<H", kind) + data, kind)
        if len(result) < 3 or result[2] != 0:
            raise ProtocolError("Configuration rejected")
