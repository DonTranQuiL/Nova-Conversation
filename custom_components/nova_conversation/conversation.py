"""Core conversation engine for Nova Conversation."""

import json
from typing import Literal

import openai
from homeassistant.components import assist_pipeline, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LLM_HASS_API, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, intent, llm
from homeassistant.helpers.chat_session import async_get_chat_session
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NovaConfigEntry
from .const import (
    CONF_CHAT_MODEL,
    CONF_ENABLE_TOOLS,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DOMAIN,
    LOGGER,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_MAX_TOKENS,
    RECOMMENDED_TEMPERATURE,
    RECOMMENDED_TOP_P,
)
from .utils import convert_ha_content_to_openai_message, format_ha_tool_for_openai

MAX_TOOL_RETRIES = 99


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NovaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the Nova conversation agent entity."""
    async_add_entities([NovaConversationEntity(config_entry)])


class NovaConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    """The central conversation agent processing LLM requests and tool execution."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: NovaConfigEntry) -> None:
        """Initialize the agent and configure device registry identity."""
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Nova AI",
            model="Nova High-Speed Agent",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

        # Enable tool-calling UI features if configured
        if self.entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return the supported languages for this agent."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """Hook into the pipeline engine when added to Home Assistant."""
        await super().async_added_to_hass()

        if hasattr(assist_pipeline, "async_migrate_engine"):
            assist_pipeline.async_migrate_engine(
                self.hass, "conversation", self.entry.entry_id, self.entity_id
            )

        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the agent registry upon removal."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process incoming natural language requests."""
        with (
            async_get_chat_session(
                self.hass, user_input.conversation_id
            ) as session,
            conversation.async_get_chat_log(self.hass, session, user_input) as chat_log,
        ):
            return await self._execute_llm_stream(user_input, chat_log)

    async def _execute_llm_stream(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Handle the core streaming logic and recursive tool execution loop."""
        assert user_input.agent_id
        config_options = self.entry.options
        api_client = self.entry.runtime_data

        # 1. Prepare LLM Context
        try:
            llm_context = llm.LLMContext(
                platform=DOMAIN,
                context=user_input.context,
                language=user_input.language,
                assistant=conversation.DOMAIN,
                device_id=getattr(user_input, "device_id", None),
            )

            if config_options.get(CONF_LLM_HASS_API):
                chat_log.llm_api = await llm.async_get_api(
                    self.hass, config_options[CONF_LLM_HASS_API], llm_context
                )
            if config_options.get(CONF_PROMPT):
                chat_log.system_prompt = config_options[CONF_PROMPT]
        except Exception as err:
            LOGGER.error("Nova Engine: Failed to build LLM context: %s", err)

        # 2. Format Tools & Messages
        tools_enabled = config_options.get(CONF_ENABLE_TOOLS, True)
        active_tools = None

        if tools_enabled and chat_log.llm_api:
            active_tools = [
                format_ha_tool_for_openai(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        conversation_history = [
            convert_ha_content_to_openai_message(content)
            for content in chat_log.content
        ]

        text_response_buffer = ""

        # 3. Tool Execution Loop
        for iteration in range(MAX_TOOL_RETRIES):
            payload = {
                "model": config_options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL),
                "messages": conversation_history,
                "max_tokens": config_options.get(
                    CONF_MAX_TOKENS, RECOMMENDED_MAX_TOKENS
                ),
                "top_p": config_options.get(CONF_TOP_P, RECOMMENDED_TOP_P),
                "temperature": config_options.get(
                    CONF_TEMPERATURE, RECOMMENDED_TEMPERATURE
                ),
                "user": chat_log.conversation_id,
                "stream": True,
            }
            if active_tools:
                payload["tools"] = active_tools

            try:
                stream_response = await api_client.chat.completions.create(**payload)
            except openai.RateLimitError as err:
                raise HomeAssistantError(
                    "Nova: API quota exceeded or rate limited."
                ) from err
            except openai.OpenAIError as err:
                raise HomeAssistantError(
                    f"Nova: Connection to provider failed: {err}"
                ) from err

            active_tool_calls = {}

            async def _stream_generator():
                """Process chunks as they arrive from the API."""
                nonlocal text_response_buffer, active_tool_calls
                try:
                    async for chunk in stream_response:
                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta

                        # Handle text tokens
                        if delta.content:
                            text_response_buffer += delta.content
                            yield conversation.AssistantContentDeltaDict(
                                role="assistant", content=delta.content
                            )

                        # Handle tool call fragments
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.index
                                if idx not in active_tool_calls:
                                    active_tool_calls[idx] = {
                                        "id": tc.id,
                                        "name": tc.function.name if tc.function else "",
                                        "arguments": tc.function.arguments
                                        if tc.function
                                        else "",
                                    }
                                else:
                                    if tc.function and tc.function.arguments:
                                        active_tool_calls[idx]["arguments"] += (
                                            tc.function.arguments
                                        )
                except openai.APIError as stream_err:
                    LOGGER.error("Nova: Stream interrupted: %s", stream_err)

                # Finalize and dispatch parsed tool calls
                if active_tool_calls:
                    finalized_calls = []
                    for idx, call_data in active_tool_calls.items():
                        try:
                            finalized_calls.append(
                                llm.ToolInput(
                                    id=call_data["id"],
                                    tool_name=call_data["name"],
                                    tool_args=json.loads(call_data["arguments"]),
                                )
                            )
                        except json.JSONDecodeError:
                            LOGGER.error(
                                "Nova: Model provided invalid JSON for tool execution."
                            )

                    if finalized_calls:
                        yield conversation.AssistantContentDeltaDict(
                            role="assistant", tool_calls=finalized_calls
                        )

            # Process the stream natively via Home Assistant
            new_log_entries = [
                content
                async for content in chat_log.async_add_delta_content_stream(
                    user_input.agent_id, _stream_generator()
                )
            ]

            # Append new data to history for the next potential tool iteration
            conversation_history.extend(
                [convert_ha_content_to_openai_message(c) for c in new_log_entries]
            )

            # Break loop if the AI is finished invoking tools
            if not getattr(chat_log, "unresponded_tool_results", False):
                break

            if iteration == MAX_TOOL_RETRIES - 1:
                LOGGER.warning(
                    "Nova: Emergency circuit breaker hit. Maximum tool iterations reached."
                )

        # 4. Finalize Intent
        intent_response = intent.IntentResponse(language=user_input.language)
        if text_response_buffer.strip():
            intent_response.async_set_speech(text_response_buffer.strip())

        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=chat_log.conversation_id,
            continue_conversation=chat_log.continue_conversation,
        )

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Reload the integration if UI options change."""
        await hass.config_entries.async_reload(entry.entry_id)
