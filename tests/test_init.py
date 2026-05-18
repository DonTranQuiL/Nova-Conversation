import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.nova_conversation.const import DOMAIN, CONF_BASE_URL


# -------------------------
# SERVICE REGISTRATION TEST
# -------------------------


@pytest.mark.asyncio
async def test_generate_image_success(hass):
    hass.config_entries = MagicMock()

    entry = MagicMock()
    entry.domain = DOMAIN
    entry.runtime_data = MagicMock()

    hass.config_entries.async_get_entry.return_value = entry

    call = MagicMock()
    call.data = {
        "config_entry": "123",
        "prompt": "a cat",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    fake_response = MagicMock()
    fake_response.data = [MagicMock(model_dump=lambda exclude: {"ok": True})]

    client = MagicMock()
    client.images.generate = AsyncMock(return_value=fake_response)
    entry.runtime_data = client

    # Capture registered service handler properly
    with patch(
        "homeassistant.helpers.selector.ConfigEntrySelector",
        lambda x: x,
    ):
        await async_setup(hass, {})

        # get registered service handler safely
        service_call = None

        def fake_register(domain, service, handler, **kwargs):
            nonlocal service_call
            service_call = handler

        hass.services = MagicMock()
        hass.services.async_register = fake_register

        await async_setup(hass, {})

        result = await service_call(call)

        assert result == {"ok": True}


# -------------------------
# INVALID ENTRY PATH
# -------------------------


@pytest.mark.asyncio
async def test_generate_image_invalid_entry(hass):
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry.return_value = None

    call = MagicMock()
    call.data = {"config_entry": "bad"}

    captured = {}

    def fake_register(domain, service, handler, **kwargs):
        captured["handler"] = handler

    hass.services = MagicMock()
    hass.services.async_register = fake_register

    await async_setup(hass, {})

    with pytest.raises(Exception):
        await captured["handler"](call)


# -------------------------
# SETUP ENTRY SUCCESS
# -------------------------


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

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is True


# -------------------------
# AUTH ERROR PATH
# -------------------------


@pytest.mark.asyncio
async def test_setup_entry_auth_error():
    import openai

    entry = MagicMock()
    entry.data = {
        "api_key": "bad",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = AsyncMock(
        side_effect=openai.AuthenticationError("bad key")
    )

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is False


# -------------------------
# NOT READY PATH
# -------------------------


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

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        with pytest.raises(Exception):
            await async_setup_entry(hass, entry)


# -------------------------
# UNLOAD
# -------------------------


@pytest.mark.asyncio
async def test_unload_entry():
    entry = MagicMock()
    hass = MagicMock()

    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)

    assert result is True
