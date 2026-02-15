import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


LOGGER = logging.getLogger(__name__)


@dataclass
class QQMessageEvent:
    event_id: str
    sender_id: str
    channel_id: Optional[str]
    group_id: Optional[str]
    text: str
    is_self_message: bool
    raw_payload: Dict[str, Any]


class QQAdapter:
    """Tencent QQ adapter for ingesting events and sending responses."""

    def __init__(self, bot_account_id: str, bot_token: str, api_base_url: str, timeout_seconds: int = 10) -> None:
        self.bot_account_id = bot_account_id
        self.bot_token = bot_token
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def parse_event(self, payload: Dict[str, Any]) -> QQMessageEvent:
        data = payload.get("d", payload)
        author = data.get("author") or {}
        sender = data.get("sender") or {}

        sender_id = str(
            author.get("id")
            or sender.get("user_id")
            or data.get("author_id")
            or data.get("user_id")
            or ""
        )
        channel_id = data.get("channel_id")
        group_id = data.get("group_openid") or data.get("group_id")
        text = data.get("content") or data.get("message") or ""
        event_id = str(payload.get("id") or data.get("id") or payload.get("event_id") or "unknown")

        is_bot_tagged = bool(author.get("bot") or sender.get("bot"))
        source_bot_id = str(payload.get("bot_appid") or payload.get("self_id") or data.get("self_id") or "")
        is_self_message = (
            sender_id == str(self.bot_account_id)
            or source_bot_id == str(self.bot_account_id)
            or is_bot_tagged
        )

        return QQMessageEvent(
            event_id=event_id,
            sender_id=sender_id,
            channel_id=channel_id,
            group_id=group_id,
            text=text,
            is_self_message=is_self_message,
            raw_payload=payload,
        )

    def send_message(self, event: QQMessageEvent, content: str) -> Tuple[int, str]:
        body: Dict[str, Any] = {"content": content}
        if event.channel_id:
            path = f"/channels/{event.channel_id}/messages"
        elif event.group_id:
            path = f"/v2/groups/{event.group_id}/messages"
        else:
            path = f"/v2/users/{event.sender_id}/messages"

        status, payload = self._post_json(path, body)
        LOGGER.info(
            "Outgoing QQ message request finished",
            extra={
                "event_id": event.event_id,
                "status_code": status,
                "response_preview": payload[:300],
            },
        )
        return status, payload

    def _post_json(self, path: str, body: Dict[str, Any]) -> Tuple[int, str]:
        encoded_body = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.api_base_url}{path}",
            method="POST",
            data=encoded_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bot {self.bot_account_id}.{self.bot_token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8", errors="replace")
                return response.status, payload
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            return exc.code, payload
        except urllib.error.URLError as exc:
            LOGGER.error("QQ API request failed", extra={"error": str(exc), "path": path})
            return 0, str(exc)
