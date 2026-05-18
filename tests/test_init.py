import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.nova_conversation import async_setup_entry
from custom_components.nova_conversation.const import CONF_BASE_URL


class FakeOpenAIError(Exception):
    pass


@pytest.mark.asyncio
async def test_setup_entry_auth_error():
    entry = MagicMock()
    entry.data = {
        "api_key": "bad",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    # create client
    client = MagicMock()
    client.platform_headers = True

    async def raise_auth(*args, **kwargs):
        raise FakeOpenAIError("unauthorized")

    client.with_options.return_value.models.list = raise_auth

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is False
