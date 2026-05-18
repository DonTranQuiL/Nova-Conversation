import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from custom_components.nova_conversation import async_setup_entry
from custom_components.nova_conversation.const import CONF_BASE_URL


@pytest.mark.asyncio
async def test_setup_entry_auth_error():
    entry = MagicMock()
    entry.data = {
        "api_key": "bad",
        CONF_BASE_URL: "https://api.openai.com/v1",
    }

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(return_value=True)

    # fake models.list that will actually be used
    async def fake_list(*args, **kwargs):
        raise Exception("unauthorized")

    fake_models = MagicMock()
    fake_models.list = fake_list

    fake_client_chain = MagicMock()
    fake_client_chain.models = fake_models

    # IMPORTANT: with_options must return our controlled chain
    client = MagicMock()
    client.platform_headers = True
    client.with_options.return_value = fake_client_chain

    with patch("openai.AsyncOpenAI", return_value=client):
        result = await async_setup_entry(hass, entry)

    assert result is False
