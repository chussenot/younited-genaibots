import hashlib
import hmac
import time
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import Request
from pydantic import BaseModel
from starlette.responses import Response

from core.user_interactions.incoming_notification_data_base import (
    IncomingNotificationDataBase,
)
from core.user_interactions.message_type import MessageType
from plugins.user_interactions.instant_messaging.slack.slack import (
    SlackPlugin,
)
import copy
import json

class SlackConfig(BaseModel):
    PLUGIN_NAME: str
    ROUTE_PATH: str
    ROUTE_METHODS: List[str]
    PLUGIN_DIRECTORY: str
    SLACK_MESSAGE_TTL: int
    SLACK_SIGNING_SECRET: str
    SLACK_BOT_TOKEN: str
    SLACK_BOT_USER_TOKEN: str
    SLACK_BOT_USER_ID: str
    SLACK_API_URL: str
    SLACK_AUTHORIZED_CHANNELS: str
    SLACK_FEEDBACK_CHANNEL: str
    SLACK_FEEDBACK_BOT_ID: str
    MAX_MESSAGE_LENGTH: int
    INTERNAL_CHANNEL: str
    WORKSPACE_NAME: str
    BEHAVIOR_PLUGIN_NAME: str

@pytest.fixture
def slack_config_data():
    return {
        "PLUGIN_NAME": "slack",
        "ROUTE_PATH": "/slack/events",
        "ROUTE_METHODS": ["POST"],
        "PLUGIN_DIRECTORY": "/plugins/user_interactions/instant_messaging/slack",
        "SLACK_MESSAGE_TTL": 60,
        "SLACK_SIGNING_SECRET": "signing_secret",
        "SLACK_BOT_TOKEN": "xoxb-bot-token",
        "SLACK_BOT_USER_TOKEN": "xoxp-user-token",
        "SLACK_BOT_USER_ID": "bot_user_id",
        "SLACK_API_URL": "https://slack.com/api",
        "SLACK_AUTHORIZED_CHANNELS": "C12345678,C23456789",
        "SLACK_FEEDBACK_CHANNEL": "C34567890",
        "SLACK_FEEDBACK_BOT_ID": "feedback_bot_id",
        "MAX_MESSAGE_LENGTH": 40000,
        "INTERNAL_CHANNEL": "C45678901",
        "WORKSPACE_NAME": "workspace_name",
        "BEHAVIOR_PLUGIN_NAME": "behavior_plugin"
    }

@pytest.fixture
def slack_plugin(mock_global_manager, slack_config_data):
    mock_global_manager.config_manager.config_model.PLUGINS.USER_INTERACTIONS.INSTANT_MESSAGING = {
        "SLACK": slack_config_data
    }
    plugin = SlackPlugin(mock_global_manager)
    plugin.slack_signing_secret = slack_config_data["SLACK_SIGNING_SECRET"]
    plugin.SLACK_MESSAGE_TTL = slack_config_data["SLACK_MESSAGE_TTL"]
    plugin.bot_user_id = slack_config_data["SLACK_BOT_USER_ID"]
    plugin.SLACK_AUTHORIZED_CHANNELS = slack_config_data["SLACK_AUTHORIZED_CHANNELS"].split(",")
    plugin.SLACK_FEEDBACK_CHANNEL = slack_config_data["SLACK_FEEDBACK_CHANNEL"]
    plugin.FEEDBACK_BOT_USER_ID = slack_config_data["SLACK_FEEDBACK_BOT_ID"]
    plugin.slack_bot_token = slack_config_data["SLACK_BOT_TOKEN"]
    plugin.MAX_MESSAGE_LENGTH = slack_config_data["MAX_MESSAGE_LENGTH"]
    plugin.backend_internal_data_processing_dispatcher = AsyncMock()
    plugin.slack_input_handler = AsyncMock()
    plugin.slack_output_handler = AsyncMock()
    return plugin

@pytest.mark.asyncio
async def test_handle_request(slack_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=b'{"user_id": "123", "channel_id": "456"}')
    request.headers = {'content-type': 'application/json'}
    request.url.path = "/slack/events"

    response = await slack_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_validate_request(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "message", "user": "U123456", "channel": "C12345678", "ts": "1234567890.123456"}}'

    # Calculer la signature correcte pour le test
    sig_basestring = f'v0:{headers["X-Slack-Request-Timestamp"]}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers['X-Slack-Signature'] = correct_signature

    # Mock is_message_too_old pour retourner False
    slack_plugin.is_message_too_old = AsyncMock(return_value=False)
    slack_plugin.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)

    is_valid = await slack_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is True

