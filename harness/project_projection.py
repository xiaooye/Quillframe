"""Mapped Project runtime projection.

This is deliberately a small, explicit compiler boundary.  A mapped Project
declares which files are sources and how each source becomes a bounded runtime
object; Core never infers Markdown semantics.  Git/Markdown remains the
durable authority.  The SQLite rows written here are rebuildable, non-Cannon
runtime projections only.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from persistence.quillframe_sqlite import QuillframeStore, now_iso

MANIFEST_SCHEMA = "quillframe_runtime_context_manifest_v1"
PREVIEW_SCHEMA = "quillframe_project_projection_preview_v1"
RECEIPT_SCHEMA = "quillframe_project_projection_receipt_v1"
STATUS_SCHEMA = "quillframe_project_projection_status_v1"
PREFLIGHT_SCHEMA = "quillframe_project_projection_preflight_v1"

_DANGEROUS_AUTHORITY = {
    "accepted", "accepted_canon", "canon", "locked", "settled", "settlement",
    "authoritative", "authority", "final", "published",
}
_SAFE_AUTHORITY = {"project_defined", "project", "project_design", "project_character_design", "project_plan", "project_profile", "active_plan", "proposal", "derived", "research", "source"}
_TARGET_TYPES = {"story_node", "document"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def fingerprint(value: Any) -> str:
    return fingerprint_bytes(canonical(value).encode("utf-8"))


def _json(value: Any, fallback: Any = None) -> Any:
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return fallback


def _manifest_path(project_root: Path, toml_manifest: dict[str, Any]) -> Path | None:
    raw = ((toml_manifest.get("paths") or {}).get("runtime_context_manifest"))
    if raw in (None, ""):
        return None
    if not isinstance(raw, str):
        raise ValueError("paths.runtime_context_manifest must be a path string")
    path = (project_root / raw).resolve()
    root = project_root.resolve()
    if path != root and root not in path.parents:
        raise ValueError("runtime_context_manifest escapes project root")
    if not path.is_file():
        raise FileNotFoundError(f"runtime context manifest does not exist: {raw}")
    return path


def _load_manifest(project_root: Path, toml_manifest: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    path = _manifest_path(project_root, toml_manifest)
    if path is None:
        raise ValueError("mapped Project has no paths.runtime_context_manifest")
    raw = path.read_bytes()
    manifest_fp = fingerprint_bytes(raw)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("runtime context manifest must be UTF-8 JSON") from exc
    if not isinstance(value, dict) or value.get("schema") not in {MANIFEST_SCHEMA, "quillframe_mapped_runtime_context_manifest_draft_v0"}:
        raise ValueError(f"runtime context manifest schema must be {MANIFEST_SCHEMA}")
    return value, manifest_fp, path.relative_to(project_root).as_posix()


def _items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("sources", manifest.get("objects", manifest.get("items")))
    if not isinstance(raw, list) or not raw:
        raise ValueError("runtime context manifest requires non-empty sources array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw_item in enumerate(raw):
        if not isinstance(raw_item, dict):
            raise ValueError(f"runtime context source {index} must be object")
        item = dict(raw_item)
        stable_id = str(item.get("stable_id", item.get("source_id", item.get("id", "")))).strip()
        if not stable_id or stable_id in seen:
            raise ValueError(f"runtime context source {index} stable_id must be unique")
        seen.add(stable_id)
        source_path = item.get("source_path", item.get("path", item.get("source")))
        if not isinstance(source_path, str) or not source_path.strip():
            raise ValueError(f"runtime context source {stable_id} requires source_path")
        object_type = str(item.get("object_type", item.get("type", ""))).strip()
        if not object_type:
            raise ValueError(f"runtime context source {stable_id} requires object_type")
        authority = str(item.get("authority", "" )).strip().lower()
        if authority in _DANGEROUS_AUTHORITY or authority not in _SAFE_AUTHORITY:
            raise ValueError(f"runtime context source {stable_id} has forbidden authority: {authority or '<missing>'}")
        lifecycle = str(item.get("lifecycle", "" )).strip()
        domain = str(item.get("domain", "" )).strip()
        stages = item.get("allowed_stages", item.get("stages"))
        if not lifecycle or not domain or not isinstance(stages, list) or not stages or any(not isinstance(x, str) or not x.strip() for x in stages):
            raise ValueError(f"runtime context source {stable_id} requires lifecycle, domain, and allowed_stages")
        # The draft Task-3 consumer contract used a list of target ids and a
        # bounded_runtime_payload object.  It is accepted only as this named,
        # frozen compatibility schema; no Markdown semantics are inferred.
        if "bounded_runtime_payload" in item and "runtime_payload" not in item and "payload" not in item:
            item["runtime_payload"] = item["bounded_runtime_payload"]
        target = item.get("target")
        if target is None and isinstance(item.get("targets"), list):
            targets = [str(value).strip() for value in item["targets"] if str(value).strip()]
            if not targets or len(set(targets)) != 1:
                raise ValueError(f"runtime context source {stable_id} requires one deterministic target")
            target = {"type": "story_node", "id": targets[0]}
        if not isinstance(target, dict):
            target = {
                "type": item.get("target_type", item.get("target_object_type")),
                "id": item.get("target_id", item.get("target_ref")),
            }
        target = dict(target)
        target_type = str(target.get("type", target.get("object_type", ""))).strip()
        target_id = str(target.get("id", target.get("target_id", ""))).strip()
        if target_type not in _TARGET_TYPES or not target_id:
            raise ValueError(f"runtime context source {stable_id} requires story_node or document target")
        target["type"] = target_type
        target["id"] = target_id
        if target_type == "story_node":
            target.setdefault("title", target_id)
        expected = item.get("source_fingerprint", item.get("fingerprint"))
        if not isinstance(expected, str) or not expected.startswith("sha256:"):
            raise ValueError(f"runtime context source {stable_id} requires source_fingerprint")
        payload = item.get("runtime_payload", item.get("payload"))
        if not isinstance(payload, dict):
            raise ValueError(f"runtime context source {stable_id} requires bounded runtime_payload object")
        result.append({
            "stable_id": stable_id,
            "source_path": source_path.strip(),
            "source_fingerprint": expected,
            "object_type": object_type,
            "authority": authority,
            "lifecycle": lifecycle,
            "domain": domain,
            "allowed_stages": sorted(set(x.strip() for x in stages)),
            "target": target,
            "runtime_payload": payload,
        })
    return sorted(result, key=lambda x: x["stable_id"])


def _read_sources(project_root: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root = project_root.resolve()
    out: list[dict[str, Any]] = []
    for item in items:
        path = (root / item["source_path"]).resolve()
        if path != root and root not in path.parents:
            raise ValueError(f"mapped source escapes project root: {item['source_path']}")
        if not path.is_file():
            raise FileNotFoundError(f"mapped source does not exist: {item['source_path']}")
        actual = fingerprint_bytes(path.read_bytes())
        if actual != item["source_fingerprint"]:
            raise ValueError(f"mapped source drift: {item['stable_id']}")
        runtime_payload = dict(item["runtime_payload"])
        ref = runtime_payload.get("ref")
        expected_projection = runtime_payload.get("fingerprint")
        if ref is not None:
            if not isinstance(ref, str) or not isinstance(expected_projection, str):
                raise ValueError(f"bounded runtime payload ref/fingerprint required: {item['stable_id']}")
            projection_path = (root / ref).resolve()
            if projection_path != root and root not in projection_path.parents:
                raise ValueError(f"bounded runtime payload escapes project root: {ref}")
            if not projection_path.is_file():
                raise FileNotFoundError(f"bounded runtime payload does not exist: {ref}")
            projection_bytes = projection_path.read_bytes()
            if fingerprint_bytes(projection_bytes) != expected_projection:
                raise ValueError(f"bounded runtime payload drift: {item['stable_id']}")
            try:
                runtime_payload["content"] = json.loads(projection_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"bounded runtime payload must be UTF-8 JSON: {item['stable_id']}") from exc
        out.append({**item, "source_fingerprint": actual, "runtime_payload": runtime_payload})
    return out


def _projection_fingerprint(manifest_fp: str, items: list[dict[str, Any]]) -> tuple[str, str]:
    universe = fingerprint([
        {"stable_id": x["stable_id"], "source_fingerprint": x["source_fingerprint"], "projection": {
            "object_type": x["object_type"], "authority": x["authority"], "lifecycle": x["lifecycle"],
            "domain": x["domain"], "allowed_stages": x["allowed_stages"], "target": x["target"], "runtime_payload": x["runtime_payload"],
        }} for x in items
    ])
    return universe, fingerprint({"manifest_fingerprint": manifest_fp, "source_universe_fingerprint": universe})


def _target_order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable topological order for target graph materialization."""
    by_target = {item["target"]["id"]: item for item in items if item["target"]["type"] == "story_node"}
    ordered: list[dict[str, Any]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item: dict[str, Any]) -> None:
        target_id = item["target"]["id"]
        if target_id in visited:
            return
        if target_id in visiting:
            raise ValueError(f"story target graph contains a cycle: {target_id}")
        visiting.add(target_id)
        parent_id = item["target"].get("parent_id")
        if parent_id and parent_id in by_target:
            visit(by_target[parent_id])
        visiting.remove(target_id)
        visited.add(target_id)
        ordered.append(item)

    for item in sorted(by_target.values(), key=lambda x: x["target"]["id"]):
        visit(item)
    ordered.extend(sorted((item for item in items if item["target"]["type"] == "document"), key=lambda x: x["target"]["id"]))
    # Multiple sources may intentionally target the same node; preserve one
    # deterministic source ordering for each target after graph prerequisites.
    seen = set()
    result = []
    for item in ordered + sorted(items, key=lambda x: x["stable_id"]):
        key = item["stable_id"]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _rows_match(conn: sqlite3.Connection, items: list[dict[str, Any]], projection_fp: str) -> bool:
    expected = {item["stable_id"]: item for item in items}
    rows = conn.execute("SELECT * FROM project_context_sources ORDER BY stable_id").fetchall()
    if {row["stable_id"] for row in rows} != set(expected):
        return False
    for row in rows:
        item = expected[row["stable_id"]]
        if row["projection_fingerprint"] != projection_fp or row["source_fingerprint"] != item["source_fingerprint"] or row["object_type"] != item["object_type"] or row["authority_class"] != item["authority"] or row["lifecycle"] != item["lifecycle"] or row["domain"] != item["domain"]:
            return False
        if _json(row["allowed_stages_json"], None) != item["allowed_stages"] or _json(row["target_json"], None) != item["target"] or _json(row["runtime_payload_json"], None) != item["runtime_payload"]:
            return False
    return True


