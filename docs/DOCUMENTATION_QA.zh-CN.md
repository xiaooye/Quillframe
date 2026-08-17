# Documentation QA

Documentation QA 用来验证 Quillframe 的当前解释仍然与 current implementation 对齐，同时不让 deterministic prose checker 假装自己拥有 semantic judgment。

## Deterministic Checks

Documentation gate 应验证 manifest registration、paired-language presence、每篇 registered page 只有一个 H1、local link/asset、UTF-8、current Framework version identity、stable router path，以及 SVG parseability/accessibility metadata。

Current public-brand surface 必须使用 Quillframe；allowlist 中的 technical identifier 与 historical record 可以保留 legacy namespace。Brand-leak check 必须有 scope，明确禁止 global string replace。

## Visual Checks

Documentation-owned SVG 要检查 valid viewBox、non-empty `<title>/<desc>`、合法颜色、不嵌入 font file、label 可读。Human review 另外执行 border budget：不承载信息的 border、card background、decoration、container 默认删除。

验收问题不是“够不够 pastel”，而是信息能否用更少 visual ink 仍然清晰，以及整页是否像 editorial canvas，而不是 dashboard。

## Semantic Review

Human/model documentation review 负责判断 mental model 是否吻合 implementation、diagram 的 authority relation 是否正确、EN/zh-CN 是否 semantic parity，以及文档有没有把 evidence 偷偷写成 authority。

Deterministic green check 本身不能证明这些 semantic property。

## Historical Records

Historical spec 保留写作当时真实使用的 public name 与 terminology。Current docs 可以加说明或链接，但 reconstruction 不改写历史。

## Scope Guard

Documentation work 不修改 Product UI、Godot/Solid/React/Vue implementation、application CSS、runtime semantics 或 consumer Project state。发现 scope 外问题，只记录为 `UI_REBRAND_FOLLOWUP` 或 `DOCUMENTATION_DISCOVERED_IMPLEMENTATION_GAP`。