@pytest.mark.asyncio
async def test_validate_request_from_bot_user(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": slack_plugin.bot_user_id,  # User ID is the bot's user ID
            "channel": "C12345678",
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "message", "user": "' + slack_plugin.bot_user_id + '", "channel": "C12345678", "ts": "1234567890.123456"}}'

    sig_basestring = f'v0:{headers["X-Slack-Request-Timestamp"]}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers['X-Slack-Signature'] = correct_signature

    slack_plugin.is_message_too_old = AsyncMock(return_value=False)

    is_valid = await slack_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is False

@pytest.mark.asyncio
async def test_validate_request_from_unauthorized_user_in_feedback_channel(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U999999",  # Unauthorized user
            "channel": slack_plugin.SLACK_FEEDBACK_CHANNEL,
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "message", "user": "U999999", "channel": "' + slack_plugin.SLACK_FEEDBACK_CHANNEL + '", "ts": "1234567890.123456"}}'

    sig_basestring = f'v0:{headers["X-Slack-Request-Timestamp"]}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers['X-Slack-Signature'] = correct_signature

    slack_plugin.is_message_too_old = AsyncMock(return_value=False)

    is_valid = await slack_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is False

@pytest.mark.asyncio
async def test_validate_request_from_unauthorized_user_in_feedback_channel(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U999999",  # Unauthorized user
            "channel": slack_plugin.SLACK_FEEDBACK_CHANNEL,
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "message", "user": "U999999", "channel": "' + slack_plugin.SLACK_FEEDBACK_CHANNEL + '", "ts": "1234567890.123456"}}'

    sig_basestring = f'v0:{headers["X-Slack-Request-Timestamp"]}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers['X-Slack-Signature'] = correct_signature

    slack_plugin.is_message_too_old = AsyncMock(return_value=False)

    is_valid = await slack_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is False

@pytest.mark.asyncio
async def test_validate_request_with_invalid_event_type(slack_plugin):
    event_data = {
        "event": {
            "type": "reaction_added",  # Invalid event type for processing
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "reaction_added", "user": "U123456", "channel": "C12345678", "ts": "1234567890.123456"}}'

    sig_basestring = f'v0:{headers["X-Slack-Request-Timestamp"]}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers['X-Slack-Signature'] = correct_signature

    slack_plugin.is_message_too_old = AsyncMock(return_value=False)

    is_valid = await slack_plugin.validate_request(event_data, headers, raw_body_str)

    assert is_valid is False

