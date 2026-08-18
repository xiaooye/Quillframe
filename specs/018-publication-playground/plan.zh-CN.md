# 018 · Publication Playground — 实施计划

## Primary mode

`SYSTEM-IMPROVE`

## 1. Freeze

- base: current `main` SHA `8533c12bec929eac44bf23a9bede45e3b24ea0af`；
- publication authority: `HARNESS_MANIFEST.yaml` + `publication/compiler.py`；
- Product site remains static Cloudflare Pages output；本任务不新增 durable backend。

## 2. Source adapter

在浏览器边界只做输入适配：

- direct `{book, chapters}` → 原样交给 compiler；
- `quillframe_agent_result_v1.final_text` → 构造 playground publication source；
- TXT/Markdown → 构造单章 playground publication source；
- adapter 用 WebCrypto 计算 exact UTF-8 SHA-256；
- adapter 不产生 Accepted/Canon authority。

## 3. Real compiler worker

新增 module Web Worker：

- 使用 Pyodide；
- 通过 Vite `?raw` 加载 exact repository `publication/compiler.py`；
- 调用 Python `compile_ir()` + `build()`；
- 收集真实输出 bytes、MIME、SHA-256、preview 与 validation；
- worker result 全部 `authority=false`。

## 4. Publication Workbench UI

把 ProductApp 的硬编码 publication mock 替换成独立 `PublicationWorkbench`：

- 真实 SVG brand mark；
- format rail；
- drop/upload + textarea；
- runtime loading/compile 状态；
- real TXT/Web/Print/EPUB preview；
- artifact download；
- provenance / validation / authority inspector。

## 5. Verification

- 新增 publication-specific static quality script；
- 纳入 `npm run quality`；
- `tsc --noEmit` + Vite build；
- `publication/compiler.py self-test` 继续作为 compiler deterministic baseline；
- PR CI 后再判断 acceptance readiness。

## 6. Follow-up boundary

Studio `Publication.tsx` ↔ Host Bridge/Core publication contract drift 单独建后续任务；本次不把 product playground 的非权威 upload contract 混入 Project Accepted export path。
