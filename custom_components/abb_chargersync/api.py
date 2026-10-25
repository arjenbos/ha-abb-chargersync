"""Asynchronous cloud client. No Bluetooth or authorization-management endpoints."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import API_URL, APP_VERSION, CLIENT_ID, CLIENT_SECRET, REQUEST_TIMEOUT


class ChargerSyncError(Exception):
    """Cloud request failed; exception messages intentionally exclude payloads and URLs."""


class AuthenticationError(ChargerSyncError):
    """Account needs to sign in again."""


class UnsupportedError(ChargerSyncError):
    """An optional endpoint or command is unavailable."""


class ChargerSyncClient:
    """REST client with serialized refresh and persisted rotated tokens."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: dict | None = None,
        on_token: Callable[[dict], None] | None = None,
    ) -> None:
        self.session = session
        self.token = dict(token or {})
        self.on_token = on_token
        self._refresh_lock = asyncio.Lock()
        self._identity_lock = asyncio.Lock()
        self._remote_identity: tuple[str, str] | None = None
        self._identity_access: str | None = None
        self._identity_expires = 0.0

    async def login(self, username: str, password: str) -> None:
        await self._token_request(
            {"grant_type": "password", "username": username, "password": password}
        )

    async def _token_request(self, fields: dict) -> None:
        response = await self._request(
            "POST",
            "api/oauth/token",
            authenticated=False,
            data={**fields, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        )
        if not isinstance(response, dict) or not response.get("access_token"):
            raise AuthenticationError("Missing access token")
        try:
            expires_in = float(response.get("expires_in", 3600))
        except (TypeError, ValueError) as err:
            raise ChargerSyncError("Invalid token expiry") from err
        self.token = {**self.token, **response, "expires_at": time.time() + expires_in}
        if self.on_token:
            self.on_token(dict(self.token))

    async def ensure_token(self, rejected: str | None = None) -> None:
        async with self._refresh_lock:
            if rejected is not None and self.token.get("access_token") != rejected:
                return
            if (
                rejected is None
                and self.token.get("access_token")
                and self.token.get("expires_at", 0) > time.time() + 60
            ):
                return
            if not self.token.get("refresh_token"):
                raise AuthenticationError("Sign in required")
            await self._token_request(
                {"grant_type": "refresh_token", "refresh_token": self.token["refresh_token"]}
            )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        retry: bool = True,
        **kwargs: Any,
    ) -> Any:
        headers = {"X-APP-VERSION": APP_VERSION, "Accept": "application/json"}
        access = None
        if authenticated:
            await self.ensure_token()
            access = self.token["access_token"]
            headers["Authorization"] = f"{self.token.get('token_type', 'Bearer')} {access}"
        try:
            async with self.session.request(
                method,
                API_URL + path.lstrip("/"),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                allow_redirects=False,
                **kwargs,
            ) as response:
                if response.status == 401 and authenticated and retry:
                    # Refresh below, outside the response context, releasing the connection first.
                    unauthorized = True
                else:
                    unauthorized = False
                    if response.status in (400, 401, 403) and not authenticated:
                        raise AuthenticationError("Sign in rejected")
                    if response.status == 401:
                        raise AuthenticationError("Account session expired")
                    if response.status in (404, 405, 501):
                        raise UnsupportedError("Endpoint unavailable")
                    if response.status >= 300:
                        raise ChargerSyncError(f"Cloud returned HTTP {response.status}")
                    if response.status == 204:
                        return None
                    body = await response.read()
                    if not body:
                        return None
                    try:
                        return await response.json(content_type=None)
                    except ValueError as err:
                        raise ChargerSyncError("Cloud returned invalid JSON") from err
            if unauthorized:
                await self.ensure_token(rejected=access)
                return await self._request(method, path, authenticated=True, retry=False, **kwargs)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ChargerSyncError("Cannot connect to ChargerSync cloud") from err

    async def user(self) -> dict:
        result = await self._request("GET", "api/v2/users/me")
        if not isinstance(result, dict) or "id" not in result:
            raise ChargerSyncError("Invalid user response")
        return result

    async def devices(self) -> list[dict]:
        result = await self._request("GET", "api/v2/devices")
        if not isinstance(result, list) or any(
            not isinstance(d, dict) or "id" not in d or "deviceNumber" not in d for d in result
        ):
            raise ChargerSyncError("Invalid device list")
        return result

    async def read(self, device_id: int, resource: str, **params: Any) -> Any:
        """Read a fixed, allowed device resource; never invoke active-session POST."""
        if resource not in {
            "schedules",
            "price",
            "sessions",
            "trends",
            "sessions/auto-export",
            "latest-upgrade-packages",
        }:
            raise ValueError("Resource not allowed")
        if resource == "sessions":
            # DashboardViewModel supplies a date range even for the first page.
            # Keep this here so background reads and ownership checks use it too.
            now = datetime.now().astimezone()
            params = {
                "startTime": (now - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
                **params,
            }
        return await self._request("GET", f"api/v2/devices/{device_id}/{resource}", params=params)

    async def currencies(self) -> Any:
        return await self._request("GET", "api/v2/currencies")

    async def create_schedule(self, device_id: int, body: dict) -> Any:
        return await self._request("POST", f"api/v2/devices/{device_id}/schedules", json=body)

    async def update_schedule(self, schedule_id: int, body: dict) -> Any:
        return await self._request("POST", f"api/v2/schedules/{schedule_id}", json=body)

    async def delete_schedule(self, schedule_id: int) -> Any:
        return await self._request("DELETE", f"api/v2/schedules/{schedule_id}")

    async def set_price(self, device_id: int, body: dict) -> Any:
        return await self._request("POST", f"api/v2/devices/{device_id}/price", json=body)

    async def set_auto_export(self, device_id: int, body: dict) -> Any:
        return await self._request(
            "POST", f"api/v2/devices/{device_id}/sessions/auto-export", json=body
        )

    async def export_sessions(self, device_id: int, body: dict) -> Any:
        return await self._request("POST", f"api/v2/devices/{device_id}/sessions/export", json=body)

    async def set_company_session(self, session_id: str, company: bool) -> Any:
        from urllib.parse import quote

        return await self._request(
            "POST",
            f"api/v2/sessions/{quote(session_id, safe='')}",
            json={"isCompanyCarSession": company},
        )

    async def rename(self, device_id: int, name: str) -> Any:
        current = await self._request("GET", f"api/v2/devices/{device_id}")
        if not isinstance(current, dict):
            raise ChargerSyncError("Cannot preserve charger settings")
        body = {
            k: current[k]
            for k in ("countryCode", "regionCode", "softVersion", "timeZone")
            if k in current
        }
        body["aliasNumber"] = name
        return await self._request("POST", f"api/v2/devices/{device_id}", json=body)

    def invalidate_remote_credentials(self) -> None:
        """Discard a rejected vendor session without discarding REST OAuth tokens."""
        self._remote_identity = None

    async def remote_credentials(self) -> tuple[str, str]:
        """Return the profile authen/sessionId pair used by the official app's WSS login."""
        await self.ensure_token()
        async with self._identity_lock:
            if (
                self._remote_identity is not None
                and self._identity_access == self.token.get("access_token")
                and self._identity_expires > time.monotonic()
            ):
                return self._remote_identity
            user = await self.user()
            authen, session_id = user.get("authen"), user.get("sessionId")
            if (
                not isinstance(authen, str)
                or not authen
                or not isinstance(session_id, str)
                or not session_id
            ):
                raise ChargerSyncError("User profile is missing remote session credentials")
            self._remote_identity = (authen, session_id)
            self._identity_access = self.token.get("access_token")
            self._identity_expires = time.monotonic() + 300
            return self._remote_identity