@pytest.mark.asyncio
async def test_process_interaction(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    with patch.object(slack_plugin.global_manager.user_interactions_behavior_dispatcher, 'process_interaction') as mock_process:
        await slack_plugin.process_interaction(event_data)
        mock_process.assert_called_once_with(
            event_data=event_data,
            event_origin=slack_plugin.plugin_name,
            plugin_name=slack_plugin.slack_config.BEHAVIOR_PLUGIN_NAME
        )
@pytest.mark.asyncio
async def test_validate_headers(slack_plugin):
    valid_headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    assert slack_plugin._validate_headers(valid_headers) is True

    invalid_headers = {
        'X-Slack-Request-Timestamp': '1531420618'
    }
    assert slack_plugin._validate_headers(invalid_headers) is False

@pytest.mark.asyncio
async def test_validate_signature(slack_plugin):
    timestamp = '1531420618'
    raw_body_str = '{"event": {"type": "message", "user": "U123456", "channel": "C12345678", "ts": "1234567890.123456"}}'
    
    # Set the root_message_timestamp
    slack_plugin.root_message_timestamp = timestamp

    # Calculer la signature correcte
    sig_basestring = f'v0:{timestamp}:{raw_body_str}'
    correct_signature = 'v0=' + hmac.new(
        slack_plugin.slack_signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'X-Slack-Request-Timestamp': timestamp,
        'X-Slack-Signature': correct_signature
    }

    assert slack_plugin._validate_signature(headers, raw_body_str) is True

    # Test with incorrect signature
    headers['X-Slack-Signature'] = 'v0=incorrect_signature'
    assert slack_plugin._validate_signature(headers, raw_body_str) is False

    # Reset root_message_timestamp to avoid affecting other tests
    slack_plugin.root_message_timestamp = None

@pytest.mark.asyncio
async def test_validate_event_data(slack_plugin):
    valid_event = {
        "type": "message",
        "user": "U123456",
        "channel": "C12345678",
        "ts": "1234567890.123456"
    }
    assert slack_plugin._validate_event_data("message", "1234567890.123456", "C12345678", "U123456", valid_event) is True

    # Test with bot user
    bot_event = valid_event.copy()
    bot_event["user"] = slack_plugin.bot_user_id
    assert slack_plugin._validate_event_data("message", "1234567890.123456", "C12345678", slack_plugin.bot_user_id, bot_event) is False

    # Test with unauthorized channel
    unauthorized_event = valid_event.copy()
    unauthorized_event["channel"] = "UNAUTHORIZED"
    assert slack_plugin._validate_event_data("message", "1234567890.123456", "UNAUTHORIZED", "U123456", unauthorized_event) is False

    # Test with reaction_added event type
    reaction_event = valid_event.copy()
    assert slack_plugin._validate_event_data("reaction_added", "1234567890.123456", "C12345678", "U123456", reaction_event) is False

@pytest.mark.asyncio
async def test_validate_processing_status(slack_plugin):
    slack_plugin.is_message_too_old = AsyncMock(return_value=False)
    slack_plugin.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value=None)

    assert await slack_plugin._validate_processing_status("C12345678", "1234567890.123456") is True

    # Test with old message
    slack_plugin.is_message_too_old = AsyncMock(return_value=True)
    assert await slack_plugin._validate_processing_status("C12345678", "1234567890.123456") is False

    # Test with already processing message
    slack_plugin.is_message_too_old = AsyncMock(return_value=False)
    slack_plugin.backend_internal_data_processing_dispatcher.read_data_content = AsyncMock(return_value="Some content")
    assert await slack_plugin._validate_processing_status("C12345678", "1234567890.123456") is False

@pytest.mark.asyncio
async def test_process_event_data(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=abcd1234'
    }
    raw_body_str = '{"event": {"type": "message", "user": "U123456", "channel": "C12345678", "ts": "1234567890.123456"}}'

    with patch.object(slack_plugin, 'validate_request', return_value=True), \
         patch.object(slack_plugin, 'handle_valid_request') as mock_handle:
        await slack_plugin.process_event_data(event_data, headers, raw_body_str)
        mock_handle.assert_called_once_with(event_data)

