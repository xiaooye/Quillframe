# Spec 023 implementation plan · Quillframe Novel-Native Host Boundary

## Scope order

1. Inventory current operation registries, MCP/skill manifests, Host Bridge,
   embedded runtime, Studio read surfaces, and all version sources.
2. Add machine-readable surface capabilities that classify novelist-facing,
   internal/ops, and privileged author operations without duplicating existing
   schemas.
3. Update product/architecture/runtime/integration/Studio documentation and
   paired manifests to state the Host/kernel/Project boundary truthfully.
4. Update the single version source and every required release surface to
   `0.9.1`, preserving historical changelog entries and documenting limits.
5. Add regressions for raw-draft visibility, privileged operation discovery,
   version consistency, optional embedded runtime behavior, and bilingual docs.
6. Run deterministic Python, Studio, site, docs, and Tauri smoke checks; review
   the diff independently before freezing the release candidate.

## Files and ownership

- `specs/023-novel-native-host-boundary/`: paired spec and plan (this contract).
- Existing `studio/host_bridge_contract.json`, MCP/skill manifests, and SDK
  capability registries: machine surface classification only.
- README, architecture, runtime, integration, Studio docs, changelog, and
  version files: wording/identity updates only; no runtime rewrite.
- Existing visibility/authority tests: regressions for the boundary.

No task may expand into a general-purpose agent framework or a site-wide UI
redesign. Any capability not required for the CH001 writer-facing review slice
is recorded as post-v0.9.1 backlog.

## Review gates

- Before implementation: source inventory and paired-document self-audit.
- After implementation: exact version scan, machine-contract validation, clean
  deterministic suite, bundle reproducibility, and independent P0/P1 review.
- Release handoff: verify exact main commit, tag, artifact checksum, and
  post-download install/doctor/MCP/Bridge smoke.
