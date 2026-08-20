/// <reference lib="webworker" />

import { loadPyodide, version as pyodideVersion } from "pyodide";
import compilerSource from "../../publication/compiler.py?raw";
import { createExclusiveWorkerExecutor, retryableRuntime } from "./workerLifecycle";

export type PublicationCompilerProfile = "clean_text" | "web_reflow" | "print_book" | "epub3";

type CompileRequest = {
  id: string;
  profile: PublicationCompilerProfile;
  source: Record<string, unknown>;
};

type WorkerRequest = {
  kind: "compile";
  payload: CompileRequest;
};

type WorkerResponse =
  | { kind: "ready"; pyodide_version: string }
  | { kind: "result"; id: string; result: string }
  | { kind: "error"; id: string; error: string };

const worker = self as DedicatedWorkerGlobalScope;
type PyodideRuntime = Awaited<ReturnType<typeof loadPyodide>>;

const PYTHON_BOOTSTRAP = String.raw`
import base64
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

_qf_compiler_namespace = {
    "__name__": "quillframe_publication_compiler",
    "__file__": "/tmp/quillframe-publication-compiler.py",
}
exec(compile(Path("/tmp/quillframe-publication-compiler.py").read_text(encoding="utf-8"), "/tmp/quillframe-publication-compiler.py", "exec"), _qf_compiler_namespace)


def _qf_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt": return "text/plain;charset=utf-8"
    if suffix in {".html", ".xhtml"}: return "text/html;charset=utf-8"
    if suffix == ".json": return "application/json;charset=utf-8"
    if suffix == ".epub": return "application/epub+zip"
    if suffix == ".css": return "text/css;charset=utf-8"
    return "application/octet-stream"


def _qf_artifact(path: Path, relative_name: str | None = None) -> dict:
    data = path.read_bytes()
    return {
        "name": relative_name or path.name,
        "mime": _qf_mime(path),
        "size": len(data),
        "sha256": _qf_compiler_namespace["sha256_bytes"](data),
        "base64": base64.b64encode(data).decode("ascii"),
    }


def qf_compile_publication(source_json: str, profile: str) -> str:
    source = json.loads(source_json)
    compile_ir = _qf_compiler_namespace["compile_ir"]
    build = _qf_compiler_namespace["build"]
    validate_epub = _qf_compiler_namespace["validate_epub"]
    ir = compile_ir(source)
    root = Path(tempfile.mkdtemp(prefix="qf-publication-playground-"))
    try:
        preview = {"kind": "text", "content": ""}
        validation = None
        artifacts = []
        if profile == "clean_text":
            output = root / "clean"
            report = build(ir, profile, output)
            txt_files = sorted(output.glob("*.txt"))
            artifacts = [_qf_artifact(path, path.name) for path in txt_files]
            ir_path = output / "publication-ir.json"
            if ir_path.exists(): artifacts.append(_qf_artifact(ir_path, ir_path.name))
            if txt_files:
                preview = {"kind": "text", "content": txt_files[0].read_text(encoding="utf-8")}
            validation = {
                "valid": bool(report["detail"].get("text_roundtrip")),
                "text_roundtrip": bool(report["detail"].get("text_roundtrip")),
                "kind": "exact-text-roundtrip",
            }
        elif profile in {"web_reflow", "print_book"}:
            output = root / profile
            report = build(ir, profile, output)
            html_name = "index.html" if profile == "web_reflow" else "book.html"
            html_path = output / html_name
            artifacts = [_qf_artifact(html_path, html_name)]
            ir_path = output / "publication-ir.json"
            if ir_path.exists(): artifacts.append(_qf_artifact(ir_path, ir_path.name))
            preview = {"kind": "html", "content": html_path.read_text(encoding="utf-8")}
            validation = {
                "valid": bool(report["detail"].get("text_roundtrip")),
                "text_roundtrip": bool(report["detail"].get("text_roundtrip")),
                "kind": "html-text-roundtrip",
            }
        elif profile == "epub3":
            output = root / "publication.epub"
            report = build(ir, profile, output)
            validation = validate_epub(output, ir=ir)
            artifacts = [_qf_artifact(output, "publication.epub")]
            with zipfile.ZipFile(output) as zf:
                chapter_names = sorted(name for name in zf.namelist() if name.startswith("EPUB/chapter-") and name.endswith(".xhtml"))
                content = zf.read(chapter_names[0]).decode("utf-8") if chapter_names else ""
                preview = {"kind": "xhtml", "content": content, "entry": chapter_names[0] if chapter_names else None}
        else:
            raise ValueError(f"unsupported playground profile: {profile}")

        detail = report.get("detail", {})
        return json.dumps({
            "schema": "quillframe_publication_playground_result_v1",
            "profile": profile,
            "compiler": "publication/compiler.py",
            "compiler_runtime": f"pyodide-{__import__('sys').version.split()[0]}",
            "source_fingerprint": ir["source_fingerprint"],
            "text_preservation": ir["text_preservation"],
            "text_roundtrip": bool(detail.get("text_roundtrip")),
            "source_authority_verified": False,
            "preview": preview,
            "validation": validation,
            "artifacts": artifacts,
            "accepted_chapters": [
                {
                    "chapter_id": chapter["chapter_id"],
                    "title": chapter["title"],
                    "accepted_fingerprint": chapter["accepted_fingerprint"],
                }
                for chapter in ir["chapters"]
            ],
            "authority": False,
            "canon_authority": False,
            "settlement_authority": False,
            "mutation_performed": False,
            "model_execution": False,
        }, ensure_ascii=False, separators=(",", ":"))
    finally:
        shutil.rmtree(root, ignore_errors=True)
`;

const getRuntime = retryableRuntime(async (): Promise<PyodideRuntime> => {
      const pyodide = await loadPyodide({
        indexURL: new URL("/pyodide/", worker.location.origin).href,
      });
      pyodide.FS.writeFile("/tmp/quillframe-publication-compiler.py", compilerSource);
      await pyodide.runPythonAsync(PYTHON_BOOTSTRAP);
      worker.postMessage({ kind: "ready", pyodide_version: pyodideVersion } satisfies WorkerResponse);
      return pyodide;
});

const executor = createExclusiveWorkerExecutor();

worker.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  if (event.data?.kind !== "compile") return;
  const { id, profile, source } = event.data.payload;
  const run = executor.run(
    getRuntime,
    async (pyodide) => {
      pyodide.globals.set("qf_source_json", JSON.stringify(source));
      pyodide.globals.set("qf_profile", profile);
      const result = await pyodide.runPythonAsync("qf_compile_publication(qf_source_json, qf_profile)");
      worker.postMessage({ kind: "result", id, result: String(result) } satisfies WorkerResponse);
    },
    (pyodide) => {
      pyodide.globals.delete("qf_source_json");
      pyodide.globals.delete("qf_profile");
    },
  );
  if (!run.accepted) {
    worker.postMessage({ kind: "error", id, error: "worker_busy" } satisfies WorkerResponse);
    return;
  }
  void run.promise.catch((value) => {
    const error = value instanceof Error ? value.message : String(value);
    worker.postMessage({ kind: "error", id, error } satisfies WorkerResponse);
  });
};
