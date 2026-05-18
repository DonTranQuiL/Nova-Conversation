import json
from unittest.mock import MagicMock
from homeassistant.components import conversation
from homeassistant.helpers import llm

from custom_components.nova_conversation.utils import (
    format_ha_tool_for_openai,
    convert_ha_content_to_openai_message,
)


def test_format_ha_tool_for_openai():
    """Test formatting a Home Assistant tool to OpenAI's spec."""
    mock_tool = MagicMock(spec=llm.Tool)
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool description"
    mock_tool.parameters = MagicMock()

    result = format_ha_tool_for_openai(mock_tool, custom_serializer=None)

    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"
    assert result["function"]["description"] == "A test tool description"


def test_convert_ha_content_to_openai_message_tool_result():
    """Test mapping a tool result to OpenAI tool role format."""
    content = MagicMock(spec=conversation.ToolResultContent)
    content.role = "tool_result"
    content.tool_call_id = "call_123"
    content.tool_result = {"status": "success"}

    result = convert_ha_content_to_openai_message(content)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call_123"
    assert result["content"] == json.dumps({"status": "success"})


def test_convert_ha_content_to_openai_message_simple_text():
    """Test mapping normal user/assistant message text."""
    content = MagicMock(spec=conversation.Content)
    content.role = "user"
    content.content = "Hello world"

    # Ensure it doesn't look like an assistant tool call structure
    if hasattr(content, "tool_calls"):
        content.tool_calls = None

    result = convert_ha_content_to_openai_message(content)

    assert result["role"] == "user"
    assert result["content"] == "Hello world"


def test_convert_ha_content_to_openai_message_assistant_tool_calls():
    """Test mapping assistant tool calls to standard structure."""
    mock_call = MagicMock()
    mock_call.id = "call_abc"
    mock_call.tool_name = "turn_on"
    mock_call.tool_args = {"entity_id": "light.living_room"}

    content = MagicMock(spec=conversation.AssistantContent)
    content.role = "assistant"
    content.content = "Let me try that."
    content.tool_calls = [mock_call]

    result = convert_ha_content_to_openai_message(content)

    assert result["role"] == "assistant"
    assert result["content"] == "Let me try that."
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["id"] == "call_abc"
    assert result["tool_calls"][0]["function"]["name"] == "turn_on"
