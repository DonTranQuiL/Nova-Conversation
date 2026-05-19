import pytest
from unittest.mock import MagicMock
from homeassistant.core import HomeAssistant

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations automatically for all tests."""
    yield

@pytest.fixture(autouse=True)
def mock_exposed_entities(hass):
    """Prevent KeyError for exposed_entities when conversation loads."""
    if isinstance(hass, HomeAssistant):
        # Silently satisfy the default conversation agent's entity registry
        hass.data["homeassistant.exposed_entities"] = MagicMock()
    yield
