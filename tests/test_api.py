import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

from custom_components.abb_chargersync.api import (
    AuthenticationError,
    ChargerSyncClient,
    ChargerSyncError,
)

pytestmark = pytest.mark.usefixtures("socket_enabled")


async def test_login_and_rotated_refresh_persist(aiohttp_client, monkeypatch):
    calls = []

    async def token(request):
        fields = dict(await request.post())
        calls.append(fields)
        return web.json_response(
            {
                "access_token": "new",
                "refresh_token": "rotated",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        )

    app = web.Application()
    app.router.add_post("/api/oauth/token", token)
    server = await aiohttp_client(app)
    monkeypatch.setattr("custom_components.abb_chargersync.api.API_URL", str(server.make_url("/")))
    saved = Mock()
    client = ChargerSyncClient(server.session, on_token=saved)
    await client.login("a@example.com", "private")
    assert calls[0]["grant_type"] == "password"
    assert client.token["refresh_token"] == "rotated"
    client.token["expires_at"] = 0
    await asyncio.gather(client.ensure_token(), client.ensure_token())
    assert len(calls) == 2
    assert calls[1]["refresh_token"] == "rotated"
    assert saved.call_count == 2


async def test_get_401_refresh_only_once(aiohttp_client, monkeypatch):
    requests = []

    async def devices(request):
        requests.append(request.headers["Authorization"])
        if request.headers["Authorization"] == "Bearer old":
            return web.Response(status=401)
        return web.json_response([dict(id=1, deviceNumber="TEST")])

    async def token(request):
        return web.json_response(dict(access_token="new", refresh_token="next", expires_in=3600))

    app = web.Application()
    app.router.add_get("/api/v2/devices", devices)
    app.router.add_post("/api/oauth/token", token)
    server = await aiohttp_client(app)
    monkeypatch.setattr("custom_components.abb_chargersync.api.API_URL", str(server.make_url("/")))
    client = ChargerSyncClient(
        server.session, dict(access_token="old", refresh_token="r", expires_at=time.time() + 3600)
    )
    assert (await client.devices())[0]["id"] == 1
    assert requests == ["Bearer old", "Bearer new"]


async def test_expired_refresh_reauth_and_no_secret_in_error(aiohttp_client, monkeypatch):
    async def reject(request):
        return web.json_response({"error": "private-secret"}, status=400)

    app = web.Application()
    app.router.add_post("/api/oauth/token", reject)
    server = await aiohttp_client(app)
    monkeypatch.setattr("custom_components.abb_chargersync.api.API_URL", str(server.make_url("/")))
    client = ChargerSyncClient(server.session, {"refresh_token": "private-secret"})
    with pytest.raises(AuthenticationError) as error:
        await client.ensure_token()
    assert "private-secret" not in str(error.value)


async def test_read_allowlist_never_posts_active_session():
    client = ChargerSyncClient(Mock())
    client._request = AsyncMock()
    with pytest.raises(ValueError):
        await client.read(1, "sessions/active")
    client._request.assert_not_called()
    await client.read(1, "sessions", page=0)
    client._request.assert_awaited_once_with("GET", "api/v2/devices/1/sessions", params={"page": 0})


async def test_malformed_inventory_and_no_password_storage():
    client = ChargerSyncClient(Mock())
    client._request = AsyncMock(return_value={"access_token": "a", "refresh_token": "b"})
    await client.login("private@example.com", "secret")
    assert "password" not in client.token and "username" not in client.token
    client._request = AsyncMock(return_value={"data": []})
    with pytest.raises(ChargerSyncError):
        await client.devices()


async def test_websocket_credentials_use_profile_session_not_oauth():
    client = ChargerSyncClient(
        Mock(), {"access_token": "oauth-secret", "expires_at": time.time() + 3600}
    )
    client.user = AsyncMock(
        return_value={"id": 42, "authen": "profile-login", "sessionId": "vendor-session"}
    )
    assert await client.remote_credentials() == ("profile-login", "vendor-session")
    assert await client.remote_credentials() == ("profile-login", "vendor-session")
    client.user.assert_awaited_once()
    assert client.token["access_token"] == "oauth-secret"
    client.invalidate_remote_credentials()
    await client.remote_credentials()
    assert client.user.await_count == 2


async def test_missing_profile_session_never_falls_back_to_oauth():
    client = ChargerSyncClient(
        Mock(), {"access_token": "oauth-secret", "expires_at": time.time() + 3600}
    )
    client.user = AsyncMock(return_value={"id": 42, "authen": "profile-login"})
    with pytest.raises(ChargerSyncError, match="missing remote session"):
        await client.remote_credentials()
