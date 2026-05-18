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

    # create client normally
    client = MagicMock()
    client.platform_headers = True

    # IMPORTANT: patch the FINAL async call directly
    async def fake_list(*args, **kwargs):
        raise Exception("unauthorized")

    with patch("openai.AsyncOpenAI", return_value=client), \
         patch.object(client.with_options.return_value.models, "list", new=fake_list):

        result = await async_setup_entry(hass, entry)

    assert result is False
