# NovelForge Framework Bundle

## Purpose

A consuming fiction project pins an exact NovelForge commit. NovelForge 7.1 additionally supports a deterministic runtime bundle so a local or remote host can verify that its materialized Framework bytes match the project lock.

The bundle is a transport/cache artifact, not a second authority. Authority remains the consumer `novelforge.lock.json` exact commit + expected bundle fingerprint.

## Format

- deterministic uncompressed POSIX tar;
- sorted file paths;
- normalized tar metadata: `mtime=0`, `uid=gid=0`, empty user/group names;
- normalized modes (`0644`, or `0755` for executable Python/shell entrypoints);
- internal `BUNDLE_CONTENT_MANIFEST.json` with path, size and SHA-256 for every payload file;
- overall `sha256:...` fingerprint of exact tar bytes.

## Included

Runtime/framework material such as Core, Surface, Harness, Learning, Corpus, Evals, Project SDK/Adapter, integration/docs/bootstrap files and deterministic scripts.

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

## Consumer Use

A 7.1 consumer may record:

```json
{
  "framework": {
    "commit": "<exact git sha>",
    "bundle_fingerprint": "sha256:<64 hex>"
  }
}
```

A materialized bundle with a mismatching fingerprint must not silently become runtime authority. Re-fetch/rebuild or explicitly upgrade the lock.

## Security / Authority Boundary

A valid bundle proves byte identity relative to the expected fingerprint. It does not prove that the project accepted a story change, that a semantic result is correct, or that the Framework has Canon-write authority.

Normal CI may build and verify bundles because this is deterministic and model-free.
