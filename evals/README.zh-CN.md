# NovelForge Evals · 评测系统

## 目的

NovelForge 严格区分 **deterministic invariant** 与 **semantic quality judgment**。

```mermaid
flowchart LR
    C[Eval Case] --> T{Judge Type}
    T -- deterministic --> D[Code Assertions]
    T -- rubric --> Q[Blind Semantic Queue]
    T -- hybrid --> D
    D -->|preconditions pass| Q
    Q --> W[Independent Reviewer]
    W --> B[Fingerprint-bound Result]
    B --> R[Eval Runner]
```

Deterministic runner 永远不能假装 regex/heuristic 等价于文学判断。

## Case Types

- `regression`：保护已知 failure mechanism；只有当前 release path 有真实 deterministic/semantic baseline 时才可作为 release blocker。
- `capability`：验证 Framework 能识别或实现目标 mechanism。
- `infrastructure`：验证 schema、authority、files、routing 与 runtime contract。

## Judge Types

### `deterministic`
只跑代码断言，适合 lifecycle、schema、file、authority、idempotency、exact fixture property。

### `rubric`
必须有真正 independent semantic judgment。缺失 judgment = `PENDING_MODEL`，绝不伪造 PASS。

### `hybrid`
先跑 deterministic precondition，再跑 semantic rubric。

## Blindness

Semantic case 文件可以保存 hidden `expected` 用于 eval scoring；`build_judge_queue.py` 会生成独立 **blind queue**，把 expected/gold/release label 全部剥掉后才交给 reviewer。

Regression bad example 是 eval fixture，不进入 first-pass Writer context。

## Normal CI

Normal CI：
- 验证 eval manifest/cases；
- 运行 deterministic release blockers；
- build blind semantic queue；
- 验证 hidden expected label 没有泄漏；
- 需要时可验证明确 versioned、人工/独立 reviewer 已审 baseline。

Reviewed baseline 是**证据索引，不是模型输出**。`validate_semantic_acceptance.py` 会重新生成当前 blind typed jobs，并要求每个 case 的 current fingerprint 与独立 reviewer 已审 PASS provenance 精确匹配。rubric、fixture 或 output contract 只要造成 fingerprint 变化，旧 baseline 就立即失效，必须重新进行独立评审。Baseline 永远不会给 `run_evals.py` 注入 judgment。

Normal CI **不会**静默调用付费或 login-bound model。

## Semantic Execution

Blind queue 先通过 Harness semantic router 变成 typed semantic jobs，再交给 eligible independent runtime。Result 做 fingerprint binding，最后由 `run_evals.py` 评分。

每次 live semantic run 还会在 reviewer 执行**之前**生成 `semantic-live-execution-identity.json`。这个 content-addressed envelope 会把 candidate commit / Framework version 与 reviewer provider、model/config、blind queue、typed jobs、capability snapshot、semantic harness source fingerprint、runner/Python environment、显式 resource-budget 状态和 GitHub run provenance 绑定起来。Provider-managed revision 或未配置 budget 如果无法精确确定，就保留为明确的 unpinned/null 事实，而不是猜测 metadata。任何已绑定字段变化都会改变 `identity_fingerprint`。

这个 envelope 是 deterministic provenance，本身不是 semantic evidence。历史 run 如果当时没有 execution identity，不会被追溯伪造；有 identity 也不会把 deterministic CI 自动变成 semantic quality claim。

## Commands

```bash
python evals/run_evals.py --release
python evals/build_judge_queue.py --output /tmp/semantic-queue.json
python evals/run_evals.py --judgments reviewed-results.json --json
python evals/validate_semantic_acceptance.py validate
python evals/evaluation_execution_identity.py self-test
python evals/evaluation_execution_identity.py validate semantic-live-execution-identity.json
```

## Quality Domains

v7 初始 suite 覆盖：
- Surface Fundamentals；
- Reader Engagement；
- Character / semantic ownership；
- Canon / Plan boundary；
- Corpus rights boundary；
- Project SDK / Framework hygiene；
- Semantic runtime integrity。

Suite 会从用户拒绝证据、Corpus research、Framework changes 与新 capability gap 中持续增长。
