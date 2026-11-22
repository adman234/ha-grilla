"""Tests for the Grilla power-off button."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogrilla import GrillaAuthError, GrillaConnectionError
from homeassistant.components.button.const import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button.const import SERVICE_PRESS
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.grilla.const import DOMAIN


def _button_id(hass: HomeAssistant) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("button", DOMAIN, "sub_sx1_power_off")
    assert entity_id is not None
    return entity_id


async def _press(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: _button_id(hass)}, blocking=True
    )


async def test_power_off_calls_client(hass, setup_grilla) -> None:
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    client = entry.runtime_data.client
    client.async_power_down = AsyncMock()
    await _press(hass)
    client.async_power_down.assert_awaited_once_with("sx1")


async def test_no_power_on_button(hass, setup_grilla) -> None:
    """Only power-off exists: the grills can't be started remotely."""
    entry, _cbs = await setup_grilla()
    buttons = [
        e
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.domain == "button"
    ]
    assert [e.unique_id for e in buttons] == ["sub_sx1_power_off"]


async def test_power_off_connection_error_raises(hass, setup_grilla) -> None:
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    entry.runtime_data.client.async_power_down = AsyncMock(side_effect=GrillaConnectionError("502"))
    with pytest.raises(HomeAssistantError):
        await _press(hass)


async def test_power_off_auth_error_starts_reauth(hass, setup_grilla) -> None:
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    entry.runtime_data.client.async_power_down = AsyncMock(side_effect=GrillaAuthError("401"))
    with pytest.raises(HomeAssistantError):
        await _press(hass)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"source": SOURCE_REAUTH}
    )
    assert len(flows) == 1


async def test_power_off_unavailable_when_grill_offline(hass, setup_grilla) -> None:
    _entry, cbs = await setup_grilla()
    cbs["avail"](False)
    await hass.async_block_till_done()
    state = hass.states.get(_button_id(hass))
    assert state is not None and state.state == "unavailable"
