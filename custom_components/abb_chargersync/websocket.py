"""Serialized cloud WebSocket commands; close on ambiguity instead of replaying writes."""

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
    FrameDecoder,
    ProtocolError,
    check_reply,
    encode,
    identity_body,
    identity_token,
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
        self._access: str | None = None
        self._decoder = FrameDecoder()
        self._ping_task: asyncio.Task | None = None
        self.stage = "disconnected"
        self.last_error: dict[str, str | int] | None = None

    async def close(self) -> None:
        if self._ping_task:
            self._ping_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._ping_task
            self._ping_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._decoder = FrameDecoder()
        self._token = bytes(8)

    @staticmethod
    def _reply_code(response: dict) -> int:
        """Match JSONObject.optInt: accept numeric strings as well as JSON numbers."""
        try:
            return int(response.get("code", -1))
        except ValueError, TypeError:
            return -1

    async def _receive(self) -> dict:
        assert self._ws is not None
        message = await self._ws.receive()
        if message.type != aiohttp.WSMsgType.TEXT:
            raise ChargerSyncError("Remote connection closed")
        try:
            data = message.json()
        except ValueError as err:
            raise ProtocolError("Invalid remote JSON") from err
        if not isinstance(data, dict):
            raise ProtocolError("Invalid remote envelope")
        return data

    async def _connect(self) -> None:
        self.stage = "token_refresh"
        await self.client.ensure_token()
        access = self.client.token["access_token"]
        if self._ws and not self._ws.closed and self._access == access:
            return
        await self.close()
        self.stage = "remote_credentials"
        authen, session_id = await self.client.remote_credentials()
        url = URL(WS_URL).with_query(t=session_id, v=1, e=authen)
        self.stage = "websocket_open"
        self._ws = await self.client.session.ws_connect(url, max_msg_size=32768)
        self._access = access
        self.stage = "cloud_login"
        while True:
            response = await self._receive()
            if response.get("method") == "login":
                code = self._reply_code(response)
                if code != 0:
                    self.client.invalidate_remote_credentials()
                    raise ChargerSyncError("Remote login rejected")
                break
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
        self._ping_task = asyncio.create_task(self._ping())

    async def _ping(self) -> None:
        try:
            while self._ws and not self._ws.closed:
                await asyncio.sleep(30)
                await self._ws.send_json({"method": "ping"})
        except aiohttp.ClientError, ConnectionError, RuntimeError:
            if self._ws:
                await self._ws.close()

    async def _exchange(self, command: int, body: bytes = b"", subtype: int | None = None) -> bytes:
        assert self._ws is not None
        await self._ws.send_json(
            {
                "method": "remote_control",
                "to": self.number,
                "data": encode(command, body, self._token).hex().upper(),
            }
        )
        while True:
            response = await self._receive()
            method = response.get("method")
            if method == "update_device_status":
                data = response.get("data", {})
                if data.get("status") in (1, 3, -1):
                    raise ChargerSyncError("Device disconnected")
                continue
            if method != "remote_control":
                continue
            code = self._reply_code(response)
            if code == 401:
                self.client.invalidate_remote_credentials()
                raise ChargerSyncError("Remote account session expired")
            if code != 0:
                raise ChargerSyncError("Remote command rejected")
            data = response.get("data")
            if not isinstance(data, dict) or data.get("deviceNumber") != self.number:
                continue
            try:
                frames = self._decoder.feed(bytes.fromhex(data.get("raw", "")))
            except (ValueError, TypeError) as err:
                raise ProtocolError("Invalid remote frame") from err
            for frame in frames:
                if frame.command != command:
                    continue
                reply = check_reply(frame)
                if subtype is not None and (
                    len(reply) < 2 or int.from_bytes(reply[:2], "little") != subtype
                ):
                    continue
                return reply

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
            except (aiohttp.ClientError, TimeoutError, ConnectionError, RuntimeError) as err:
                self.last_error = {"stage": self.stage, "error": type(err).__name__}
                if isinstance(err, aiohttp.WSServerHandshakeError):
                    self.last_error["http_status"] = err.status
                await self.close()
                raise ChargerSyncError("Remote command failed; outcome may be unknown") from None
            except UnsupportedError:
                raise
            except asyncio.CancelledError:
                await self.close()
                raise
            except Exception as err:
                self.last_error = {"stage": self.stage, "error": type(err).__name__}
                await self.close()
                raise

    async def query_configuration(self, kind: int) -> bytes:
        from .protocol import configuration

        return configuration(await self.command(240, struct.pack("<H", kind), kind), kind)

    async def configure(self, kind: int, data: bytes) -> None:
        result = await self.command(167, struct.pack("<H", kind) + data, kind)
        if len(result) < 3 or result[2] != 0:
            raise ProtocolError("Configuration rejected")
