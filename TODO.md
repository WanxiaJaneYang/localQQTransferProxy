# TODO - localQQTransferProxy

## High priority

- [ ] Add webhook request authentication / signature verification based on QQ callback secret.
- [ ] Add automated tests for:
  - [ ] `BridgeConfig.from_env` validation paths.
  - [ ] `QQAdapter.parse_event` with representative payload variants.
  - [ ] `BridgeService.handle_incoming_event` flow and ignore cases.
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

- [ ] Keep `readme.md` aligned with behavior when env vars or endpoints change.
- [ ] Keep `CHECKLIST.md` updated at each milestone/release.
- [ ] Define release checklist and semantic versioning approach.
