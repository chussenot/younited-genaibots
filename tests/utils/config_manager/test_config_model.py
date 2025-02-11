import pytest
from pydantic import ValidationError

from utils.config_manager.config_model import (
    ActionInteractions,
    Azure,
    Backend,
    BotConfig,
    ConfigModel,
    Environment,
    File,
    GenaiInteractions,
    Logging,
    Plugin,
    Plugins,
    SensitiveData,
    UserInteractions,
    UserInteractionsBehaviors,
    Utils,
)


def test_bot_config():
    # Test valid BotConfig
    valid_data = {
        "CORE_PROMPT": "core_prompt",
        "MAIN_PROMPT": "main_prompt",
        "PROMPTS_FOLDER": "prompts_folder",
        "SUBPROMPTS_FOLDER": "subprompts_folder",
        "FEEDBACK_GENERAL_BEHAVIOR": "feedback_behavior",
        "REQUIRE_MENTION_NEW_MESSAGE": True,
        "REQUIRE_MENTION_THREAD_MESSAGE": True,
        "LOG_DEBUG_LEVEL": "DEBUG",
        "SHOW_COST_IN_THREAD": True,
        "ACKNOWLEDGE_NONPROCESSED_MESSAGE": True,
        "GET_URL_CONTENT": True,
        "ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME": "default_action_plugin",
        "INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME": "default_processing_plugin",
        "USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME": "default_instant_messaging_plugin",
        "GENAI_TEXT_DEFAULT_PLUGIN_NAME": "default_genai_text_plugin",
        "GENAI_IMAGE_DEFAULT_PLUGIN_NAME": "default_genai_image_plugin",
        "GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME": "default_genai_vector_search_plugin",
        "LLM_CONVERSION_FORMAT": "conversion_format",
        "BREAK_KEYWORD": "break",
        "START_KEYWORD": "start"
    }
    bot_config = BotConfig(**valid_data)
    assert bot_config.CORE_PROMPT == "core_prompt"

    # Test invalid BotConfig (missing required field)
    invalid_data = valid_data.copy()
    invalid_data.pop("CORE_PROMPT")
    with pytest.raises(ValidationError):
        BotConfig(**invalid_data)

def test_logging():
    # Test valid Logging
    file_data = {"PLUGIN_NAME": "file_plugin", "LEVEL": "DEBUG", "FILE_PATH": "path/to/log"}
    azure_data = {"PLUGIN_NAME": "azure_plugin", "APPLICATIONINSIGHTS_CONNECTION_STRING": "connection_string"}
    logging = Logging(FILE=File(**file_data), AZURE=Azure(**azure_data))
    assert logging.FILE.PLUGIN_NAME == "file_plugin"
    assert logging.AZURE.PLUGIN_NAME == "azure_plugin"

    # Test invalid Logging (invalid nested model)
    invalid_file_data = file_data.copy()
    invalid_file_data["LEVEL"] = 123  # Invalid type for LEVEL
    with pytest.raises(ValidationError):
        Logging(FILE=File(**invalid_file_data))

def test_utils():
    # Test valid Utils
    file_data = {"PLUGIN_NAME": "file_plugin", "LEVEL": "DEBUG", "FILE_PATH": "path/to/log"}
    logging = Logging(FILE=File(**file_data))
    utils = Utils(LOGGING=logging)
    assert utils.LOGGING.FILE.LEVEL == "DEBUG"

def test_plugins():
    # Test valid Plugins
    plugin_data = {"PLUGIN_NAME": "plugin_name"}
    action_interactions = ActionInteractions(DEFAULT={"default_plugin": Plugin(**plugin_data)})
    backend = Backend(INTERNAL_DATA_PROCESSING={"key": "value"})
    user_interactions = UserInteractions(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})
    genai_interactions = GenaiInteractions(TEXT={"key": "value"}, IMAGE={"key": "value"}, VECTOR_SEARCH={"key": "value"})
    user_interactions_behaviors = UserInteractionsBehaviors(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})

    plugins = Plugins(
        ACTION_INTERACTIONS=action_interactions,
        BACKEND=backend,
        USER_INTERACTIONS=user_interactions,
        GENAI_INTERACTIONS=genai_interactions,
        USER_INTERACTIONS_BEHAVIORS=user_interactions_behaviors
    )
    assert plugins.ACTION_INTERACTIONS.DEFAULT["default_plugin"].PLUGIN_NAME == "plugin_name"

