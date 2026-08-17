# 质量保障

Quillframe 的质量体系是一条 evidence + ownership 链，不是一个文学总分。每次判断都先问：哪些事实可以机械证明，哪些必须 semantic judgment，失败真正属于哪个 mechanism？

## Pre-independent Candidate Qualification

进入成本更高或更 consequential 的 independent gate 前，`candidate_qualification.py` 把 non-independent 的 semantic self-audit 与 reader-engagement result 绑定到 exact candidate，再结合 continuity evidence；只要经历过 repair，还必须有 objective-preservation comparison evidence。

Pass 的含义只是 **qualified for independent review**，绝不是“已经独立通过”。

## FIX + PRESERVE

<img src="assets/concepts/objective-preserving-repair.zh-CN.svg" alt="FIX + PRESERVE：目标缺陷改善，同时 objective envelope baseline 不被破坏" width="100%" />

Objective envelope 是 compact、fingerprinted、来自 authorized evidence 的 must-preserve objectives；它不能从 rejected prose 反推。替换 envelope 需要显式 change authority，并链接 previous fingerprint。

Repair preservation comparison 分开看 target outcome、objective preservation、reader value、character/relationship energy。证据不足就 pending；局部变好但伴随 collateral regression 就 fail。

## Incumbent 与 Challenger

`quality_evolution.py` 为 incumbent/challenger 保存 exact content fingerprint；semantic winner 由 registered `quality.compare` 判断。Deterministic ledger 只验证 exact pair、objective envelope、consume-once，并更新 incumbent 或 no-gain / plateau state。

Absolute score 不能单独决定 keep/discard。

## Repair-induced Regression Protection

`repair_objective_regression.py` 专门观察“repair target 改善，但 protected objective 退化”的失败；`regression_escape.py` 记录 known regression 没有在 expected stage 被抓住的 escape。两者都不自行作文学判断，只把已有 evidence 精确绑定到 artifact 与 stage。

## Fresh Regeneration Contamination Boundary

Fresh regeneration 可以挑战 incumbent，同时对 writer context 隐藏 rejected prose。它为了 comparison 仍有 comparison parent，但不能有 prose parent。这个边界由 Candidate Lineage 显式执行，不靠 prose similarity 猜测。

## Exact Fingerprint Review Binding

每个 semantic review receipt 都绑定 candidate fingerprint、semantic job fingerprint 与 result fingerprint。Candidate 只要 materially changed，旧 review evidence 就 stale。Lineage 或 binding 缺失时 runtime fail closed，不猜 ancestry。

## Acceptance Evidence 不等于 Settlement Authority

Candidate Lineage 可以把 opaque acceptance evidence ref 绑定到 exact artifact fingerprint，但会明确返回 `authority_verified=false`、`settlement_authorized=false`。真正的 authority layer 必须另外验证 acceptance。

## Independent Semantic Integrity

<img src="assets/concepts/independent-semantic-review.zh-CN.svg" alt="Independent review 必须来自独立 reviewer invocation，并绑定 exact candidate fingerprint" width="100%" />

Manager self-review != independent review；Telemetry != semantic judgment。有效 semantic rejection 是判断结果，不是 infrastructure failure；必须回 owning repair mechanism，不能 reviewer-shopping。
