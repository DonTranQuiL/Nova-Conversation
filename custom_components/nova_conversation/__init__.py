"""Initialize the Nova Conversation integration."""

from __future__ import annotations

import logging
import openai
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_BASE_URL

_LOGGER = logging.getLogger(__name__)

SERVICE_GENERATE_IMAGE = "generate_image"
PLATFORMS = (Platform.CONVERSATION,)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type NovaConfigEntry = ConfigEntry[openai.AsyncClient]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Nova Conversation global services."""

    async def generate_dalle_image(call: ServiceCall) -> ServiceResponse:
        """Handle requests to render an image using the configured AI provider."""
        entry_id = call.data["config_entry"]
        target_entry = hass.config_entries.async_get_entry(entry_id)

        if target_entry is None or target_entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_config_entry",
                translation_placeholders={"config_entry": entry_id},
            )

        nova_client: openai.AsyncClient = target_entry.runtime_data

        try:
            # Note: Hardcoded to dall-e-3 as it provides the most consistent URL formats
            api_response = await nova_client.images.generate(
                model="dall-e-3",
                output_format="url",
                prompt=call.data["prompt"],
                size=call.data["size"],
                quality=call.data["quality"],
                style=call.data["style"],
                n=1,
            )
        except openai.RateLimitError as err:
            _LOGGER.error("Nova Image Generation: Quota exceeded (%s)", err)
            raise HomeAssistantError(
                "Rate limit exceeded. Check your API dashboard."
            ) from err
        except openai.OpenAIError as err:
            _LOGGER.error("Nova Image Generation: Provider rejected request (%s)", err)
            raise HomeAssistantError(f"Failed to generate image: {err}") from err

        # Strip heavy base64 strings to keep the event bus clean
        return api_response.data[0].model_dump(exclude={"b64_json"})

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_IMAGE,
        generate_dalle_image,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {"integration": DOMAIN}
                ),
                vol.Required("prompt"): cv.string,
                vol.Optional("size", default="1024x1024"): vol.In(
                    ("1024x1024", "1024x1792", "1792x1024")
                ),
                vol.Optional("quality", default="standard"): vol.In(("standard", "hd")),
                vol.Optional("style", default="vivid"): vol.In(("vivid", "natural")),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NovaConfigEntry) -> bool:
    """Initialize the asynchronous OpenAI client for the Nova integration."""
    nova_client = openai.AsyncOpenAI(
        api_key=entry.data[CONF_API_KEY],
        http_client=get_async_client(hass),
        base_url=entry.data[CONF_BASE_URL],
    )

    # Pre-cache platform headers to optimize subsequent requests
    try:
        await hass.async_add_executor_job(lambda: nova_client.platform_headers)
    except Exception:
        # Some local providers (e.g., LM Studio) don't support platform headers
        pass

    try:
        # Ping the provider to validate credentials before completing setup
        await nova_client.with_options(timeout=10.0).models.list()
    except openai.AuthenticationError as err:
        _LOGGER.error("Nova Setup: Invalid API key or unauthorized. (%s)", err)
        return False
    except openai.OpenAIError as err:
        _LOGGER.warning("Nova Setup: Provider unreachable, will retry. (%s)", err)
        raise ConfigEntryNotReady(err) from err

    entry.runtime_data = nova_client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Safely tear down the Nova integration and clear listeners."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
