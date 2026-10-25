"""Coordinate REST inventory and cloud device state independently."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthenticationError, ChargerSyncClient, ChargerSyncError, UnsupportedError
from .const import DEFAULT_INTERVAL, DOMAIN
from .controller import ChargerController
from .websocket import RemoteCharger

_LOGGER = logging.getLogger(__name__)


class ChargerSyncCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ChargerSyncClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get("scan_interval", DEFAULT_INTERVAL)),
        )
        self.client = client
        self.entry = entry
        self.options_snapshot = dict(entry.options)
        self.controllers: dict[int, ChargerController] = {}
        self._rest: dict[int, dict] = {}
        self._rest_updated = 0.0
        self._optional_unsupported: set[tuple[int, str]] = set()
        self._semaphore = asyncio.Semaphore(3)

    async def async_close(self) -> None:
        await asyncio.gather(*(c.remote.close() for c in self.controllers.values()))

    async def _inventory(self) -> None:
        devices = await self.client.devices()
        inventory = {int(d["id"]): d for d in devices}
        for device_id in set(self.controllers) - inventory.keys():
            await self.controllers.pop(device_id).remote.close()
        fresh = {}
        for device_id, device in inventory.items():
            snapshot = {"device": device, "resources": {}}
            for resource in (
                "schedules",
                "price",
                "sessions/auto-export",
                "latest-upgrade-packages",
            ):
                key = (device_id, resource)
                if key in self._optional_unsupported:
                    continue
                try:
                    snapshot["resources"][resource] = await self.client.read(device_id, resource)
                except UnsupportedError:
                    self._optional_unsupported.add(key)
                except AuthenticationError:
                    raise
                except ChargerSyncError:
                    # Do not retain an old resource as though it were freshly fetched.
                    continue
            fresh[device_id] = snapshot
        self._rest = fresh
        self._rest_updated = time.monotonic()

    async def _device(self, device_id: int, snapshot: dict) -> dict:
        async with self._semaphore:
            device = snapshot["device"]
            result = {**snapshot, "remote_available": False, "state": {}}
            controller = self.controllers.get(device_id)
            if controller is None:
                controller = self.controllers[device_id] = ChargerController(
                    RemoteCharger(
                        self.client,
                        device["deviceNumber"],
                        self.entry.data["username"],
                        lambda: int(dt_util.now().utcoffset().total_seconds() / 3600),
                    )
                )
            # Zero is explicitly offline; missing online status still permits a cloud attempt.
            if device.get("online") == 0:
                await controller.remote.close()
                return result
            try:
                result["state"] = await controller.status()
                result["remote_available"] = True
                result["state"].update(await controller.settings())
            except AuthenticationError as err:
                raise ConfigEntryAuthFailed("ChargerSync sign-in expired") from err
            except ChargerSyncError:
                # Keep any successful status update. Settings are independently unavailable.
                result["remote_error"] = True
            return result

    async def _async_update_data(self) -> dict[int, dict]:
        try:
            if time.monotonic() - self._rest_updated >= 300 or not self._rest_updated:
                await self._inventory()
            pairs = list(self._rest.items())
            snapshots = await asyncio.gather(*(self._device(i, s) for i, s in pairs))
            return {device_id: data for (device_id, _), data in zip(pairs, snapshots, strict=True)}
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed("ChargerSync sign-in expired") from err
        except ChargerSyncError as err:
            raise UpdateFailed(str(err)) from err

    async def action(self, device_id: int, operation: str, **kwargs: Any) -> None:
        if device_id not in self.controllers:
            raise HomeAssistantError("Charger is no longer linked to this account")
        controller = self.controllers[device_id]
        try:
            if operation == "start":
                await controller.simple(180, b"\0\0")
            elif operation == "stop":
                await controller.simple(182, b"\0")
            elif operation in ("lock", "unlock"):
                state = await controller.status()
                if state.get("status_code") == 6:
                    raise ChargerSyncError("Stop charging before operating the cable lock")
                await controller.simple(231 if operation == "lock" else 209)
            elif operation == "skip_delay":
                await controller.skip_delay()
            elif operation == "set_current":
                await controller.set_current(**kwargs)
            elif operation == "set_mode":
                await controller.set_mode(**kwargs)
            elif operation == "ignore_threshold":
                await controller.remote.configure(38, bytes((int(kwargs["enabled"]),)))
            elif operation == "set_solar_offsets":
                await controller.set_solar_offsets(**kwargs)
            elif operation == "replace_limits":
                await controller.replace_limits(**kwargs)
            else:
                raise HomeAssistantError("Unknown operation")
        except AuthenticationError as err:
            self.entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Sign in again to ChargerSync") from err
        except (ChargerSyncError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        # A successful write is never made to look failed by a following status refresh.
        await self.async_request_refresh()
