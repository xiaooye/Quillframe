from pathlib import Path

root=Path('.')

# Top-level CLI: expose validator and include it in full self-test/doctor surface.
p=root/'novelforge.py'
s=p.read_text(encoding='utf-8')
needle='    "publication": ROOT / "publication" / "compiler.py",\n'
assert needle in s and '"semantic-acceptance"' not in s
s=s.replace(needle, needle+'    "semantic-acceptance": ROOT / "evals" / "validate_semantic_acceptance.py",\n', 1)
needle='(MCP,["--self-test"]),(TOOLS["publication"],["self-test"]),(TOOLS["bundle"],["self-test"])]'
assert needle in s
s=s.replace(needle,'(MCP,["--self-test"]),(TOOLS["publication"],["self-test"]),(TOOLS["semantic-acceptance"],["self-test"]),(TOOLS["bundle"],["self-test"])]',1)
p.write_text(s,encoding='utf-8')

# Manifest: declare baseline/validator and deterministic CI obligation.
p=root/'HARNESS_MANIFEST.yaml'
s=p.read_text(encoding='utf-8')
needle='  blind_queue_builder: evals/build_judge_queue.py\n'
assert needle in s and 'semantic_acceptance_baseline:' not in s
addition=(
'  semantic_acceptance_schema: evals/semantic_acceptance.schema.json\n'
'  semantic_acceptance_baseline: evals/baselines/semantic-8.0-dev.1.json\n'
'  semantic_acceptance_validator: evals/validate_semantic_acceptance.py\n'
'  reviewed_baseline_is_model_output: false\n'
'  reviewed_baseline_fingerprint_match_required: true\n'
)
s=s.replace(needle,needle+addition,1)
needle='generic-eval-blind-queue, session-self-test'
assert needle in s
s=s.replace(needle,'generic-eval-blind-queue, semantic-acceptance-baseline-self-test, session-self-test',1)
p.write_text(s,encoding='utf-8')

# English eval docs: make baseline semantics and command explicit.
p=root/'evals/README.en.md'
s=p.read_text(encoding='utf-8')
needle='- may validate committed reviewed baselines when explicitly versioned.\n\nNormal CI does **not** silently call paid/login-bound models.\n'
assert needle in s
replacement=('- may validate committed reviewed baselines when explicitly versioned.\n\n'
'A reviewed baseline is an **evidence index, not model output**. `validate_semantic_acceptance.py` rebuilds the current blind typed jobs and requires an exact case/fingerprint match against independently reviewed PASS provenance. Any rubric, fixture, or output-contract change that changes a fingerprint invalidates the old baseline and requires fresh independent review. The baseline never supplies judgments to `run_evals.py`.\n\n'
'Normal CI does **not** silently call paid/login-bound models.\n')
s=s.replace(needle,replacement,1)
needle='python evals/run_evals.py --judgments reviewed-results.json --json\n'
assert needle in s
s=s.replace(needle,needle+'python evals/validate_semantic_acceptance.py validate\n',1)
p.write_text(s,encoding='utf-8')

# Chinese eval docs: same contract, native wording.
p=root/'evals/README.zh-CN.md'
s=p.read_text(encoding='utf-8')
needle='- 需要时可验证明确 versioned、人工/独立 reviewer 已审 baseline。\n\nNormal CI **不会**静默调用付费或 login-bound model。\n'
assert needle in s
replacement=('- 需要时可验证明确 versioned、人工/独立 reviewer 已审 baseline。\n\n'
'Reviewed baseline 是**证据索引，不是模型输出**。`validate_semantic_acceptance.py` 会重新生成当前 blind typed jobs，并要求每个 case 的 current fingerprint 与独立 reviewer 已审 PASS provenance 精确匹配。rubric、fixture 或 output contract 只要造成 fingerprint 变化，旧 baseline 就立即失效，必须重新进行独立评审。Baseline 永远不会给 `run_evals.py` 注入 judgment。\n\n'
'Normal CI **不会**静默调用付费或 login-bound model。\n')
s=s.replace(needle,replacement,1)
needle='python evals/run_evals.py --judgments reviewed-results.json --json\n'
assert needle in s
s=s.replace(needle,needle+'python evals/validate_semantic_acceptance.py validate\n',1)
p.write_text(s,encoding='utf-8')
