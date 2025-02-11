import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.action_interactions.action_input import ActionInput
from plugins.genai_interactions.image.azure_dalle.azure_dalle import AzureDallePlugin


@pytest.fixture
def mock_config():
    return {
        "PLUGIN_NAME": "azure_dalle",  # Use the actual plugin name
        "AZURE_OPENAI_KEY": "fake_key",
        "AZURE_OPENAI_ENDPOINT": "https://fake_endpoint",
        "OPENAI_API_VERSION": "v1",
        "IMAGE_GENERATOR_MODEL_NAME": "dall-e-3",
        "INPUT_TOKEN_PRICE": 0.01,
        "OUTPUT_TOKEN_PRICE": 0.01,
    }

@pytest.fixture
def extended_mock_global_manager(mock_global_manager, mock_config):
    mock_global_manager.config_manager.config_model.PLUGINS.GENAI_INTERACTIONS.IMAGE = {
        "AZURE_DALLE": mock_config
    }
    return mock_global_manager

@pytest.fixture
def azure_dalle_plugin(extended_mock_global_manager):
    plugin = AzureDallePlugin(global_manager=extended_mock_global_manager)
    plugin.initialize()
    return plugin

def test_initialize(azure_dalle_plugin):
    assert azure_dalle_plugin.azure_openai_key == "fake_key"
    assert azure_dalle_plugin.azure_openai_endpoint == "https://fake_endpoint"
    assert azure_dalle_plugin.openai_api_version == "v1"
    assert azure_dalle_plugin.model_name == "dall-e-3"
    assert azure_dalle_plugin.plugin_name == "azure_dalle"  # Check the actual plugin name

@pytest.mark.asyncio
async def test_handle_action(azure_dalle_plugin):
    with patch.object(azure_dalle_plugin.client.images, 'generate', new_callable=AsyncMock) as mock_generate:
        # Mock the result of generate to return a MagicMock with model_dump_json returning the expected JSON string
        mock_result = MagicMock()
        mock_result.model_dump_json.return_value = json.dumps({
            'data': [{'url': 'http://fake_url.com/image.png'}]
        })
        mock_generate.return_value = mock_result

        action_input = ActionInput(action_name='generate_image', parameters={'prompt': 'test prompt', 'size': '256x256'})
        result = await azure_dalle_plugin.handle_action(action_input)
        assert result == 'http://fake_url.com/image.png'
        mock_generate.assert_called_once_with(
            model="dall-e-3",
            prompt="test prompt",
            n=1,
            size="256x256"
        )
