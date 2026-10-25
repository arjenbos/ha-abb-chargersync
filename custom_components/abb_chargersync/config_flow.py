"""Account sign-in only. Access permissions remain managed in the official app."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import AuthenticationError, ChargerSyncClient, ChargerSyncError
from .const import DEFAULT_INTERVAL, DOMAIN


class ChargerSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        return await self._sign_in("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._sign_in("reauth_confirm", user_input)

    async def _sign_in(self, step, user_input):
        errors = {}
        if user_input:
            username = user_input[CONF_USERNAME].strip()
            client = ChargerSyncClient(async_get_clientsession(self.hass))
            try:
                await client.login(username, user_input[CONF_PASSWORD])
                user = await client.user()
                devices = await client.devices()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ChargerSyncError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(str(user["id"]))
                data = {"username": user.get("email") or username, "token": client.token}
                if step == "reauth_confirm":
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=data
                    )
                self._abort_if_unique_id_configured()
                if not devices:
                    return self.async_abort(reason="no_devices")
                return self.async_create_entry(title="ABB ChargerSync", data=data)
        default = (
            self._get_reauth_entry().data.get("username", "") if step == "reauth_confirm" else ""
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=default): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL)
                ),
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ChargerSyncOptionsFlow()


class ChargerSyncOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", DEFAULT_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=15, max=300)),
                }
            ),
        )