def preview(project_root: Path, *, toml_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read and compile a mapped manifest without opening or writing SQLite."""
    root = project_root.expanduser().resolve()
    if toml_manifest is None:
        import tomllib
        with (root / "quillframe.toml").open("rb") as fh:
            toml_manifest = tomllib.load(fh)
    manifest, manifest_fp, manifest_path = _load_manifest(root, toml_manifest)
    declared_items = _items(manifest)
    context_set = manifest.get("context_set")
    if isinstance(context_set, dict) and isinstance(context_set.get("allowed_object_ids"), list):
        allowed = {str(value) for value in context_set["allowed_object_ids"]}
        outside = sorted(item["stable_id"] for item in declared_items if item["stable_id"] not in allowed)
        if outside:
            raise ValueError("runtime context source outside declared allowed_object_ids: " + ", ".join(outside))
    items = _read_sources(root, declared_items)
    # A mapped chapter declaration may explicitly bind both its story node and
    # document at manifest level.  Keep that binding in the compiled target;
    # Core never guesses a document from arbitrary Markdown.
    manifest_target = manifest.get("target")
    if isinstance(manifest_target, dict) and manifest_target.get("document_id"):
        for item in items:
            if item["target"]["type"] == "story_node":
                item["target"]["document_id"] = str(manifest_target["document_id"])
    if isinstance(manifest_target, dict) and manifest_target.get("story_node_id"):
        expected_target = str(manifest_target["story_node_id"])
        outside_targets = sorted({item["target"]["id"] for item in items if item["target"]["type"] == "story_node" and item["target"]["id"] != expected_target})
        if outside_targets:
            raise ValueError("runtime context target outside declared story_node_id: " + ", ".join(outside_targets))
    source_universe_fp, projection_fp = _projection_fingerprint(manifest_fp, items)
    return {
        "schema": PREVIEW_SCHEMA,
        "project_id": str((toml_manifest.get("project") or {}).get("id") or manifest.get("project_id") or ""),
        "manifest_path": manifest_path,
        "manifest_fingerprint": manifest_fp,
        "source_universe_fingerprint": source_universe_fp,
        "projection_fingerprint": projection_fp,
        "objects": items,
        "authority": False,
        "mutation_performed": False,
        "model_invocations": 0,
    }


def _target_apply(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    target = item["target"]
    target_type, target_id = target["type"], target["id"]
    if target_type == "story_node":
        kind = str(target.get("kind", item["object_type"] if item["object_type"] in {"book", "volume", "arc", "unit", "chapter", "scene"} else "chapter"))
        if kind not in {"book", "volume", "arc", "unit", "chapter", "scene"}:
            raise ValueError(f"invalid story node kind: {kind}")
        parent = target.get("parent_id")
        ordinal = int(target.get("ordinal", 0))
        title = str(target.get("title") or item["stable_id"])
        metadata = target.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"story node metadata must be object: {target_id}")
        existing = conn.execute("SELECT * FROM story_nodes WHERE node_id=?", (target_id,)).fetchone()
        if existing:
            if any(existing[key] != value for key, value in (("parent_id", parent), ("kind", kind), ("ordinal", ordinal), ("title", title))):
                raise ValueError(f"story node target conflict: {target_id}")
        else:
            conn.execute("INSERT INTO story_nodes(node_id,parent_id,kind,ordinal,title,pov_character_id,location_id,metadata_json) VALUES(?,?,?,?,?,?,?,?)", (target_id, parent, kind, ordinal, title, target.get("pov_character_id"), target.get("location_id"), canonical(metadata)))
        document_id = target.get("document_id")
        if document_id:
            document_id = str(document_id)
            doc_kind = str(target.get("document_kind", "plan"))
            title_for_doc = str(target.get("document_title") or title)
            existing_doc = conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
            if existing_doc:
                if any(existing_doc[key] != value for key, value in (("story_node_id", target_id), ("document_kind", doc_kind), ("title", title_for_doc))):
                    raise ValueError(f"document target conflict: {document_id}")
            else:
                conn.execute("INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,?,?,?)", (document_id, target_id, doc_kind, title_for_doc, now_iso()))
    else:
        doc_kind = str(target.get("document_kind", "plan"))
        if doc_kind not in {"manuscript", "note", "plan", "research_note", "publication_source"}:
            raise ValueError(f"invalid document kind: {doc_kind}")
        title = str(target.get("title") or item["stable_id"])
        story_node_id = target.get("story_node_id")
        existing = conn.execute("SELECT * FROM documents WHERE document_id=?", (target_id,)).fetchone()
        if existing:
            if any(existing[key] != value for key, value in (("story_node_id", story_node_id), ("document_kind", doc_kind), ("title", title))):
                raise ValueError(f"document target conflict: {target_id}")
            return
        if story_node_id and not conn.execute("SELECT 1 FROM story_nodes WHERE node_id=?", (story_node_id,)).fetchone():
            raise ValueError(f"document target story node missing: {story_node_id}")
        conn.execute("INSERT INTO documents(document_id,story_node_id,document_kind,title,created_at) VALUES(?,?,?,?,?)", (target_id, story_node_id, doc_kind, title, now_iso()))


def apply(project_root: Path, *, data_dir: Path | None = None, expected_projection_fingerprint: str | None = None, toml_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply one exact preview in a single project SQLite transaction."""
    compiled = preview(project_root, toml_manifest=toml_manifest)
    projection_fp = compiled["projection_fingerprint"]
    project_id = compiled["project_id"]
    if not project_id:
        raise ValueError("mapped Project project.id is required")
    store = QuillframeStore(data_dir)
    location = store.location(project_id)
    created_project = not location.database.exists()
    if created_project:
        project = (toml_manifest or {}).get("project", {}) if toml_manifest else {}
        store.create_project(project_id, str(project.get("title") or project_id), str(project.get("language") or "zh-CN"))
    with store.open_project(project_id) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            identity = conn.execute("SELECT project_id FROM project_identity").fetchone()
            if not identity or identity["project_id"] != project_id:
                raise ValueError("mapped projection Project database identity mismatch")
            latest = conn.execute("SELECT * FROM project_projection_receipts ORDER BY created_at DESC,rowid DESC LIMIT 1").fetchone()
            if latest and latest["projection_fingerprint"] == projection_fp:
                if not _rows_match(conn, compiled["objects"], projection_fp):
                    raise ValueError("projection idempotent replay found tampered runtime rows")
                conn.rollback()
                return json.loads(latest["receipt_json"])
            if latest and expected_projection_fingerprint is None:
                raise ValueError("projection CAS requires expected_projection_fingerprint for replacement")
            if latest and latest["projection_fingerprint"] != expected_projection_fingerprint:
                raise ValueError("projection CAS current fingerprint mismatch")
            for item in _target_order(compiled["objects"]):
                _target_apply(conn, item)
                conn.execute(
                "INSERT INTO project_context_sources(stable_id,source_path,source_fingerprint,object_type,authority_class,lifecycle,domain,allowed_stages_json,target_json,runtime_payload_json,manifest_fingerprint,projection_fingerprint,applied_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(stable_id) DO UPDATE SET source_path=excluded.source_path,source_fingerprint=excluded.source_fingerprint,object_type=excluded.object_type,authority_class=excluded.authority_class,lifecycle=excluded.lifecycle,domain=excluded.domain,allowed_stages_json=excluded.allowed_stages_json,target_json=excluded.target_json,runtime_payload_json=excluded.runtime_payload_json,manifest_fingerprint=excluded.manifest_fingerprint,projection_fingerprint=excluded.projection_fingerprint,applied_at=excluded.applied_at",
                    (item["stable_id"], item["source_path"], item["source_fingerprint"], item["object_type"], item["authority"], item["lifecycle"], item["domain"], canonical(item["allowed_stages"]), canonical(item["target"]), canonical(item["runtime_payload"]), compiled["manifest_fingerprint"], projection_fp, now_iso()),
                )
            ids = [item["stable_id"] for item in compiled["objects"]]
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM project_context_sources WHERE stable_id NOT IN ({placeholders})", ids)
            receipt = {"schema": RECEIPT_SCHEMA, "project_id": project_id, "manifest_fingerprint": compiled["manifest_fingerprint"], "source_universe_fingerprint": compiled["source_universe_fingerprint"], "projection_fingerprint": projection_fp, "object_count": len(compiled["objects"]), "status": "applied", "authority": False, "accepted": False, "settled": False}
            conn.execute("INSERT INTO project_projection_receipts(projection_fingerprint,manifest_fingerprint,source_universe_fingerprint,status,receipt_json,created_at) VALUES(?,?,?,?,?,?)", (projection_fp, compiled["manifest_fingerprint"], compiled["source_universe_fingerprint"], "applied", canonical(receipt), now_iso()))
            conn.commit()
            return receipt
        except Exception:
            conn.rollback()
            if created_project:
                # This operation created the only project database.  Remove
                # exactly that newly-created location and registry row so a
                # failed target/CAS cannot leave a half-materialized Project.
                try:
                    with sqlite3.connect(store.global_db) as global_conn:
                        global_conn.execute("DELETE FROM project_registry WHERE project_id=?", (project_id,))
                        global_conn.commit()
                    shutil.rmtree(location.directory, ignore_errors=False)
                except OSError:
                    # The original contract failure remains the useful error;
                    # status/doctor will surface any cleanup residue.
                    pass
            raise


def status(project_root: Path, *, data_dir: Path | None = None, toml_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = project_root.expanduser().resolve()
    try:
        compiled = preview(root, toml_manifest=toml_manifest)
        preview_error = None
    except Exception as exc:
        compiled, preview_error = None, f"{type(exc).__name__}: {exc}"
    project_id = compiled["project_id"] if compiled else ""
    if not project_id:
        try:
            import tomllib
            with (root / "quillframe.toml").open("rb") as fh: project_id = str((tomllib.load(fh).get("project") or {}).get("id") or "")
        except Exception: pass
    latest = None; projected_count = 0
    if project_id:
        try:
            with QuillframeStore(data_dir).open_project(project_id) as conn:
                identity = conn.execute("SELECT project_id FROM project_identity").fetchone()
                if not identity or identity["project_id"] != project_id:
                    raise ValueError("mapped projection Project database identity mismatch")
                row = conn.execute("SELECT * FROM project_projection_receipts ORDER BY created_at DESC,rowid DESC LIMIT 1").fetchone()
                latest = dict(row) if row else None
                projected_count = int(conn.execute("SELECT COUNT(*) AS n FROM project_context_sources").fetchone()["n"])
                if compiled and latest and latest.get("projection_fingerprint") == compiled["projection_fingerprint"]:
                    rows_match = _rows_match(conn, compiled["objects"], compiled["projection_fingerprint"])
                else:
                    rows_match = False
        except Exception as exc:
            if preview_error is None: preview_error = f"{type(exc).__name__}: {exc}"
            rows_match = False
    else:
        rows_match = False
    current_fp = compiled["projection_fingerprint"] if compiled else None
    applied_fp = latest.get("projection_fingerprint") if latest else None
    ready = preview_error is None and current_fp == applied_fp and rows_match
    return {"schema": STATUS_SCHEMA, "project_id": project_id, "ready": ready, "state": "current" if ready else ("stale" if latest else "unapplied"), "preview_error": preview_error, "manifest_fingerprint": compiled.get("manifest_fingerprint") if compiled else None, "source_universe_fingerprint": compiled.get("source_universe_fingerprint") if compiled else None, "projection_fingerprint": current_fp, "applied_projection_fingerprint": applied_fp, "projected_object_count": projected_count, "projection_rows_match": rows_match, "authority": False}


def materialize_context(project_root: Path, stage: str, *, data_dir: Path | None = None, target_id: str | None = None) -> dict[str, Any]:
    st = stage.strip()
    if not st: raise ValueError("stage is required")
    st_alias = {"draft": {"draft", "DRAFT"}, "DRAFT": {"draft", "DRAFT"}}.get(st, {st})
    info = status(project_root, data_dir=data_dir)
    if not info["ready"]: raise ValueError("projection is not current: " + str(info.get("preview_error") or info["state"]))
    with QuillframeStore(data_dir).open_project(info["project_id"]) as conn:
        rows = conn.execute("SELECT * FROM project_context_sources ORDER BY stable_id").fetchall()
    objects = []
    for row in rows:
        stages = set(_json(row["allowed_stages_json"], []))
        if not stages.intersection(st_alias): continue
        target = _json(row["target_json"], {})
        if target_id and target.get("id") != target_id and row["stable_id"] != target_id: continue
        objects.append({"stable_id": row["stable_id"], "object_type": row["object_type"], "authority": row["authority_class"], "lifecycle": row["lifecycle"], "domain": row["domain"], "allowed_stages": sorted(stages), "target": target, "runtime_payload": _json(row["runtime_payload_json"], {})})
    return {"schema": "quillframe_bounded_context_projection_v1", "project_id": info["project_id"], "stage": st, "projection_fingerprint": info["projection_fingerprint"], "objects": objects, "authority": False, "model_invocations": 0}


def preflight(project_root: Path, target_id: str, stage: str, *, data_dir: Path | None = None) -> dict[str, Any]:
    """Fail-closed preflight; this function never invokes a model."""
    info = status(project_root, data_dir=data_dir)
    errors: list[str] = []
    if not info["project_id"]: errors.append("project identity missing")
    if not info["ready"]: errors.append("projection is not current")
    if info["project_id"]:
        try:
            with QuillframeStore(data_dir).open_project(info["project_id"]) as conn:
                node = conn.execute("SELECT node_id FROM story_nodes WHERE node_id=?", (target_id,)).fetchone()
                doc = conn.execute("SELECT document_id FROM documents WHERE document_id=? OR story_node_id=?", (target_id, target_id)).fetchone()
                if not node: errors.append("target story node missing")
                if not doc: errors.append("target document missing")
        except Exception as exc: errors.append(f"project database unavailable: {exc}")
    context = None
    if not errors:
        try: context = materialize_context(project_root, stage, data_dir=data_dir, target_id=target_id)
        except Exception as exc: errors.append(str(exc))
    return {"schema": PREFLIGHT_SCHEMA, "project_id": info["project_id"], "target_id": target_id, "stage": stage, "ready": not errors, "errors": errors, "context": context, "model_invocations": 0, "authority": False}
