#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label} anchor drifted: {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def restore_specs() -> None:
    run("git", "fetch", "origin", "agent/state-integrity-p0:refs/remotes/origin/state-integrity-p0-old")
    dst = ROOT / "specs" / "008-state-integrity-p0"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("plan.en.md", "plan.zh-CN.md", "spec.en.md", "spec.zh-CN.md"):
        data = subprocess.check_output(
            ["git", "show", f"refs/remotes/origin/state-integrity-p0-old:specs/008-state-integrity-p0/{name}"],
            cwd=ROOT,
        )
        (dst / name).write_bytes(data)

    (dst / "tasks.en.md").write_text(
        """# 008 Tasks · State Integrity P0

## Stage A · #69 property ownership
- [x] Evidence/overlap review against state graph, Settlement, Canon/State and Project Adapter.
- [x] Define minimal mutation classes and deterministic route vocabulary.
- [x] Implement resolver/schema + Project-path integration without reinterpreting legacy Projects.
- [x] Preserve the validated implementation as content-addressed blobs while salvaging from stale PR #75 onto current main.
- [x] Add cross-contract regression proving valid Runtime operational authorization cannot bypass a `settlement_only` Project property.
- [x] Fresh salvage full NovelForge CI `31905483778` green; state-integrity job `95062461054` executed all P0 steps.

## Stage B · #63 propagation debt
- [x] Review state graph, Settlement, memory invalidation, quality evolution and resume semantics for overlap.
- [x] Implement explicit-dependency, fingerprint-bound debt identity/lifecycle with no global invalidation.
- [x] Deterministic regressions cover idempotent replay, conflicting replay rejection, discharge binding, contiguous supersession, evidence-bound waiver and restart.
- [x] Keep debt non-authoritative and non-executing: no automatic repair, replan, regeneration, Canon write or Framework write.
- [x] Revalidate both P0 mechanisms against the post-#83 Runtime Control baseline.

## Integration / promotion gate
- [x] Wire the dedicated State Integrity workflow into current full NovelForge CI.
- [x] Register tool/schema/write-boundary semantics in `HARNESS_MANIFEST.yaml` without removing current Runtime Control entries.
- [x] Add property policy, propagation debt and Runtime/property cross-contract checks to reusable deterministic contracts.
- [x] Register paired 008 spec/plan/tasks in documentation governance.
- [ ] Run final exact-head full NovelForge CI after this manifest/docs/contracts integration and inspect jobs/artifacts.
- [ ] Recheck current main, exact diff and rollback boundary; keep all downstream Project locks unchanged.
- [ ] Supersede stale PR #75 only after this fresh salvage candidate fully replaces its evidence.
""",
        encoding="utf-8",
    )
    (dst / "tasks.zh-CN.md").write_text(
        """# 008 Tasks · State Integrity P0

## Stage A · #69 property ownership
- [x] 对 state graph、Settlement、Canon/State 与 Project Adapter 完成 evidence/overlap review。
- [x] 定义最小 mutation classes 与 deterministic route vocabulary。
- [x] 实现 resolver/schema + Project-path integration，且不重新解释 legacy Project。
- [x] 从 stale PR #75 salvage 时以 content-addressed blobs 原样保留已验证实现，并重新建立在 current main 上。
- [x] 增加 cross-contract regression：合法 Runtime operational authorization 不能绕过 `settlement_only` Project property。
- [x] Fresh salvage full NovelForge CI `31905483778` 全绿；state-integrity job `95062461054` 实际执行全部 P0 steps。

## Stage B · #63 propagation debt
- [x] 对 state graph、Settlement、memory invalidation、quality evolution 与 resume semantics 完成 overlap review。
- [x] 实现 explicit-dependency、fingerprint-bound debt identity/lifecycle，不做 global invalidation。
- [x] Deterministic regressions 覆盖幂等 replay、conflicting replay rejection、discharge binding、contiguous supersession、evidence-bound waiver 与 restart。
- [x] Debt 始终 non-authoritative / non-executing：不自动 repair、replan、regenerate，不获得 Canon / Framework write。
- [x] 在 #83 修复后的 Runtime Control baseline 上重新验证两套 P0 mechanism。

## Integration / promotion gate
- [x] 把 dedicated State Integrity workflow 接入 current full NovelForge CI。
- [x] 在 `HARNESS_MANIFEST.yaml` 注册 tool/schema/write-boundary semantics，并完整保留 current Runtime Control 条目。
- [x] 在 reusable deterministic contracts 中加入 property policy、propagation debt 与 Runtime/property cross-contract。
- [x] 在 documentation governance 注册成对的 008 spec/plan/tasks。
- [ ] 本次 manifest/docs/contracts integration 后运行 final exact-head full NovelForge CI，并检查 jobs/artifacts。
- [ ] 再核 current main、exact diff 与 rollback boundary；所有 downstream Project lock 保持不变。
- [ ] 只有 fresh salvage candidate 完整替代旧证据后，才 supersede stale PR #75。
""",
        encoding="utf-8",
    )


