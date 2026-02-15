import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .claude_adapter import ClaudeAdapter
from .config import BridgeConfig
from .qq_adapter import QQAdapter


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


LOGGER = logging.getLogger(__name__)


class BridgeService:
    """Coordinates QQ event ingestion with per-user Claude sessions."""

    def __init__(self, qq_adapter: QQAdapter, claude_adapter: ClaudeAdapter) -> None:
        self.qq_adapter = qq_adapter
        self.claude_adapter = claude_adapter

    def handle_incoming_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = self.qq_adapter.parse_event(payload)
        LOGGER.info("Incoming QQ event", extra={"event_id": event.event_id})

        if event.is_self_message:
            LOGGER.info(
                "Ignoring bot self message to prevent reply loop",
                extra={"event_id": event.event_id, "sender_id": event.sender_id},
            )
            return {"status": "ignored", "reason": "self_message", "event_id": event.event_id}

        if not event.sender_id or not event.text.strip():
            return {"status": "ignored", "reason": "empty_sender_or_text", "event_id": event.event_id}

        session_key = event.sender_id
        LOGGER.info(
            "Routing QQ message to Claude session",
            extra={"event_id": event.event_id, "session_key": session_key},
        )

        claude_response = self.claude_adapter.ask(session_key, event.text)
        status_code, response_payload = self.qq_adapter.send_message(event, claude_response)

        return {
            "status": "ok",
            "event_id": event.event_id,
            "session_key": session_key,
            "qq_send_status": status_code,
            "qq_send_response": response_payload[:500],
        }


class BridgeRequestHandler(BaseHTTPRequestHandler):
    service: Optional[BridgeService] = None

    def do_POST(self) -> None:
        if self.path != "/qq/webhook":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown path")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload")
            return

        if not self.service:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Service not initialized")
            return

        response_data = self.service.handle_incoming_event(payload)
        response_bytes = json.dumps(response_data).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, fmt: str, *args: Any) -> None:
        LOGGER.info("HTTP request", extra={"message": fmt % args})


def build_service() -> BridgeService:
    config = BridgeConfig.from_env()

    qq_adapter = QQAdapter(
        bot_account_id=config.qq_app_id,
        bot_token=config.qq_bot_token,
        api_base_url=config.qq_api_base_url,
    )
    claude_adapter = ClaudeAdapter(
        command=config.claude_cmd,
        idle_timeout_seconds=config.session_timeout_seconds,
    )
    return BridgeService(qq_adapter=qq_adapter, claude_adapter=claude_adapter)


def run() -> None:
    configure_logging()
    host = os.getenv("BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("BRIDGE_PORT", "8080"))

    try:
        service = build_service()
    except ValueError as exc:
        LOGGER.error(str(exc))
        raise SystemExit(1) from exc
    BridgeRequestHandler.service = service

    server = ThreadingHTTPServer((host, port), BridgeRequestHandler)
    LOGGER.info("Bridge server started", extra={"host": host, "port": port})

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Bridge server stopping")
    finally:
        service.claude_adapter.close()
        server.server_close()


if __name__ == "__main__":
    run()
