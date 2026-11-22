"""Button platform for the Grilla integration: remote power-off.

There is deliberately no power-on button: the controllers can't be started remotely.
"""

from __future__ import annotations

from aiogrilla import GrillaAuthError, GrillaClient, GrillaConnectionError
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import GrillaCoordinator
from .entity import GrillaEntity
from .models import GrillaConfigEntry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Grilla power-off buttons."""
    client = entry.runtime_data.client
    async_add_entities(
        GrillaPowerOffButton(coordinator, client)
        for coordinator in entry.runtime_data.coordinators.values()
    )


class GrillaPowerOffButton(GrillaEntity, ButtonEntity):  # type: ignore[misc]
    """Turn the grill off (it runs its normal shutdown/cool-down)."""

    _attr_translation_key = "power_off"

    def __init__(self, coordinator: GrillaCoordinator, client: GrillaClient) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "power_off")
        self._client = client

    async def async_press(self) -> None:
        """Send the vendor's PowerDown call."""
        try:
            await self._client.async_power_down(self.coordinator.grill.id)
        except GrillaAuthError as err:
            entry = self.coordinator.config_entry
            assert entry is not None
            entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except GrillaConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
