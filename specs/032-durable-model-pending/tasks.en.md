# Durable model pending tasks

2026-08-31 · truthful task state.

## Engineering

- [x] Bind one stable request key to each frozen model-call ordinal.
- [x] Persist pollability before loopback dispatch.
- [x] Return `202 model_pending` after a short HTTP wait.
- [x] Join identical concurrent publications and reject changed bodies.
- [x] Publish worker heartbeat and terminal state.
- [x] Remove the default arbitrary process timeout for keyed durable workers.
- [x] Keep elapsed pending rows pollable without creating another stage call.
- [x] Preserve safe pending fields through `NativeStyleRunner`.
- [x] Add focused deterministic tests for crash, poll, terminal, expiry, and duplicate protection.

## Documentation

- [x] Add paired 032 specification, plan, tasks, and verification.
- [x] Update paired Model Runtime and Agent Runtime guides.
- [x] Record the v2-to-v3 supersession boundary without rewriting specification 027.

## Live production

- [ ] Freeze and deploy the final verified source snapshot to the isolated WSL runtime.
- [ ] Build and bind the CH001 REVISE-only one-off pack.
- [ ] Register the exact authorized REVISE through Core.
- [ ] Complete the manager graph within 12 main calls, polling only exact pending requests.
- [ ] Complete one fresh independent review from packet-only context.
- [ ] Reconcile the reset epoch and the historical manager ledger separately.
- [ ] Read the Core-released, unaccepted and unsettled Review Draft.
