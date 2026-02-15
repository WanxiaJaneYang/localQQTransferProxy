# Development Checklist - localQQTransferProxy

Use this checklist while implementing features, reviewing changes, and preparing releases.

## 1) Environment and setup

- [ ] Python version is compatible (3.10+ recommended).
- [ ] Virtual environment is active.
- [ ] Dependencies installed (`pip install -r requirements.txt`).
- [ ] `.env` exists locally and includes required QQ and Claude settings.

## 2) Code changes

- [ ] Change is scoped and documented.
- [ ] Config changes are validated in `BridgeConfig`.
- [ ] QQ payload changes preserve compatibility with existing event shapes.
- [ ] Claude session behavior (create/reuse/cleanup) is still correct.
- [ ] Self-message loop prevention remains intact.

## 3) Local verification

- [ ] Service starts successfully (`python -m src.bridge.main`).
- [ ] Basic webhook call returns valid JSON response.
- [ ] Logs contain useful trace fields (`event_id`, status, errors).
- [ ] No secrets were logged accidentally.

## 4) Quality gates

- [ ] Static checks/tests (when present) pass.
- [ ] New tests added for behavior changes.
- [ ] Documentation updates included (`readme.md`, `TODO.md`, this checklist).

## 5) Release/readiness

- [ ] Breaking changes are clearly called out.
- [ ] Operational impacts are documented (env vars, ports, process model).
- [ ] Rollback strategy is known (previous image/tag/config).
- [ ] Follow-up tasks are tracked in `TODO.md`.
