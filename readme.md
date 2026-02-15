# Local QQ Transfer Proxy

Bridge QQ messages to a local terminal agent (MVP: Claude CLI), so you can chat with your local agent directly from QQ.

## Purpose

This project provides a minimal proxy service that:

1. Receives QQ bot message events via HTTP webhook
2. Routes each sender to a dedicated local Claude CLI session
3. Sends Claude responses back to QQ through Tencent APIs
4. Keeps credentials and runtime settings in environment variables (recommended via `.env`)

This enables a practical "QQ as chat frontend + local agent runtime" workflow.

---

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create a local `.env` from the example values in this README (or from `.env.example` if present)
3. Fill in QQ bot credentials and local Claude command
4. Start service: `python -m src.bridge.main`

Required runtime settings are validated during service startup.

---

## Current Code Structure

```text
.
├─ readme.md
└─ src/
   └─ bridge/
      ├─ __init__.py
      ├─ main.py            # HTTP server, request handler, wiring adapters
      ├─ qq_adapter.py      # QQ event parsing + QQ send-message API client
      └─ claude_adapter.py  # per-user Claude process sessions + idle cleanup
```

### Module Responsibilities

- `src/bridge/main.py`
  - Starts a `ThreadingHTTPServer`
  - Exposes webhook endpoint: `POST /qq/webhook`
  - Parses JSON payload, dispatches to `BridgeService`
  - Coordinates event handling: parse event → invoke Claude → send QQ reply

- `src/bridge/qq_adapter.py`
  - Normalizes incoming QQ event into `QQMessageEvent`
  - Detects self-message and bot-tagged events to prevent loops
  - Sends response using Tencent Bot HTTP API with `Authorization: Bot <appid>.<token>`
  - Supports channel/group/user message paths based on available IDs

- `src/bridge/claude_adapter.py`
  - Maintains long-lived Claude subprocesses keyed by sender session key
  - Reuses sessions for conversational continuity
  - Reads CLI output with timeout + short quiet-window buffering
  - Cleans up idle sessions in a background thread

---

## Runtime Flow

```text
QQ User -> Tencent event -> /qq/webhook
         -> QQAdapter.parse_event(...)
         -> ClaudeAdapter.ask(session_key, text)
         -> QQAdapter.send_message(...)
         -> QQ receives bot reply
```

### Event Handling Rules (current implementation)

- Ignore self messages (`is_self_message`) to avoid reply loops
- Ignore events with empty sender or empty text
- Use sender ID as session key

---

## Configuration Guideline

The code reads config from environment variables. Use a local `.env` file plus your preferred loader (shell export, docker env-file, direnv, etc.).

### Required / important environment variables

- `QQ_BOT_APP_ID` — bot app/account ID used in auth and self-message checks
- `QQ_BOT_TOKEN` — bot token
- `QQ_API_BASE_URL` — default `https://api.sgroup.qq.com`
- `CLAUDE_COMMAND` — command string for local agent, default `claude`
- `CLAUDE_SESSION_IDLE_TIMEOUT` — seconds before idle session cleanup, default `900`
- `BRIDGE_HOST` — HTTP bind host, default `0.0.0.0`
- `BRIDGE_PORT` — HTTP bind port, default `8080`
- `LOG_LEVEL` — logging level, default `INFO`

### Recommended `.env.example`

```env
QQ_BOT_APP_ID=
QQ_BOT_TOKEN=
QQ_API_BASE_URL=https://api.sgroup.qq.com

CLAUDE_COMMAND=claude
CLAUDE_SESSION_IDLE_TIMEOUT=900

BRIDGE_HOST=0.0.0.0
BRIDGE_PORT=8080
LOG_LEVEL=INFO
```

### Security Guidelines

- Do **not** commit `.env` files
- Rotate QQ bot tokens regularly
- Do not print secrets in logs
- Restrict production host/network exposure for webhook endpoint

---

## Tencent Communication Plan Guideline (for MVP hardening)

Before production rollout, align integration details with Tencent official docs and lock decisions in project docs:

1. Webhook authenticity verification (signature/timestamp/nonce if required by chosen flow)
2. Event schema fields used for sender/content/thread context
3. Outbound API endpoint variants (channel/group/C2C) and required auth headers
4. Retry/idempotency strategy for duplicate event delivery
5. Rate-limit and transient failure backoff behavior

> Current code already covers outbound auth header and route selection, but callback signature verification and idempotency persistence should be added for stronger reliability/security.

---

## Run Guideline

### 1) Set environment

- Create `.env` using the example above
- Ensure `claude` CLI is available in PATH (or set `CLAUDE_COMMAND` explicitly)

### 2) Start service

Example (module mode):

```bash
python -m src.bridge.main
```

Service starts on `http://<BRIDGE_HOST>:<BRIDGE_PORT>/qq/webhook`.

### 3) Configure QQ callback

Point Tencent QQ bot callback to:

```text
http(s)://<your-host>/qq/webhook
```

Use a reachable HTTPS endpoint in real deployments (reverse proxy/tunnel as needed).

---

## Development Guidelines

- Keep adapter boundaries clear:
  - QQ protocol logic in `qq_adapter.py`
  - local process/session logic in `claude_adapter.py`
  - orchestration and HTTP in `main.py`
- Prefer small, testable functions around event normalization and subprocess I/O
- Add tests for:
  - QQ event parsing variants
  - self-message detection
  - session reuse + idle cleanup behavior
  - timeout behavior in Claude output reading
- For protocol changes, update README and implementation together

---

## Known MVP Limitations

- No callback signature verification yet
- No persistent dedup/idempotency store for repeated events
- Session key currently only uses sender ID (no channel/thread scoping)
- No structured command controls (e.g. `/reset`, moderation, ACL)

---

## Suggested Next Steps

1. Add webhook signature verification per Tencent official requirement
2. Add idempotency cache by event ID
3. Add `.env.example` + `.gitignore` if missing
4. Add basic unit tests for adapters and BridgeService
5. Add operational docs for deployment (reverse proxy, TLS, logging)
