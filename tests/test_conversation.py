import pytest
import openai
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_LLM_HASS_API

from custom_components.nova_conversation.conversation import (
    async_setup_entry,
    NovaConversationEntity,
)


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant):
    """Test correct processing and registration of the core agent component entity."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "abc123_id"
    mock_entry.title = "Nova Voice Agent"
    mock_entry.options = {}

    async_add_entities = MagicMock()

    await async_setup_entry(hass, mock_entry, async_add_entities)
    async_add_entities.assert_called_once()
    entity = async_add_entities.call_args[0][0][0]
    assert isinstance(entity, NovaConversationEntity)


@pytest.mark.asyncio
async def test_entity_properties_and_features():
    """Test configuration entity capabilities mapping out features correctly."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_id"
    mock_entry.title = "Nova Entity"
    mock_entry.options = {CONF_LLM_HASS_API: "llm_assist_api"}

    entity = NovaConversationEntity(mock_entry)
    assert entity.supported_languages == "*"
    assert entity.supported_features == conversation.ConversationEntityFeature.CONTROL


@pytest.mark.asyncio
@patch("custom_components.nova_conversation.conversation.async_get_chat_session")
@patch(
    "custom_components.nova_conversation.conversation.conversation.async_get_chat_log"
)
async def test_async_process_text_stream_success(
    mock_get_chat_log, mock_get_session, hass: HomeAssistant
):
    """Test full pipeline processing handling incoming natural language generation tokens."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_123"
    mock_entry.options = {CONF_LLM_HASS_API: "assist", "prompt": "Test Prompt"}

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello human!"))]

    async def mock_stream_iter():
        yield mock_chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_iter())
    mock_entry.runtime_data = mock_client

    entity = NovaConversationEntity(mock_entry)
    entity.hass = hass

    mock_log = MagicMock()
    mock_log.conversation_id = "session_id"
    mock_log.continue_conversation = True
    mock_log.content = []

    def mock_add_delta_stream(agent_id, generator):
        async def inner_gen():
            async for delta in generator:
                pass
            mock_content = MagicMock()
            mock_content.role = "assistant"
            mock_content.content = "Hello human!"
            mock_content.tool_calls = None
            yield mock_content

        return inner_gen()

    mock_log.async_add_delta_content_stream = MagicMock(
        side_effect=mock_add_delta_stream
    )

    mock_get_session.return_value.__enter__.return_value = MagicMock()
    mock_get_chat_log.return_value.__enter__.return_value = mock_log

    user_input = conversation.ConversationInput(
        text="Hello",
        context=MagicMock(),
        conversation_id="session_id",
        language="en",
        agent_id="agent_nova",
        device_id=None,
        satellite_id=None,
    )

    result = await entity.async_process(user_input)
    assert isinstance(result, conversation.ConversationResult)
    assert result.response.speech["plain"]["speech"] == "Hello human!"


@pytest.mark.asyncio
@patch(
    "custom_components.nova_conversation.conversation.async_get_chat_session"
)
@patch(
    "custom_components.nova_conversation.conversation.conversation.async_get_chat_log"
)
async def test_async_process_tool_call(
    mock_get_chat_log, mock_get_session, hass: HomeAssistant
):
    """Test handling incoming tool execution chunk structures safely."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_123"
    mock_entry.options = {CONF_LLM_HASS_API: "assist"}

    mock_tc = MagicMock()
    mock_tc.index = 0
    mock_tc.id = "call_xyz"
    mock_tc.function.name = "turn_on_light"
    mock_tc.function.arguments = '{"entity_id":'

    mock_tc_append = MagicMock()
    mock_tc_append.index = 0
    mock_tc_append.id = "call_xyz"
    mock_tc_append.function = MagicMock(arguments='"light.kitchen"}')

    chunk_1 = MagicMock(
        choices=[MagicMock(delta=MagicMock(content=None, tool_calls=[mock_tc]))]
    )
    chunk_2 = MagicMock(
        choices=[MagicMock(delta=MagicMock(content=None, tool_calls=[mock_tc_append]))]
    )

    async def mock_stream_iter():
        yield chunk_1
        yield chunk_2

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_iter())
    mock_entry.runtime_data = mock_client

    entity = NovaConversationEntity(mock_entry)
    entity.hass = hass

    mock_log = MagicMock()
    mock_log.conversation_id = "session_id"
    mock_log.content = []
    mock_log.unresponded_tool_results = False

    def mock_add_delta_stream(agent_id, generator):
        async def inner_gen():
            async for delta in generator:
                pass

            mock_call = MagicMock()
            mock_call.id = "call_xyz"
            mock_call.tool_name = "turn_on_light"
            mock_call.tool_args = {"entity_id": "light.kitchen"}

            mock_content = MagicMock()
            mock_content.role = "assistant"
            mock_content.content = ""
            mock_content.tool_calls = [mock_call]
            yield mock_content

        return inner_gen()

    mock_log.async_add_delta_content_stream = MagicMock(
        side_effect=mock_add_delta_stream
    )

    mock_get_session.return_value.__enter__.return_value = MagicMock()
    mock_get_chat_log.return_value.__enter__.return_value = mock_log

    user_input = conversation.ConversationInput(
        text="Turn on kitchen light",
        context=MagicMock(),
        conversation_id="session_id",
        language="en",
        agent_id="agent_nova",
        device_id=None,
        satellite_id=None,
    )

    await entity.async_process(user_input)
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
@patch(
    "custom_components.nova_conversation.conversation.chat_session.async_get_chat_session"
)
@patch(
    "custom_components.nova_conversation.conversation.conversation.async_get_chat_log"
)
async def test_async_process_errors(
    mock_get_chat_log, mock_get_session, hass: HomeAssistant
):
    """Test full coverage error handling strategies for provider-side faults."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "entry_123"
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_entry.runtime_data = mock_client

    entity = NovaConversationEntity(mock_entry)
    entity.hass = hass

    mock_log = MagicMock()
    mock_log.content = []
    mock_get_session.return_value.__enter__.return_value = MagicMock()
    mock_get_chat_log.return_value.__enter__.return_value = mock_log

    user_input = conversation.ConversationInput(
        text="Crash me",
        context=MagicMock(),
        conversation_id="session_id",
        language="en",
        agent_id="agent_nova",
        device_id=None,
        satellite_id=None,
    )

    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.RateLimitError(
            message="Limited", response=MagicMock(status_code=429), body=None
        )
    )
    with pytest.raises(HomeAssistantError, match="API quota exceeded"):
        await entity.async_process(user_input)

    mock_client.chat.completions.create = AsyncMock(
        side_effect=openai.OpenAIError("Connection reset")
    )
    with pytest.raises(HomeAssistantError, match="Connection to provider failed"):
        await entity.async_process(user_input)
