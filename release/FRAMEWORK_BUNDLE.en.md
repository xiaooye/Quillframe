# NovelForge Framework Bundle

## Purpose

A consuming fiction project pins an exact NovelForge Framework revision. The deterministic Framework bundle lets a local or remote host verify that its materialized Framework bytes match the evidence recorded by the project lock.

The bundle is a transport/cache artifact, not a second authority. Project bootstrap still resolves the exact Framework dependency from `novelforge.lock.json`; a bundle fingerprint proves byte identity for that dependency, not story truth.

## Format

- deterministic uncompressed POSIX tar;
- sorted file paths;
- normalized tar metadata: `mtime=0`, `uid=gid=0`, empty user/group names;
- normalized modes (`0644`, or `0755` for executable Python/shell entrypoints);
- internal `BUNDLE_CONTENT_MANIFEST.json` with path, size and SHA-256 for every payload file;
- overall `sha256:...` fingerprint of exact tar bytes.

## Included

Runtime/Framework material such as Core, Surface, Harness, Learning, Corpus, Evals, Project SDK/Adapter, integration/docs/bootstrap files, schemas, and deterministic scripts according to the current bundle builder contract.

## Excluded

- `.git` history;
- `specs/` engineering work records;
- `.novelforge/` runtime state;
- caches/bytecode;
- SQLite/runtime databases and WAL/SHM files;
- generated bundle files and bundle attestation metadata.

Bundle attestation is excluded intentionally so publishing the fingerprint cannot create a circular self-hash.

## Build

```bash
python release/build_framework_bundle.py build \
  --output dist/novelforge-framework.tar \
  --report dist/novelforge-framework-build.json
```

## Verify

```bash
python release/build_framework_bundle.py verify \
  --bundle dist/novelforge-framework.tar \
  --expected 'sha256:...'
```

Verification checks the outer fingerprint, normalized tar metadata, file-set identity, and every declared payload hash/size.

## Project lock use

A resolved production lock may record evidence such as:

```json
{
  "framework": {
    "name": "NovelForge",
    "version": "<resolved release version>",
    "commit": "<exact git sha>",
    "bundle_fingerprint": "sha256:<64 hex>"
  }
}
```

The exact commit and expected bundle fingerprint are the important reproducibility bindings. Documentation examples deliberately avoid hard-coding a release number that will become stale.

A materialized bundle with a mismatching fingerprint must not silently become runtime authority. Re-fetch/rebuild the expected dependency or perform an explicit Framework upgrade through the Project change workflow.

## Relationship to the Project bundle

Do not confuse two derived artifacts:

- **Framework bundle** — immutable materialization of the pinned generic NovelForge dependency;
- **Project bundle** — indexed derived view of one consuming fiction project's own files/authority mappings.

Neither bundle is a second source of truth. Both are reproducible views whose fingerprints help detect drift.

## Security / authority boundary

A valid Framework bundle proves byte identity relative to the expected fingerprint. It does not prove:

- that a project accepted a story change;
- that a semantic judgment is correct;
- that a session/runtime owns Canon;
- that the Framework may mutate project authority;
- that a newer implementation has been formally promoted to a new release.

Normal CI may build and verify bundles because the operation is deterministic and model-free.

## Release-metadata discipline

The release version advertised by a consuming project must come from the Framework's release authority and exact lock resolution, not from a version number copied out of this guide. If implementation metadata and release metadata drift, report and resolve that through the release workflow rather than editing documentation examples to hide the mismatch.

## Related contracts

- [`build_framework_bundle.py`](build_framework_bundle.py) — deterministic builder/verifier.
- [Project SDK](../docs/project-sdk.en.md) — project manifest, exact lock and derived project bundle.
- [Project Adapter Protocol](../harness/PROJECT_ADAPTER_PROTOCOL.en.md) — dependency materialization and legacy mapping.
- `HARNESS_MANIFEST.yaml` — current Framework release authority.