def patch_harness() -> None:
    replace_once(
        "HARNESS_MANIFEST.yaml",
        "  settlement_runtime: harness/settlement_runtime.py\n  control_plane: harness/control_plane/CONTROL_PLANE.md\n",
        "  settlement_runtime: harness/settlement_runtime.py\n"
        "  property_write_policy: harness/property_write_policy.py\n"
        "  property_write_policy_schema: harness/property_write_policy.schema.json\n"
        "  propagation_debt: harness/propagation_debt.py\n"
        "  propagation_debt_schema: harness/propagation_debt.schema.json\n"
        "  control_plane: harness/control_plane/CONTROL_PLANE.md\n",
        "harness tools",
    )
    replace_once(
        "HARNESS_MANIFEST.yaml",
        "  local_framework_materialization: .novelforge/framework\n  layouts: [standard, mapped]\n",
        "  local_framework_materialization: .novelforge/framework\n"
        "  optional_property_write_policy_path_key: property_write_policy\n"
        "  property_write_policy_absent_behavior: legacy_unmanaged\n"
        "  layouts: [standard, mapped]\n",
        "project engineering",
    )
    replace_once(
        "HARNESS_MANIFEST.yaml",
        "  weekly_maintenance: .github/workflows/novelforge-weekly-maintenance.yml\n  peer_chat:\n",
        "  weekly_maintenance: .github/workflows/novelforge-weekly-maintenance.yml\n"
        "  state_integrity_p0: .github/workflows/novelforge-state-integrity-p0.yml\n"
        "  peer_chat:\n",
        "workflow discovery",
    )
    replace_once(
        "HARNESS_MANIFEST.yaml",
        "scenario-fork-self-test, settlement-runtime-self-test",
        "scenario-fork-self-test, property-write-policy-self-test, propagation-debt-self-test, state-integrity-cross-contract-self-test, settlement-runtime-self-test",
        "normal ci list",
    )
    replace_once(
        "HARNESS_MANIFEST.yaml",
        "  quality_evolution_result_grants_canon_authority: false\n  promotion_gate_result_grants_framework_write: false\n",
        "  quality_evolution_result_grants_canon_authority: false\n"
        "  property_write_policy_grants_canon_authority: false\n"
        "  property_write_policy_grants_framework_write: false\n"
        "  property_write_policy_resolves_write_route_only: true\n"
        "  propagation_debt_grants_canon_authority: false\n"
        "  propagation_debt_grants_framework_write: false\n"
        "  propagation_debt_can_auto_repair: false\n"
        "  propagation_debt_requires_explicit_dependency_evidence: true\n"
        "  promotion_gate_result_grants_framework_write: false\n",
        "write boundary",
    )


def patch_contracts() -> None:
    path = ".github/workflows/novelforge-contracts.yml"
    replace_once(
        path,
        "          python harness/scenario_fork.py --db /tmp/novelforge-scenario-ci.db self-test --path /tmp/novelforge-scenario-selftest-ci.db > scenario-fork-test.json\n"
        "          python quality/findings.py self-test > quality-finding-test.json\n",
        "          python harness/scenario_fork.py --db /tmp/novelforge-scenario-ci.db self-test --path /tmp/novelforge-scenario-selftest-ci.db > scenario-fork-test.json\n"
        "          python harness/property_write_policy.py self-test > property-write-policy-test.json\n"
        "          python harness/propagation_debt.py self-test --path /tmp/novelforge-propagation-debt-contract-ci.db > propagation-debt-test.json\n"
        "          python harness/state_integrity_cross_contract.py > state-integrity-cross-contract.json\n"
        "          python quality/findings.py self-test > quality-finding-test.json\n",
        "contract execution",
    )
    replace_once(
        path,
        "            'scenario-fork-test.json':('scenario_fork_contract','PASS'),'quality-finding-test.json':('quality_finding_contract','PASS'),\n",
        "            'scenario-fork-test.json':('scenario_fork_contract','PASS'),'property-write-policy-test.json':('property_write_policy_contract','PASS'),\n"
        "            'propagation-debt-test.json':('propagation_debt_contract','PASS'),'state-integrity-cross-contract.json':('contract','PASS'),'quality-finding-test.json':('quality_finding_contract','PASS'),\n",
        "contract checks map",
    )
    replace_once(
        path,
        "          assert loaded['memory-tiers-test.json']['grounding_reports_budget_drop'] is True\n          s=loaded['semantic-router-test.json']\n",
        "          assert loaded['memory-tiers-test.json']['grounding_reports_budget_drop'] is True\n"
        "          pw=loaded['property-write-policy-test.json']\n"
        "          assert pw['payload_cannot_self_escalate'] is True\n"
        "          assert pw['mixed_writer_routes_to_reconcile'] is True\n"
        "          assert pw['policy_absence_preserves_legacy_behavior'] is True\n"
        "          assert pw['derived_only_is_non_authoritative'] is True\n"
        "          assert pw['route_authority_is_scoped'] is True\n"
        "          pd=loaded['propagation-debt-test.json']\n"
        "          assert pd['no_global_invalidation_without_dependency'] is True\n"
        "          assert pd['conflicting_replay_is_rejected'] is True\n"
        "          assert pd['restart_preserves_open_debt_without_duplicate'] is True\n"
        "          cross=loaded['state-integrity-cross-contract.json']\n"
        "          assert cross['checks']['runtime_authorization_is_valid_and_granted'] is True\n"
        "          assert cross['checks']['runtime_authorization_scope_excludes_project_write'] is True\n"
        "          assert cross['checks']['runtime_writer_cannot_bypass_settlement_only_property'] is True\n"
        "          assert cross['checks']['only_settlement_writer_gets_guarded_direct_route'] is True\n"
        "          s=loaded['semantic-router-test.json']\n",
        "contract detailed assertions",
    )


