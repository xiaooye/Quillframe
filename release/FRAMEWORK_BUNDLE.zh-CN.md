# Quillframe Framework Bundle · 中文版

## 目的

Consumer Project 可以传输 deterministic Quillframe runtime bundle。本 bundle fingerprint 只证明 materialized bytes 的 evidence；Project identity 与 authority 仍由 native five-key manifest/context 决定。

Bundle 只是 transport/cache artifact，不是第二权威。fingerprint 不授予 Project authority。

## 格式

- deterministic、未压缩 POSIX tar；
- path 排序固定；
- tar metadata 归一化：`mtime=0`、`uid=gid=0`、空 user/group name；
- mode 归一化（通常 `0644`，可执行 Python/shell entrypoint 为 `0755`）；
- bundle 内含 `BUNDLE_CONTENT_MANIFEST.json`，记录每个 payload path / size / SHA-256；
- 整个 tar exact bytes 再计算一个 `sha256:...` fingerprint。

## 包含

Core、Surface、Harness、Learning、Corpus、Evals、typed Host Bridge 入口与 contract、integration/docs/bootstrap、deterministic scripts 等 Framework runtime material。

## 排除

- `.git` history；
- `specs/` 工程过程记录；
- `.quillframe/` runtime state；
- cache/bytecode；
- SQLite/runtime DB 及 WAL/SHM；
- 已生成的 `release/acceptance/` 报告与任务证明；
- 已生成 bundle 与 bundle verification metadata。

Bundle verification metadata 与 release acceptance 报告故意排除在 fingerprint input 外，避免发布证据反向改变它所证明的 bundle。

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

Verify 会检查 outer fingerprint、tar metadata normalization、file-set identity，以及每个 payload 的 hash/size。

## Evidence 使用

release evidence 可以记录：

```json
{
  "transport": {
    "commit": "<exact git sha>",
    "bundle_fingerprint": "sha256:<64 hex>"
  }
}
```

Materialized bundle fingerprint 不匹配时必须 fail closed 并重新 build；它不能成为 Project runtime authority。

## Security / Authority Boundary

Bundle valid 只能证明 bytes 与 expected fingerprint 一致。它不能证明 Project 接受了故事修改、semantic result 正确，也不会授予 Framework Canon-write authority。

Normal CI 可以 build/verify bundle，因为这是纯 deterministic、model-free 的工程操作。
