"""Tests for the Grilla setpoint (number) platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiogrilla import Grill, GrillaConnectionError
from homeassistant.components.number.const import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number.const import DOMAIN as NUMBER_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.grilla.const import DOMAIN


def _lookup(hass: HomeAssistant, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("number", DOMAIN, f"sub_sx1_{key}")


def _number_id(hass: HomeAssistant, key: str) -> str:
    entity_id = _lookup(hass, key)
    assert entity_id is not None
    return entity_id


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


async def test_setpoints_show_current_targets(hass, setup_grilla, make_state) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await setup_grilla()
    cbs["avail"](True)
    cbs["state"](make_state())
    await hass.async_block_till_done()

    grill = hass.states.get(_number_id(hass, "grill_setpoint"))
    assert grill is not None
    assert float(grill.state) == 250.0
    assert grill.attributes["min"] == 180
    assert grill.attributes["max"] == 500
    assert grill.attributes["step"] == 5
    probe = hass.states.get(_number_id(hass, "probe_setpoint"))
    assert probe is not None and float(probe.state) == 195.0
    probe2 = hass.states.get(_number_id(hass, "probe2_setpoint"))
    assert probe2 is not None and probe2.state == "unknown"


async def test_setpoints_unknown_before_telemetry(hass, setup_grilla) -> None:
    """Connected but no state yet: setpoints are unknown, not an error."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    _entry, cbs = await setup_grilla()
    cbs["avail"](True)
    await hass.async_block_till_done()
    state = hass.states.get(_number_id(hass, "grill_setpoint"))
    assert state is not None and state.state == "unknown"


async def test_set_grill_setpoint_calls_client(hass, setup_grilla) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    client = entry.runtime_data.client
    client.async_set_target_temp = AsyncMock(return_value=225)
    await _set(hass, _number_id(hass, "grill_setpoint"), 225)
    client.async_set_target_temp.assert_awaited_once_with("sx1", 225)


async def test_set_probe_setpoints_call_client(hass, setup_grilla) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    client = entry.runtime_data.client
    client.async_set_probe_target_temp = AsyncMock(return_value=165)
    await _set(hass, _number_id(hass, "probe_setpoint"), 165)
    await _set(hass, _number_id(hass, "probe2_setpoint"), 203)
    assert [
        c.args + (c.kwargs["probe"],) for c in client.async_set_probe_target_temp.await_args_list
    ] == [
        ("sx1", 165, 1),
        ("sx1", 203, 2),
    ]


@pytest.mark.parametrize("error", [GrillaConnectionError("offline"), ValueError("range")])
async def test_set_setpoint_errors_raise(hass, setup_grilla, error) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    entry, cbs = await setup_grilla()
    cbs["avail"](True)
    entry.runtime_data.client.async_set_target_temp = AsyncMock(side_effect=error)
    with pytest.raises(HomeAssistantError):
        await _set(hass, _number_id(hass, "grill_setpoint"), 225)


async def test_single_probe_model_has_no_probe2_setpoint(hass, setup_grilla) -> None:
    await setup_grilla(grills=[Grill("sx1", "Old", "silverbac")])
    assert _lookup(hass, "probe_setpoint") is not None
    assert _lookup(hass, "probe2_setpoint") is None


async def test_setpoints_unavailable_when_grill_offline(hass, setup_grilla, make_state) -> None:
    _entry, cbs = await setup_grilla()
    cbs["avail"](True)
    cbs["state"](make_state())
    cbs["avail"](False)
    await hass.async_block_till_done()
    state = hass.states.get(_number_id(hass, "grill_setpoint"))
    assert state is not None and state.state == "unavailable"