def patch_docs_manifest() -> None:
    path = "docs/documentation_manifest.json"
    anchor = '    {"id":"007-production-quality-gate-hardening-tasks","tier":"C","english":"specs/007-production-quality-gate-hardening/tasks.en.md","chinese":"specs/007-production-quality-gate-hardening/tasks.zh-CN.md","audience":"framework quality and runtime maintainers","purpose":"production quality gate hardening task ledger","authority_sources":["specs/007-production-quality-gate-hardening/","quality/",".github/workflows/novelforge-quality-gate-hardening.yml"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"quality-maintainers","status":"candidate_review"},\n'
    additions = (
        '    {"id":"008-state-integrity-p0-spec","tier":"C","english":"specs/008-state-integrity-p0/spec.en.md","chinese":"specs/008-state-integrity-p0/spec.zh-CN.md","audience":"framework state and runtime maintainers","purpose":"property write-source policy and propagation-debt requirements","authority_sources":["specs/008-state-integrity-p0/","harness/property_write_policy.py","harness/property_write_policy.schema.json","harness/propagation_debt.py","HARNESS_MANIFEST.yaml"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"state-integrity-maintainers","status":"candidate_review"},\n'
        '    {"id":"008-state-integrity-p0-plan","tier":"C","english":"specs/008-state-integrity-p0/plan.en.md","chinese":"specs/008-state-integrity-p0/plan.zh-CN.md","audience":"framework state and runtime maintainers","purpose":"state-integrity P0 implementation plan","authority_sources":["specs/008-state-integrity-p0/","harness/property_write_policy.py","harness/propagation_debt.py","HARNESS_MANIFEST.yaml"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"state-integrity-maintainers","status":"candidate_review"},\n'
        '    {"id":"008-state-integrity-p0-tasks","tier":"C","english":"specs/008-state-integrity-p0/tasks.en.md","chinese":"specs/008-state-integrity-p0/tasks.zh-CN.md","audience":"framework state and runtime maintainers","purpose":"state-integrity P0 executable task ledger","authority_sources":["specs/008-state-integrity-p0/",".github/workflows/novelforge-state-integrity-p0.yml",".github/workflows/novelforge-contracts.yml"],"visual_policy":"contract","rewrite_policy":"rebuild","freshness_owner":"state-integrity-maintainers","status":"candidate_review"},\n'
    )
    replace_once(path, anchor, anchor + additions, "documentation registry")


def verify() -> None:
    run("git", "diff", "--check")
    run(sys.executable, "-m", "py_compile", "harness/property_write_policy.py", "harness/propagation_debt.py", "harness/propagation_debt_selftest.py", "harness/state_integrity_cross_contract.py")
    run(sys.executable, "harness/property_write_policy.py", "self-test")
    run(sys.executable, "harness/propagation_debt.py", "self-test", "--path", "/tmp/propagation-debt-integration-v2.db")
    run(sys.executable, "harness/state_integrity_cross_contract.py")
    run(sys.executable, "scripts/version_identity.py")
    run(sys.executable, "scripts/docs_quality.py")
    run(sys.executable, "novelforge.py", "self-test")


def commit() -> None:
    temp_paths = {
        ".github/workflows/tmp-state-integrity-integration-v2.yml",
        "scripts/tmp_state_integrity_integration.py",
    }
    for rel in temp_paths:
        (ROOT / rel).unlink()

    expected = {
        ".github/workflows/novelforge-contracts.yml",
        "HARNESS_MANIFEST.yaml",
        "docs/documentation_manifest.json",
        "specs/008-state-integrity-p0/plan.en.md",
        "specs/008-state-integrity-p0/plan.zh-CN.md",
        "specs/008-state-integrity-p0/spec.en.md",
        "specs/008-state-integrity-p0/spec.zh-CN.md",
        "specs/008-state-integrity-p0/tasks.en.md",
        "specs/008-state-integrity-p0/tasks.zh-CN.md",
        *temp_paths,
    }
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()
    actual: set[str] = set()
    for line in status:
        rel = line[3:]
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        actual.add(rel)
    if actual != expected:
        raise SystemExit(f"unexpected integration diff set: actual={sorted(actual)!r} expected={sorted(expected)!r}")

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "-A")
    run("git", "commit", "-m", "state: integrate P0 contracts and documentation")
    run("git", "push", "origin", "HEAD:agent/state-integrity-p0-v2")


def main() -> int:
    restore_specs()
    patch_harness()
    patch_contracts()
    patch_docs_manifest()
    verify()
    commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
