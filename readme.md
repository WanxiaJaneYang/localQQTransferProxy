# localQQTransferProxy

A lightweight Python bridge service that receives QQ bot webhook events, forwards user messages to a local Claude CLI process, and sends Claude replies back to QQ.

## Purpose

This repository exists to:
- connect QQ incoming events to a local Claude runtime;
- keep per-user Claude session context for more coherent multi-turn conversations;
- provide a simple HTTP webhook service that can be self-hosted.

## How it works

1. QQ sends an event payload to `POST /qq/webhook`.
2. The service parses the event, filters bot/self messages, and extracts sender + content.
3. The sender ID is used as a Claude session key.
4. The prompt is written into a long-lived Claude CLI subprocess.
5. Claude output is read and sent back through QQ OpenAPI.

## Repository structure

```text
.
├── requirements.txt            # Python dependency list
├── readme.md                   # Project introduction and developer guide
└── src/
    └── bridge/
        ├── __init__.py         # Package marker
        ├── main.py             # HTTP server + request handling + service wiring
        ├── config.py           # Environment config loading and validation
        ├── qq_adapter.py       # QQ event parsing and message sending
        └── claude_adapter.py   # Claude subprocess session manager
```

## Prerequisites

- Python 3.10+
- A reachable QQ Bot/OpenAPI setup
- Claude CLI installed and available in `PATH` (or configured command)

## Configuration

Set runtime environment variables (usually via `.env`):

| Variable | Required | Description |
|---|---|---|
| `QQ_APP_ID` (or `QQ_BOT_APP_ID`) | Yes | Bot app/account ID used for auth and self-message detection |
| `QQ_APP_SECRET` | Yes | QQ app secret (validated at startup) |
| `QQ_BOT_TOKEN` | Yes | QQ bot token used in `Authorization` header |
| `QQ_CALLBACK_SECRET` | No | HMAC secret used to verify webhook callback signatures |
| `QQ_API_BASE_URL` | No | QQ API base URL, default `https://api.sgroup.qq.com` |
| `CLAUDE_CMD` (or `CLAUDE_COMMAND`) | No | Command used to spawn Claude CLI, default `claude` |
| `SESSION_TIMEOUT_SECONDS` (or `CLAUDE_SESSION_IDLE_TIMEOUT`) | No | Per-user Claude session idle timeout in seconds, default `1800` |
| `BRIDGE_HOST` | No | HTTP bind host, default `0.0.0.0` |
| `BRIDGE_PORT` | No | HTTP bind port, default `8080` |
| `LOG_LEVEL` | No | Python log level, default `INFO` |

## Development quick start

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from the template and then fill values from the Configuration section:
   ```bash
   cp .env.example .env
   ```
4. Run the service:
   ```bash
   python -m src.bridge.main
   ```
5. Send a local webhook test:
   ```bash
   curl -X POST http://127.0.0.1:8080/qq/webhook \
     -H 'Content-Type: application/json' \
     -d '{"id":"evt-1","d":{"author":{"id":"user-1"},"content":"hello"}}'
   ```

## Current progress snapshot

Implemented:
- webhook endpoint (`/qq/webhook`) and JSON request parsing;
- runtime configuration validation for required environment values;
- QQ event normalization and response routing (channel/group/private);
- per-user Claude subprocess sessions with idle cleanup;
- prevention of bot self-reply loops;
- callback signature verification with optional `QQ_CALLBACK_SECRET`;
- timeout-aware QQ send retry strategy for temporary upstream failures;
- automated unit tests for configuration parsing, QQ event parsing, and bridge flow behavior.

Not yet implemented:
- production deployment examples and observability dashboards;


## Development notes

- Keep secrets only in local environment files; do not commit them.
- Use sender ID as conversation session key unless you intentionally redesign session strategy.
- When changing webhook payload parsing, keep backward-compatible handling for multiple QQ payload shapes.
- Prefer small, focused adapters over putting provider-specific logic into HTTP handler code.
