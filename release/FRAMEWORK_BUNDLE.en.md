# Quillframe Framework Bundle

## Purpose

A consuming fiction project may transport a deterministic Quillframe Framework bundle. The bundle fingerprint is evidence about materialized bytes; Project identity and authority remain the native four-key manifest and context with top-level `scope: "novel"`.

The bundle is a transport/cache artifact, not a second authority. A bundle fingerprint proves byte identity for transport evidence, not story truth or Project authority.

## Format

- deterministic uncompressed POSIX tar;
- sorted file paths;
- normalized tar metadata: `mtime=0`, `uid=gid=0`, empty user/group names;
- normalized modes (`0644`, or `0755` for executable Python/shell entrypoints);
- internal `BUNDLE_CONTENT_MANIFEST.json` with path, size and SHA-256 for every payload file;
- overall `sha256:...` fingerprint of exact tar bytes.

## Included

Runtime/Framework material such as Core, Surface, Harness, Learning, Corpus, Evals, the typed Host Bridge entry and contract, integration/docs/bootstrap files, schemas, and deterministic scripts according to the current bundle builder contract.

## Excluded

- `.git` history;
- `specs/` engineering work records;
- `.quillframe/` runtime state;
- caches/bytecode;
- SQLite/runtime databases and WAL/SHM files;
- generated `release/acceptance/` reports and task attestations;
- generated bundle files and bundle verification metadata.

Bundle verification metadata and release acceptance reports are excluded intentionally so publishing evidence cannot recursively alter the bundle it attests.

## Build

```bash
python release/build_framework_bundle.py build \
  --output dist/quillframe-framework.tar \
  --report dist/quillframe-framework-build.json
```

## Verify

```bash
python release/build_framework_bundle.py verify \
  --bundle dist/quillframe-framework.tar \
  --expected 'sha256:...'
```

Verification checks the outer fingerprint, normalized tar metadata, file-set identity, and every declared payload hash/size.

## Evidence use

A release evidence record may contain:

```json
{
  "transport": {
    "name": "Quillframe",
    "version": "<resolved release version>",
    "commit": "<exact git sha>",
    "bundle_fingerprint": "sha256:<64 hex>"
  }
}
```

The exact commit and bundle fingerprint are reproducibility evidence. They do not replace the Project's native manifest or context.

A materialized bundle with a mismatching fingerprint must fail closed and be rebuilt. It must never become Project runtime authority.

## Relationship to the Project bundle

Do not confuse two derived artifacts:

- **Framework bundle** — immutable materialization of the pinned generic Quillframe dependency;
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

The release version advertised by a consuming project must come from the Framework release authority and exact commit/bundle fingerprint evidence, not from a version number copied out of this guide. If implementation metadata and release metadata drift, report and resolve that through the release workflow rather than editing documentation examples to hide the mismatch. This evidence never becomes Project authority.

## Related contracts

- [`build_framework_bundle.py`](build_framework_bundle.py) — deterministic builder/verifier.
- [Native Project Contract](../docs/project-contract.en.md) — exact four-key Project identity, novel context, fingerprint, and storage boundary.
- `HARNESS_MANIFEST.yaml` — current Framework release authority.
