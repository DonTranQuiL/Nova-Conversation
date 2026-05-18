import pytest
import httpx
import openai
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API

from custom_components.nova_conversation.config_flow import NovaConfigFlow
from custom_components.nova_conversation.const import (
    CONF_BASE_URL,
    CONF_RECOMMENDED,
    CONF_PROMPT,
)


@pytest.mark.asyncio
async def test_config_flow_user_form(hass: HomeAssistant):
    """Test step form is initially presented."""
    flow = NovaConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == FlowResultType.SHOW_FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.config_flow.validate_input")
async def test_config_flow_user_success(mock_validate, hass: HomeAssistant):
    """Test successful entry configuration processing."""
    flow = NovaConfigFlow()
    flow.hass = hass

    mock_validate.return_value = None

    user_input = {"api_key": "valid-key", CONF_BASE_URL: "https://api.test.com/v1"}
    result = await flow.async_step_user(user_input=user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Nova Conversation"
    assert result["data"] == user_input


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.config_flow.validate_input")
async def test_config_flow_errors(mock_validate, hass: HomeAssistant):
    """Test error handling paths for various exceptions."""
    flow = NovaConfigFlow()
    flow.hass = hass

    # Test connection issues
    mock_validate.side_effect = openai.APIConnectionError(request=MagicMock())
    result = await flow.async_step_user(
        user_input={"api_key": "key", CONF_BASE_URL: "url"}
    )
    assert result["errors"]["base"] == "cannot_connect"

    # Test auth validation problems
    mock_validate.side_effect = openai.AuthenticationError(
        message="Unauthorized", response=MagicMock(status_code=401), body=None
    )
    result = await flow.async_step_user(
        user_input={"api_key": "key", CONF_BASE_URL: "url"}
    )
    assert result["errors"]["base"] == "invalid_auth"

    # Test completely unexpected exceptions
    mock_validate.side_effect = RuntimeWarning("Random bad event")
    result = await flow.async_step_user(
        user_input={"api_key": "key", CONF_BASE_URL: "url"}
    )
    assert result["errors"]["base"] == "unknown"


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.config_flow.get_async_client")
async def test_options_flow_init_recommended(mock_get_client, hass: HomeAssistant):
    """Test standard initialization and generation of the options layout."""
    entry = MagicMock(spec=ConfigEntry)
    entry.options = {CONF_RECOMMENDED: True, CONF_PROMPT: "Default instructions"}
    entry.data = {"api_key": "key", CONF_BASE_URL: "url"}

    # Mock full dynamic model discovery failure fallback behavior
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=httpx.RequestError("Unreachable endpoint"))
    mock_get_client.return_value = mock_client

    flow = NovaConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.config_entry = entry

    result = await flow.async_step_init(user_input=None)
    assert result["type"] == FlowResultType.SHOW_FORM
    assert "init" == result["step_id"]


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.config_flow.get_async_client")
async def test_options_flow_fetch_models_success(mock_get_client, hass: HomeAssistant):
    """Test generating searchable model listings when remote call is functional."""
    entry = MagicMock(spec=ConfigEntry)
    entry.options = {CONF_RECOMMENDED: False}
    entry.data = {"api_key": "key", CONF_BASE_URL: "https://api.test.com"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"id": "nova-pro"}, {"id": "nova-lite"}]
    }

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    flow = NovaConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.config_entry = entry

    await flow.async_step_init(user_input=None)
    assert flow.available_models == ["nova-lite", "nova-pro"]


@pytest.mark.asyncio
async def test_options_flow_submit(hass: HomeAssistant):
    """Test form submission data adjustments, tracking toggle states."""
    entry = MagicMock(spec=ConfigEntry)
    entry.options = {CONF_RECOMMENDED: False}
    entry.data = {"api_key": "key", CONF_BASE_URL: "url"}

    flow = NovaConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.config_entry = entry
    flow.last_rendered_recommended = False

    user_input = {
        CONF_RECOMMENDED: False,
        CONF_PROMPT: "Custom prompt",
        CONF_LLM_HASS_API: "none",
    }

    result = await flow.async_step_init(user_input=user_input)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "none" not in result["data"]  # Verifies logic filtering "none" references


@pytest.mark.asyncio
async def test_options_flow_toggle_recommended(hass: HomeAssistant):
    """Test form rerendering path when the recommended settings toggle changes status."""
    entry = MagicMock(spec=ConfigEntry)
    entry.options = {CONF_RECOMMENDED: False}
    entry.data = {"api_key": "key", CONF_BASE_URL: "url"}

    flow = NovaConfigFlow.async_get_options_flow(entry)
    flow.hass = hass
    flow.config_entry = entry
    flow.last_rendered_recommended = False

    # Simulate submission changing recommended flag state
    user_input = {
        CONF_RECOMMENDED: True,
        CONF_PROMPT: "Custom prompt",
        CONF_LLM_HASS_API: "assist",
    }

    result = await flow.async_step_init(user_input=user_input)
    assert result["type"] == FlowResultType.SHOW_FORM
    assert flow.last_rendered_recommended is True
