#!/usr/bin/env python3
"""Trusted source-free publication boundary for the General Style Atlas.

Raw StyleStudyRunner candidate bundles can build review previews but never
grant release authority. Release requires a Host-configured publisher which
looks up an immutable completion receipt and verifies fixed-trust signatures.
Hashes prove integrity only. Passing is not copyright clearance or legal safety.
"""
from __future__ import annotations

from contextlib import contextmanager
import errno, hashlib, hmac, json, os, re, stat, tempfile, unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from corpus.style_contract import STYLE_AXES, compile_writer_safe_projection, validate_style_contract, validate_writer_projection

ATLAS_SCHEMA = "quillframe_public_general_style_atlas_v1"
PREVIEW_SCHEMA = "quillframe_public_general_style_atlas_preview_v1"
REGISTRY_SCHEMA = "quillframe_public_general_style_registry_v1"
RELEASE_SCHEMA = "quillframe_public_general_style_release_v1"
RELEASE_RECEIPT_SCHEMA = "quillframe_style_atlas_release_receipt_v1"
TRANSITION_RECEIPT_SCHEMA = "quillframe_style_registry_transition_receipt_v1"
TRUST_POLICY_SCHEMA = "quillframe_style_publication_trust_policy_v1"
ATTESTATION_SCHEMA = "quillframe_style_publication_attestation_v1"
PERSISTED_CANDIDATE_SCHEMA = "quillframe_persisted_style_candidate_v1"
RUNNER_RECEIPT_SCHEMA = "quillframe_corpus_style_completion_receipt_v1"
GATE_CLAIM_SCHEMA = "quillframe_style_release_gate_claim_v1"
RELEASE_CHALLENGE_SCHEMA = "quillframe_style_atlas_release_challenge_v1"
REGISTRY_TRANSITION_SCHEMA = "quillframe_style_registry_transition_v1"
SEMANTIC_LEAKAGE_GATE_SCHEMA = "quillframe_style_semantic_leakage_gate_v1"
BLIND_AB_GATE_SCHEMA = "quillframe_style_blind_ab_gate_v1"
STYLE_CANDIDATE_BUNDLE_SCHEMA = "quillframe_corpus_style_candidate_bundle_v1"
STYLE_ANALYSIS_PROTOCOL_ID = "quillframe_corpus_style_learning_v1"
STYLE_ANALYSIS_PROTOCOL_VERSION = "1"
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "general" / "style_registry.json"
TRUST_POLICY_FILENAME = "style_publication_trust_policy.json"
DEFAULT_TRUST_POLICY_PATH = DEFAULT_REGISTRY_PATH.parent / TRUST_POLICY_FILENAME

MAX_ATLAS_BYTES, MAX_PRIVATE_BYTES = 256 * 1024, 2 * 1024 * 1024
MAX_PUBLIC_DEPTH, MAX_PUBLIC_NODES, MAX_CRAFT_CANDIDATES = 12, 4096, 64
_FP = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOKEN = re.compile(r"^style-preview-[0-9a-f]{64}$")
_PS = re.compile(r"^PS-[0-9a-f]{32}$")
_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
_SIG = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40,64}$")
_PATH = re.compile(r"(?:[a-z]:[\\/]|(?:file|smb|ftp|https?)://|\\\\(?:\?\\)?[^\\/\s]+[\\/][^\\/\s]+|//[^/\s]+/[^/\s]+|(?:^|[\\/])(?:users|home|mnt|private|var[\\/]tmp)[\\/]|(?:^|[\s(])/(?!/)[^\s/]+(?:/[^\s]*)?|(?:^|[\s(])~[\\/]|(?:^|[\s(])\.\.[\\/])", re.I)
_IMITATION = re.compile(r"(?:\bin\s+the\s+style\s+of\b|\bwrite\s+like\b|\bimitat(?:e|ing|ion)\b|模仿.{0,24}(?:作者|作家|文风|风格)?|仿写|仿.{0,12}(?:作者|作家)|作者风格|作家风格)", re.I)
_INTERNAL = re.compile(r"(?<![a-z0-9_])(?:style|craft|work|run|study|evidence|pw|ps)-[a-z0-9_.:-]+(?![a-z0-9_])", re.I)

_BUNDLE = {"schema","analysis_protocol_id","public_study_id","profile","result_state","style_contract","writer_projection","candidate_artifact_fingerprint","craft_pack_fingerprint","local_leakage","promotion_state","missing_gates","activation_performed","promotion_performed","authority","bundle_fingerprint"}
_LOCAL = {"schema","local_status","release_ready","candidate_text_fingerprint","reference_count","batch_report_fingerprints","semantic_check","summary_fingerprint"}
_CRAFT = {"axis","operation","effect","applies_when","avoid_when","failure_boundary","content_zone","confidence_ppm"}
_ATLAS = {"schema","analysis_protocol_version","content_zone","attribution_mode","style_artifact_fingerprint","craft_artifact_fingerprint","style_contract_fingerprint","craft_candidates","atlas_fingerprint"}
_PREVIEW = {"schema","atlas","release_gates","preview_token","preview_fingerprint"}
_GATES = {"local_leakage","semantic_leakage","blind_ab","promotion","manual_approval"}
_SEMANTIC = {"schema","status","style_artifact_fingerprint","craft_artifact_fingerprint","independent","performed","review_fingerprint"}
_BLIND = {"schema","status","style_artifact_fingerprint","craft_artifact_fingerprint","blind","order_swapped","source_independent_tasks","evaluation_fingerprint"}
_RUNNER = {"schema","style_run_id","study_id","public_study_id","profile","checklist_hash","protocol_fingerprint","sampling_config_fingerprint","semantic_config_fingerprint","semantic_evidence_fingerprint","used_source_set_fingerprint","candidate_bundle_fingerprint","candidate_artifact_fingerprint","craft_pack_fingerprint","receipt_fingerprint"}
_PERSISTED = {"schema","candidate_bundle","completion_receipt","forbidden_identity_terms","identity_policy_complete","identity_policy_fingerprint","provenance_receipt_fingerprint"}
_ATTEST = {"schema","role","key_id","payload","signature"}
_GATE_CLAIM = {"schema","gate_role","status","completion_receipt_fingerprint","candidate_bundle_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","gate_fingerprint","identity_policy_fingerprint","registered_contract","authority_scope","legal_safety_claim"}
_REGISTRY = {"schema","registry_version","revision","status","atlas_schema","active_atlas_fingerprint","parent_registry_fingerprint","releases","events","registry_fingerprint"}
_ENTRY = {"atlas_fingerprint","preview_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","analysis_protocol_version","content_zone","preview_token","semantic_leakage_status","blind_ab_status","promotion_status","manual_approval_status","state","release_receipt_fingerprint","base_registry_fingerprint","base_registry_revision"}
_EVENT = {"revision","kind","receipt_fingerprint"}
_CHALLENGE = {"schema","status","preview_token","preview_fingerprint","atlas_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","promotion_gate_fingerprint","target_commit","environment","registry_path_fingerprint","base_registry_fingerprint","base_registry_revision"}
_TRANSITION = {"schema","action","target_atlas_fingerprint","environment","registry_path_fingerprint","base_registry_fingerprint","base_registry_revision"}
_RELEASE_RECEIPT = {"schema","completion_receipt_fingerprint","atlas_fingerprint","preview_fingerprint","preview_token","style_artifact_fingerprint","craft_artifact_fingerprint","gate_claims","gate_attestations","manual_approval_challenge","manual_approval_attestation","receipt_fingerprint"}
_TRANSITION_RECEIPT = {"schema","transition","manual_approval_attestation","receipt_fingerprint"}
_TRUST_POLICY = {"schema","policy_version","status","roles","policy_fingerprint"}
_TRUST_ROLE = {"key_id","secret_fingerprint"}
TRUSTED_ROLES = ("provenance","semantic_leakage","blind_ab","promotion","manual_approval")
_ROLES = set(TRUSTED_ROLES)
_CONTRACT = {"provenance":"corpus.provenance.public_abstraction","semantic_leakage":"learning.prose_semantic_leakage","blind_ab":"learning.blind_prose_pair","promotion":"learning.promotion_gate.evaluate"}
_FORBIDDEN = {"id","public_study_id","study_id","style_run_id","run_id","public_work_id","work_id","record_id","contract_id","candidate_id","craft_id","evidence","evidence_refs","evidence_id","count","counts","supporting_work_count","counterexample_count","reference_count","title","author","creator","path","source_path","file_path","filepath","filename","quote","excerpt","passage","prose","source_text","raw","raw_text","text","url","uri"}


class StylePublicationError(ValueError):
    def __init__(self, code: str, message: str | None = None): self.code = code; super().__init__(message or code)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":"), allow_nan=False).encode()


def fingerprint(value: Any) -> str: return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()
def _without(value: Mapping[str, Any], *keys: str) -> dict[str, Any]: return {k:v for k,v in value.items() if k not in set(keys)}
def _valid_fp(value: Any) -> bool: return isinstance(value,str) and _FP.fullmatch(value) is not None


def style_publication_secret_fingerprint(secret: bytes) -> str:
    """Return the domain-separated public fingerprint used by a trust policy."""
    if not isinstance(secret,bytes) or len(secret)<32: raise StylePublicationError("trust_anchor_invalid")
    return "sha256:"+hashlib.sha256(b"quillframe-style-publication-trust-secret-v1\0"+secret).hexdigest()


def _plain(value: Any, code: str, limit: int = MAX_PRIVATE_BYTES) -> dict[str, Any]:
    if not isinstance(value, Mapping): raise StylePublicationError(code)
    try:
        raw = _canonical(value)
        if len(raw) > limit: raise StylePublicationError(code + "_size_limit")
        result = json.loads(raw)
    except StylePublicationError: raise
    except Exception as exc: raise StylePublicationError(code + "_not_canonical_json") from exc
    if not isinstance(result, dict): raise StylePublicationError(code)
    return result


def _require(errors: Sequence[str], default: str):
    if errors: raise StylePublicationError(errors[0] or default, ",".join(errors))


