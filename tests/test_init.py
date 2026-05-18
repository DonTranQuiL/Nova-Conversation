import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.nova_conversation.const import DOMAIN, CONF_BASE_URL


# -----------------------------
# async_setup SERVICE TESTS
# -----------------------------


@pytest.mark.asyncio
async def test_generate_image_success(hass: HomeAssistant):
    hass.config_entries = MagicMock()

    entry = MagicMock()
    entry.domain = DOMAIN

    hass.config_entries.async_get_entry.return_value = entry

    client = MagicMock()
    client.images.generate = AsyncMock(
        return_value=MagicMock(
            data=[MagicMock(model_dump=lambda exclude: {"ok": True})]
        )
    )

    entry.runtime_data = client

    call = MagicMock()
    call.data = {
        "config_entry": "123",
        "prompt": "a cat",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    with patch("homeassistant.helpers.selector.ConfigEntrySelector", lambda x: x):
        await async_setup(hass, {})

        handler = hass.services.async_register.call_args[0][2]
        result = await handler(call)

        assert result == {"ok": True}


@pytest.mark.asyncio
async def test_generate_image_invalid_entry(hass: HomeAssistant):
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry.return_value = None

    call = MagicMock()
    call.data = {"config_entry": "bad"}

    await async_setup(hass, {})

    handler = hass.services.async_register.call_args[0][2]

    with pytest.raises(Exception):
        await handler(call)


# -----------------------------
# async_setup_entry TESTS
# -----------------------------


@pytest.mark.asyncio
async def test_setup_entry_success():
    entry = MagicMock()
    entry.data = {
        "api_key": "test",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=client):
        hass = MagicMock()

        result = await async_setup_entry(hass, entry)

        assert result is True


@pytest.mark.asyncio
async def test_setup_entry_auth_error():
    entry = MagicMock()
    entry.data = {
        "api_key": "bad",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = AsyncMock(
        side_effect=Exception("auth")
    )

    with patch("openai.AsyncOpenAI", return_value=client):
        hass = MagicMock()

        result = await async_setup_entry(hass, entry)

        assert result is False


@pytest.mark.asyncio
async def test_setup_entry_not_ready():
    import openai

    entry = MagicMock()
    entry.data = {
        "api_key": "test",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = AsyncMock(
        side_effect=openai.OpenAIError("down")
    )

    with patch("openai.AsyncOpenAI", return_value=client):
        hass = MagicMock()

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


# -----------------------------
# unload
# -----------------------------


@pytest.mark.asyncio
async def test_unload_entry():
    entry = MagicMock()
    hass = MagicMock()

    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)

    assert result is True
