# Tasks 013 · Automatic Feedback Learning Intake

## Contract
- [x] T01 升级 `learning.preference_interpret`：`capture|skip`，skip 不制造 scope/mechanism。
- [x] T02 增加 `reasoned_acceptance / comparison / correction` 与 model-directed hypothesis action。
- [x] T03 保持 semantic contract `independent_gate=false`、所有 durable write permission=false。

## Persistence / Author Model
- [x] T04 Author Model capture 支持 deterministic event-derived evidence ID。
- [x] T05 支持 `create / strengthen / contest / supersede / split`，exact target + scope/project compatibility + version/CAS。
- [x] T06 automatic intake activation flags 永远 false；current explicit instruction priority 保持不变。
- [x] T07 rejection 保存 fingerprint/ref + negative-only disposition，不复制 rejected prose。

## Intake Runtime
- [x] T08 新增 `learning/feedback_intake.py`，使用现有 Learning DB，不创建第二 DB。
- [x] T09 接受 legacy Author Steering feedback payload + generic feedback observation payload。
- [x] T10 durable states: observed / awaiting_semantic / interpreted / skipped / persisted / blocked / failed。
- [x] T11 semantic unavailable → pending/resumable，不做 heuristic classification。
- [x] T12 `learning_feedback:*` consumer-specific receipt 与 author steering receipt 独立。
- [x] T13 side-effect-free status/list projection。

## Harness / Documentation
- [x] T14 更新 HARNESS manifest：automatic intake component/schema/projection/invariants。
- [x] T15 更新 Skill/Harness/Adaptive Learning/Self-Improvement/Control Plane/Session docs（中英适用处）。
- [x] T16 明确 basic intake 是任何 primary mode 的 bounded internal subroutine；LEARN mode 保留。
- [x] T17 文档化 privacy、active!=relevant、current explicit instruction precedence、no auto-promotion。

## Deterministic Tests
- [x] T18 REVISE automatic project feedback。
- [x] T19 one-off 不激活。
- [x] T20 user_taste candidate 不激活。
- [x] T21 general_craft overreach 不 promotion。
- [x] T22 “继续下一段” skip。
- [x] T23 “ok” skip。
- [x] T24 rejection negative-only + fingerprint binding。
- [x] T25 comparison strengthens existing project hypothesis。
- [x] T26 contradiction contest/supersede/applicability。
- [x] T27 same-event retry exactly once。
- [x] T28 two independent turns → two evidence refs / one hypothesis。
- [x] T29 dual steering + learning consumers。
- [x] T30 missing semantic capability pending。
- [x] T31 resume pending exactly once。
- [x] T32 current explicit instruction wins。
- [x] T33 user-specific data not written to Generic repo。
- [x] T34 normal CI model_execution=false。

## Semantic / Ablation
- [x] T35 新增 feedback-learning ablation family/fixtures：BEFORE/AFTER、negative、authority、dual-consumer、contradiction。
- [x] T36 生成 fingerprint-bound paired packets；需要 independence 时只接受 separate invocation/session。
- [x] T37 无 eligible reviewer → `PENDING_MODEL`，禁止 manager self-PASS。

## Verification / Release
- [x] T38 py_compile / JSON schema validation。
- [x] T39 现有 Control Plane / Author Steering / Author Model / Learning Store / Learning Cycle / Promotion Gate regressions。
- [x] T40 semantic contract registry/catalog consistency。
- [x] T41 generic evals + deterministic framework bundle build/verify。
- [x] T42 docs quality / framework hygiene / machine namespace hygiene。
- [ ] T43 draft PR；记录 CI、semantic evidence、bundle fingerprint；不 repin consumer Project。
