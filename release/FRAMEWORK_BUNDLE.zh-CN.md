# NovelForge Framework Bundle · 中文版

## 目的

Consumer Project 继续锁定 NovelForge exact commit。7.1 额外提供 deterministic runtime bundle，使本地/远程 host 可以验证自己 materialize 的 Framework bytes 是否与 Project lock 一致。

Bundle 只是 transport/cache artifact，不是第二权威。Authority 仍然是 consumer `novelforge.lock.json` 的 exact commit + expected bundle fingerprint。

## 格式

- deterministic、未压缩 POSIX tar；
- path 排序固定；
- tar metadata 归一化：`mtime=0`、`uid=gid=0`、空 user/group name；
- mode 归一化（通常 `0644`，可执行 Python/shell entrypoint 为 `0755`）；
- bundle 内含 `BUNDLE_CONTENT_MANIFEST.json`，记录每个 payload path / size / SHA-256；
- 整个 tar exact bytes 再计算一个 `sha256:...` fingerprint。

## 包含

Core、Surface、Harness、Learning、Corpus、Evals、Project SDK/Adapter、integration/docs/bootstrap、deterministic scripts 等 Framework runtime material。

## 排除

- `.git` history；
- `specs/` 工程过程记录；
- `.novelforge/` runtime state；
- cache/bytecode；
- SQLite/runtime DB 及 WAL/SHM；
- 已生成 bundle 与 bundle attestation metadata。

Bundle attestation 故意排除在 fingerprint input 外，避免“把 fingerprint 写回文件后又改变 fingerprint”的 circular self-hash。

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

Verify 会检查 outer fingerprint、tar metadata normalization、file-set identity，以及每个 payload 的 hash/size。

## Consumer 使用

7.1 consumer 可以记录：

```json
{
  "framework": {
    "commit": "<exact git sha>",
    "bundle_fingerprint": "sha256:<64 hex>"
  }
}
```

Materialized bundle fingerprint 不匹配时，不能静默成为 runtime authority；应重新 fetch/build，或显式升级 lock。

## Security / Authority Boundary

Bundle valid 只能证明 bytes 与 expected fingerprint 一致。它不能证明 Project 接受了故事修改、semantic result 正确，也不会授予 Framework Canon-write authority。

Normal CI 可以 build/verify bundle，因为这是纯 deterministic、model-free 的工程操作。