def _norm(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKC",value).casefold() if unicodedata.category(ch) not in {"Cf","Cc","Cs","Co","Cn"})


def _terms(values: Iterable[str]) -> tuple[str,...]:
    if isinstance(values,str): values=(values,)
    try: iterator=iter(values)
    except TypeError: return ()
    return tuple(sorted(dict.fromkeys(x for v in iterator if isinstance(v,str) for x in [_norm(v).strip()] if 2 <= len(x) <= 300)))


def canonicalize_identity_terms(values: Iterable[str]) -> list[str]:
    """Canonicalize private identity terms before sealing a persisted record."""
    return list(_terms(values))


def identity_policy_fingerprint(values: Iterable[str]) -> str:
    return fingerprint({"schema":"quillframe_style_identity_policy_v1","forbidden_identity_terms":list(_terms(values))})


def _walk(value: Any, depth=0, counter=None) -> Iterator[tuple[str|None,Any]]:
    if depth > MAX_PUBLIC_DEPTH: raise StylePublicationError("public_payload_depth_limit")
    counter = counter or [0]; counter[0]+=1
    if counter[0] > MAX_PUBLIC_NODES: raise StylePublicationError("public_payload_node_limit")
    if isinstance(value,Mapping):
        for k,v in value.items(): yield str(k),v; yield from _walk(v,depth+1,counter)
    elif isinstance(value,list):
        for v in value: yield None,v; yield from _walk(v,depth+1,counter)


def _bad_key(value: str) -> bool:
    k=value.strip().casefold().replace("-","_")
    return k in _FORBIDDEN or k.endswith("_id") or k.endswith("_count") or k.startswith(("source_","author_","creator_","title_","path_","quote_","raw_","prose_","evidence_","work_","run_"))


def _safety(value: Any, identities: Iterable[str]=()) -> list[str]:
    errors=set(); terms=_terms(identities)
    try: nodes=list(_walk(value))
    except StylePublicationError as exc: return [exc.code]
    for key,child in nodes:
        if key is not None and _bad_key(key): errors.add("forbidden_public_field")
        if not isinstance(child,str): continue
        text=_norm(child)
        if _PATH.search(text): errors.add("path_like_public_value")
        if _IMITATION.search(text): errors.add("named_author_imitation_forbidden")
        if _INTERNAL.search(text): errors.add("internal_id_public_value")
        if any(term in text for term in terms): errors.add("forbidden_identity_term")
    return sorted(errors)


def _strict_schema_errors(value: Any, schema: Mapping[str,Any], root_schema: Mapping[str,Any], schemas: Mapping[str,Mapping[str,Any]], path: tuple[Any,...]=()) -> list[str]:
    """Execute the closed subset of Draft 2020-12 used by committed schemas."""
    if "$ref" in schema:
        ref=schema["$ref"]
        if ref.startswith("#/"):
            target: Any=root_schema
            for part in ref[2:].split("/"): target=target[part.replace("~1","/").replace("~0","~")]
        else:
            target=schemas.get(ref)
            if target is None: return ["json_schema_unresolved_ref"]
        return _strict_schema_errors(value,target,target if not ref.startswith("#/") else root_schema,schemas,path)
    if "allOf" in schema:
        errors=[error for option in schema["allOf"] for error in _strict_schema_errors(value,option,root_schema,schemas,path)]
        remainder={key:child for key,child in schema.items() if key!="allOf"}
        if remainder: errors.extend(_strict_schema_errors(value,remainder,root_schema,schemas,path))
        return errors
    errors=[]
    if "oneOf" in schema:
        matches=sum(not _strict_schema_errors(value,option,root_schema,schemas,path) for option in schema["oneOf"])
        if matches!=1: errors.append("json_schema:"+"/".join(map(str,path)))
        return errors
    expected=schema.get("type")
    type_ok={"object":isinstance(value,dict),"array":isinstance(value,list),"string":isinstance(value,str),"integer":isinstance(value,int) and not isinstance(value,bool),"null":value is None}.get(expected,True)
    if not type_ok: return ["json_schema:"+"/".join(map(str,path))]
    if "const" in schema and value!=schema["const"]: errors.append("json_schema:"+"/".join(map(str,path)))
    if "enum" in schema and value not in schema["enum"]: errors.append("json_schema:"+"/".join(map(str,path)))
    if isinstance(value,dict):
        required=set(schema.get("required",[])); properties=schema.get("properties",{})
        for key in required-set(value): errors.append("json_schema:"+"/".join(map(str,(*path,key))))
        if schema.get("additionalProperties") is False:
            for key in set(value)-set(properties): errors.append("json_schema:"+"/".join(map(str,(*path,key))))
        for key,child in value.items():
            if key in properties: errors.extend(_strict_schema_errors(child,properties[key],root_schema,schemas,(*path,key)))
    if isinstance(value,list):
        if len(value)<schema.get("minItems",0) or len(value)>schema.get("maxItems",10**18): errors.append("json_schema:"+"/".join(map(str,path)))
        if schema.get("uniqueItems") and len({_canonical(x) for x in value})!=len(value): errors.append("json_schema:"+"/".join(map(str,path)))
        if isinstance(schema.get("items"),Mapping):
            for index,child in enumerate(value): errors.extend(_strict_schema_errors(child,schema["items"],root_schema,schemas,(*path,index)))
    if isinstance(value,str):
        if len(value)<schema.get("minLength",0) or len(value)>schema.get("maxLength",10**18): errors.append("json_schema:"+"/".join(map(str,path)))
        if "pattern" in schema and re.search(schema["pattern"],value) is None: errors.append("json_schema:"+"/".join(map(str,path)))
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if value<schema.get("minimum",float("-inf")) or value>schema.get("maximum",float("inf")): errors.append("json_schema:"+"/".join(map(str,path)))
    return errors


def _schema_errors(value: Any, name: str) -> list[str]:
    try:
        root=Path(__file__).resolve().parent/"general"; schema=json.loads((root/name).read_text(encoding="utf-8")); atlas_schema=json.loads((root/"style_atlas.schema.json").read_text(encoding="utf-8")); schemas={atlas_schema["$id"]:atlas_schema}
    except Exception: return ["json_schema_unavailable"]
    strict=_strict_schema_errors(value,schema,schema,schemas)
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError: return sorted(set(strict))
    Draft202012Validator.check_schema(schema); registry=Registry().with_resource(atlas_schema["$id"],Resource.from_contents(atlas_schema))
    draft=["json_schema:"+"/".join(map(str,e.path)) for e in Draft202012Validator(schema,registry=registry).iter_errors(value)]
    return sorted(set(strict+draft))


def make_style_publication_trust_policy(anchors: Mapping[str,Mapping[str,bytes]]|None=None, *, status: str="active") -> dict[str,Any]:
    """Build a reviewable policy projection; it never contains signing secrets."""
    if not isinstance(status,str) or status not in {"unconfigured","active"}: raise StylePublicationError("trust_policy_status_invalid")
    if status=="unconfigured":
        if anchors not in (None,{}): raise StylePublicationError("unconfigured_trust_policy_has_anchors")
        roles={role:{"key_id":None,"secret_fingerprint":None} for role in TRUSTED_ROLES}
    else:
        if not isinstance(anchors,Mapping) or set(anchors)!=_ROLES: raise StylePublicationError("trust_anchor_roles_incomplete")
        roles={}
        secret_fingerprints=[]
        for role in TRUSTED_ROLES:
            keys=anchors.get(role)
            if not isinstance(keys,Mapping) or len(keys)!=1: raise StylePublicationError("trust_anchor_role_cardinality_invalid")
            key_id,secret=next(iter(keys.items()))
            if not isinstance(key_id,str) or not _KEY.fullmatch(key_id): raise StylePublicationError("trust_anchor_invalid")
            secret_fp=style_publication_secret_fingerprint(secret); secret_fingerprints.append(secret_fp)
            roles[role]={"key_id":key_id,"secret_fingerprint":secret_fp}
        if len(set(secret_fingerprints))!=len(secret_fingerprints): raise StylePublicationError("trust_anchor_role_separation_invalid")
    value={"schema":TRUST_POLICY_SCHEMA,"policy_version":1,"status":status,"roles":roles}
    value["policy_fingerprint"]=fingerprint(value)
    _require(validate_style_publication_trust_policy(value),"trust_policy_invalid")
    return value


def validate_style_publication_trust_policy(policy: Mapping[str,Any]) -> list[str]:
    errors=set()
    try: policy=_plain(policy,"trust_policy_not_object",MAX_ATLAS_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(policy,"style_publication_trust_policy.schema.json"))
    if set(policy)!=_TRUST_POLICY: return sorted(errors|{"trust_policy_schema_not_closed"})
    if policy.get("schema")!=TRUST_POLICY_SCHEMA or policy.get("policy_version")!=1: errors.add("trust_policy_header_invalid")
    status=policy.get("status")
    if not isinstance(status,str) or status not in {"unconfigured","active"}: errors.add("trust_policy_status_invalid")
    roles=policy.get("roles")
    if not isinstance(roles,Mapping) or set(roles)!=_ROLES: errors.add("trust_policy_roles_incomplete"); roles={}
    secret_fingerprints=[]
    for role in TRUSTED_ROLES:
        item=roles.get(role)
        if not isinstance(item,Mapping) or set(item)!=_TRUST_ROLE: errors.add("trust_policy_role_schema_not_closed"); continue
        key_id,secret_fp=item.get("key_id"),item.get("secret_fingerprint")
        if status=="active":
            if not isinstance(key_id,str) or not _KEY.fullmatch(key_id): errors.add("trust_policy_key_id_invalid")
            if not _valid_fp(secret_fp): errors.add("trust_policy_secret_fingerprint_invalid")
            elif secret_fp in secret_fingerprints: errors.add("trust_policy_role_separation_invalid")
            else: secret_fingerprints.append(secret_fp)
        elif key_id is not None or secret_fp is not None: errors.add("unconfigured_trust_policy_has_anchors")
    if policy.get("policy_fingerprint")!=fingerprint(_without(policy,"policy_fingerprint")): errors.add("trust_policy_fingerprint_mismatch")
    return sorted(errors)


def _local_errors(value: Any, contract: Mapping[str,Any]) -> list[str]:
    if not isinstance(value,Mapping) or set(value)!=_LOCAL: return ["local_leakage_summary_schema_not_closed"]
    errors=set()
    if value.get("schema")!="quillframe_style_leakage_summary_v1": errors.add("local_leakage_summary_schema_invalid")
    if not isinstance(value.get("local_status"),str) or value.get("local_status") not in {"pass","blocked","not_performed"}: errors.add("local_leakage_status_invalid")
    if value.get("release_ready") is not False: errors.add("local_leakage_cannot_grant_release")
    if value.get("candidate_text_fingerprint")!=fingerprint(contract): errors.add("local_leakage_candidate_binding_mismatch")
    count=value.get("reference_count")
    if isinstance(count,bool) or not isinstance(count,int) or count<0: errors.add("local_leakage_reference_count_invalid")
    reports=value.get("batch_report_fingerprints")
    if not isinstance(reports,list) or any(not _valid_fp(x) for x in reports): errors.add("local_leakage_report_fingerprints_invalid")
    if value.get("semantic_check")!="required_external": errors.add("local_leakage_semantic_check_invalid")
    if value.get("summary_fingerprint")!=fingerprint(_without(value,"summary_fingerprint")): errors.add("local_leakage_summary_fingerprint_mismatch")
    return sorted(errors)


def _candidate(candidate: Mapping[str,Any], identities: Iterable[str]=()) -> dict[str,Any]:
    bundle=_plain(candidate,"candidate_bundle_invalid"); errors=set()
    if set(bundle)!=_BUNDLE: raise StylePublicationError("candidate_bundle_schema_not_closed")
    if bundle.get("schema")!=STYLE_CANDIDATE_BUNDLE_SCHEMA: errors.add("candidate_bundle_schema_invalid")
    if bundle.get("analysis_protocol_id")!=STYLE_ANALYSIS_PROTOCOL_ID: errors.add("analysis_protocol_invalid")
    if not _PS.fullmatch(str(bundle.get("public_study_id") or "")): errors.add("candidate_public_study_id_invalid")
    if bundle.get("profile")!="general": errors.add("general_content_zone_required")
    if not isinstance(bundle.get("result_state"),str) or bundle.get("result_state") not in {"candidate","blocked_local_leakage"}: errors.add("candidate_bundle_result_state_invalid")
    if any(bundle.get(x) is not False for x in ("activation_performed","promotion_performed","authority")): errors.add("candidate_bundle_authority_invalid")
    if bundle.get("bundle_fingerprint")!=fingerprint(_without(bundle,"bundle_fingerprint")): errors.add("candidate_bundle_fingerprint_mismatch")
    contract,projection,local=bundle.get("style_contract"),bundle.get("writer_projection"),bundle.get("local_leakage")
    ce=validate_style_contract(contract,forbidden_identity_terms=identities); pe=validate_writer_projection(projection,forbidden_identity_terms=identities)
    if ce: errors.add("style_contract_invalid")
    if pe: errors.add("writer_projection_invalid")
    if isinstance(contract,Mapping) and contract.get("content_zone")!="general": errors.add("style_contract_content_zone_invalid")
    if isinstance(projection,Mapping) and projection.get("content_zone")!="general": errors.add("writer_projection_content_zone_invalid")
    if not ce and not pe:
        try: expected_projection=compile_writer_safe_projection(contract,forbidden_identity_terms=identities)
        except Exception: errors.add("writer_projection_binding_invalid")
        else:
            if expected_projection!=projection: errors.add("writer_projection_binding_mismatch")
    if not isinstance(projection,Mapping) or bundle.get("craft_pack_fingerprint")!=projection.get("projection_fingerprint"): errors.add("craft_artifact_fingerprint_mismatch")
    if isinstance(contract,Mapping): errors.update(_local_errors(local,contract))
    else: errors.add("local_leakage_summary_invalid")
    if isinstance(contract,Mapping) and isinstance(projection,Mapping) and isinstance(local,Mapping):
        expected=fingerprint({"style_contract":contract,"writer_projection":projection,"local_leakage_summary_fingerprint":local.get("summary_fingerprint")})
        if bundle.get("candidate_artifact_fingerprint")!=expected: errors.add("style_artifact_fingerprint_mismatch")
    _require(sorted(errors),"candidate_bundle_invalid")
    return {"bundle":bundle,"projection":projection,"local":local,"style_fp":bundle["candidate_artifact_fingerprint"],"craft_fp":bundle["craft_pack_fingerprint"]}


def make_semantic_leakage_gate(style_fp: str, craft_fp: str, *, status: str, independent: bool, performed: bool) -> dict[str,Any]:
    """Preview evidence only; it cannot authorize release."""
    value={"schema":SEMANTIC_LEAKAGE_GATE_SCHEMA,"status":status,"style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"independent":independent,"performed":performed}
    value["review_fingerprint"]=fingerprint(value); _require(_semantic_errors(value,style_fp,craft_fp),"semantic_leakage_gate_invalid"); return value


def _semantic_errors(value: Any, style_fp: str, craft_fp: str) -> list[str]:
    if not isinstance(value,Mapping) or set(value)!=_SEMANTIC: return ["semantic_leakage_gate_schema_not_closed"]
    errors=set()
    if value.get("schema")!=SEMANTIC_LEAKAGE_GATE_SCHEMA: errors.add("semantic_leakage_gate_schema_invalid")
    if not isinstance(value.get("status"),str) or value.get("status") not in {"pass","fail","pending"}: errors.add("semantic_leakage_status_invalid")
    if value.get("style_artifact_fingerprint")!=style_fp or value.get("craft_artifact_fingerprint")!=craft_fp: errors.add("semantic_leakage_artifact_binding_mismatch")
    if value.get("status")=="pass" and (value.get("independent") is not True or value.get("performed") is not True): errors.add("semantic_leakage_pass_requires_independent_review")
    if value.get("review_fingerprint")!=fingerprint(_without(value,"review_fingerprint")): errors.add("semantic_leakage_review_fingerprint_mismatch")
    return sorted(errors)


def make_blind_ab_gate(style_fp: str, craft_fp: str, *, status: str, blind: bool, order_swapped: bool, source_independent_tasks: bool) -> dict[str,Any]:
    """Preview evidence only; it cannot authorize release."""
    value={"schema":BLIND_AB_GATE_SCHEMA,"status":status,"style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"blind":blind,"order_swapped":order_swapped,"source_independent_tasks":source_independent_tasks}
    value["evaluation_fingerprint"]=fingerprint(value); _require(_blind_errors(value,style_fp,craft_fp),"blind_ab_gate_invalid"); return value


def _blind_errors(value: Any, style_fp: str, craft_fp: str) -> list[str]:
    if not isinstance(value,Mapping) or set(value)!=_BLIND: return ["blind_ab_gate_schema_not_closed"]
    errors=set()
    if value.get("schema")!=BLIND_AB_GATE_SCHEMA: errors.add("blind_ab_gate_schema_invalid")
    if not isinstance(value.get("status"),str) or value.get("status") not in {"pass","fail","pending"}: errors.add("blind_ab_status_invalid")
    if value.get("style_artifact_fingerprint")!=style_fp or value.get("craft_artifact_fingerprint")!=craft_fp: errors.add("blind_ab_artifact_binding_mismatch")
    if value.get("status")=="pass" and any(value.get(x) is not True for x in ("blind","order_swapped","source_independent_tasks")): errors.add("blind_ab_pass_requires_sealed_design")
    if value.get("evaluation_fingerprint")!=fingerprint(_without(value,"evaluation_fingerprint")): errors.add("blind_ab_evaluation_fingerprint_mismatch")
    return sorted(errors)


def _gate_summary(value: Any, style_fp: str, craft_fp: str, kind: str) -> dict[str,Any]:
    if value is None: return {"status":"pending","style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"gate_fingerprint":None}
    value=_plain(value,kind+"_gate_invalid"); errors=_semantic_errors(value,style_fp,craft_fp) if kind=="semantic_leakage" else _blind_errors(value,style_fp,craft_fp); _require(errors,kind+"_gate_invalid")
    return {"status":value["status"],"style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"gate_fingerprint":value["review_fingerprint" if kind=="semantic_leakage" else "evaluation_fingerprint"]}


def _promotion_summary(gate: Any, candidate: Any, style_fp: str, craft_fp: str) -> dict[str,Any]:
    if gate is None and candidate is None: return {"status":"pending","style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"gate_fingerprint":None}
    if gate is None or candidate is None: raise StylePublicationError("promotion_gate_and_candidate_required")
    gate,candidate=_plain(gate,"promotion_gate_invalid"),_plain(candidate,"promotion_candidate_invalid")
    from learning.promotion_gate import evaluate
    if evaluate(candidate)!=gate: raise StylePublicationError("promotion_gate_evaluator_mismatch")
    binding=gate.get("artifact_binding")
    if gate.get("schema")!="quillframe_learning_promotion_gate_v2" or gate.get("scope")!="general_craft": raise StylePublicationError("promotion_gate_schema_invalid")
    if not isinstance(binding,Mapping) or binding.get("candidate_artifact_fingerprint")!=style_fp or binding.get("craft_pack_fingerprint")!=craft_fp: raise StylePublicationError("promotion_gate_artifact_binding_mismatch")
    if gate.get("status")=="promotable" and (gate.get("blockers") or binding.get("all_bound") is not True): raise StylePublicationError("promotion_gate_promotable_binding_invalid")
    return {"status":gate.get("status"),"style_artifact_fingerprint":style_fp,"craft_artifact_fingerprint":craft_fp,"gate_fingerprint":fingerprint(gate)}


def _preview_token(preview_fp: str, atlas_fp: str) -> str:
    return "style-preview-"+hashlib.sha256((preview_fp+"\0"+atlas_fp).encode("ascii")).hexdigest()


def build_style_atlas_preview(candidate_bundle: Mapping[str,Any], *, semantic_leakage: Mapping[str,Any]|None=None, blind_ab: Mapping[str,Any]|None=None, promotion_gate: Mapping[str,Any]|None=None, promotion_candidate: Mapping[str,Any]|None=None, forbidden_identity_terms: Iterable[str]=()) -> dict[str,Any]:
    """Build a closed review preview. Raw input never carries authority."""
    context=_candidate(candidate_bundle,forbidden_identity_terms)
    craft=[{k:item[k] for k in _CRAFT} for item in context["projection"]["craft_candidates"]]
    atlas={"schema":ATLAS_SCHEMA,"analysis_protocol_version":STYLE_ANALYSIS_PROTOCOL_VERSION,"content_zone":"general","attribution_mode":"source_free","style_artifact_fingerprint":context["style_fp"],"craft_artifact_fingerprint":context["craft_fp"],"style_contract_fingerprint":context["projection"]["style_contract_fingerprint"],"craft_candidates":craft}
    _require(_safety(atlas,forbidden_identity_terms),"public_style_atlas_unsafe"); atlas["atlas_fingerprint"]=fingerprint(atlas)
    gates={"local_leakage":{"status":context["local"]["local_status"],"summary_fingerprint":context["local"]["summary_fingerprint"]},"semantic_leakage":_gate_summary(semantic_leakage,context["style_fp"],context["craft_fp"],"semantic_leakage"),"blind_ab":_gate_summary(blind_ab,context["style_fp"],context["craft_fp"],"blind_ab"),"promotion":_promotion_summary(promotion_gate,promotion_candidate,context["style_fp"],context["craft_fp"]),"manual_approval":{"status":"external_exact_preview_confirmation_required"}}
    base={"schema":PREVIEW_SCHEMA,"atlas":atlas,"release_gates":gates}; preview_fp=fingerprint(base)
    preview={**base,"preview_token":_preview_token(preview_fp,atlas["atlas_fingerprint"]),"preview_fingerprint":preview_fp}
    _require(validate_style_atlas_preview(preview,forbidden_identity_terms=forbidden_identity_terms),"style_atlas_preview_invalid"); return preview


preview_style_atlas=build_style_atlas_preview


def _short(value: Any) -> bool:
    return isinstance(value,str) and value==value.strip() and 0<len(value)<=600 and "\x00" not in value


def _conditions(value: Any) -> bool:
    return isinstance(value,list) and 0<len(value)<=16 and all(_short(x) for x in value) and len(value)==len(set(value))


def validate_style_atlas(atlas: Mapping[str,Any], *, forbidden_identity_terms: Iterable[str]=()) -> list[str]:
    errors=set()
    try: atlas=_plain(atlas,"style_atlas_not_object",MAX_ATLAS_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(atlas,"style_atlas.schema.json")); errors.update(_safety(atlas,forbidden_identity_terms))
    if set(atlas)!=_ATLAS: return sorted(errors|{"style_atlas_schema_not_closed"})
    if atlas.get("schema")!=ATLAS_SCHEMA or atlas.get("analysis_protocol_version")!="1" or atlas.get("content_zone")!="general" or atlas.get("attribution_mode")!="source_free": errors.add("style_atlas_header_invalid")
    for key in ("style_artifact_fingerprint","craft_artifact_fingerprint","style_contract_fingerprint","atlas_fingerprint"):
        if not _valid_fp(atlas.get(key)): errors.add(key+"_invalid")
    craft=atlas.get("craft_candidates")
    if not isinstance(craft,list) or not 0<len(craft)<=MAX_CRAFT_CANDIDATES: errors.add("craft_candidates_invalid"); craft=[]
    seen=set()
    for item in craft:
        if not isinstance(item,Mapping) or set(item)!=_CRAFT: errors.add("craft_candidate_schema_not_closed"); continue
        if item.get("axis") not in STYLE_AXES or item.get("content_zone")!="general": errors.add("craft_boundary_invalid")
        if any(not _short(item.get(k)) for k in ("operation","effect","failure_boundary")): errors.add("craft_text_invalid")
        if any(not _conditions(item.get(k)) for k in ("applies_when","avoid_when")): errors.add("craft_conditions_invalid")
        confidence=item.get("confidence_ppm")
        if isinstance(confidence,bool) or not isinstance(confidence,int) or not 0<=confidence<=1_000_000: errors.add("craft_confidence_invalid")
        item_fp=fingerprint(item)
        if item_fp in seen: errors.add("duplicate_craft_candidate")
        seen.add(item_fp)
    if craft and _valid_fp(atlas.get("style_contract_fingerprint")) and _valid_fp(atlas.get("craft_artifact_fingerprint")):
        projection={"schema":"quillframe_writer_style_projection_v1","style_contract_fingerprint":atlas["style_contract_fingerprint"],"content_zone":"general","attribution_mode":"source_free","craft_candidates":craft,"semantic_leakage_check":"required_external","projection_fingerprint":atlas["craft_artifact_fingerprint"]}
        if validate_writer_projection(projection,forbidden_identity_terms=forbidden_identity_terms): errors.add("craft_artifact_projection_binding_mismatch")
    if atlas.get("atlas_fingerprint")!=fingerprint(_without(atlas,"atlas_fingerprint")): errors.add("atlas_fingerprint_mismatch")
    return sorted(errors)


def validate_style_atlas_preview(preview: Mapping[str,Any], *, forbidden_identity_terms: Iterable[str]=()) -> list[str]:
    errors=set()
    try: preview=_plain(preview,"style_atlas_preview_not_object",MAX_ATLAS_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(preview,"style_atlas_preview.schema.json"))
    if set(preview)!=_PREVIEW: return sorted(errors|{"style_atlas_preview_schema_not_closed"})
    if preview.get("schema")!=PREVIEW_SCHEMA: errors.add("style_atlas_preview_schema_invalid")
    errors.update(validate_style_atlas(preview.get("atlas",{}),forbidden_identity_terms=forbidden_identity_terms))
    if not isinstance(preview.get("release_gates"),Mapping) or set(preview["release_gates"])!=_GATES: errors.add("release_gates_schema_not_closed")
    else:
        gates=preview["release_gates"]; atlas=preview.get("atlas",{}) if isinstance(preview.get("atlas"),Mapping) else {}
        local=gates.get("local_leakage")
        if not isinstance(local,Mapping) or set(local)!={"status","summary_fingerprint"} or not isinstance(local.get("status"),str) or local.get("status") not in {"pass","blocked","not_performed"} or not _valid_fp(local.get("summary_fingerprint")): errors.add("local_public_gate_invalid")
        for name,allowed in (("semantic_leakage",{"pending","pass","fail"}),("blind_ab",{"pending","pass","fail"}),("promotion",{"pending","promotable","blocked"})):
            gate=gates.get(name)
            if not isinstance(gate,Mapping) or set(gate)!={"status","style_artifact_fingerprint","craft_artifact_fingerprint","gate_fingerprint"}: errors.add(name+"_public_gate_invalid"); continue
            if not isinstance(gate.get("status"),str) or gate.get("status") not in allowed or gate.get("style_artifact_fingerprint")!=atlas.get("style_artifact_fingerprint") or gate.get("craft_artifact_fingerprint")!=atlas.get("craft_artifact_fingerprint"): errors.add(name+"_public_gate_invalid")
            if (gate.get("status")=="pending") != (gate.get("gate_fingerprint") is None): errors.add(name+"_public_gate_invalid")
            if gate.get("status")!="pending" and not _valid_fp(gate.get("gate_fingerprint")): errors.add(name+"_public_gate_invalid")
        manual=gates.get("manual_approval")
        if manual!={"status":"external_exact_preview_confirmation_required"}: errors.add("manual_public_gate_invalid")
    expected=fingerprint(_without(preview,"preview_token","preview_fingerprint"))
    if preview.get("preview_fingerprint")!=expected: errors.add("preview_fingerprint_mismatch")
    atlas_fp=preview.get("atlas",{}).get("atlas_fingerprint","") if isinstance(preview.get("atlas"),Mapping) else ""
    if preview.get("preview_token")!=_preview_token(expected,str(atlas_fp)): errors.add("preview_token_mismatch")
    return sorted(errors)


class StylePublicationTrustStore:
    """Immutable copy of Host-configured HMAC trust anchors."""
    def __init__(self, anchors: Mapping[str,Mapping[str,bytes]]):
        if not isinstance(anchors,Mapping) or set(anchors)!=_ROLES: raise StylePublicationError("trust_anchor_roles_incomplete")
        copied={}
        secret_fingerprints=[]
        for role in TRUSTED_ROLES:
            keys=anchors[role]
            if not isinstance(keys,Mapping) or len(keys)!=1: raise StylePublicationError("trust_anchor_role_cardinality_invalid")
            copied[role]={}
            for key_id,secret in keys.items():
                if not isinstance(key_id,str) or not _KEY.fullmatch(key_id) or not isinstance(secret,bytes) or len(secret)<32: raise StylePublicationError("trust_anchor_invalid")
                copied[role][key_id]=bytes(secret)
                secret_fingerprints.append(style_publication_secret_fingerprint(secret))
        if len(set(secret_fingerprints))!=len(secret_fingerprints): raise StylePublicationError("trust_anchor_role_separation_invalid")
        self._anchors=copied

    def require_policy(self, policy: Mapping[str,Any]):
        _require(validate_style_publication_trust_policy(policy),"trust_policy_invalid")
        if policy.get("status")!="active": raise StylePublicationError("style_publication_trust_policy_unconfigured")
        for role in TRUSTED_ROLES:
            expected=policy["roles"][role]; keys=self._anchors.get(role,{})
            if set(keys)!={expected["key_id"]}: raise StylePublicationError("trust_store_policy_mismatch")
            if style_publication_secret_fingerprint(keys[expected["key_id"]])!=expected["secret_fingerprint"]: raise StylePublicationError("trust_store_policy_mismatch")

    def verify(self, attestation: Mapping[str,Any], role: str, payload: Mapping[str,Any]):
        value=_plain(attestation,role+"_attestation_invalid")
        if set(value)!=_ATTEST or value.get("schema")!=ATTESTATION_SCHEMA or value.get("role")!=role or value.get("payload")!=payload: raise StylePublicationError(role+"_attestation_invalid")
        secret=self._anchors.get(role,{}).get(value.get("key_id"))
        if secret is None: raise StylePublicationError(role+"_trust_anchor_missing")
        expected=_signature(role,value["key_id"],payload,secret)
        if not isinstance(value.get("signature"),str) or not _SIG.fullmatch(value["signature"]) or not hmac.compare_digest(value["signature"],expected): raise StylePublicationError(role+"_attestation_signature_invalid")


def _signature(role: str, key_id: str, payload: Mapping[str,Any], secret: bytes) -> str:
    material=_canonical({"schema":ATTESTATION_SCHEMA,"role":role,"key_id":key_id,"payload":payload})
    return "hmac-sha256:"+hmac.new(secret,b"quillframe-style-publication-v1\0"+material,hashlib.sha256).hexdigest()


def sign_style_publication_attestation(role: str, key_id: str, secret: bytes, payload: Mapping[str,Any]) -> dict[str,Any]:
    """Trusted-adapter helper; a configured 256-bit secret is mandatory."""
    if role not in _ROLES or not _KEY.fullmatch(str(key_id)) or not isinstance(secret,bytes) or len(secret)<32: raise StylePublicationError("attestation_signing_authority_invalid")
    payload=_plain(payload,"attestation_payload_invalid")
    return {"schema":ATTESTATION_SCHEMA,"role":role,"key_id":key_id,"payload":payload,"signature":_signature(role,key_id,payload,secret)}


def _persisted(value: Mapping[str,Any], expected_receipt: str|None=None) -> dict[str,Any]:
    value=_plain(value,"persisted_candidate_invalid")
    if set(value)!=_PERSISTED or value.get("schema")!=PERSISTED_CANDIDATE_SCHEMA: raise StylePublicationError("persisted_candidate_schema_not_closed")
    terms=_terms(value.get("forbidden_identity_terms",[]))
    if value.get("identity_policy_complete") is not True or not terms or list(terms)!=value.get("forbidden_identity_terms"): raise StylePublicationError("identity_policy_incomplete")
    if value.get("identity_policy_fingerprint")!=identity_policy_fingerprint(terms): raise StylePublicationError("identity_policy_fingerprint_mismatch")
    if not _valid_fp(value.get("provenance_receipt_fingerprint")): raise StylePublicationError("provenance_receipt_fingerprint_invalid")
    context=_candidate(value.get("candidate_bundle",{}),terms); receipt=value.get("completion_receipt")
    if not isinstance(receipt,Mapping) or set(receipt)!=_RUNNER or receipt.get("schema")!=RUNNER_RECEIPT_SCHEMA: raise StylePublicationError("completion_receipt_schema_not_closed")
    for key in ("checklist_hash","protocol_fingerprint","sampling_config_fingerprint","semantic_config_fingerprint","semantic_evidence_fingerprint","used_source_set_fingerprint","candidate_bundle_fingerprint","candidate_artifact_fingerprint","craft_pack_fingerprint","receipt_fingerprint"):
        if not _valid_fp(receipt.get(key)): raise StylePublicationError("completion_receipt_field_invalid")
    for key in ("style_run_id","study_id","public_study_id","profile"):
        if not isinstance(receipt.get(key),str) or not receipt[key]: raise StylePublicationError("completion_receipt_field_invalid")
    if receipt.get("receipt_fingerprint")!=fingerprint(_without(receipt,"receipt_fingerprint")): raise StylePublicationError("completion_receipt_fingerprint_mismatch")
    if expected_receipt and receipt["receipt_fingerprint"]!=expected_receipt: raise StylePublicationError("completion_receipt_lookup_mismatch")
    for left,right in (("bundle_fingerprint","candidate_bundle_fingerprint"),("candidate_artifact_fingerprint","candidate_artifact_fingerprint"),("craft_pack_fingerprint","craft_pack_fingerprint")):
        if context["bundle"].get(left)!=receipt.get(right): raise StylePublicationError("completion_receipt_candidate_binding_mismatch")
    if receipt.get("profile")!="general" or receipt.get("public_study_id")!=context["bundle"].get("public_study_id"): raise StylePublicationError("completion_receipt_study_binding_mismatch")
    return value


def _gate_claim(role: str, status: str, persisted: Mapping[str,Any], gate_fp: str) -> dict[str,Any]:
    return {"schema":GATE_CLAIM_SCHEMA,"gate_role":role,"status":status,"completion_receipt_fingerprint":persisted["completion_receipt"]["receipt_fingerprint"],"candidate_bundle_fingerprint":persisted["candidate_bundle"]["bundle_fingerprint"],"style_artifact_fingerprint":persisted["candidate_bundle"]["candidate_artifact_fingerprint"],"craft_artifact_fingerprint":persisted["candidate_bundle"]["craft_pack_fingerprint"],"gate_fingerprint":gate_fp,"identity_policy_fingerprint":persisted["identity_policy_fingerprint"],"registered_contract":_CONTRACT[role],"authority_scope":"evidence_only","legal_safety_claim":False}


def make_gate_attestation_payload(role: str, status: str, persisted_candidate: Mapping[str,Any], gate_fingerprint: str) -> dict[str,Any]:
    persisted=_persisted(persisted_candidate)
    if role not in _CONTRACT or not _valid_fp(gate_fingerprint): raise StylePublicationError("gate_attestation_payload_invalid")
    return _gate_claim(role,status,persisted,gate_fingerprint)


def _empty_registry() -> dict[str,Any]:
    value={"schema":REGISTRY_SCHEMA,"registry_version":1,"revision":0,"status":"awaiting_first_validated_release","atlas_schema":ATLAS_SCHEMA,"active_atlas_fingerprint":None,"parent_registry_fingerprint":None,"releases":[],"events":[]}; value["registry_fingerprint"]=fingerprint(value); return value


def validate_style_registry(registry: Mapping[str,Any]) -> list[str]:
    errors=set()
    try: registry=_plain(registry,"style_registry_not_object",MAX_ATLAS_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(registry,"style_atlas_registry.schema.json"))
    if set(registry)!=_REGISTRY: return sorted(errors|{"style_registry_schema_not_closed"})
    if registry.get("schema")!=REGISTRY_SCHEMA or registry.get("registry_version")!=1 or registry.get("atlas_schema")!=ATLAS_SCHEMA: errors.add("style_registry_header_invalid")
    revision=registry.get("revision")
    if isinstance(revision,bool) or not isinstance(revision,int) or revision<0: errors.add("style_registry_revision_invalid")
    releases=registry.get("releases")
    if not isinstance(releases,list): errors.add("style_registry_releases_invalid"); releases=[]
    events=registry.get("events")
    if not isinstance(events,list): errors.add("style_registry_events_invalid"); events=[]
    event_fingerprints=set(); release_event_fingerprints=[]
    for index,event in enumerate(events,1):
        if not isinstance(event,Mapping) or set(event)!=_EVENT: errors.add("style_registry_event_schema_not_closed"); continue
        if event.get("revision")!=index: errors.add("style_registry_event_revision_invalid")
        if not isinstance(event.get("kind"),str) or event.get("kind") not in {"release","transition"}: errors.add("style_registry_event_kind_invalid")
        receipt_fp=event.get("receipt_fingerprint")
        if not _valid_fp(receipt_fp) or receipt_fp in event_fingerprints: errors.add("style_registry_event_fingerprint_invalid")
        elif event.get("kind")=="release": release_event_fingerprints.append(receipt_fp)
        if _valid_fp(receipt_fp): event_fingerprints.add(receipt_fp)
    active=[]; seen=set(); sortable=True
    for entry in releases:
        if not isinstance(entry,Mapping) or set(entry)!=_ENTRY: errors.add("style_registry_release_schema_not_closed"); sortable=False; continue
        fp=entry.get("atlas_fingerprint")
        if not _valid_fp(fp): errors.add("style_registry_release_fingerprint_invalid")
        elif fp in seen: errors.add("style_registry_release_fingerprint_invalid")
        else: seen.add(fp)
        if entry.get("state")=="active": active.append(fp)
        if not isinstance(entry.get("state"),str) or entry.get("state") not in {"active","superseded","rolled_back","deprecated","contested"}: errors.add("style_registry_release_state_invalid")
        for key in ("preview_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","release_receipt_fingerprint","base_registry_fingerprint"):
            if not _valid_fp(entry.get(key)): errors.add("style_registry_"+key+"_invalid")
        if entry.get("analysis_protocol_version")!="1" or entry.get("content_zone")!="general" or not _TOKEN.fullmatch(str(entry.get("preview_token") or "")): errors.add("style_registry_release_header_invalid")
        if entry.get("semantic_leakage_status")!="pass" or entry.get("blind_ab_status")!="pass" or entry.get("promotion_status")!="promotable" or entry.get("manual_approval_status")!="confirmed_exact_preview": errors.add("style_registry_release_gate_invalid")
        base_revision=entry.get("base_registry_revision")
        if isinstance(base_revision,bool) or not isinstance(base_revision,int) or base_revision<0: errors.add("style_registry_base_revision_invalid")
    if sortable and releases!=sorted(releases,key=lambda x:str(x.get("atlas_fingerprint") or "")): errors.add("style_registry_release_order_invalid")
    entry_receipts=[entry.get("release_receipt_fingerprint") for entry in releases if isinstance(entry,Mapping)]
    if any(not _valid_fp(value) for value in entry_receipts) or sorted(release_event_fingerprints)!=sorted(entry_receipts): errors.add("style_registry_release_event_binding_invalid")
    if isinstance(revision,int) and not isinstance(revision,bool) and revision!=len(events): errors.add("style_registry_revision_event_count_mismatch")
    if registry.get("status")=="active":
        if len(active)!=1 or registry.get("active_atlas_fingerprint")!=active[0]: errors.add("style_registry_active_pointer_invalid")
    elif registry.get("status")=="awaiting_first_validated_release":
        if releases or events or registry.get("active_atlas_fingerprint") is not None or revision!=0: errors.add("style_registry_empty_state_invalid")
    else: errors.add("style_registry_status_invalid")
    if revision==0 and registry.get("parent_registry_fingerprint") is not None: errors.add("style_registry_parent_invalid")
    if revision and not _valid_fp(registry.get("parent_registry_fingerprint")): errors.add("style_registry_parent_invalid")
    if registry.get("registry_fingerprint")!=fingerprint(_without(registry,"registry_fingerprint")): errors.add("style_registry_fingerprint_mismatch")
    return sorted(errors)


def atlas_filename(atlas_fp: str) -> str:
    if not _valid_fp(atlas_fp): raise StylePublicationError("atlas_fingerprint_invalid")
    return "style-atlas-"+atlas_fp[7:]+".json"


def release_receipt_filename(receipt_fp: str) -> str:
    if not _valid_fp(receipt_fp): raise StylePublicationError("release_receipt_fingerprint_invalid")
    return "style-release-receipt-"+receipt_fp[7:]+".json"


def validate_style_release_receipt(receipt: Mapping[str,Any]) -> list[str]:
    """Validate the closed, source-free publication receipt without granting trust."""
    errors=set()
    try: receipt=_plain(receipt,"release_receipt_not_object",MAX_PRIVATE_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(receipt,"style_atlas_release_receipt.schema.json"))
    if set(receipt)!=_RELEASE_RECEIPT: return sorted(errors|{"release_receipt_schema_not_closed"})
    if receipt.get("schema")!=RELEASE_RECEIPT_SCHEMA: errors.add("release_receipt_schema_invalid")
    for key in ("completion_receipt_fingerprint","atlas_fingerprint","preview_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","receipt_fingerprint"):
        if not _valid_fp(receipt.get(key)): errors.add("release_receipt_"+key+"_invalid")
    if not _TOKEN.fullmatch(str(receipt.get("preview_token") or "")): errors.add("release_receipt_preview_token_invalid")
    claims=receipt.get("gate_claims")
    if not isinstance(claims,Mapping) or set(claims)!=set(_CONTRACT): errors.add("release_receipt_gate_claims_incomplete"); claims={}
    expected_status={"provenance":"pass","semantic_leakage":"pass","blind_ab":"pass","promotion":"promotable"}
    common=None
    for role in _CONTRACT:
        claim=claims.get(role)
        if not isinstance(claim,Mapping) or set(claim)!=_GATE_CLAIM: errors.add("release_receipt_gate_claim_schema_not_closed"); continue
        if claim.get("schema")!=GATE_CLAIM_SCHEMA or claim.get("gate_role")!=role or claim.get("status")!=expected_status[role] or claim.get("registered_contract")!=_CONTRACT[role] or claim.get("authority_scope")!="evidence_only" or claim.get("legal_safety_claim") is not False: errors.add("release_receipt_gate_claim_invalid")
        for key in ("completion_receipt_fingerprint","candidate_bundle_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","gate_fingerprint","identity_policy_fingerprint"):
            if not _valid_fp(claim.get(key)): errors.add("release_receipt_gate_claim_fingerprint_invalid")
        binding=tuple(claim.get(k) for k in ("completion_receipt_fingerprint","candidate_bundle_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","identity_policy_fingerprint"))
        if common is None: common=binding
        elif binding!=common: errors.add("release_receipt_gate_claim_binding_mismatch")
        if claim.get("completion_receipt_fingerprint")!=receipt.get("completion_receipt_fingerprint") or claim.get("style_artifact_fingerprint")!=receipt.get("style_artifact_fingerprint") or claim.get("craft_artifact_fingerprint")!=receipt.get("craft_artifact_fingerprint"): errors.add("release_receipt_gate_claim_binding_mismatch")
    attestations=receipt.get("gate_attestations")
    if not isinstance(attestations,Mapping) or set(attestations)!=set(_CONTRACT): errors.add("release_receipt_gate_attestations_incomplete"); attestations={}
    for role in _CONTRACT:
        attestation=attestations.get(role)
        if not isinstance(attestation,Mapping) or set(attestation)!=_ATTEST: errors.add("release_receipt_gate_attestation_schema_not_closed"); continue
        if attestation.get("schema")!=ATTESTATION_SCHEMA or attestation.get("role")!=role or attestation.get("payload")!=claims.get(role) or not _KEY.fullmatch(str(attestation.get("key_id") or "")) or not _SIG.fullmatch(str(attestation.get("signature") or "")): errors.add("release_receipt_gate_attestation_invalid")
    challenge=receipt.get("manual_approval_challenge")
    if not isinstance(challenge,Mapping) or set(challenge)!=_CHALLENGE: errors.add("release_receipt_manual_challenge_schema_not_closed"); challenge={}
    if challenge.get("schema")!=RELEASE_CHALLENGE_SCHEMA or challenge.get("status")!="confirm_exact_preview": errors.add("release_receipt_manual_challenge_invalid")
    for key in ("preview_fingerprint","atlas_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint","promotion_gate_fingerprint","registry_path_fingerprint","base_registry_fingerprint"):
        if not _valid_fp(challenge.get(key)): errors.add("release_receipt_manual_challenge_fingerprint_invalid")
    if not _TOKEN.fullmatch(str(challenge.get("preview_token") or "")) or not _COMMIT.fullmatch(str(challenge.get("target_commit") or "")) or not isinstance(challenge.get("environment"),str) or not _KEY.fullmatch(challenge.get("environment")): errors.add("release_receipt_manual_challenge_invalid")
    base_revision=challenge.get("base_registry_revision")
    if isinstance(base_revision,bool) or not isinstance(base_revision,int) or base_revision<0: errors.add("release_receipt_manual_challenge_invalid")
    for receipt_key,challenge_key in (("preview_token","preview_token"),("preview_fingerprint","preview_fingerprint"),("atlas_fingerprint","atlas_fingerprint"),("style_artifact_fingerprint","style_artifact_fingerprint"),("craft_artifact_fingerprint","craft_artifact_fingerprint")):
        if receipt.get(receipt_key)!=challenge.get(challenge_key): errors.add("release_receipt_manual_challenge_binding_mismatch")
    if isinstance(claims.get("promotion"),Mapping) and challenge.get("promotion_gate_fingerprint")!=claims["promotion"].get("gate_fingerprint"): errors.add("release_receipt_manual_challenge_binding_mismatch")
    manual=receipt.get("manual_approval_attestation")
    if not isinstance(manual,Mapping) or set(manual)!=_ATTEST: errors.add("release_receipt_manual_attestation_schema_not_closed")
    elif manual.get("schema")!=ATTESTATION_SCHEMA or manual.get("role")!="manual_approval" or manual.get("payload")!=challenge or not _KEY.fullmatch(str(manual.get("key_id") or "")) or not _SIG.fullmatch(str(manual.get("signature") or "")): errors.add("release_receipt_manual_attestation_invalid")
    if receipt.get("receipt_fingerprint")!=fingerprint(_without(receipt,"receipt_fingerprint")): errors.add("release_receipt_fingerprint_mismatch")
    return sorted(errors)


def _make_release_receipt(persisted: Mapping[str,Any], preview: Mapping[str,Any], claims: Mapping[str,Any], attestations: Mapping[str,Any], challenge: Mapping[str,Any], manual_confirmation: Mapping[str,Any]) -> dict[str,Any]:
    atlas=preview["atlas"]
    value={"schema":RELEASE_RECEIPT_SCHEMA,"completion_receipt_fingerprint":persisted["completion_receipt"]["receipt_fingerprint"],"atlas_fingerprint":atlas["atlas_fingerprint"],"preview_fingerprint":preview["preview_fingerprint"],"preview_token":preview["preview_token"],"style_artifact_fingerprint":atlas["style_artifact_fingerprint"],"craft_artifact_fingerprint":atlas["craft_artifact_fingerprint"],"gate_claims":_plain(claims,"release_gate_claims_invalid"),"gate_attestations":_plain(attestations,"release_gate_attestations_invalid"),"manual_approval_challenge":_plain(challenge,"manual_approval_challenge_invalid"),"manual_approval_attestation":_plain(manual_confirmation,"manual_approval_attestation_invalid")}
    value["receipt_fingerprint"]=fingerprint(value)
    _require(validate_style_release_receipt(value),"release_receipt_invalid")
    return value


def transition_receipt_filename(receipt_fp: str) -> str:
    if not _valid_fp(receipt_fp): raise StylePublicationError("transition_receipt_fingerprint_invalid")
    return "style-transition-receipt-"+receipt_fp[7:]+".json"


def validate_style_transition_receipt(receipt: Mapping[str,Any]) -> list[str]:
    errors=set()
    try: receipt=_plain(receipt,"transition_receipt_not_object",MAX_PRIVATE_BYTES)
    except StylePublicationError as exc: return [exc.code]
    errors.update(_schema_errors(receipt,"style_registry_transition_receipt.schema.json"))
    if set(receipt)!=_TRANSITION_RECEIPT: return sorted(errors|{"transition_receipt_schema_not_closed"})
    if receipt.get("schema")!=TRANSITION_RECEIPT_SCHEMA: errors.add("transition_receipt_schema_invalid")
    transition=receipt.get("transition")
    if not isinstance(transition,Mapping) or set(transition)!=_TRANSITION: errors.add("transition_receipt_payload_schema_not_closed"); transition={}
    if transition.get("schema")!=REGISTRY_TRANSITION_SCHEMA or not isinstance(transition.get("action"),str) or transition.get("action") not in {"activate_rollback","deprecate","contest"}: errors.add("transition_receipt_payload_invalid")
    for key in ("target_atlas_fingerprint","registry_path_fingerprint","base_registry_fingerprint"):
        if not _valid_fp(transition.get(key)): errors.add("transition_receipt_payload_fingerprint_invalid")
    if not isinstance(transition.get("environment"),str) or not _KEY.fullmatch(transition.get("environment")): errors.add("transition_receipt_payload_invalid")
    base_revision=transition.get("base_registry_revision")
    if isinstance(base_revision,bool) or not isinstance(base_revision,int) or base_revision<0: errors.add("transition_receipt_payload_invalid")
    manual=receipt.get("manual_approval_attestation")
    if not isinstance(manual,Mapping) or set(manual)!=_ATTEST: errors.add("transition_receipt_manual_attestation_schema_not_closed")
    elif manual.get("schema")!=ATTESTATION_SCHEMA or manual.get("role")!="manual_approval" or manual.get("payload")!=transition or not _KEY.fullmatch(str(manual.get("key_id") or "")) or not _SIG.fullmatch(str(manual.get("signature") or "")): errors.add("transition_receipt_manual_attestation_invalid")
    if not _valid_fp(receipt.get("receipt_fingerprint")) or receipt.get("receipt_fingerprint")!=fingerprint(_without(receipt,"receipt_fingerprint")): errors.add("transition_receipt_fingerprint_mismatch")
    return sorted(errors)


def _make_transition_receipt(payload: Mapping[str,Any], manual_confirmation: Mapping[str,Any]) -> dict[str,Any]:
    value={"schema":TRANSITION_RECEIPT_SCHEMA,"transition":_plain(payload,"registry_transition_invalid"),"manual_approval_attestation":_plain(manual_confirmation,"manual_approval_attestation_invalid")}
    value["receipt_fingerprint"]=fingerprint(value)
    _require(validate_style_transition_receipt(value),"transition_receipt_invalid")
    return value


def _read_regular_bytes(path: Path, code: str, limit: int=MAX_PRIVATE_BYTES) -> bytes:
    fd=None
    try:
        if path.is_symlink(): raise StylePublicationError(code+"_symlink_forbidden")
        fd=os.open(path,os.O_RDONLY|getattr(os,"O_BINARY",0)|getattr(os,"O_NOFOLLOW",0))
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode): raise StylePublicationError(code+"_not_regular")
        if info.st_nlink!=1: raise StylePublicationError(code+"_hardlink_forbidden")
        if info.st_size>limit: raise StylePublicationError(code+"_size_limit")
        chunks=[]; remaining=limit+1
        while remaining:
            chunk=os.read(fd,min(65536,remaining))
            if not chunk: break
            chunks.append(chunk); remaining-=len(chunk)
        raw=b"".join(chunks)
        if len(raw)>limit: raise StylePublicationError(code+"_size_limit")
        return raw
    except StylePublicationError: raise
    except Exception as exc: raise StylePublicationError(code) from exc
    finally:
        if fd is not None: os.close(fd)


def _read_json(path: Path, code: str) -> dict[str,Any]:
    try: value=json.loads(_read_regular_bytes(path,code).decode("utf-8"))
    except StylePublicationError: raise
    except Exception as exc: raise StylePublicationError(code) from exc
    if not isinstance(value,dict): raise StylePublicationError(code)
    return value


def _fsync_dir(root: Path):
    try:
        fd=os.open(root,os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL,errno.EPERM,errno.ENOTSUP,errno.EACCES}: raise


def _stage_json(root: Path, value: Mapping[str,Any], prefix: str) -> Path:
    handle=tempfile.NamedTemporaryFile(mode="wb",delete=False,dir=root,prefix=prefix,suffix=".tmp"); path=Path(handle.name).resolve()
    try: handle.write(_canonical(value)+b"\n"); handle.flush(); os.fsync(handle.fileno()); handle.close(); return path
    except Exception:
        try: handle.close()
        finally:
            try: path.unlink()
            except FileNotFoundError: pass
        raise


def _has_symlink(path: Path) -> bool:
    absolute=path.absolute(); current=absolute
    while True:
        if current.is_symlink(): return True
        if current.parent==current: return False
        current=current.parent


@contextmanager
def _registry_lock(root: Path) -> Iterator[None]:
    path=root/".style-registry.lock"
    if path.is_symlink(): raise StylePublicationError("style_registry_lock_symlink_forbidden")
    fd=os.open(path,os.O_CREAT|os.O_RDWR|getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode): raise StylePublicationError("style_registry_lock_not_regular")
        if info.st_nlink!=1: raise StylePublicationError("style_registry_lock_hardlink_forbidden")
        if os.name=="nt":
            import msvcrt
            if os.fstat(fd).st_size==0: os.write(fd,b"0"); os.fsync(fd)
            os.lseek(fd,0,os.SEEK_SET)
            try: msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            except OSError as exc: raise StylePublicationError("style_registry_locked") from exc
            try: yield
            finally: os.lseek(fd,0,os.SEEK_SET); msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc: raise StylePublicationError("style_registry_locked") from exc
            try: yield
            finally: fcntl.flock(fd,fcntl.LOCK_UN)
    finally: os.close(fd)


def _path_fp(path: Path) -> str: return fingerprint({"registry_path":os.path.normcase(str(path.resolve()))})


class StyleAtlasPublisher:
    """Trusted Host boundary. Release accepts receipt fingerprints, not bundles."""
    def __init__(self, *, registry_path: str|Path, trust_store: StylePublicationTrustStore, candidate_receipt_loader: Callable[[str],Mapping[str,Any]], environment: str="public_general_style_atlas"):
        if not isinstance(trust_store,StylePublicationTrustStore) or not callable(candidate_receipt_loader): raise StylePublicationError("publisher_configuration_invalid")
        if not isinstance(environment,str) or not _KEY.fullmatch(environment): raise StylePublicationError("publisher_environment_invalid")
        requested=Path(registry_path).expanduser().absolute()
        if requested.name!="style_registry.json" or _has_symlink(requested): raise StylePublicationError("style_registry_path_invalid")
        resolved_parent=requested.parent.resolve()
        if requested.parent!=resolved_parent: raise StylePublicationError("style_registry_path_invalid")
        self.registry_path=resolved_parent/requested.name
        self.trust_policy_path=resolved_parent/TRUST_POLICY_FILENAME
        if _has_symlink(self.trust_policy_path) or not self.trust_policy_path.exists(): raise StylePublicationError("style_publication_trust_policy_missing")
        policy=_read_json(self.trust_policy_path,"style_publication_trust_policy_read_failed")
        _require(validate_style_publication_trust_policy(policy),"style_publication_trust_policy_invalid")
        trust_store.require_policy(policy)
        self.trust_policy_fingerprint=policy["policy_fingerprint"]
        self.trust_store,self.loader,self.environment=trust_store,candidate_receipt_loader,environment

    def _require_current_trust_policy(self, root: Path):
        if self.trust_policy_path.is_symlink() or self.trust_policy_path.parent.resolve()!=root.resolve(): raise StylePublicationError("style_publication_trust_policy_symlink_or_containment_invalid")
        if not self.trust_policy_path.exists(): raise StylePublicationError("style_publication_trust_policy_missing")
        policy=_read_json(self.trust_policy_path,"style_publication_trust_policy_read_failed")
        _require(validate_style_publication_trust_policy(policy),"style_publication_trust_policy_invalid")
        if policy["policy_fingerprint"]!=self.trust_policy_fingerprint: raise StylePublicationError("style_publication_trust_policy_changed")
        self.trust_store.require_policy(policy)

    def _load(self, receipt_fp: str) -> dict[str,Any]:
        if not _valid_fp(receipt_fp): raise StylePublicationError("completion_receipt_fingerprint_invalid")
        try: value=self.loader(receipt_fp)
        except Exception as exc: raise StylePublicationError("completion_receipt_lookup_failed") from exc
        return _persisted(value,receipt_fp)

    def _prepare(self, receipt_fp: str, *, semantic_leakage: Mapping[str,Any], blind_ab: Mapping[str,Any], promotion_gate: Mapping[str,Any], promotion_candidate: Mapping[str,Any], attestations: Mapping[str,Mapping[str,Any]]) -> tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
        persisted=self._load(receipt_fp); preview=build_style_atlas_preview(persisted["candidate_bundle"],semantic_leakage=semantic_leakage,blind_ab=blind_ab,promotion_gate=promotion_gate,promotion_candidate=promotion_candidate,forbidden_identity_terms=persisted["forbidden_identity_terms"]); gates=preview["release_gates"]
        claims={"provenance":_gate_claim("provenance","pass",persisted,persisted["provenance_receipt_fingerprint"]),"semantic_leakage":_gate_claim("semantic_leakage",gates["semantic_leakage"]["status"],persisted,gates["semantic_leakage"]["gate_fingerprint"]),"blind_ab":_gate_claim("blind_ab",gates["blind_ab"]["status"],persisted,gates["blind_ab"]["gate_fingerprint"]),"promotion":_gate_claim("promotion",gates["promotion"]["status"],persisted,gates["promotion"]["gate_fingerprint"])}
        if set(attestations)!=set(claims): raise StylePublicationError("release_gate_attestations_incomplete")
        for role,payload in claims.items(): self.trust_store.verify(attestations[role],role,payload)
        if persisted["candidate_bundle"]["local_leakage"]["local_status"]!="pass": raise StylePublicationError("local_leakage_pass_required")
        if claims["semantic_leakage"]["status"]!="pass": raise StylePublicationError("semantic_leakage_pass_required")
        if claims["blind_ab"]["status"]!="pass": raise StylePublicationError("blind_ab_pass_required")
        if claims["promotion"]["status"]!="promotable": raise StylePublicationError("promotion_gate_promotable_required")
        return persisted,preview,claims

    def _release_receipt(self, root: Path, entry: Mapping[str,Any]) -> dict[str,Any]:
        path=root/release_receipt_filename(entry["release_receipt_fingerprint"])
        if path.is_symlink() or path.parent.resolve()!=root.resolve(): raise StylePublicationError("registered_style_release_receipt_symlink_or_containment_invalid")
        if not path.exists(): raise StylePublicationError("registered_style_release_receipt_missing")
        receipt=_read_json(path,"registered_style_release_receipt_invalid")
        _require(validate_style_release_receipt(receipt),"registered_style_release_receipt_invalid")
        if receipt["receipt_fingerprint"]!=entry["release_receipt_fingerprint"]: raise StylePublicationError("registered_style_release_receipt_binding_mismatch")
        claims,attestations=receipt["gate_claims"],receipt["gate_attestations"]
        for role in _CONTRACT: self.trust_store.verify(attestations[role],role,claims[role])
        challenge=receipt["manual_approval_challenge"]
        self.trust_store.verify(receipt["manual_approval_attestation"],"manual_approval",challenge)
        if challenge["environment"]!=self.environment or challenge["registry_path_fingerprint"]!=_path_fp(self.registry_path): raise StylePublicationError("registered_style_release_receipt_target_mismatch")
        if challenge["base_registry_fingerprint"]!=entry["base_registry_fingerprint"] or challenge["base_registry_revision"]!=entry["base_registry_revision"]: raise StylePublicationError("registered_style_release_receipt_base_mismatch")
        bindings=(("atlas_fingerprint","atlas_fingerprint"),("preview_fingerprint","preview_fingerprint"),("preview_token","preview_token"),("style_artifact_fingerprint","style_artifact_fingerprint"),("craft_artifact_fingerprint","craft_artifact_fingerprint"))
        if any(receipt.get(left)!=entry.get(right) for left,right in bindings): raise StylePublicationError("registered_style_release_receipt_binding_mismatch")
        if claims["semantic_leakage"]["status"]!=entry["semantic_leakage_status"] or claims["blind_ab"]["status"]!=entry["blind_ab_status"] or claims["promotion"]["status"]!=entry["promotion_status"]: raise StylePublicationError("registered_style_release_receipt_gate_mismatch")
        return receipt

    def _transition_receipt(self, root: Path, receipt_fp: str) -> dict[str,Any]:
        path=root/transition_receipt_filename(receipt_fp)
        if path.is_symlink() or path.parent.resolve()!=root.resolve(): raise StylePublicationError("registered_style_transition_receipt_symlink_or_containment_invalid")
        if not path.exists(): raise StylePublicationError("registered_style_transition_receipt_missing")
        receipt=_read_json(path,"registered_style_transition_receipt_invalid")
        _require(validate_style_transition_receipt(receipt),"registered_style_transition_receipt_invalid")
        if receipt["receipt_fingerprint"]!=receipt_fp: raise StylePublicationError("registered_style_transition_receipt_binding_mismatch")
        payload=receipt["transition"]
        self.trust_store.verify(receipt["manual_approval_attestation"],"manual_approval",payload)
        if payload["environment"]!=self.environment or payload["registry_path_fingerprint"]!=_path_fp(self.registry_path): raise StylePublicationError("registered_style_transition_receipt_target_mismatch")
        return receipt

    @staticmethod
    def _transition_projection(registry: Mapping[str,Any], payload: Mapping[str,Any], event: Mapping[str,Any]) -> dict[str,Any]:
        action,target=payload["action"],payload["target_atlas_fingerprint"]
        if target not in {entry["atlas_fingerprint"] for entry in registry["releases"]}: raise StylePublicationError("registry_transition_target_missing")
        entries=[]
        for entry in registry["releases"]:
            state=entry["state"]
            if action=="activate_rollback":
                if entry["atlas_fingerprint"]==target:
                    if state in {"deprecated","contested"}: raise StylePublicationError("registry_transition_target_blocked")
                    state="active"
                elif state=="active": state="rolled_back"
            elif entry["atlas_fingerprint"]==target:
                if state=="active": raise StylePublicationError("active_release_cannot_be_deprecated")
                state="deprecated" if action=="deprecate" else "contested"
            entries.append({**entry,"state":state})
        next_registry={**_without(registry,"registry_fingerprint"),"revision":registry["revision"]+1,"active_atlas_fingerprint":target if action=="activate_rollback" else registry["active_atlas_fingerprint"],"parent_registry_fingerprint":registry["registry_fingerprint"],"releases":entries,"events":[*registry["events"],event]}
        next_registry["registry_fingerprint"]=fingerprint(next_registry)
        _require(validate_style_registry(next_registry),"style_registry_next_invalid")
        return next_registry

    def _replay_registry(self, root: Path, registry: Mapping[str,Any], release_receipts: Mapping[str,Mapping[str,Any]]):
        replay=_empty_registry(); entries_by_receipt={entry["release_receipt_fingerprint"]:entry for entry in registry["releases"]}
        for event in registry["events"]:
            if event["revision"]!=replay["revision"]+1: raise StylePublicationError("style_registry_event_chain_revision_mismatch")
            receipt_fp=event["receipt_fingerprint"]
            if event["kind"]=="release":
                entry=entries_by_receipt.get(receipt_fp); receipt=release_receipts.get(receipt_fp)
                if entry is None or receipt is None: raise StylePublicationError("style_registry_release_event_binding_invalid")
                challenge=receipt["manual_approval_challenge"]
                if entry["base_registry_fingerprint"]!=replay["registry_fingerprint"] or entry["base_registry_revision"]!=replay["revision"] or challenge["base_registry_fingerprint"]!=replay["registry_fingerprint"] or challenge["base_registry_revision"]!=replay["revision"]: raise StylePublicationError("style_registry_release_event_base_mismatch")
                if entry["atlas_fingerprint"] in {existing["atlas_fingerprint"] for existing in replay["releases"]}: raise StylePublicationError("style_registry_release_event_duplicate")
                prior=[{**existing,"state":"superseded" if existing["state"]=="active" else existing["state"]} for existing in replay["releases"]]
                original={**entry,"state":"active"}
                next_registry={"schema":REGISTRY_SCHEMA,"registry_version":1,"revision":replay["revision"]+1,"status":"active","atlas_schema":ATLAS_SCHEMA,"active_atlas_fingerprint":entry["atlas_fingerprint"],"parent_registry_fingerprint":replay["registry_fingerprint"],"releases":sorted([*prior,original],key=lambda item:item["atlas_fingerprint"]),"events":[*replay["events"],event]}
                next_registry["registry_fingerprint"]=fingerprint(next_registry); _require(validate_style_registry(next_registry),"style_registry_event_projection_invalid"); replay=next_registry
            else:
                transition=self._transition_receipt(root,receipt_fp)["transition"]
                if transition["base_registry_fingerprint"]!=replay["registry_fingerprint"] or transition["base_registry_revision"]!=replay["revision"]: raise StylePublicationError("style_registry_transition_event_base_mismatch")
                replay=self._transition_projection(replay,transition,event)
        if replay!=registry: raise StylePublicationError("style_registry_event_chain_projection_mismatch")

    def _registry(self, root: Path) -> dict[str,Any]:
        self._require_current_trust_policy(root)
        if self.registry_path.is_symlink() or self.registry_path.parent.resolve()!=root.resolve(): raise StylePublicationError("style_registry_symlink_or_containment_invalid")
        registry=_read_json(self.registry_path,"style_registry_read_failed") if self.registry_path.exists() else _empty_registry(); _require(validate_style_registry(registry),"style_registry_invalid")
        release_receipts={}
        for entry in registry["releases"]:
            path=root/atlas_filename(entry["atlas_fingerprint"])
            if path.is_symlink() or path.parent.resolve()!=root.resolve(): raise StylePublicationError("registered_style_atlas_symlink_or_containment_invalid")
            if not path.exists(): raise StylePublicationError("registered_style_atlas_missing")
            atlas=_read_json(path,"registered_style_atlas_invalid"); _require(validate_style_atlas(atlas),"registered_style_atlas_invalid")
            if any(atlas.get(k)!=entry.get(k) for k in ("atlas_fingerprint","style_artifact_fingerprint","craft_artifact_fingerprint")): raise StylePublicationError("registered_style_atlas_binding_mismatch")
            release_receipts[entry["release_receipt_fingerprint"]]=self._release_receipt(root,entry)
        self._replay_registry(root,registry,release_receipts)
        return registry

    def _challenge(self, preview: Mapping[str,Any], promotion: Mapping[str,Any], registry: Mapping[str,Any]) -> dict[str,Any]:
        atlas=preview["atlas"]
        return {"schema":RELEASE_CHALLENGE_SCHEMA,"status":"confirm_exact_preview","preview_token":preview["preview_token"],"preview_fingerprint":preview["preview_fingerprint"],"atlas_fingerprint":atlas["atlas_fingerprint"],"style_artifact_fingerprint":atlas["style_artifact_fingerprint"],"craft_artifact_fingerprint":atlas["craft_artifact_fingerprint"],"promotion_gate_fingerprint":preview["release_gates"]["promotion"]["gate_fingerprint"],"target_commit":promotion["artifact_binding"]["framework_ci"]["commit"],"environment":self.environment,"registry_path_fingerprint":_path_fp(self.registry_path),"base_registry_fingerprint":registry["registry_fingerprint"],"base_registry_revision":registry["revision"]}

    def prepare_release(self, completion_receipt_fingerprint: str, **kwargs: Any) -> dict[str,Any]:
        _,preview,_=self._prepare(completion_receipt_fingerprint,**kwargs); root=self.registry_path.parent; root.mkdir(parents=True,exist_ok=True)
        with _registry_lock(root): registry=self._registry(root)
        return {"schema":"quillframe_style_release_preparation_v1","preview":preview,"manual_approval_payload":self._challenge(preview,kwargs["promotion_gate"],registry),"completion_receipt_fingerprint":completion_receipt_fingerprint}

    def release(self, completion_receipt_fingerprint: str, *, manual_confirmation: Mapping[str,Any], **kwargs: Any) -> dict[str,Any]:
        persisted,preview,claims=self._prepare(completion_receipt_fingerprint,**kwargs); root=self.registry_path.parent; root.mkdir(parents=True,exist_ok=True); atlas=preview["atlas"]; target=root/atlas_filename(atlas["atlas_fingerprint"])
        if target.is_symlink() or target.parent.resolve()!=root.resolve(): raise StylePublicationError("style_atlas_target_symlink_or_containment_invalid")
        with _registry_lock(root):
            registry=self._registry(root); existing=next((x for x in registry["releases"] if x["atlas_fingerprint"]==atlas["atlas_fingerprint"]),None)
            if existing is not None:
                if existing["preview_fingerprint"]!=preview["preview_fingerprint"]: raise StylePublicationError("style_registry_release_conflict")
                stored=self._release_receipt(root,existing); current_challenge=self._challenge(preview,kwargs["promotion_gate"],registry)
                try: self.trust_store.verify(manual_confirmation,"manual_approval",current_challenge)
                except StylePublicationError:
                    self.trust_store.verify(manual_confirmation,"manual_approval",stored["manual_approval_challenge"])
                return {"schema":RELEASE_SCHEMA,"status":"released","atlas_fingerprint":atlas["atlas_fingerprint"],"preview_fingerprint":preview["preview_fingerprint"],"registry_fingerprint":registry["registry_fingerprint"],"idempotent":True}
            challenge=self._challenge(preview,kwargs["promotion_gate"],registry); self.trust_store.verify(manual_confirmation,"manual_approval",challenge)
            release_receipt=_make_release_receipt(persisted,preview,claims,kwargs["attestations"],challenge,manual_confirmation); release_receipt_fp=release_receipt["receipt_fingerprint"]; receipt_target=root/release_receipt_filename(release_receipt_fp)
            if receipt_target.is_symlink() or receipt_target.parent.resolve()!=root.resolve(): raise StylePublicationError("style_release_receipt_target_symlink_or_containment_invalid")
            entry={"atlas_fingerprint":atlas["atlas_fingerprint"],"preview_fingerprint":preview["preview_fingerprint"],"style_artifact_fingerprint":atlas["style_artifact_fingerprint"],"craft_artifact_fingerprint":atlas["craft_artifact_fingerprint"],"analysis_protocol_version":"1","content_zone":"general","preview_token":preview["preview_token"],"semantic_leakage_status":"pass","blind_ab_status":"pass","promotion_status":"promotable","manual_approval_status":"confirmed_exact_preview","state":"active","release_receipt_fingerprint":release_receipt_fp,"base_registry_fingerprint":registry["registry_fingerprint"],"base_registry_revision":registry["revision"]}
            prior=[{**x,"state":"superseded" if x["state"]=="active" else x["state"]} for x in registry["releases"]]
            event={"revision":registry["revision"]+1,"kind":"release","receipt_fingerprint":release_receipt_fp}
            next_registry={"schema":REGISTRY_SCHEMA,"registry_version":1,"revision":registry["revision"]+1,"status":"active","atlas_schema":ATLAS_SCHEMA,"active_atlas_fingerprint":atlas["atlas_fingerprint"],"parent_registry_fingerprint":registry["registry_fingerprint"],"releases":sorted([*prior,entry],key=lambda x:x["atlas_fingerprint"]),"events":[*registry["events"],event]}; next_registry["registry_fingerprint"]=fingerprint(next_registry); _require(validate_style_registry(next_registry),"style_registry_next_invalid")
            expected_atlas=_canonical(atlas)+b"\n"; expected_receipt=_canonical(release_receipt)+b"\n"
            if target.exists() and _read_regular_bytes(target,"style_atlas_target_invalid")!=expected_atlas: raise StylePublicationError("style_atlas_target_conflict")
            if receipt_target.exists() and _read_regular_bytes(receipt_target,"style_release_receipt_target_invalid")!=expected_receipt: raise StylePublicationError("style_release_receipt_target_conflict")
            atlas_stage=receipt_stage=registry_stage=None; placed=[]; registry_committed=False
            try:
                if not target.exists(): atlas_stage=_stage_json(root,atlas,".style-atlas-"); os.replace(atlas_stage,target); atlas_stage=None; placed.append(target)
                if not receipt_target.exists(): receipt_stage=_stage_json(root,release_receipt,".style-release-receipt-"); os.replace(receipt_stage,receipt_target); receipt_stage=None; placed.append(receipt_target)
                _fsync_dir(root)
                if _read_regular_bytes(target,"style_atlas_post_write_invalid")!=expected_atlas or _read_regular_bytes(receipt_target,"style_release_receipt_post_write_invalid")!=expected_receipt: raise StylePublicationError("style_release_artifact_post_write_mismatch")
                registry_stage=_stage_json(root,next_registry,".style-registry-"); os.replace(registry_stage,self.registry_path); registry_stage=None; registry_committed=True; _fsync_dir(root)
                if _read_json(self.registry_path,"style_registry_post_write_invalid")!=next_registry: raise StylePublicationError("style_registry_post_write_mismatch")
            except Exception:
                for stage in (atlas_stage,receipt_stage,registry_stage):
                    if stage is not None:
                        try: stage.unlink()
                        except FileNotFoundError: pass
                if not registry_committed:
                    for path in placed:
                        try: path.unlink()
                        except FileNotFoundError: pass
                    if placed: _fsync_dir(root)
                raise
        return {"schema":RELEASE_SCHEMA,"status":"released","atlas_fingerprint":atlas["atlas_fingerprint"],"preview_fingerprint":preview["preview_fingerprint"],"registry_fingerprint":next_registry["registry_fingerprint"],"idempotent":False}

    def prepare_registry_transition(self, action: str, target_atlas_fingerprint: str) -> dict[str,Any]:
        if not isinstance(action,str) or action not in {"activate_rollback","deprecate","contest"}: raise StylePublicationError("registry_transition_action_invalid")
        root=self.registry_path.parent
        with _registry_lock(root): registry=self._registry(root)
        if target_atlas_fingerprint not in {x["atlas_fingerprint"] for x in registry["releases"]}: raise StylePublicationError("registry_transition_target_missing")
        return {"schema":REGISTRY_TRANSITION_SCHEMA,"action":action,"target_atlas_fingerprint":target_atlas_fingerprint,"environment":self.environment,"registry_path_fingerprint":_path_fp(self.registry_path),"base_registry_fingerprint":registry["registry_fingerprint"],"base_registry_revision":registry["revision"]}

    def apply_registry_transition(self, payload: Mapping[str,Any], manual_confirmation: Mapping[str,Any]) -> dict[str,Any]:
        payload=_plain(payload,"registry_transition_invalid")
        if set(payload)!=_TRANSITION or payload.get("schema")!=REGISTRY_TRANSITION_SCHEMA: raise StylePublicationError("registry_transition_schema_not_closed")
        if not isinstance(payload.get("action"),str) or payload.get("action") not in {"activate_rollback","deprecate","contest"}: raise StylePublicationError("registry_transition_action_invalid")
        if not _valid_fp(payload.get("target_atlas_fingerprint")) or not _valid_fp(payload.get("base_registry_fingerprint")): raise StylePublicationError("registry_transition_fingerprint_invalid")
        base_revision=payload.get("base_registry_revision")
        if isinstance(base_revision,bool) or not isinstance(base_revision,int) or base_revision<0: raise StylePublicationError("registry_transition_base_revision_invalid")
        if payload.get("environment")!=self.environment or payload.get("registry_path_fingerprint")!=_path_fp(self.registry_path): raise StylePublicationError("registry_transition_target_mismatch")
        self.trust_store.verify(manual_confirmation,"manual_approval",payload); root=self.registry_path.parent
        with _registry_lock(root):
            registry=self._registry(root)
            if payload["base_registry_fingerprint"]!=registry["registry_fingerprint"] or payload["base_registry_revision"]!=registry["revision"]: raise StylePublicationError("registry_transition_base_mismatch")
            if payload["target_atlas_fingerprint"] not in {entry["atlas_fingerprint"] for entry in registry["releases"]}: raise StylePublicationError("registry_transition_target_missing")
            transition_receipt=_make_transition_receipt(payload,manual_confirmation); transition_fp=transition_receipt["receipt_fingerprint"]; receipt_target=root/transition_receipt_filename(transition_fp)
            if receipt_target.is_symlink() or receipt_target.parent.resolve()!=root.resolve(): raise StylePublicationError("style_transition_receipt_target_symlink_or_containment_invalid")
            event={"revision":registry["revision"]+1,"kind":"transition","receipt_fingerprint":transition_fp}; next_registry=self._transition_projection(registry,payload,event); expected_receipt=_canonical(transition_receipt)+b"\n"
            if receipt_target.exists() and _read_regular_bytes(receipt_target,"style_transition_receipt_target_invalid")!=expected_receipt: raise StylePublicationError("style_transition_receipt_target_conflict")
            receipt_stage=registry_stage=None; placed=False; registry_committed=False
            try:
                if not receipt_target.exists(): receipt_stage=_stage_json(root,transition_receipt,".style-transition-receipt-"); os.replace(receipt_stage,receipt_target); receipt_stage=None; placed=True; _fsync_dir(root)
                if _read_regular_bytes(receipt_target,"style_transition_receipt_post_write_invalid")!=expected_receipt: raise StylePublicationError("style_transition_receipt_post_write_mismatch")
                registry_stage=_stage_json(root,next_registry,".style-registry-"); os.replace(registry_stage,self.registry_path); registry_stage=None; registry_committed=True; _fsync_dir(root)
                if _read_json(self.registry_path,"style_registry_post_write_invalid")!=next_registry: raise StylePublicationError("style_registry_post_write_mismatch")
            except Exception:
                for stage in (receipt_stage,registry_stage):
                    if stage is not None:
                        try: stage.unlink()
                        except FileNotFoundError: pass
                if placed and not registry_committed:
                    try: receipt_target.unlink(); _fsync_dir(root)
                    except FileNotFoundError: pass
                raise
        return {"schema":RELEASE_SCHEMA,"status":"registry_transition_applied","registry_fingerprint":next_registry["registry_fingerprint"],"idempotent":False}


def release_style_atlas(*args: Any, **kwargs: Any) -> dict[str,Any]:
    """Fail closed: use a Host-configured ``StyleAtlasPublisher``."""
    raise StylePublicationError("trusted_style_atlas_publisher_required")


publish_style_atlas=release_style_atlas

__all__=["ATLAS_SCHEMA","ATTESTATION_SCHEMA","BLIND_AB_GATE_SCHEMA","DEFAULT_REGISTRY_PATH","DEFAULT_TRUST_POLICY_PATH","GATE_CLAIM_SCHEMA","PERSISTED_CANDIDATE_SCHEMA","PREVIEW_SCHEMA","REGISTRY_SCHEMA","RELEASE_CHALLENGE_SCHEMA","RELEASE_RECEIPT_SCHEMA","RELEASE_SCHEMA","RUNNER_RECEIPT_SCHEMA","SEMANTIC_LEAKAGE_GATE_SCHEMA","TRANSITION_RECEIPT_SCHEMA","TRUSTED_ROLES","TRUST_POLICY_FILENAME","TRUST_POLICY_SCHEMA","StyleAtlasPublisher","StylePublicationError","StylePublicationTrustStore","atlas_filename","build_style_atlas_preview","canonicalize_identity_terms","fingerprint","identity_policy_fingerprint","make_blind_ab_gate","make_gate_attestation_payload","make_semantic_leakage_gate","make_style_publication_trust_policy","preview_style_atlas","publish_style_atlas","release_receipt_filename","release_style_atlas","sign_style_publication_attestation","style_publication_secret_fingerprint","transition_receipt_filename","validate_style_atlas","validate_style_atlas_preview","validate_style_publication_trust_policy","validate_style_registry","validate_style_release_receipt","validate_style_transition_receipt"]
