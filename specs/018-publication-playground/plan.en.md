# 018 · Publication Playground — Implementation Plan

1. Freeze current main and publication compiler authority.
2. Add a browser-only adapter for publication JSON, `quillframe_agent_result_v1.final_text`, TXT, and Markdown. Compute exact UTF-8 SHA-256 when adapting raw text; never infer Project acceptance.
3. Add a module Web Worker that initializes Pyodide and executes the exact repository `publication/compiler.py` through `compile_ir()` and `build()`.
4. Return real artifact bytes, MIME, SHA-256, preview projection, and validation without persistence or authority.
5. Replace the hard-coded ProductApp publication route with `PublicationWorkbench`.
6. Add upload/drop, source editor, runtime state, real previews, downloads, provenance, and validation UI while preserving Borderless Kawaii Editorial design.
7. Add a deterministic static quality gate and run product quality/build.
8. Leave Studio/Core durable publication contract migration as a separate explicit follow-up.
