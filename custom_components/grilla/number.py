"""Number platform for the Grilla integration: grill and food-probe setpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiogrilla import GrillaClient, GrillaConnectionError, GrillState
from aiogrilla.const import (
    GRILL_TARGET_MAX_F,
    GRILL_TARGET_MIN_F,
    GRILL_TARGET_STEP_F,
    PROBE_TARGET_MAX_F,
    PROBE_TARGET_MIN_F,
)
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import GrillaCoordinator
from .entity import GrillaEntity
from .models import GrillaConfigEntry

PARALLEL_UPDATES = 1

# Controllers with a single food-probe port (the app shows probe 2 only on the others).
_SINGLE_PROBE_MODELS = frozenset({"grilla", "silverbac", "chimp", "piero", "kong"})


@dataclass(frozen=True, kw_only=True)
class GrillaNumberDescription(NumberEntityDescription):
    """Setpoint description: where the current target lives and how to send a new one."""

    value_fn: Callable[[GrillState], float | None]
    set_fn: Callable[[GrillaClient, str, float], Awaitable[int]]
    second_probe: bool = False


NUMBERS: tuple[GrillaNumberDescription, ...] = (
    GrillaNumberDescription(
        key="grill_setpoint",
        translation_key="grill_setpoint",
        native_min_value=GRILL_TARGET_MIN_F,
        native_max_value=GRILL_TARGET_MAX_F,
        native_step=GRILL_TARGET_STEP_F,
        value_fn=lambda s: s.target_grill_temp,
        set_fn=lambda c, gid, v: c.async_set_target_temp(gid, v),
    ),
    GrillaNumberDescription(
        key="probe_setpoint",
        translation_key="probe_setpoint",
        native_min_value=PROBE_TARGET_MIN_F,
        native_max_value=PROBE_TARGET_MAX_F,
        native_step=1,
        value_fn=lambda s: s.target_probe_temp,
        set_fn=lambda c, gid, v: c.async_set_probe_target_temp(gid, v, probe=1),
    ),
    GrillaNumberDescription(
        key="probe2_setpoint",
        translation_key="probe2_setpoint",
        native_min_value=PROBE_TARGET_MIN_F,
        native_max_value=PROBE_TARGET_MAX_F,
        native_step=1,
        value_fn=lambda s: s.target_probe2_temp,
        set_fn=lambda c, gid, v: c.async_set_probe_target_temp(gid, v, probe=2),
        second_probe=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Grilla setpoint numbers."""
    client = entry.runtime_data.client
    async_add_entities(
        GrillaNumber(coordinator, client, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in NUMBERS
        if not description.second_probe
        or coordinator.grill.model.casefold() not in _SINGLE_PROBE_MODELS
    )


class GrillaNumber(GrillaEntity, NumberEntity):  # type: ignore[misc]
    """A grill or food-probe setpoint. The controller always works in °F."""

    entity_description: GrillaNumberDescription
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: GrillaCoordinator,
        client: GrillaClient,
        description: GrillaNumberDescription,
    ) -> None:
        """Initialize the setpoint."""
        super().__init__(coordinator, description.key)
        self.entity_description = description  # pyright: ignore[reportIncompatibleVariableOverride]
        self._client = client

    @property
    def native_value(self) -> float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the grill's current target (None until telemetry arrives)."""
        data = self.coordinator.data
        return None if data is None else self.entity_description.value_fn(data)

    async def async_set_native_value(self, value: float) -> None:
        """Send the new setpoint; the next telemetry push confirms it."""
        try:
            await self.entity_description.set_fn(self._client, self.coordinator.grill.id, value)
        except ValueError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="setpoint_out_of_range",
                translation_placeholders={"error": str(err)},
            ) from err
        except GrillaConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
