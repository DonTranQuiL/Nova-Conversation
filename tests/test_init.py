import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import openai
import voluptuous as vol

from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    ConfigEntryNotReady,
)
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import llm

from custom_components.nova_conversation import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.nova_conversation.utils import (
    format_ha_tool_for_openai,
    convert_ha_content_to_openai_message,
)
from custom_components.nova_conversation.const import DOMAIN, CONF_BASE_URL


# ----------------------------
# FIXTURES
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
    e = MagicMock(spec=ConfigEntry)
    e.domain = DOMAIN
    e.entry_id = "test_entry_id"
    e.data = {CONF_API_KEY: "test-key", CONF_BASE_URL: "https://api.openai.com/v1"}
    e.runtime_data = MagicMock()
    return e


@pytest.fixture
def service_call_data():
    """Standard payload data for the service call."""
    return {
        "config_entry": "test_entry_id",
        "prompt": "test prompt",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
    }


# ----------------------------
# SERVICE TESTS (async_setup)
# ----------------------------


@pytest.mark.asyncio
async def test_generate_image_success(hass, entry, service_call_data):
    """Test successful image generation and returning data."""
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    mock_image = MagicMock()
    mock_image.model_dump.return_value = {"url": "https://example.com/image.png"}
    mock_response = MagicMock()
    mock_response.data = [mock_image]

    client = AsyncMock()
    client.images.generate = AsyncMock(return_value=mock_response)
    entry.runtime_data = client

    result = await handler(MagicMock(data=service_call_data))

    assert result == {"url": "https://example.com/image.png"}
    mock_image.model_dump.assert_called_once_with(exclude={"b64_json"})


@pytest.mark.asyncio
async def test_generate_image_invalid_config_entry(hass, service_call_data):
    """Test error when entry is missing or belongs to a different domain."""
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]

    # Case 1: Entry is missing
    hass.config_entries.async_get_entry = MagicMock(return_value=None)
    with pytest.raises(ServiceValidationError):
        await handler(MagicMock(data=service_call_data))

    # Case 2: Entry belongs to a different domain
    wrong_entry = MagicMock(spec=ConfigEntry)
    wrong_entry.domain = "not_nova"
    hass.config_entries.async_get_entry = MagicMock(return_value=wrong_entry)
    with pytest.raises(ServiceValidationError):
        await handler(MagicMock(data=service_call_data))


@pytest.mark.asyncio
async def test_generate_image_rate_limit_error(hass, entry, service_call_data):
    """Test rate limit error handling."""
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = AsyncMock()
    mock_request = MagicMock()
    mock_request.url = "https://api.openai.com/v1"
    rate_limit_err = openai.RateLimitError(
        message="Rate limit hit",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    client.images.generate = AsyncMock(side_effect=rate_limit_err)
    entry.runtime_data = client

    with pytest.raises(HomeAssistantError, match="Rate limit exceeded"):
        await handler(MagicMock(data=service_call_data))


@pytest.mark.asyncio
async def test_generate_image_generic_openai_error(hass, entry, service_call_data):
    """Test general provider error handling."""
    await async_setup(hass, {})
    handler = hass.services.async_register.call_args[0][2]
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    client = AsyncMock()
    openai_err = openai.OpenAIError("API Connection issues")
    client.images.generate = AsyncMock(side_effect=openai_err)
    entry.runtime_data = client

    with pytest.raises(HomeAssistantError, match="Failed to generate image"):
        await handler(MagicMock(data=service_call_data))


# ----------------------------
# SETUP ENTRY TESTS (async_setup_entry)
# ----------------------------


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.openai.AsyncOpenAI")
async def test_async_setup_entry_success(mock_openai, hass, entry):
    """Test full successful integration setup flow."""
    mock_client = MagicMock()
    mock_client.platform_headers = {"test": "header"}
    mock_client.with_options().models.list = AsyncMock()
    mock_openai.return_value = mock_client

    hass.async_add_executor_job = AsyncMock(side_effect=lambda f: f())
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    assert await async_setup_entry(hass, entry) is True
    assert entry.runtime_data == mock_client
    hass.config_entries.async_forward_entry_setups.assert_called_once_with(
        entry, (Platform.CONVERSATION,)
    )


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.openai.AsyncOpenAI")
async def test_async_setup_entry_platform_header_exception(mock_openai, hass, entry):
    """Test setup tolerates local providers missing platform headers."""
    mock_client = MagicMock()
    type(mock_client).platform_headers = pytest.fail
    mock_client.with_options().models.list = AsyncMock()
    mock_openai.return_value = mock_client

    hass.async_add_executor_job = AsyncMock(side_effect=Exception("Platform headers not supported"))
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    assert await async_setup_entry(hass, entry) is True


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.openai.AsyncOpenAI")
async def test_async_setup_entry_auth_error(mock_openai, hass, entry):
    """Test explicit authentication error behavior."""
    mock_client = MagicMock()
    auth_err = openai.AuthenticationError(
        message="Invalid API Key",
        response=MagicMock(status_code=401),
        body=None,
    )
    mock_client.with_options().models.list = AsyncMock(side_effect=auth_err)
    mock_openai.return_value = mock_client

    hass.async_add_executor_job = AsyncMock()

    assert await async_setup_entry(hass, entry) is False


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.openai.AsyncOpenAI")
async def test_async_setup_entry_not_ready(mock_openai, hass, entry):
    """Test transient provider errors set configuration to retry."""
    mock_client = MagicMock()
    generic_err = openai.OpenAIError("Server gateway timeout")
    mock_client.with_options().models.list = AsyncMock(side_effect=generic_err)
    mock_openai.return_value = mock_client

    hass.async_add_executor_job = AsyncMock()

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, entry)


# ----------------------------
# UNLOAD TESTS (async_unload_entry)
# ----------------------------


@pytest.mark.asyncio
async def test_async_unload_entry(hass, entry):
    """Test safely unloading integration components."""
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)
    assert result is True
    hass.config_entries.async_unload_platforms.assert_called_once_with(
        entry, (Platform.CONVERSATION,)
    )


# ----------------------------
# UTILS MODULE LOGIC TESTS
# ----------------------------


def test_format_ha_tool_for_openai():
    """Test formatting a Home Assistant tool to OpenAI's spec."""
    mock_tool = MagicMock(spec=llm.Tool)
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool description"
    mock_tool.parameters = vol.Schema({})

    result = format_ha_tool_for_openai(mock_tool, custom_serializer=None)

    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"
    assert result["function"]["description"] == "A test tool description"


def test_convert_ha_content_to_openai_message_simple_text():
    """Test mapping normal user/assistant message text."""
    content = MagicMock()
    content.role = "user"
    content.content = "Hello world"

    result = convert_ha_content_to_openai_message(content)

    assert result["role"] == "user"
    assert result["content"] == "Hello world"