def test_config_model():
    # Test valid ConfigModel
    bot_config_data = {
        "CORE_PROMPT": "core_prompt",
        "MAIN_PROMPT": "main_prompt",
        "PROMPTS_FOLDER": "prompts_folder",
        "SUBPROMPTS_FOLDER": "subprompts_folder",
        "FEEDBACK_GENERAL_BEHAVIOR": "feedback_behavior",
        "REQUIRE_MENTION_NEW_MESSAGE": True,
        "REQUIRE_MENTION_THREAD_MESSAGE": True,
        "LOG_DEBUG_LEVEL": "DEBUG",
        "SHOW_COST_IN_THREAD": True,
        "ACKNOWLEDGE_NONPROCESSED_MESSAGE": True,
        "GET_URL_CONTENT": True,
        "ACTION_INTERACTIONS_DEFAULT_PLUGIN_NAME": "default_action_plugin",
        "INTERNAL_DATA_PROCESSING_DEFAULT_PLUGIN_NAME": "default_processing_plugin",
        "USER_INTERACTIONS_INSTANT_MESSAGING_BEHAVIOR_DEFAULT_PLUGIN_NAME": "default_instant_messaging_plugin",
        "GENAI_TEXT_DEFAULT_PLUGIN_NAME": "default_genai_text_plugin",
        "GENAI_IMAGE_DEFAULT_PLUGIN_NAME": "default_genai_image_plugin",
        "GENAI_VECTOR_SEARCH_DEFAULT_PLUGIN_NAME": "default_genai_vector_search_plugin",
        "LLM_CONVERSION_FORMAT": "conversion_format",
        "BREAK_KEYWORD": "break",
        "START_KEYWORD": "start"
    }
    file_data = {"PLUGIN_NAME": "file_plugin", "LEVEL": "DEBUG", "FILE_PATH": "path/to/log"}
    logging = Logging(FILE=File(**file_data))
    utils = Utils(LOGGING=logging)

    plugin_data = {"PLUGIN_NAME": "plugin_name"}
    action_interactions = ActionInteractions(DEFAULT={"default_plugin": Plugin(**plugin_data)})
    backend = Backend(INTERNAL_DATA_PROCESSING={"key": "value"})
    user_interactions = UserInteractions(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})
    genai_interactions = GenaiInteractions(TEXT={"key": "value"}, IMAGE={"key": "value"}, VECTOR_SEARCH={"key": "value"})
    user_interactions_behaviors = UserInteractionsBehaviors(INSTANT_MESSAGING={"key": "value"}, CUSTOM_API={"key": "value"})

    plugins = Plugins(
        ACTION_INTERACTIONS=action_interactions,
        BACKEND=backend,
        USER_INTERACTIONS=user_interactions,
        GENAI_INTERACTIONS=genai_interactions,
        USER_INTERACTIONS_BEHAVIORS=user_interactions_behaviors
    )

    config_model = ConfigModel(BOT_CONFIG=BotConfig(**bot_config_data), UTILS=utils, PLUGINS=plugins)
    assert config_model.BOT_CONFIG.CORE_PROMPT == "core_prompt"
    assert config_model.UTILS.LOGGING.FILE.PLUGIN_NAME == "file_plugin"
    assert config_model.PLUGINS.ACTION_INTERACTIONS.DEFAULT["default_plugin"].PLUGIN_NAME == "plugin_name"

def test_sensitive_data():
    # Test valid SensitiveData
    environment_data = {"PLUGIN_NAME": "env_plugin"}
    sensitive_data = SensitiveData(ENVIRONMENT=Environment(**environment_data))
    assert sensitive_data.ENVIRONMENT.PLUGIN_NAME == "env_plugin"

