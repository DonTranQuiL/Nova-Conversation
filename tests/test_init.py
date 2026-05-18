import voluptuous as vol

def test_format_ha_tool_for_openai():
    """Test formatting a Home Assistant tool to OpenAI's spec."""
    mock_tool = MagicMock(spec=llm.Tool)
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool description"
    # Pass a real blank Voluptuous Schema instead of a MagicMock
    mock_tool.parameters = vol.Schema({})

    result = format_ha_tool_for_openai(mock_tool, custom_serializer=None)

    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"
    assert result["function"]["description"] == "A test tool description"