@pytest.mark.asyncio
async def test_handle_valid_request(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    with patch.object(slack_plugin, 'process_event_by_type') as mock_process:
        await slack_plugin.handle_valid_request(event_data)
        mock_process.assert_called_once_with(event_data, "message", None)

# Ajoutez ce nouveau test pour process_event_by_type
@pytest.mark.asyncio
async def test_process_event_by_type(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    
    # Test for normal message
    with patch.object(slack_plugin, 'process_interaction') as mock_process:
        await slack_plugin.process_event_by_type(event_data, "message", None)
        mock_process.assert_called_once_with(event_data)
    
    # Test for file_share
    event_data["event"]["subtype"] = "file_share"
    with patch.object(slack_plugin, 'process_interaction') as mock_process:
        await slack_plugin.process_event_by_type(event_data, "message", "file_share")
        mock_process.assert_called_once_with(event_data)
    
    # Test for ignored subtype
    event_data["event"]["subtype"] = "channel_join"
    with patch.object(slack_plugin.logger, 'info') as mock_logger:
        await slack_plugin.process_event_by_type(event_data, "message", "channel_join")
        mock_logger.assert_called_once_with("ignoring channel event subtype: channel_join")
    
    # Test for non-message event type
    with patch.object(slack_plugin.logger, 'debug') as mock_logger:
        await slack_plugin.process_event_by_type(event_data, "reaction_added", None)
        mock_logger.assert_called_once_with("Event type is not 'message', it's 'reaction_added'. Skipping processing.")

async def test_send_message(slack_plugin, requests_mock):
    requests_mock.post('https://slack.com/api/chat.postMessage', json={'ok': True})

    message = "Hello, world!"
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    message_type = MessageType.TEXT

    # Test regular message
    response = await slack_plugin.send_message(message, event, message_type)
    assert response.status_code == 200
    assert response.json() == {'ok': True}

    # Test with show_ref=True
    slack_plugin.add_reference_message = AsyncMock(return_value=True)
    response = await slack_plugin.send_message(message, event, message_type, show_ref=True)
    assert slack_plugin.add_reference_message.called
    assert response.status_code == 200

    # Test internal message
    slack_plugin.handle_internal_message = AsyncMock(return_value=("1234567890.123457", "C87654321"))
    response = await slack_plugin.send_message(message, event, message_type, is_internal=True)
    assert slack_plugin.handle_internal_message.called
    assert response.status_code == 200

    # Test with invalid message type
    with pytest.raises(ValueError):
        await slack_plugin.send_message(message, event, "INVALID_TYPE")

@pytest.mark.asyncio
async def test_add_reaction(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    channel_id = "C12345678"
    timestamp = "1234567890.123456"
    reaction_name = "like"

    # Mock the post_notification method
    slack_plugin.post_notification = AsyncMock()
    slack_plugin.slack_output_handler.add_reaction = AsyncMock()  # Utilisation d'AsyncMock pour gérer les appels await

    await slack_plugin.add_reaction(event, channel_id, timestamp, reaction_name)

    assert slack_plugin.slack_output_handler.add_reaction.called

@pytest.mark.asyncio
async def test_remove_reaction(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    channel_id = "C12345678"
    timestamp = "1234567890.123456"
    reaction_name = "like"

    # Mock the post_notification method
    slack_plugin.post_notification = AsyncMock()
    slack_plugin.slack_output_handler.remove_reaction = AsyncMock()  # Utilisation d'AsyncMock pour gérer les appels await

    await slack_plugin.remove_reaction(event, channel_id, timestamp, reaction_name)

    assert slack_plugin.slack_output_handler.remove_reaction.called

def test_initialize(slack_plugin):
    slack_plugin.initialize()
    assert slack_plugin.slack_input_handler is not None
    assert slack_plugin.slack_output_handler is not None
    assert slack_plugin.SLACK_MESSAGE_TTL == slack_plugin.slack_config.SLACK_MESSAGE_TTL
    assert slack_plugin.SLACK_AUTHORIZED_CHANNELS == slack_plugin.slack_config.SLACK_AUTHORIZED_CHANNELS.split(",")
    assert slack_plugin.SLACK_FEEDBACK_CHANNEL == slack_plugin.slack_config.SLACK_FEEDBACK_CHANNEL
    assert slack_plugin.slack_bot_token == slack_plugin.slack_config.SLACK_BOT_TOKEN
    assert slack_plugin.slack_signing_secret == slack_plugin.slack_config.SLACK_SIGNING_SECRET
    assert slack_plugin._route_path == slack_plugin.slack_config.ROUTE_PATH
    assert slack_plugin._route_methods == slack_plugin.slack_config.ROUTE_METHODS
    assert slack_plugin.bot_user_id == slack_plugin.slack_config.SLACK_BOT_USER_ID
    assert slack_plugin.MAX_MESSAGE_LENGTH == slack_plugin.slack_config.MAX_MESSAGE_LENGTH
    assert slack_plugin.INTERNAL_CHANNEL == slack_plugin.slack_config.INTERNAL_CHANNEL
    assert slack_plugin.WORKSPACE_NAME == slack_plugin.slack_config.WORKSPACE_NAME
    assert slack_plugin.plugin_name == slack_plugin.slack_config.PLUGIN_NAME
    assert slack_plugin.FEEDBACK_BOT_USER_ID == slack_plugin.slack_config.SLACK_FEEDBACK_BOT_ID

@pytest.mark.asyncio
async def test_request_to_notification_data(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    slack_plugin.slack_input_handler.request_to_notification_data = AsyncMock(return_value=IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="message",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Hello, world!",
        origin="slack"
    ))

    result = await slack_plugin.request_to_notification_data(event_data)

    assert isinstance(result, IncomingNotificationDataBase)
    assert result.text == "Hello, world!"
    assert result.user_id == "U123456"
    assert result.channel_id == "C12345678"

def test_split_message(slack_plugin):
    message = "This is a long message that needs to be split into multiple parts."
    length = 20

    result = slack_plugin.split_message(message, length)

    assert len(result) == 4
    assert result[0] == "This is a long messa"
    assert result[1] == "ge that needs to be "
    assert result[2] == "split into multiple "
    assert result[3] == "parts."

    # Test with None input
    assert slack_plugin.split_message(None, length) == []

    # Test with empty string
    assert slack_plugin.split_message("", length) == []

@pytest.mark.asyncio
async def test_is_message_too_old(slack_plugin):
    # Test with a recent message
    recent_ts = str(time.time())
    assert await slack_plugin.is_message_too_old(recent_ts) is False

    # Test with an old message
    old_ts = str(time.time() - slack_plugin.SLACK_MESSAGE_TTL - 1)
    assert await slack_plugin.is_message_too_old(old_ts) is True

def test_format_trigger_genai_message(slack_plugin):
    message = "Hello, AI!"
    formatted = slack_plugin.format_trigger_genai_message(message)
    assert formatted == f"<@{slack_plugin.bot_user_id}> Hello, AI!"

@pytest.mark.asyncio
async def test_execute_slash_command(slack_plugin, monkeypatch):
    # Mock the necessary methods
    monkeypatch.setattr(slack_plugin.backend_internal_data_processing_dispatcher, "list_container_files", AsyncMock(return_value=["file1.txt", "file2.txt"]))
    monkeypatch.setattr(slack_plugin.slack_output_handler, "send_slack_message", AsyncMock())

    # Test /listprompt command
    request = MagicMock()
    request.headers = {"X-Slack-Request-Timestamp": "1234567890", "X-Slack-Signature": "v0=abcd1234"}
    raw_body_str = "command=/listprompt&channel_id=C12345678"

    await slack_plugin.execute_slash_command(request, raw_body_str)

    slack_plugin.slack_output_handler.send_slack_message.assert_called_once()

    # Test /setprompt command
    slack_plugin.slack_output_handler.send_slack_message.reset_mock()
    monkeypatch.setattr(slack_plugin.backend_internal_data_processing_dispatcher, "read_data_content", AsyncMock(return_value="Prompt content"))
    monkeypatch.setattr(slack_plugin.backend_internal_data_processing_dispatcher, "write_data_content", AsyncMock())

    raw_body_str = "command=/setprompt&text=new_prompt&channel_id=C12345678"

    await slack_plugin.execute_slash_command(request, raw_body_str)

    slack_plugin.backend_internal_data_processing_dispatcher.write_data_content.assert_called_once()
    slack_plugin.slack_output_handler.send_slack_message.assert_called_once()

@pytest.mark.asyncio
async def test_add_reference_message(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    message_blocks = ["Hello, world!"]
    
    slack_plugin.slack_input_handler.get_message_permalink_and_text = AsyncMock(return_value=("https://example.com", "Test message"))
    
    result = await slack_plugin.add_reference_message(event, message_blocks, "1234567890.123456")
    
    assert result is True
    assert len(message_blocks) == 2
    assert message_blocks[0].startswith("<https://example.com|[ref msg link]>")

@pytest.mark.asyncio
async def test_handle_internal_message(slack_plugin):
    slack_plugin.INTERNAL_CHANNEL = "C87654321"
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    event_copy = copy.deepcopy(event)

    # Test when already_found_internal_ts is a specific timestamp
    result = await slack_plugin.handle_internal_message(event, event_copy, "1234567890.123456", "1234567890.123456", False)
    assert result == ("1234567890.123456", slack_plugin.INTERNAL_CHANNEL)

    # Test when already_found_internal_ts is True
    result = await slack_plugin.handle_internal_message(event, event_copy, "1234567890.123456", True, False)
    assert result == (True, slack_plugin.INTERNAL_CHANNEL)


def test_construct_payload(slack_plugin):
    channel_id = "C12345678"
    response_id = "1234567890.123456"
    message_block = "Hello, world!"
    block_index = 0
    total_blocks = 1
    title = "Test Title"
    is_new_message_added = False

    # Test with different message type
    message_type = MessageType.COMMENT
    
    # Créez un mock synchrone pour format_slack_message
    mock_format_slack_message = MagicMock(return_value=[{"type": "section", "text": {"type": "mrkdwn", "text": "Formatted message"}}])

    with patch.object(slack_plugin.slack_output_handler, 'format_slack_message', mock_format_slack_message):
        payload = slack_plugin.construct_payload(channel_id, response_id, message_block, message_type, block_index, total_blocks, title, is_new_message_added)
    
    assert 'blocks' in payload
    blocks = json.loads(payload['blocks'])
    assert blocks[0]['text']['text'] == "Formatted message"

@pytest.mark.asyncio
async def test_send_message(slack_plugin, requests_mock):
    requests_mock.post('https://slack.com/api/chat.postMessage', json={'ok': True})

    message = "Hello, world!"
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    message_type = MessageType.TEXT

    # Test regular message
    response = await slack_plugin.send_message(message, event, message_type)
    assert response.status_code == 200
    assert response.json() == {'ok': True}

    # Test with show_ref=True
    slack_plugin.add_reference_message = AsyncMock(return_value=True)
    response = await slack_plugin.send_message(message, event, message_type, show_ref=True)
    assert slack_plugin.add_reference_message.called
    assert response.status_code == 200

    # Test internal message
    slack_plugin.handle_internal_message = AsyncMock(return_value=("1234567890.123457", "C87654321"))
    response = await slack_plugin.send_message(message, event, message_type, is_internal=True)
    assert slack_plugin.handle_internal_message.called
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_upload_file(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    file_content = b"Test file content"
    filename = "test.txt"
    title = "Test File"

    slack_plugin.handle_internal_channel = AsyncMock()
    slack_plugin.slack_output_handler.upload_file_to_slack = AsyncMock()

    # Test regular file upload
    await slack_plugin.upload_file(event, file_content, filename, title)
    slack_plugin.slack_output_handler.upload_file_to_slack.assert_called_once()

    # Test internal file upload
    slack_plugin.slack_output_handler.upload_file_to_slack.reset_mock()
    await slack_plugin.upload_file(event, file_content, filename, title, is_internal=True)
    slack_plugin.handle_internal_channel.assert_called_once()
    slack_plugin.slack_output_handler.upload_file_to_slack.assert_called_once()

@pytest.mark.asyncio
async def test_handle_internal_channel(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    event_copy = copy.deepcopy(event)

    # Test when INTERNAL_CHANNEL is None
    slack_plugin.INTERNAL_CHANNEL = None
    with patch.object(slack_plugin.logger, 'warning') as mock_logger:
        await slack_plugin.handle_internal_channel(event, event_copy)
        mock_logger.assert_called_once_with("An internal message was sent but INTERNAL_CHANNEL is not defined, so the message is sent in the original thread.")

    # Test when INTERNAL_CHANNEL is set
    slack_plugin.INTERNAL_CHANNEL = "C87654321"
    slack_plugin.wait_for_internal_message = AsyncMock()
    await slack_plugin.handle_internal_channel(event, event_copy)
    assert event_copy.channel_id == "C87654321"
    assert slack_plugin.wait_for_internal_message.called

@pytest.mark.asyncio
async def test_wait_for_internal_message(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    event_copy = copy.deepcopy(event)

    # Test when internal message is found
    slack_plugin.slack_input_handler.search_message_in_thread = AsyncMock(return_value="1234567890.123457")
    await slack_plugin.wait_for_internal_message(event, event_copy)
    assert event_copy.thread_id == "1234567890.123457"

    # Test when internal message is not found
    slack_plugin.slack_input_handler.search_message_in_thread = AsyncMock(return_value=None)
    with patch.object(slack_plugin.logger, 'warning') as mock_logger:
        await slack_plugin.wait_for_internal_message(event, event_copy)
        mock_logger.assert_called_once_with("Internal message not found after 15 seconds, sending the message in the original thread.")

@pytest.mark.asyncio
async def test_process_event_data_invalid_request(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    headers = {
        'X-Slack-Request-Timestamp': '1531420618',
        'X-Slack-Signature': 'v0=invalid_signature'
    }
    raw_body_str = '{"event": {"type": "message", "user": "U123456", "channel": "C12345678", "ts": "1234567890.123456"}}'

    with patch.object(slack_plugin, 'validate_request', return_value=False), \
         patch.object(slack_plugin.logger, 'debug') as mock_logger:
        await slack_plugin.process_event_data(event_data, headers, raw_body_str)
        mock_logger.assert_called_with("Request discarded")

@pytest.mark.asyncio
async def test_handle_valid_request_error(slack_plugin):
    event_data = {
        "event": {
            "type": "message",
            "user": "U123456",
            "channel": "C12345678",
            "ts": "1234567890.123456",
            "text": "Hello, world!"
        }
    }
    with patch.object(slack_plugin, 'process_event_by_type', side_effect=Exception("Test error")), \
         patch.object(slack_plugin.logger, 'error') as mock_logger:
        with pytest.raises(Exception) as exc_info:
            await slack_plugin.handle_valid_request(event_data)
        
        assert str(exc_info.value) == "Test error"
        mock_logger.assert_called_once_with("An error occurred while processing user input: Test error")

@pytest.mark.asyncio
async def test_handle_request_challenge(slack_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps({"challenge": "test_challenge"}).encode())
    request.headers = {'content-type': 'application/json'}
    request.url.path = "/slack/events"

    response = await slack_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.body == b"test_challenge"

@pytest.mark.asyncio
async def test_handle_request_exception(slack_plugin):
    request = MagicMock(spec=Request)
    request.body = AsyncMock(side_effect=Exception("Test error"))
    request.headers = {'content-type': 'application/json'}
    request.url.path = "/slack/events"

    response = await slack_plugin.handle_request(request)

    assert isinstance(response, Response)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_execute_slash_command_unknown(slack_plugin):
    request = MagicMock()
    request.headers = {"X-Slack-Request-Timestamp": "1234567890", "X-Slack-Signature": "v0=abcd1234"}
    raw_body_str = "command=/unknown&channel_id=C12345678"

    await slack_plugin.execute_slash_command(request, raw_body_str)

    # Vérifiez que rien n'est appelé ou qu'un message d'erreur est envoyé
    slack_plugin.slack_output_handler.send_slack_message.assert_not_called()

@pytest.mark.asyncio
async def test_upload_file_no_internal_channel(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    file_content = b"Test file content"
    filename = "test.txt"
    title = "Test File"

    # Set INTERNAL_CHANNEL to None
    slack_plugin.INTERNAL_CHANNEL = None
    
    # Mock the upload_file_to_slack method
    slack_plugin.slack_output_handler.upload_file_to_slack = AsyncMock()

    # Call the method
    await slack_plugin.upload_file(event, file_content, filename, title, is_internal=True)
    
    # Check that upload_file_to_slack was called with the correct arguments
    slack_plugin.slack_output_handler.upload_file_to_slack.assert_called_once()
    
    call_args = slack_plugin.slack_output_handler.upload_file_to_slack.call_args
    assert call_args is not None
    kwargs = call_args.kwargs

    # Check each argument individually
    assert kwargs['file_content'] == file_content
    assert kwargs['filename'] == filename
    assert kwargs['title'] == title
    
    # Check the event object's attributes
    assert kwargs['event'].timestamp == event.timestamp
    assert kwargs['event'].converted_timestamp == event.converted_timestamp
    assert kwargs['event'].event_label == event.event_label
    assert kwargs['event'].channel_id == event.channel_id
    assert kwargs['event'].thread_id == event.thread_id
    assert kwargs['event'].response_id == event.response_id
    assert kwargs['event'].user_name == event.user_name
    assert kwargs['event'].user_email == event.user_email
    assert kwargs['event'].user_id == event.user_id
    assert kwargs['event'].is_mention == event.is_mention
    assert kwargs['event'].text == event.text
    assert kwargs['event'].origin == event.origin

    # Verify that the channel_id wasn't changed (since INTERNAL_CHANNEL is None)
    assert kwargs['event'].channel_id == "C12345678"

@pytest.mark.asyncio
async def test_wait_for_internal_message_timeout(slack_plugin):
    event = IncomingNotificationDataBase(
        timestamp="1234567890.123456",
        converted_timestamp="1234567890.123456",
        event_label="test_event",
        channel_id="C12345678",
        thread_id="1234567890.123456",
        response_id="1234567890.123456",
        user_name="test_user",
        user_email="test_user@example.com",
        user_id="U123456",
        is_mention=False,
        text="Test message",
        origin="slack"
    )
    event_copy = copy.deepcopy(event)

    slack_plugin.slack_input_handler.search_message_in_thread = AsyncMock(return_value=None)
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await slack_plugin.wait_for_internal_message(event, event_copy)
    
    assert event_copy.thread_id == event.thread_id 