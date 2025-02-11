from unittest.mock import AsyncMock, MagicMock

import pytest

from utils.prompt_manager.prompt_manager import PromptManager


@pytest.fixture
def mock_global_manager_with_dispatcher(mock_global_manager):
    mock_global_manager.backend_internal_data_processing_dispatcher = AsyncMock()
    return mock_global_manager


@pytest.mark.asyncio
async def test_initialize(mock_global_manager_with_dispatcher):
    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Mock the methods that will be called during initialization
    prompt_manager.get_core_prompt = AsyncMock(return_value='core_prompt_content')
    prompt_manager.get_main_prompt = AsyncMock(return_value='main_prompt_content')

    # Call the initialize method
    await prompt_manager.initialize()

    # Check if the prompts were set correctly
    assert prompt_manager.core_prompt == 'core_prompt_content'
    assert prompt_manager.main_prompt == 'main_prompt_content'
    assert hasattr(prompt_manager, 'prompt_container')


@pytest.mark.asyncio
async def test_get_sub_prompt(mock_global_manager_with_dispatcher):
    # Mock the config manager to return a specific folder name
    mock_global_manager_with_dispatcher.config_manager.get_config = MagicMock(return_value='subprompts_folder')
    # Mock the backend dispatcher to return specific content
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value='sub_prompt_content')

    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)
    message_type = 'test_message'

    # Call the get_sub_prompt method
    sub_prompt = await prompt_manager.get_sub_prompt(message_type)

    # Check if the sub prompt was retrieved correctly
    assert sub_prompt == 'sub_prompt_content'
    mock_global_manager_with_dispatcher.config_manager.get_config.assert_called_with(['BOT_CONFIG', 'SUBPROMPTS_FOLDER'])
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with('subprompts_folder', f'{message_type}.txt')


@pytest.mark.asyncio
async def test_get_core_prompt(mock_global_manager_with_dispatcher):
    # Mock the config manager to return a specific file name
    mock_global_manager_with_dispatcher.config_manager.get_config = MagicMock(return_value='core_prompt_file')
    # Mock the backend dispatcher to return specific content
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value='core_prompt_content')

    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Call the initialize method to set prompt_container
    await prompt_manager.initialize()

    # Call the get_core_prompt method
    core_prompt = await prompt_manager.get_core_prompt()

    # Check if the core prompt was retrieved correctly
    assert core_prompt == 'core_prompt_content'
    mock_global_manager_with_dispatcher.config_manager.get_config.assert_called_with(['BOT_CONFIG', 'CORE_PROMPT'])
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with(prompt_manager.prompt_container, 'core_prompt_file.txt')


@pytest.mark.asyncio
async def test_get_main_prompt(mock_global_manager_with_dispatcher):
    # Mock the config manager to return a specific file name
    mock_global_manager_with_dispatcher.config_manager.get_config = MagicMock(return_value='main_prompt_file')
    # Mock the backend dispatcher to return specific content
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value='main_prompt_content')

    prompt_manager = PromptManager(mock_global_manager_with_dispatcher)

    # Call the initialize method to set prompt_container
    await prompt_manager.initialize()

    # Call the get_main_prompt method
    main_prompt = await prompt_manager.get_main_prompt()

    # Check if the main prompt was retrieved correctly
    assert main_prompt == 'main_prompt_content'
    mock_global_manager_with_dispatcher.config_manager.get_config.assert_called_with(['BOT_CONFIG', 'MAIN_PROMPT'])
    mock_global_manager_with_dispatcher.backend_internal_data_processing_dispatcher.read_data_content.assert_called_with(prompt_manager.prompt_container, 'main_prompt_file.txt')
