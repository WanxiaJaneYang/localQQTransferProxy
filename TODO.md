# TODO - localQQTransferProxy

## High priority

- [x] Add webhook request authentication / signature verification based on QQ callback secret.
- [x] Add automated tests for:
  - [x] `BridgeConfig.from_env` validation paths.
  - [x] `QQAdapter.parse_event` with representative payload variants.
  - [x] `BridgeService.handle_incoming_event` flow and ignore cases.
- [ ] Add retry + timeout strategy for QQ send failures and temporary upstream errors.

## Medium priority

- [ ] Provide Dockerfile and docker-compose local development profile.
- [ ] Add structured log fields/documentation for easier tracing (`event_id`, `session_key`).
- [ ] Add graceful shutdown integration tests for Claude session cleanup.
- [ ] Support optional request ID propagation for end-to-end debugging.

## Low priority

- [ ] Add health/readiness endpoints (`/healthz`, `/readyz`).
- [ ] Add metrics export (e.g., Prometheus) for request counts and latency.
- [ ] Add optional message length guardrails/chunking for large model responses.
- [ ] Improve docs with deployment examples (systemd/reverse proxy).

## Documentation and process

- [x] Keep `readme.md` aligned with behavior when env vars or endpoints change.
- [x] Keep `CHECKLIST.md` updated at each milestone/release.
- [ ] Define release checklist and semantic versioning approach.

## Work log (latest)

- Implemented webhook signature verification in request handling using `QQ_CALLBACK_SECRET`.
- Added unit tests for config validation, event parsing variants, signature verification, and bridge service flow.
- Updated README quick-start with explicit `.env` setup command.
- Started the next highest-priority remaining task by introducing HTTP timeout-aware retry strategy for QQ send failures.
