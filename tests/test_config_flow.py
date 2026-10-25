"""Exercise real Home Assistant flow manager, including duplicate and reauthentication paths."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abb_chargersync.api import AuthenticationError, ChargerSyncError
from custom_components.abb_chargersync.const import DOMAIN


@pytest.fixture
def cloud():
    with patch("custom_components.abb_chargersync.config_flow.ChargerSyncClient") as cls:
        client = cls.return_value
        client.login = AsyncMock()
        client.user = AsyncMock(return_value={"id": 42, "email": "a@example.com"})
        client.devices = AsyncMock(return_value=[{"id": 1, "deviceNumber": "TEST"}])
        client.token = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 9999999999,
        }
        yield client


async def test_login_flow_stores_tokens_not_password(hass, cloud):
    with patch("custom_components.abb_chargersync.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "a@example.com", "password": "secret"}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "42"
    assert result["data"]["token"]["refresh_token"] == "refresh"
    assert "password" not in result["data"]


@pytest.mark.parametrize(
    "error,key", [(AuthenticationError, "invalid_auth"), (ChargerSyncError, "cannot_connect")]
)
async def test_login_errors(hass, cloud, error, key):
    cloud.login.side_effect = error("failure")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"username": "a@example.com", "password": "secret"}
    )
    assert result["errors"] == {"base": key}


async def test_no_devices_and_duplicate(hass, cloud):
    cloud.devices.return_value = []
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"username": "a@example.com", "password": "secret"}
    )
    assert result["reason"] == "no_devices"
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"username": "a@example.com", "password": "secret"}
    )
    assert result["reason"] == "already_configured"


async def test_reauth_same_account_and_wrong_account(hass, cloud):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    cloud.user.return_value = {"id": 99}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"username": "other@example.com", "password": "secret"}
    )
    assert result["reason"] == "unique_id_mismatch"
    cloud.user.return_value = {"id": 42, "email": "a@example.com"}
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(hass.config_entries, "async_reload", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "a@example.com", "password": "secret"}
        )
    assert result["reason"] == "reauth_successful"
    assert entry.data["token"] == cloud.token
