import pytest
from homeassistant.setup import async_setup_component

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations automatically for all tests."""
    yield

@pytest.fixture(autouse=True)
async def setup_homeassistant_core(hass):
    """Set up the core Home Assistant component for voice assistants."""
    await async_setup_component(hass, "homeassistant", {})
