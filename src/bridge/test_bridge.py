import hashlib
import hmac
import os
import unittest
import urllib.error
from unittest.mock import Mock

from src.bridge.config import BridgeConfig
from src.bridge.main import BridgeService
from src.bridge.qq_adapter import QQAdapter, QQMessageEvent


class BridgeConfigFromEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        self._keys = [
            "QQ_APP_ID",
            "QQ_BOT_APP_ID",
            "QQ_APP_SECRET",
            "QQ_BOT_TOKEN",
            "QQ_CALLBACK_SECRET",
            "QQ_API_BASE_URL",
            "CLAUDE_CMD",
            "CLAUDE_COMMAND",
            "SESSION_TIMEOUT_SECONDS",
            "CLAUDE_SESSION_IDLE_TIMEOUT",
        ]
        self._original = {key: os.environ.get(key) for key in self._keys}
        for key in self._keys:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_missing_required_fields_raise_validation_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            BridgeConfig.from_env()

        message = str(ctx.exception)
        self.assertIn("QQ_APP_ID is required.", message)
        self.assertIn("QQ_APP_SECRET is required.", message)
        self.assertIn("QQ_BOT_TOKEN is required", message)

    def test_invalid_session_timeout_raises_validation_error(self) -> None:
        os.environ["QQ_APP_ID"] = "app"
        os.environ["QQ_APP_SECRET"] = "secret"
        os.environ["QQ_BOT_TOKEN"] = "token"
        os.environ["SESSION_TIMEOUT_SECONDS"] = "0"

        with self.assertRaises(ValueError) as ctx:
            BridgeConfig.from_env()

        self.assertIn("SESSION_TIMEOUT_SECONDS must be a positive integer.", str(ctx.exception))

    def test_alias_values_are_accepted(self) -> None:
        os.environ["QQ_BOT_APP_ID"] = "bot-app"
        os.environ["QQ_APP_SECRET"] = "secret"
        os.environ["QQ_BOT_TOKEN"] = "token"
        os.environ["CLAUDE_COMMAND"] = "claude --print"
        os.environ["CLAUDE_SESSION_IDLE_TIMEOUT"] = "99"

        config = BridgeConfig.from_env()

        self.assertEqual(config.qq_app_id, "bot-app")
        self.assertEqual(config.claude_cmd, ["claude", "--print"])
        self.assertEqual(config.session_timeout_seconds, 99)


class QQAdapterParseEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = QQAdapter(bot_account_id="bot-1", bot_token="token", api_base_url="https://api.example.com")

    def test_parse_channel_payload(self) -> None:
        payload = {
            "id": "evt-1",
            "d": {
                "author": {"id": "user-1"},
                "channel_id": "ch-1",
                "content": "hello",
            },
        }

        event = self.adapter.parse_event(payload)

        self.assertEqual(event.event_id, "evt-1")
        self.assertEqual(event.sender_id, "user-1")
        self.assertEqual(event.channel_id, "ch-1")
        self.assertEqual(event.group_id, None)
        self.assertEqual(event.text, "hello")
        self.assertFalse(event.is_self_message)

    def test_parse_group_payload_with_sender_alias_fields(self) -> None:
        payload = {
            "event_id": "evt-2",
            "sender": {"user_id": "user-2"},
            "group_openid": "group-1",
            "message": "hi group",
        }

        event = self.adapter.parse_event(payload)

        self.assertEqual(event.event_id, "evt-2")
        self.assertEqual(event.sender_id, "user-2")
        self.assertEqual(event.group_id, "group-1")
        self.assertEqual(event.text, "hi group")

    def test_parse_marks_self_message_by_author_bot_flag(self) -> None:
        payload = {
            "d": {
                "author": {"id": "user-3", "bot": True},
                "content": "echo",
            }
        }

        event = self.adapter.parse_event(payload)

        self.assertTrue(event.is_self_message)

    def test_verify_callback_signature_accepts_raw_body_hmac(self) -> None:
        adapter = QQAdapter(
            bot_account_id="bot-1",
            bot_token="token",
            api_base_url="https://api.example.com",
            callback_secret="abc",
        )
        body = b'{"id":"evt"}'
        signature = hmac.new(b"abc", body, hashlib.sha256).hexdigest()

        is_valid = adapter.verify_callback_signature(body, {"X-Signature": signature})

        self.assertTrue(is_valid)

    def test_retry_on_temporary_http_error_then_success(self) -> None:
        adapter = QQAdapter(
            bot_account_id="bot-1",
            bot_token="token",
            api_base_url="https://api.example.com",
            max_retries=1,
            retry_backoff_seconds=0,
        )

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok":true}'

        first_error = urllib.error.HTTPError(
            url="https://api.example.com/path",
            code=503,
            msg="unavailable",
            hdrs=None,
            fp=None,
        )

        with unittest.mock.patch("urllib.request.urlopen", side_effect=[first_error, FakeResponse()]):
            status, payload = adapter._post_json("/path", {"content": "x"})

        self.assertEqual(status, 200)
        self.assertIn('ok', payload)

    def test_retry_on_url_error_exhausted(self) -> None:
        adapter = QQAdapter(
            bot_account_id="bot-1",
            bot_token="token",
            api_base_url="https://api.example.com",
            max_retries=1,
            retry_backoff_seconds=0,
        )

        with unittest.mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
            status, payload = adapter._post_json("/path", {"content": "x"})

        self.assertEqual(status, 0)
        self.assertIn("boom", payload)


class BridgeServiceHandleIncomingEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.qq_adapter = Mock(spec=QQAdapter)
        self.claude_adapter = Mock()
        self.service = BridgeService(qq_adapter=self.qq_adapter, claude_adapter=self.claude_adapter)

    def test_ignores_self_messages(self) -> None:
        event = QQMessageEvent(
            event_id="evt-1",
            sender_id="bot-1",
            channel_id="ch-1",
            group_id=None,
            text="hello",
            is_self_message=True,
            raw_payload={},
        )
        self.qq_adapter.parse_event.return_value = event

        result = self.service.handle_incoming_event({"id": "evt-1"})

        self.assertEqual(result["status"], "ignored")
        self.assertEqual(result["reason"], "self_message")
        self.claude_adapter.ask.assert_not_called()
        self.qq_adapter.send_message.assert_not_called()

    def test_ignores_empty_sender_or_text(self) -> None:
        event = QQMessageEvent(
            event_id="evt-2",
            sender_id="",
            channel_id=None,
            group_id=None,
            text="   ",
            is_self_message=False,
            raw_payload={},
        )
        self.qq_adapter.parse_event.return_value = event

        result = self.service.handle_incoming_event({"id": "evt-2"})

        self.assertEqual(result["status"], "ignored")
        self.assertEqual(result["reason"], "empty_sender_or_text")
        self.claude_adapter.ask.assert_not_called()

    def test_routes_message_and_returns_status(self) -> None:
        event = QQMessageEvent(
            event_id="evt-3",
            sender_id="user-1",
            channel_id="ch-1",
            group_id=None,
            text="hello",
            is_self_message=False,
            raw_payload={},
        )
        self.qq_adapter.parse_event.return_value = event
        self.claude_adapter.ask.return_value = "world"
        self.qq_adapter.send_message.return_value = (200, '{"ok":true}')

        result = self.service.handle_incoming_event({"id": "evt-3"})

        self.claude_adapter.ask.assert_called_once_with("user-1", "hello")
        self.qq_adapter.send_message.assert_called_once_with(event, "world")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["session_key"], "user-1")
        self.assertEqual(result["qq_send_status"], 200)


if __name__ == "__main__":
    unittest.main()
