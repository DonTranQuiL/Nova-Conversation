import os
import pytest
import respx
from httpx import Response
import openai
from unittest.mock import patch, MagicMock, AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResultStatus
from homeassistant.const import CONF_API_KEY
from homeassistant.components import conversation

from custom_components.nova_conversation.const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_ENABLE_TOOLS,
    CONF_MAX_TOKENS,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    CONF_PROMPT,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


# =========================================================================
# 1. CONFIG FLOW TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant):
    """Test successful initial config flow entry registration."""
    with patch(
        "custom_components.nova_conversation.config_flow.validate_input",
        new_callable=AsyncMock,
    ) as mock_validate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] == ConfigFlowResultStatus.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "test-valid-key",
                CONF_BASE_URL: "https://api.openai.com/v1",
            },
        )
        assert result2["type"] == ConfigFlowResultStatus.CREATE_ENTRY
        assert result2["title"] == "Nova Conversation"
        mock_validate.assert_called_once()


@pytest.mark.asyncio
async def test_config_flow_invalid_auth(hass: HomeAssistant):
    """Test config flow catches and prints invalid authorization error structures."""
    with patch(
        "custom_components.nova_conversation.config_flow.validate_input",
        side_effect=openai.AuthenticationError(
            message="Unauthorized API Access", response=MagicMock(), body=None
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_API_KEY: "wrong-bad-key",
                CONF_BASE_URL: "https://api.openai.com/v1",
            },
        )
        assert result2["type"] == ConfigFlowResultStatus.FORM
        assert result2["errors"] == {"base": "invalid_auth"}


# =========================================================================
# 2. OPTIONS FLOW TESTS (DYNAMIC MODEL LIST FETCHING)
# =========================================================================

@pytest.mark.asyncio
@respx.mock
async def test_options_flow_fetch_models(hass: HomeAssistant):
    """Test options flow uses httpx to list available provider model choices."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Nova Conversation",
        data={
            CONF_API_KEY: "mock-key",
            CONF_BASE_URL: "https://api.custom-provider.ai/v1",
        },
        options={},
        entry_id="nova_opts_test",
    )
    entry.add_to_hass(hass)

    # Intercept and mock the model endpoint call using respx
    respx.get("https://api.custom-provider.ai/v1/models").mock(
        return_value=Response(
            200, json={"data": [{"id": "model-alpha"}, {"id": "model-beta"}]}
        )
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == ConfigFlowResultStatus.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_PROMPT: "Custom prompt template rules.",
            "llm_hass_api": "none",
            CONF_ENABLE_TOOLS: True,
            "recommended": False,  # Opens advanced fields
            CONF_CHAT_MODEL: "model-beta",
            CONF_MAX_TOKENS: 200,
            CONF_TOP_P: 0.9,
            CONF_TEMPERATURE: 0.8,
        },
    )
    assert result2["type"] == ConfigFlowResultStatus.CREATE_ENTRY


# =========================================================================
# 3. CORE SERVICE TEST: IMAGE GENERATION
# =========================================================================

@pytest.mark.asyncio
async def test_generate_image_service_call(hass: HomeAssistant):
    """Test the specialized service callback to generate images using Dall-E."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Nova AI Engine",
        data={
            CONF_API_KEY: "sk-mock-key",
            CONF_BASE_URL: "https://api.openai.com/v1",
        },
        entry_id="nova_service_test_id",
    )
    entry.add_to_hass(hass)

    # Reconstruct the expected object response hierarchy of the OpenAI client
    mock_client = AsyncMock()
    mock_image_instance = MagicMock()
    mock_image_instance.model_dump.return_value = {
        "url": "https://images.openai.com/render_out.png"
    }
    mock_image_response = MagicMock()
    mock_image_response.data = [mock_image_instance]
    mock_client.images.generate = AsyncMock(return_value=mock_image_response)
    mock_client.with_options.return_value.models.list = AsyncMock()

    with patch(
        "custom_components.nova_conversation.openai.AsyncOpenAI",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Call the registered service routine natively
        service_response = await hass.services.async_call(
            DOMAIN,
            "generate_image",
            {
                "config_entry": entry.entry_id,
                "prompt": "An isometric rendering of a smart server rack room",
                "size": "1024x1024",
                "quality": "standard",
                "style": "vivid",
            },
            blocking=True,
            return_response=True,
        )

        assert service_response == {
            "url": "https://images.openai.com/render_out.png"
        }
        mock_client.images.generate.assert_called_once()


# =========================================================================
# 4. CONVERSATION LOOP TEST (STREAMING TEXT RESPONSE)
# =========================================================================

@pytest.mark.asyncio
async def test_conversation_agent_streaming_text(hass: HomeAssistant):
    """Test that text entries stream responses back to the conversation engine wrapper."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Nova Agent",
        data={
            CONF_API_KEY: "sk-mock-key",
            CONF_BASE_URL: "https://api.openai.com/v1",
        },
        options={
            CONF_PROMPT: "Test instruction prompt",
            CONF_CHAT_MODEL: "gpt-4o-mini",
            CONF_MAX_TOKENS: 150,
            CONF_TOP_P: 1.0,
            CONF_TEMPERATURE: 1.0,
            CONF_ENABLE_TOOLS: False,
        },
        entry_id="nova_conversation_agent_id",
    )
    entry.add_to_hass(hass)

    # An asynchronous generator factory simulating live streaming token iterations
    async def mock_chat_stream_generator(*args, **kwargs):
        tokens = ["System ", "Online. ", "How can I assist you with your setup?"]
        for token in tokens:
            chunk = MagicMock()
            choice = MagicMock()
            choice.delta.content = token
            choice.delta.tool_calls = None
            chunk.choices = [choice]
            yield chunk

    mock_client = AsyncMock()
    mock_client.with_options.return_value.models.list = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=mock_chat_stream_generator
    )

    with (
        patch(
            "custom_components.nova_conversation.openai.AsyncOpenAI",
            return_value=mock_client,
        ),
        patch(
            "custom_components.nova_conversation.conversation.convert_ha_content_to_openai_message",
            return_value={"role": "user", "content": "Ping agent"},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Execute conversation input through the core engine proxy
        agent_result = await conversation.async_process(
            hass,
            text="Ping agent",
            agent_id=entry.entry_id,
        )

        assert agent_result is not None
        assert (
            agent_result.response.speech["plain"]["speech"]
            == "System Online. How can I assist you with your setup?"
        )
