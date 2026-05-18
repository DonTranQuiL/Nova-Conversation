import pytest
from unittest.mock import MagicMock, AsyncMock

from homeassistant.exceptions import HomeAssistantError

from custom_components.nova_conversation import async_setup


# ----------------------------
# FIXTURES (WERE MISSING)
# ----------------------------


@pytest.fixture
def hass():
    """Minimal mocked Home Assistant."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def entry():
    """Mock config entry."""
    e = MagicMock()
    e.entry_id = "test_entry_id"
    e.runtime_data = MagicMock()
    return e


# ----------------------------
# TESTS
# ----------------------------


@pytest.mark.asyncio
async def test_generate_image_generic_error(hass, entry):
    """Test generic error mapping to Home AssistantError."""

    # Setup integration (registers service)
    await async_setup(hass, {})

    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = MagicMock()

    async def fail(*args, **kwargs):
        # IMPORTANT: don't use OpenAIError constructor (broken in SDK v1 tests)
        raise Exception("boom")

    client.images.generate = AsyncMock(side_effect=fail)
    entry.runtime_data = client

    with pytest.raises(HomeAssistantError):
        await handler(
            MagicMock(
                data={
                    "config_entry": "test_entry_id",
                    "prompt": "test",
                    "size": "1024x1024",
                    "quality": "standard",
                    "style": "vivid",
                }
            )
        )
