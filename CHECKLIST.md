# Development Checklist - localQQTransferProxy

Use this checklist while implementing features, reviewing changes, and preparing releases.

## 1) Environment and setup

- [x] Python version is compatible (3.10+ recommended).
- [x] Virtual environment is active.
- [x] Dependencies installed (`pip install -r requirements.txt`).
- [x] `.env` exists locally and includes required QQ and Claude settings.

## 2) Code changes

- [x] Change is scoped and documented.
- [x] Config changes are validated in `BridgeConfig`.
- [x] QQ payload changes preserve compatibility with existing event shapes.
- [x] Claude session behavior (create/reuse/cleanup) is still correct.
- [x] Self-message loop prevention remains intact.

## 3) Local verification

- [x] Service starts successfully (`python -m src.bridge.main`).
- [ ] Basic webhook call returns valid JSON response.
- [x] Logs contain useful trace fields (`event_id`, status, errors).
- [x] No secrets were logged accidentally.

## 4) Quality gates

- [x] Static checks/tests (when present) pass.
- [x] New tests added for behavior changes.
- [x] Documentation updates included (`readme.md`, `TODO.md`, this checklist).

## 5) Release/readiness

- [ ] Breaking changes are clearly called out.
- [x] Operational impacts are documented (env vars, ports, process model).
- [ ] Rollback strategy is known (previous image/tag/config).
- [x] Follow-up tasks are tracked in `TODO.md`.
