import pytest
import openai
from unittest.mock import MagicMock, AsyncMock

from homeassistant.exceptions import HomeAssistantError


@pytest.mark.asyncio
async def test_generate_image_generic_error(hass, entry):
    """Test generic OpenAI error mapping correctly to Home Assistant error."""

    await async_setup(hass, {})

    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = MagicMock()

    async def fail(*args, **kwargs):
        # IMPORTANT: must be OpenAIError so code catches it correctly
        raise openai.OpenAIError("boom")

    client.images.generate = AsyncMock(side_effect=fail)
    entry.runtime_data = client

    with pytest.raises(HomeAssistantError):
        await handler(MagicMock(data={
            "config_entry": "test_entry_id",
            "prompt": "test",
            "size": "1024x1024",
            "quality": "standard",
            "style": "vivid",
        }))
