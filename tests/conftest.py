"""Enable custom integrations in Home Assistant's test harness."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def account_reads():
    """Default optional REST reads; tests override the returned values when needed."""
    with (
        patch(
            "custom_components.abb_chargersync.api.ChargerSyncClient.rfid_cards",
            new_callable=AsyncMock,
            return_value=[],
        ) as cards,
        patch(
            "custom_components.abb_chargersync.api.ChargerSyncClient.firmware_notice",
            new_callable=AsyncMock,
            return_value=None,
        ) as notice,
    ):
        yield {"rfid_cards": cards, "firmware_notice": notice}
