"""Utility functions for formatting and converting Nova AI messages."""

import json
from collections.abc import Callable
from typing import Any, cast

from homeassistant.components import conversation
from homeassistant.helpers import llm

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_message_function_tool_call import Function
from openai.types.shared_params import FunctionDefinition
from voluptuous_openapi import convert


def format_ha_tool_for_openai(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> ChatCompletionToolParam:
    """
    Format Home Assistant tool specifications into standard OpenAI function parameters.
    """
    function_definition = FunctionDefinition(
        name=tool.name,
        parameters=convert(tool.parameters, custom_serializer=custom_serializer),
    )
    
    if tool.description:
        function_definition["description"] = tool.description
        
    return ChatCompletionToolParam(type="function", function=function_definition)


def convert_ha_content_to_openai_message(
    content: conversation.Content,
) -> ChatCompletionMessageParam:
    """
    Convert Home Assistant's native chat log content into the OpenAI API message format.
    """
    if content.role == "tool_result":
        assert type(content) is conversation.ToolResultContent
        return ChatCompletionToolMessageParam(
            role="tool",
            tool_call_id=content.tool_call_id,
            content=json.dumps(content.tool_result),
        )

    if content.role != "assistant" or not getattr(content, "tool_calls", None):
        return cast(
            ChatCompletionMessageParam,
            {"role": content.role, "content": content.content},
        )

    assert type(content) is conversation.AssistantContent
    
    # Map Home Assistant tool calls to OpenAI's expected structure
    formatted_tool_calls = [
        ChatCompletionMessageToolCallParam(
            id=call.id,
            function=Function(
                arguments=json.dumps(call.tool_args),
                name=call.tool_name,
            ),
            type="function",
        )
        for call in content.tool_calls
    ]

    return ChatCompletionAssistantMessageParam(
        role="assistant",
        content=content.content,
        tool_calls=formatted_tool_calls,
    )
