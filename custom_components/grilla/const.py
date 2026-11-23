"""Constants for the Grilla integration."""

from homeassistant.const import Platform

DOMAIN = "grilla"
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.BUTTON,
    Platform.NUMBER,
]

CONF_REFRESH_TOKEN = "refresh_token"
CONF_EMAIL = "email"
CONF_MODELS = "models"  # options: {grill_id: friendly_model_name}
# options: send the app's client heartbeat (original controllers stop reporting without it)
CONF_HEARTBEAT = "heartbeat"

# Controller codes (casefolded) of models with a single meat-probe port. The Grilla app
# shows probe 2 only for models with a "three-readings" dashboard card: silverbacxl,
# silverbac20, chimp20 and mammoth. Pie-Ro and Kong use other cards, so no probe 2.
SINGLE_PROBE_MODELS = frozenset({"grilla", "silverbac", "chimp", "piero", "kong"})

# Display names for the model picker (app-connected Grilla models). The picker also
# accepts a free-text custom value, so this list need not be exhaustive.
GRILLA_MODELS = [
    "Grilla",
    "Silverbac",
    "Silverbac Built-In",
    "Silverbac 2.0",
    "Silverbac 2.0 Built-In",
    "Silverbac XL",
    "Silverbac 2.0 XL",
    "Silverbac 2.0 XL Built-In",
    "Chimp",
    "Chimp 2.0",
    "Kong",
    "Mammoth",
    "Pie-Ro",
]
