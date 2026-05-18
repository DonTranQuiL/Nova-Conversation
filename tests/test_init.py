import pytest
import openai
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError, HomeAssistantError

from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.nova_conversation.const import DOMAIN, CONF_BASE_URL


@pytest.fixture
def mock_hass():
    """Fixture for a mocked Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.async_add_executor_job = AsyncMock(return_value=True)
    hass.config_entries = MagicMock()
    hass.services = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Fixture for a mocked config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        "api_key": "test-key",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }
    return entry


# ==================== ENTRY SETUP TESTS ====================


@pytest.mark.asyncio
async def test_setup_entry_success(mock_hass, mock_config_entry):
    """Test successful initialization of the integration."""
    fake_models = MagicMock()
    fake_models.list = AsyncMock(return_value=MagicMock())

    fake_client_chain = MagicMock()
    fake_client_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_client_chain

    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(mock_hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.runtime_data == client
    mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
        mock_config_entry,
        (MagicMock(),),  # Platform.CONVERSATION tuple
    )


@pytest.mark.asyncio
async def test_setup_entry_auth_error(mock_hass, mock_config_entry):
    """Test handling of invalid credentials during setup."""

    async def fake_list(*args, **kwargs):
        raise openai.AuthenticationError(
            message="unauthorized",
            response=MagicMock(),
            body=None,
        )

    fake_models = MagicMock()
    fake_models.list = fake_list
    fake_client_chain = MagicMock()
    fake_client_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_client_chain

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(mock_hass, mock_config_entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_not_ready(mock_hass, mock_config_entry):
    """Test handling of temporary connection failures during setup."""

    async def fake_list(*args, **kwargs):
        raise openai.APIConnectionError(request=MagicMock())

    fake_models = MagicMock()
    fake_models.list = fake_list
    fake_client_chain = MagicMock()
    fake_client_chain.models = fake_models

    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_client_chain

    with patch("openai.AsyncOpenAI", return_value=client):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(mock_hass, mock_config_entry)


@pytest.mark.asyncio
async def test_setup_entry_platform_headers_exception(mock_hass, mock_config_entry):
    """Test that setup continues even if platform headers cause an exception (e.g. LM Studio)."""
    mock_hass.async_add_executor_job = AsyncMock(side_effect=Exception("Unsupported"))

    fake_models = MagicMock()
    fake_models.list = AsyncMock()
    fake_client_chain = MagicMock()
    fake_client_chain.models = fake_models

    client = MagicMock()
    client.with_options.return_value = fake_client_chain

    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(mock_hass, mock_config_entry)

    assert result is True


@pytest.mark.asyncio
async def test_unload_entry(mock_hass, mock_config_entry):
    """Test clean breakdown and unloading of config entry."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(mock_hass, mock_config_entry)

    assert result is True
    mock_hass.config_entries.async_unload_platforms.assert_called_once()


# ==================== GLOBAL SERVICE TESTS ====================


@pytest.mark.asyncio
async def test_async_setup_registers_service(mock_hass):
    """Test that the image generation service gets globally registered."""
    result = await async_setup(mock_hass, {})
    assert result is True
    mock_hass.services.async_register.assert_called_once()


@pytest.mark.asyncio
async def test_generate_image_service_success(mock_hass, mock_config_entry):
    """Test a valid and successful DALL-E image generation request."""
    # Register service to capture the handler closure function
    await async_setup(mock_hass, {})
    service_handler = mock_hass.services.async_register.call_args[0][2]

    # Mock HA config entries store
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    # Mock OpenAI response data structure
    mock_image = MagicMock()
    mock_image.model_dump.return_value = {
        "url": "https://nova.ai/img.png",
        "b64_json": "heavy-string",
    }

    mock_response = MagicMock()
    mock_response.data = [mock_image]

    mock_client = MagicMock()
    mock_client.images.generate = AsyncMock(return_value=mock_response)
    mock_config_entry.runtime_data = mock_client

    # Call the actual service handler closure
    call = MagicMock()
    call.data = {
        "config_entry": "test_entry_id",
        "prompt": "A cute synthwave robot",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    result = await service_handler(call)

    # Ensure heavy b64 keys are removed per your code implementation
    assert result == {"url": "https://nova.ai/img.png"}


@pytest.mark.asyncio
async def test_generate_image_invalid_entry(mock_hass):
    """Test validation errors when missing or mismatched config entries are targeted."""
    await async_setup(mock_hass, {})
    service_handler = mock_hass.services.async_register.call_args[0][2]

    mock_hass.config_entries.async_get_entry.return_value = None  # Entry doesn't exist

    call = MagicMock()
    call.data = {"config_entry": "dead-beef", "prompt": "test"}

    with pytest.raises(ServiceValidationError):
        await service_handler(call)


@pytest.mark.asyncio
async def test_generate_image_rate_limit(mock_hass, mock_config_entry):
    """Test handling of provider rate limits/exhausted quotas."""
    await async_setup(mock_hass, {})
    service_handler = mock_hass.services.async_register.call_args[0][2]
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    mock_client = MagicMock()
    mock_client.images.generate = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Quota exceeded", response=MagicMock(), body=None
        )
    )
    mock_config_entry.runtime_data = mock_client

    call = MagicMock()
    call.data = {
        "config_entry": "test_entry_id",
        "prompt": "test",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    with pytest.raises(HomeAssistantError, match="Rate limit exceeded"):
        await service_handler(call)


@pytest.mark.asyncio
async def test_generate_image_generic_openai_error(mock_hass, mock_config_entry):
    """Test generic OpenAI errors mapping correctly to Home Assistant errors."""
    await async_setup(mock_hass, {})
    service_handler = mock_hass.services.async_register.call_args[0][2]
    mock_hass.config_entries.async_get_entry.return_value = mock_config_entry

    mock_client = MagicMock()
    mock_client.images.generate = AsyncMock(
        side_effect=openai.BadRequestError(
            message="Safety system triggered", response=MagicMock(), body=None
        )
    )
    mock_config_entry.runtime_data = mock_client

    call = MagicMock()
    call.data = {
        "config_entry": "test_entry_id",
        "prompt": "unsafe content",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }

    with pytest.raises(HomeAssistantError, match="Failed to generate image"):
        await service_handler(call)
