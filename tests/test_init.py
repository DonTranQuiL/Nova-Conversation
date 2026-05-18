import pytest
import openai
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.exceptions import HomeAssistantError
from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)


# =========================
# SETUP ENTRY TESTS
# =========================


@pytest.mark.asyncio
async def test_setup_entry_success(hass, entry):
    fake_models = MagicMock()
    fake_models.list = AsyncMock(return_value=None)

    fake_chain = MagicMock()
    fake_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_chain

    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_setup_entry_auth_error(hass, entry):
    async def fail(*args, **kwargs):
        raise openai.AuthenticationError(
            "unauthorized",
            response=MagicMock(),
            body=None,
        )

    fake_models = MagicMock()
    fake_models.list = fail

    fake_chain = MagicMock()
    fake_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_chain

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_not_ready(hass, entry):
    async def fail(*args, **kwargs):
        raise openai.APIConnectionError(request=MagicMock())

    fake_models = MagicMock()
    fake_models.list = fail

    fake_chain = MagicMock()
    fake_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_chain

    with patch("openai.AsyncOpenAI", return_value=client):
        with pytest.raises(Exception):
            await async_setup_entry(hass, entry)


# =========================
# SERVICE REGISTRATION
# =========================


@pytest.mark.asyncio
async def test_async_setup_registers_service(hass):
    await async_setup(hass, {})

    hass.services.async_register.assert_called_once()


@pytest.mark.asyncio
async def test_unload_entry(hass, entry):
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)

    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once()


# =========================
# IMAGE GENERATION TESTS
# =========================


@pytest.mark.asyncio
async def test_generate_image_generic_error(hass, entry):
    """FIXED: no OpenAIError construction"""

    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    class FakeOpenAIError(Exception):
        pass

    client = MagicMock()

    async def fail(*args, **kwargs):
        raise FakeOpenAIError("boom")

    client.images.generate = AsyncMock(side_effect=fail)
    entry.runtime_data = client

    with patch("openai.OpenAIError", FakeOpenAIError):
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
