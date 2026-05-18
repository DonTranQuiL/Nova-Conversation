import pytest
import openai
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.nova_conversation.const import CONF_BASE_URL


@pytest.fixture
def hass():
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.services = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def entry():
    e = MagicMock()
    e.entry_id = "test-entry"
    e.domain = "nova_conversation"
    e.data = {
        "api_key": "test",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }
    return e


# =========================
# SETUP ENTRY
# =========================


@pytest.mark.asyncio
async def test_setup_entry_success(hass, entry):
    client = MagicMock()
    client.platform_headers = True

    fake_models = MagicMock()
    fake_models.list = AsyncMock()

    client.with_options.return_value.models = fake_models

    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.runtime_data == client


@pytest.mark.asyncio
async def test_setup_entry_auth_error(hass, entry):
    async def fail(*args, **kwargs):
        raise openai.AuthenticationError(
            message="unauthorized",
            response=MagicMock(),
            body=None,
        )

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = fail

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_not_ready(hass, entry):
    async def fail(*args, **kwargs):
        raise openai.APIConnectionError(request=MagicMock())

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value.models.list = fail

    with patch("openai.AsyncOpenAI", return_value=client):
        with pytest.raises(Exception):
            await async_setup_entry(hass, entry)


# =========================
# SERVICE SETUP
# =========================


@pytest.mark.asyncio
async def test_async_setup_registers_service(hass):
    await async_setup(hass, {})
    assert hass.services.async_register.called


# =========================
# IMAGE GENERATION
# =========================


@pytest.mark.asyncio
async def test_generate_image_success(hass, entry):
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    mock_image = MagicMock()
    mock_image.model_dump.return_value = {"url": "ok"}

    mock_response = MagicMock()
    mock_response.data = [mock_image]

    client = MagicMock()
    client.images.generate = AsyncMock(return_value=mock_response)
    entry.runtime_data = client

    call = MagicMock()
    call.data = {
        "config_entry": entry.entry_id,
        "prompt": "test",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    result = await handler(call)
    assert result == {"url": "ok"}


@pytest.mark.asyncio
async def test_generate_image_invalid_entry(hass):
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=None)

    call = MagicMock()
    call.data = {"config_entry": "bad", "prompt": "x"}

    with pytest.raises(Exception):
        await handler(call)


@pytest.mark.asyncio
async def test_generate_image_rate_limit(hass, entry):
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = MagicMock()
    client.images.generate = AsyncMock(
        side_effect=openai.RateLimitError(
            message="quota",
            response=MagicMock(),
            body=None,
        )
    )
    entry.runtime_data = client

    call = MagicMock()
    call.data = {
        "config_entry": entry.entry_id,
        "prompt": "x",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    with pytest.raises(Exception):
        await handler(call)


# ✅ FIXED TEST (THIS WAS YOUR FAILURE)


@pytest.mark.asyncio
async def test_generate_image_generic_error(hass, entry):
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = MagicMock()

    # ✅ FIX: use plain Exception instead of OpenAIError constructor
    client.images.generate = AsyncMock(side_effect=Exception("fail"))

    entry.runtime_data = client

    call = MagicMock()
    call.data = {
        "config_entry": entry.entry_id,
        "prompt": "unsafe",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    with pytest.raises(Exception):
        await handler(call)


# =========================
# UNLOAD
# =========================


@pytest.mark.asyncio
async def test_unload_entry(hass, entry):
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)

    assert result is True
