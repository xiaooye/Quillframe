# 018 · Publication Playground — 规格

## Primary mode

`SYSTEM-IMPROVE`

## 问题

当前 product site 的 `/publication` 仍是展示型 mock：预览正文、`exact text`、artifact provenance 都是硬编码 UI；截图中的 preview header 还出现了错误/乱码品牌标识。与此同时，仓库已经存在唯一的真实出版编译器 `publication/compiler.py`，能够生成 `clean_text | web_reflow | print_book | epub3`，因此不应再实现一套 TypeScript exporter。

另有已知但不属于本任务主实现范围的 drift：Studio Publication route 与 current Host Bridge `publication.preview` contract 的参数不一致，Core `publication.build` 仍只持久化 `md/txt`。本任务不得借机重构 Canon/SQLite publication authority。

## 目标

把 product site `/publication` 改造成真实、浏览器本地的 Publication Playground：

1. 修复 preview branding，使用 repository 的 Quillframe SVG mark；
2. 支持拖拽/选择 `.json/.txt/.md/.markdown`；
3. 直接执行仓库当前的 `publication/compiler.py`，不复制 compiler 逻辑；
4. 支持 Quillframe publication source JSON，并识别 `quillframe_agent_result_v1.final_text`；
5. 对普通 TXT/Markdown 或 agent `final_text` 建立明确的 playground adapter，计算 exact UTF-8 SHA-256 后构造非权威 publication source；
6. 真实生成 TXT/Web/Print/EPUB artifact，并提供浏览器下载；
7. preview 必须来自真实 compiler artifact，而不是 fixture；
8. Web/Print 用 sandboxed iframe，EPUB preview 从实际 EPUB spine/chapter XHTML 提取；
9. 展示 source fingerprint、artifact fingerprint、text roundtrip 与 EPUB internal validation；
10. 所有 upload/playground source 永远标记 `source_authority_verified=false`、`authority=false`，不得把上传 JSON 自报的 accepted fingerprint 当 Project acceptance 证据；
11. 不写 Project、Canon、SQLite，不执行 SETTLE；
12. EPUB playground 只声明 internal validation；release-grade EPUB 仍要求外部 EPUBCheck。

## 架构

```text
SolidJS Publication Playground
  → browser-local adapter
  → module Web Worker
  → Pyodide
  → exact repository publication/compiler.py
  → quillframe_publication_ir_v1
  → real derived artifacts
  → preview + browser download
```

Pyodide 只作为 Python runtime，不拥有业务规则。业务规则唯一来源仍是 `publication/compiler.py`。

## 输入合同

支持：

- `quillframe_publication_source` 形状：`{book, chapters}`；
- `quillframe_agent_result_v1`：读取 `final_text` 作为 playground text source；
- 纯 `.txt/.md/.markdown`；
- 页面 textarea 中的普通文本或 JSON。

对于上传/粘贴 source：

- compiler 所需 `accepted_fingerprint` 只是 exact-text integrity guard；
- UI 必须明确说明它不证明 Project Accepted authority；
- 若 direct publication source 自带 fingerprint，compiler 仍验证 exact match，但 UI 保持 `source_authority_verified=false`。

## 输出合同

Playground result 至少包含：

- profile；
- compiler identity；
- source fingerprint；
- text roundtrip；
- validation；
- preview kind/content；
- artifacts: name, MIME, bytes, SHA-256；
- `authority=false` / `canon_authority=false` / `source_authority_verified=false`。

## UX

保持现有 Borderless Kawaii Editorial 视觉哲学：warm canvas、排版/留白优先、柔和语义色、少量 kawaii motif。禁止把上传区做成企业 dashboard card soup。

触控目标至少 44px。编译在 Web Worker 中执行，避免阻塞 UI。运行时首次加载可以显示明确的 Python runtime loading 状态。

## 非目标

- 不在本任务中修改 Canon / Settlement 语义；
- 不把 Cloudflare Pages 临时存储当 durable backend；
- 不新增第二套 JS compiler；
- 不声称浏览器 internal EPUB validation 等于 release conformance；
- 不偷偷解决 Studio/Core publication contract drift；该 drift 作为后续工程债单独处理。

## Acceptance

- `npm run quality` 通过；
- `npm run build` 通过；
- static quality 能证明 ProductApp 不再含 publication fixture 正文；
- worker 从 exact `publication/compiler.py?raw` 加载 Python source；
- real download code path 存在；
- branding 使用真实 SVG mark；
- authority boundary 文案与 typed result 明确；
- no direct SQLite/Core authority write path。
