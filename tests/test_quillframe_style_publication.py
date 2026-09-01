from __future__ import annotations

import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from corpus.style_contract import compile_style_contract, compile_writer_safe_projection, fingerprint as sfp, make_craft_candidate
import corpus.style_publication as publication


def evidence(work: str, item: str, role: str) -> dict:
    return {"work_id":work,"evidence_id":item,"role":role,"evidence_fingerprint":sfp({"work":work,"item":item,"role":role})}


def bundle(operation: str="让视角先记录动作，再选择与人物判断有关的巨乳或其他体态细节。", local="pass") -> dict:
    craft=make_craft_candidate(record_id="PRIVATE-CLAIM-1",axis="body_appearance",operation=operation,effect="让外貌描写服务人物判断与场景运动。",applies_when=["视角人物确实会注意该身体或外貌细节。"],avoid_when=["细节与人物、动作和场景压力都没有关系。"],failure_boundary="堆砌部位标签会把人物降成静态清单。",content_zone="general",evidence_refs=[evidence("PRIVATE-WORK-A","PRIVATE-EVIDENCE-A","support"),evidence("PRIVATE-WORK-B","PRIVATE-EVIDENCE-B","support"),evidence("PRIVATE-WORK-C","PRIVATE-EVIDENCE-C","counterexample")],supports=["cross_work_discovery","heldout_replication"],counterexamples=["successful_scene_without_surface_pattern"],confidence_ppm=820000)
    contract=compile_style_contract("STYLE-INTERNAL-CONTRACT-1",[craft],content_zone="general"); projection=compile_writer_safe_projection(contract)
    leakage={"schema":"quillframe_style_leakage_summary_v1","local_status":local,"release_ready":False,"candidate_text_fingerprint":publication.fingerprint(contract),"reference_count":3,"batch_report_fingerprints":[publication.fingerprint({"report":1})],"semantic_check":"required_external"}; leakage["summary_fingerprint"]=publication.fingerprint(leakage)
    value={"schema":publication.STYLE_CANDIDATE_BUNDLE_SCHEMA,"analysis_protocol_id":publication.STYLE_ANALYSIS_PROTOCOL_ID,"public_study_id":"PS-"+"a"*32,"profile":"general","result_state":"candidate" if local=="pass" else "blocked_local_leakage","style_contract":contract,"writer_projection":projection,"candidate_artifact_fingerprint":publication.fingerprint({"style_contract":contract,"writer_projection":projection,"local_leakage_summary_fingerprint":leakage["summary_fingerprint"]}),"craft_pack_fingerprint":projection["projection_fingerprint"],"local_leakage":leakage,"promotion_state":"manual_review_required","missing_gates":["semantic","ab","promotion"],"activation_performed":False,"promotion_performed":False,"authority":False}; value["bundle_fingerprint"]=publication.fingerprint(value); return value


def promotion(b: dict) -> tuple[dict,dict]:
    from learning import promotion_gate as pg
    s,c=b["candidate_artifact_fingerprint"],b["craft_pack_fingerprint"]; refs=["ledger:a","ledger:b"]
    candidate={"schema":pg.SCHEMA,"candidate_id":"GC-REAL","scope":"general_craft","mechanism":"viewpoint embodied description","candidate_artifact_fingerprint":s,"craft_pack_fingerprint":c,"evidence":{"evidence_refs":refs,"version_target":"atlas-v1","rollback_binding":{"rollback_ref":"git:baseline","candidate_artifact_fingerprint":s,"craft_pack_fingerprint":c},"framework_ci":{"conclusion":"success","commit":"0123456789abcdef0123456789abcdef01234567","candidate_artifact_fingerprint":s,"craft_pack_fingerprint":c},"provenance_refs":refs,"logical_work_refs":refs,"counterexample_refs":["ledger:c"],"profile_boundary":{"content_zone":"general"},"public_corpus_version":"atlas-v1"}}
    candidate["semantic_review_binding"]=pg._semantic_binding(candidate["candidate_id"],"general_craft",candidate["mechanism"],refs,candidate_artifact_fingerprint=s,craft_pack_fingerprint=c)
    candidate["independent_eval_binding"]=pg._eval_binding(candidate["candidate_id"],"general_craft",candidate["mechanism"],candidate_artifact_fingerprint=s,craft_pack_fingerprint=c)
    return candidate,pg.evaluate(candidate)


def persisted(b: dict) -> dict:
    receipt={"schema":publication.RUNNER_RECEIPT_SCHEMA,"style_run_id":"STYLE-RUN-1","study_id":"STUDY-1","public_study_id":b["public_study_id"],"profile":"general","checklist_hash":publication.fingerprint({"check":1}),"protocol_fingerprint":publication.fingerprint({"protocol":1}),"sampling_config_fingerprint":publication.fingerprint({"sampling":1}),"semantic_config_fingerprint":publication.fingerprint({"semantic_config":1}),"semantic_evidence_fingerprint":publication.fingerprint({"semantic_evidence":1}),"used_source_set_fingerprint":publication.fingerprint({"used_source_set":1}),"candidate_bundle_fingerprint":b["bundle_fingerprint"],"candidate_artifact_fingerprint":b["candidate_artifact_fingerprint"],"craft_pack_fingerprint":b["craft_pack_fingerprint"]}; receipt["receipt_fingerprint"]=publication.fingerprint(receipt)
    terms=list(publication._terms(["秘密作者名","PRIVATE-EVIDENCE-A","PRIVATE-WORK-A"]))
    return {"schema":publication.PERSISTED_CANDIDATE_SCHEMA,"candidate_bundle":b,"completion_receipt":receipt,"forbidden_identity_terms":terms,"identity_policy_complete":True,"identity_policy_fingerprint":publication.identity_policy_fingerprint(terms),"provenance_receipt_fingerprint":publication.fingerprint({"provenance":"documented for abstraction","legal_safety":False})}


SECRETS={role:(role.encode()*32)[:32] for role in ("provenance","semantic_leakage","blind_ab","promotion","manual_approval")}


def release_fixture(root: Path, b: dict|None=None):
    b=b or bundle(); p=persisted(b); pc,pg=promotion(b); s,c=b["candidate_artifact_fingerprint"],b["craft_pack_fingerprint"]
    semantic=publication.make_semantic_leakage_gate(s,c,status="pass",independent=True,performed=True); blind=publication.make_blind_ab_gate(s,c,status="pass",blind=True,order_swapped=True,source_independent_tasks=True)
    policy=publication.make_style_publication_trust_policy({r:{"host":k} for r,k in SECRETS.items()}); (root/publication.TRUST_POLICY_FILENAME).write_bytes(publication._canonical(policy)+b"\n")
    trust=publication.StylePublicationTrustStore({r:{"host":k} for r,k in SECRETS.items()}); publisher=publication.StyleAtlasPublisher(registry_path=root/"style_registry.json",trust_store=trust,candidate_receipt_loader=lambda fp:p)
    claims={"provenance":publication.make_gate_attestation_payload("provenance","pass",p,p["provenance_receipt_fingerprint"]),"semantic_leakage":publication.make_gate_attestation_payload("semantic_leakage","pass",p,semantic["review_fingerprint"]),"blind_ab":publication.make_gate_attestation_payload("blind_ab","pass",p,blind["evaluation_fingerprint"]),"promotion":publication.make_gate_attestation_payload("promotion","promotable",p,publication.fingerprint(pg))}
    attest={r:publication.sign_style_publication_attestation(r,"host",SECRETS[r],v) for r,v in claims.items()}
    kwargs={"semantic_leakage":semantic,"blind_ab":blind,"promotion_gate":pg,"promotion_candidate":pc,"attestations":attest}; return publisher,p,kwargs


class StylePublicationTests(unittest.TestCase):
    def test_committed_trust_policy_is_unconfigured_and_role_separated(self):
        root=Path(__file__).resolve().parents[1]/"corpus"/"general"
        policy=json.loads((root/publication.TRUST_POLICY_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual([],publication.validate_style_publication_trust_policy(policy)); self.assertEqual("unconfigured",policy["status"])
        shared=b"z"*32
        with self.assertRaises(publication.StylePublicationError) as raised:
            publication.StylePublicationTrustStore({role:{"host":shared} for role in publication.TRUSTED_ROLES})
        self.assertEqual("trust_anchor_role_separation_invalid",raised.exception.code)
        with tempfile.TemporaryDirectory() as raw:
            target=Path(raw); (target/publication.TRUST_POLICY_FILENAME).write_bytes(publication._canonical(policy)+b"\n")
            trust=publication.StylePublicationTrustStore({role:{"host":SECRETS[role]} for role in publication.TRUSTED_ROLES})
            with self.assertRaises(publication.StylePublicationError) as raised:
                publication.StyleAtlasPublisher(registry_path=target/"style_registry.json",trust_store=trust,candidate_receipt_loader=lambda fp:{})
            self.assertEqual("style_publication_trust_policy_unconfigured",raised.exception.code)

    def test_preview_closed_source_free_body_appearance_general(self):
        b=bundle(); pc,pg=promotion(b); s,c=b["candidate_artifact_fingerprint"],b["craft_pack_fingerprint"]
        preview=publication.build_style_atlas_preview(b,semantic_leakage=publication.make_semantic_leakage_gate(s,c,status="pass",independent=True,performed=True),blind_ab=publication.make_blind_ab_gate(s,c,status="pass",blind=True,order_swapped=True,source_independent_tasks=True),promotion_gate=pg,promotion_candidate=pc)
        self.assertEqual([],publication.validate_style_atlas_preview(preview)); self.assertEqual([],publication.validate_style_atlas(preview["atlas"])); self.assertIn("巨乳",preview["atlas"]["craft_candidates"][0]["operation"]); self.assertEqual("general",preview["atlas"]["content_zone"]); self.assertNotIn("release_gates",preview["atlas"])
        text=json.dumps(preview["atlas"],ensure_ascii=False); self.assertNotIn("PRIVATE-WORK",text); self.assertNotIn("legal_safe",text)

    def test_preview_gate_is_not_release_authority_and_raw_release_fails_closed(self):
        b=bundle(); preview=publication.build_style_atlas_preview(b)
        self.assertEqual("pending",preview["release_gates"]["semantic_leakage"]["status"])
        with self.assertRaises(publication.StylePublicationError) as raised: publication.release_style_atlas(b)
        self.assertEqual("trusted_style_atlas_publisher_required",raised.exception.code)

    def test_completion_receipt_requires_bound_ai_native_semantic_fingerprints(self):
        accepted=persisted(bundle())
        for key in ("semantic_config_fingerprint","semantic_evidence_fingerprint","used_source_set_fingerprint"):
            with self.subTest(missing=key):
                missing=copy.deepcopy(accepted); missing["completion_receipt"].pop(key)
                with self.assertRaises(publication.StylePublicationError) as raised:
                    publication.make_gate_attestation_payload(
                        "provenance","pass",missing,missing["provenance_receipt_fingerprint"]
                    )
                self.assertEqual("completion_receipt_schema_not_closed",raised.exception.code)

            with self.subTest(forged=key):
                forged=copy.deepcopy(accepted)
                forged["completion_receipt"][key]=publication.fingerprint({"forged":key})
                with self.assertRaises(publication.StylePublicationError) as raised:
                    publication.make_gate_attestation_payload(
                        "provenance","pass",forged,forged["provenance_receipt_fingerprint"]
                    )
                self.assertEqual("completion_receipt_fingerprint_mismatch",raised.exception.code)

        malformed=copy.deepcopy(accepted)
        malformed["completion_receipt"]["semantic_evidence_fingerprint"]="not-a-fingerprint"
        malformed["completion_receipt"]["receipt_fingerprint"]=publication.fingerprint(
            {key:value for key,value in malformed["completion_receipt"].items() if key!="receipt_fingerprint"}
        )
        with self.assertRaises(publication.StylePublicationError) as raised:
            publication.make_gate_attestation_payload(
                "provenance","pass",malformed,malformed["provenance_receipt_fingerprint"]
            )
        self.assertEqual("completion_receipt_field_invalid",raised.exception.code)

    def test_exact_promotion_evaluator_output_required(self):
        b=bundle(); pc,pg=promotion(b); fake={"schema":"quillframe_learning_promotion_gate_v2","scope":"general_craft","status":"promotable","artifact_binding":{"candidate_artifact_fingerprint":b["candidate_artifact_fingerprint"],"craft_pack_fingerprint":b["craft_pack_fingerprint"],"all_bound":True}}
        with self.assertRaises(publication.StylePublicationError) as raised: publication.build_style_atlas_preview(b,promotion_gate=fake,promotion_candidate=pc)
        self.assertEqual("promotion_gate_evaluator_mismatch",raised.exception.code)
        self.assertEqual("promotable",publication.build_style_atlas_preview(b,promotion_gate=pg,promotion_candidate=pc)["release_gates"]["promotion"]["status"])

    def test_unicode_unc_internal_and_identity_leaks_fail_closed(self):
        synthetic_private_title = "SYNTHETIC_PRIVATE_TITLE_MARKER"
        cases=[("使用PW-"+"a"*32+"作为内部标识","internal_id_public_value"),(r"读取\\private-server\share\范文.txt","path_like_public_value"),("使用PRIVATE-EVIDENCE-A做标签","internal_id_public_value"),("秘密作者名的标志性节奏","forbidden_identity_term"),(f"借用{synthetic_private_title}的专属节奏","forbidden_identity_term")]
        for text,code in cases:
            with self.subTest(code=code):
                preview=publication.build_style_atlas_preview(bundle()); preview["atlas"]["craft_candidates"][0]["operation"]=text; preview["atlas"]["atlas_fingerprint"]=publication.fingerprint({k:v for k,v in preview["atlas"].items() if k!="atlas_fingerprint"})
                self.assertIn(code,publication.validate_style_atlas(preview["atlas"],forbidden_identity_terms=["秘密作者名","PRIVATE-EVIDENCE-A",synthetic_private_title]))

    def test_release_requires_trusted_lookup_and_signatures(self):
        with tempfile.TemporaryDirectory() as raw:
            publisher,p,kwargs=release_fixture(Path(raw)); receipt=p["completion_receipt"]["receipt_fingerprint"]
            bad=copy.deepcopy(kwargs); bad["attestations"]["semantic_leakage"]["signature"]="hmac-sha256:"+"0"*64
            with self.assertRaises(publication.StylePublicationError): publisher.prepare_release(receipt,**bad)
            with self.assertRaises(publication.StylePublicationError): publisher.prepare_release("sha256:"+"0"*64,**kwargs)

    def test_release_exact_manual_registry_binding_and_idempotence(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); receipt=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(receipt,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"])
            result=publisher.release(receipt,manual_confirmation=manual,**kwargs); self.assertFalse(result["idempotent"])
            atlas=json.loads((root/publication.atlas_filename(result["atlas_fingerprint"])).read_text(encoding="utf-8")); self.assertNotIn("release_gates",atlas); self.assertEqual([],publication.validate_style_atlas(atlas))
            registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8")); self.assertEqual(1,registry["revision"]); self.assertEqual(result["atlas_fingerprint"],registry["active_atlas_fingerprint"]); self.assertEqual([],publication.validate_style_registry(registry))
            self.assertTrue(publisher.release(receipt,manual_confirmation=manual,**kwargs)["idempotent"])

    def test_fresh_manual_challenge_can_idempotently_replay_existing_release(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); receipt=p["completion_receipt"]["receipt_fingerprint"]
            first=publisher.prepare_release(receipt,**kwargs); first_manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],first["manual_approval_payload"])
            publisher.release(receipt,manual_confirmation=first_manual,**kwargs)
            fresh=publisher.prepare_release(receipt,**kwargs); fresh_manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],fresh["manual_approval_payload"])
            self.assertTrue(publisher.release(receipt,manual_confirmation=fresh_manual,**kwargs)["idempotent"])

    def test_release_receipt_is_content_addressed_and_reverified(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); publisher.release(completion,manual_confirmation=manual,**kwargs)
            registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8")); entry=registry["releases"][0]
            self.assertNotIn("gate_attestations",entry); self.assertNotIn("manual_approval_attestation",entry)
            receipt_path=root/publication.release_receipt_filename(entry["release_receipt_fingerprint"]); release_receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual([],publication.validate_style_release_receipt(release_receipt)); self.assertEqual(set(publication._CONTRACT),set(release_receipt["gate_attestations"]))
            forged=copy.deepcopy(release_receipt); forged["gate_attestations"]["semantic_leakage"]["signature"]="hmac-sha256:"+"0"*64; forged["receipt_fingerprint"]=publication.fingerprint({k:v for k,v in forged.items() if k!="receipt_fingerprint"})
            forged_path=root/publication.release_receipt_filename(forged["receipt_fingerprint"]); forged_path.write_bytes(publication._canonical(forged)+b"\n")
            registry["releases"][0]["release_receipt_fingerprint"]=forged["receipt_fingerprint"]; registry["events"][0]["receipt_fingerprint"]=forged["receipt_fingerprint"]; registry["registry_fingerprint"]=publication.fingerprint({k:v for k,v in registry.items() if k!="registry_fingerprint"}); (root/"style_registry.json").write_bytes(publication._canonical(registry)+b"\n")
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.prepare_release(completion,**kwargs)
            self.assertEqual("semantic_leakage_attestation_signature_invalid",raised.exception.code)

    def test_missing_existing_release_receipt_blocks_load(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); publisher.release(completion,manual_confirmation=manual,**kwargs)
            registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8")); (root/publication.release_receipt_filename(registry["releases"][0]["release_receipt_fingerprint"])).unlink()
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.prepare_release(completion,**kwargs)
            self.assertEqual("registered_style_release_receipt_missing",raised.exception.code)

    def test_trust_policy_mismatch_blocks_publisher(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); active=publication.make_style_publication_trust_policy({r:{"host":k} for r,k in SECRETS.items()}); (root/publication.TRUST_POLICY_FILENAME).write_bytes(publication._canonical(active)+b"\n")
            with self.assertRaises(publication.StylePublicationError) as raised:
                publication.StylePublicationTrustStore({r:{"host":b"shared-secret-value".ljust(32,b"x")} for r in publication.TRUSTED_ROLES})
            self.assertEqual("trust_anchor_role_separation_invalid",raised.exception.code)
            changed={**SECRETS,"provenance":b"different-provenance-anchor-value"[:32].ljust(32,b"x")}
            trust=publication.StylePublicationTrustStore({r:{"host":k} for r,k in changed.items()})
            with self.assertRaises(publication.StylePublicationError) as raised: publication.StyleAtlasPublisher(registry_path=root/"style_registry.json",trust_store=trust,candidate_receipt_loader=lambda fp:{})
            self.assertEqual("trust_store_policy_mismatch",raised.exception.code)

    def test_trust_policy_post_construction_drift_blocks_load(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]
            drift=publication.make_style_publication_trust_policy(status="unconfigured"); (root/publication.TRUST_POLICY_FILENAME).write_bytes(publication._canonical(drift)+b"\n")
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.prepare_release(completion,**kwargs)
            self.assertEqual("style_publication_trust_policy_changed",raised.exception.code)

    def test_changed_registry_rejects_old_manual_approval(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); receipt=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(receipt,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"])
            registry=publication._empty_registry(); registry["revision"]=1; registry["status"]="active"; registry["active_atlas_fingerprint"]="sha256:"+"f"*64; registry["parent_registry_fingerprint"]=registry["registry_fingerprint"]; registry["releases"]=[]; registry["registry_fingerprint"]=publication.fingerprint({k:v for k,v in registry.items() if k!="registry_fingerprint"})
            # Invalid registry also fails closed before an old approval can be reused.
            (root/"style_registry.json").write_text(json.dumps(registry),encoding="utf-8")
            with self.assertRaises(publication.StylePublicationError): publisher.release(receipt,manual_confirmation=manual,**kwargs)

    def test_missing_existing_atlas_blocks_next_release(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); receipt=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(receipt,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); result=publisher.release(receipt,manual_confirmation=manual,**kwargs)
            (root/publication.atlas_filename(result["atlas_fingerprint"])).unlink()
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.prepare_release(receipt,**kwargs)
            self.assertEqual("registered_style_atlas_missing",raised.exception.code)

    def test_schema_and_hand_validation_agree_on_specialized_preview_gates(self):
        preview=publication.build_style_atlas_preview(bundle()); preview["release_gates"]["semantic_leakage"]["status"]="promotable"; preview["release_gates"]["semantic_leakage"]["gate_fingerprint"]=publication.fingerprint({"forged":True})
        preview["preview_fingerprint"]=publication.fingerprint({k:v for k,v in preview.items() if k not in {"preview_token","preview_fingerprint"}}); preview["preview_token"]=publication._preview_token(preview["preview_fingerprint"],preview["atlas"]["atlas_fingerprint"])
        self.assertTrue(publication._schema_errors(preview,"style_atlas_preview.schema.json")); self.assertIn("semantic_leakage_public_gate_invalid",publication.validate_style_atlas_preview(preview))

    def test_registry_type_errors_are_stable_and_posix_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); publisher.release(completion,manual_confirmation=manual,**kwargs)
            registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8")); registry["releases"][0]["atlas_fingerprint"]=[]; registry["registry_fingerprint"]=publication.fingerprint({k:v for k,v in registry.items() if k!="registry_fingerprint"})
            self.assertIn("style_registry_release_fingerprint_invalid",publication.validate_style_registry(registry))
        with self.assertRaises(publication.StylePublicationError) as raised: publication.build_style_atlas_preview(bundle("读取 /opt/corpus/licensed.txt 后提炼外貌动作。"))
        self.assertEqual("path_like_public_value",raised.exception.code)

    def test_apply_transition_revalidates_signed_action(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]
            prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); result=publisher.release(completion,manual_confirmation=manual,**kwargs); registry=publisher._registry(root)
            payload={"schema":publication.REGISTRY_TRANSITION_SCHEMA,"action":"bogus","target_atlas_fingerprint":result["atlas_fingerprint"],"environment":publisher.environment,"registry_path_fingerprint":publication._path_fp(publisher.registry_path),"base_registry_fingerprint":registry["registry_fingerprint"],"base_registry_revision":registry["revision"]}; approval=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],payload)
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.apply_registry_transition(payload,approval)
            self.assertEqual("registry_transition_action_invalid",raised.exception.code)

    def test_registry_event_chain_blocks_unsigned_offline_rollback(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            first_pub,first_p,first_kwargs=release_fixture(root,bundle("先写动作，再选择巨乳等体态细节一。")); first_completion=first_p["completion_receipt"]["receipt_fingerprint"]; first_prepared=first_pub.prepare_release(first_completion,**first_kwargs); first_manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],first_prepared["manual_approval_payload"]); first=first_pub.release(first_completion,manual_confirmation=first_manual,**first_kwargs)
            second_pub,second_p,second_kwargs=release_fixture(root,bundle("先改变距离，再选择巨乳等体态细节二。")); second_completion=second_p["completion_receipt"]["receipt_fingerprint"]; second_prepared=second_pub.prepare_release(second_completion,**second_kwargs); second_manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],second_prepared["manual_approval_payload"]); second_pub.release(second_completion,manual_confirmation=second_manual,**second_kwargs)
            registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8"))
            for entry in registry["releases"]: entry["state"]="active" if entry["atlas_fingerprint"]==first["atlas_fingerprint"] else "rolled_back"
            registry["active_atlas_fingerprint"]=first["atlas_fingerprint"]; registry["registry_fingerprint"]=publication.fingerprint({k:v for k,v in registry.items() if k!="registry_fingerprint"}); (root/"style_registry.json").write_bytes(publication._canonical(registry)+b"\n")
            with self.assertRaises(publication.StylePublicationError) as raised: second_pub._registry(root)
            self.assertEqual("style_registry_event_chain_projection_mismatch",raised.exception.code)

    def test_transition_receipt_is_persisted_replayed_and_required(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            first_pub,first_p,first_kwargs=release_fixture(root,bundle("动作后选择巨乳等体态细节甲。")); first_completion=first_p["completion_receipt"]["receipt_fingerprint"]; first_prepared=first_pub.prepare_release(first_completion,**first_kwargs); first_manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],first_prepared["manual_approval_payload"]); first=first_pub.release(first_completion,manual_confirmation=first_manual,**first_kwargs)
            publisher,p,kwargs=release_fixture(root,bundle("距离后选择巨乳等体态细节乙。")); completion=p["completion_receipt"]["receipt_fingerprint"]; prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); publisher.release(completion,manual_confirmation=manual,**kwargs)
            transition=publisher.prepare_registry_transition("activate_rollback",first["atlas_fingerprint"]); approval=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],transition); publisher.apply_registry_transition(transition,approval)
            registry=publisher._registry(root); self.assertEqual(first["atlas_fingerprint"],registry["active_atlas_fingerprint"]); self.assertEqual("transition",registry["events"][-1]["kind"])
            receipt_path=root/publication.transition_receipt_filename(registry["events"][-1]["receipt_fingerprint"]); receipt=json.loads(receipt_path.read_text(encoding="utf-8")); self.assertEqual([],publication.validate_style_transition_receipt(receipt))
            receipt_path.unlink()
            with self.assertRaises(publication.StylePublicationError) as raised: publisher._registry(root)
            self.assertEqual("registered_style_transition_receipt_missing",raised.exception.code)

    def test_tampered_transition_receipt_and_failed_registry_commit_are_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); completion=p["completion_receipt"]["receipt_fingerprint"]; prepared=publisher.prepare_release(completion,**kwargs); manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"]); result=publisher.release(completion,manual_confirmation=manual,**kwargs)
            transition=publisher.prepare_registry_transition("activate_rollback",result["atlas_fingerprint"]); approval=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],transition)
            real_replace=publication.os.replace
            def fail_registry_replace(source, target):
                if Path(target)==publisher.registry_path: raise OSError("registry commit failed")
                return real_replace(source,target)
            with patch("corpus.style_publication.os.replace",side_effect=fail_registry_replace):
                with self.assertRaises(OSError): publisher.apply_registry_transition(transition,approval)
            self.assertEqual([],list(root.glob("style-transition-receipt-*.json"))); self.assertEqual([],list(root.glob(".style-transition-receipt-*.tmp")))

            publisher.apply_registry_transition(transition,approval); registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8")); event=registry["events"][-1]; receipt_path=root/publication.transition_receipt_filename(event["receipt_fingerprint"]); receipt=json.loads(receipt_path.read_text(encoding="utf-8")); receipt["manual_approval_attestation"]["signature"]="hmac-sha256:"+"0"*64; receipt["receipt_fingerprint"]=publication.fingerprint({k:v for k,v in receipt.items() if k!="receipt_fingerprint"}); forged_path=root/publication.transition_receipt_filename(receipt["receipt_fingerprint"]); forged_path.write_bytes(publication._canonical(receipt)+b"\n"); event["receipt_fingerprint"]=receipt["receipt_fingerprint"]; registry["registry_fingerprint"]=publication.fingerprint({k:v for k,v in registry.items() if k!="registry_fingerprint"}); (root/"style_registry.json").write_bytes(publication._canonical(registry)+b"\n")
            with self.assertRaises(publication.StylePublicationError) as raised: publisher._registry(root)
            self.assertEqual("manual_approval_attestation_signature_invalid",raised.exception.code)

    def test_stage_failure_cleans_temp(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            with patch("corpus.style_publication.os.fsync",side_effect=OSError("boom")):
                with self.assertRaises(OSError): publication._stage_json(root,{"x":1},".style-registry-")
            self.assertEqual([],list(root.glob(".style-registry-*.tmp")))

    def test_registry_and_atlas_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            root,outside=Path(raw),Path(outside_raw); target=outside/"style_registry.json"; target.write_text("{}",encoding="utf-8")
            try: (root/"style_registry.json").symlink_to(target)
            except OSError: self.skipTest("runtime cannot create symlinks")
            trust=publication.StylePublicationTrustStore({r:{"host":k} for r,k in SECRETS.items()})
            with self.assertRaises(publication.StylePublicationError): publication.StyleAtlasPublisher(registry_path=root/"style_registry.json",trust_store=trust,candidate_receipt_loader=lambda fp:{})

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            root=Path(raw); publisher,p,kwargs=release_fixture(root); receipt=p["completion_receipt"]["receipt_fingerprint"]; prepared=publisher.prepare_release(receipt,**kwargs)
            atlas_fp=prepared["preview"]["atlas"]["atlas_fingerprint"]; outside=Path(outside_raw)/"atlas.json"; outside.write_bytes(publication._canonical(prepared["preview"]["atlas"])+b"\n")
            (root/publication.atlas_filename(atlas_fp)).symlink_to(outside)
            manual=publication.sign_style_publication_attestation("manual_approval","host",SECRETS["manual_approval"],prepared["manual_approval_payload"])
            with self.assertRaises(publication.StylePublicationError) as raised: publisher.release(receipt,manual_confirmation=manual,**kwargs)
            self.assertEqual("style_atlas_target_symlink_or_containment_invalid",raised.exception.code)

    def test_committed_schemas_execute_without_optional_dependency(self):
        root=Path(__file__).resolve().parents[1]/"corpus"/"general"; registry=json.loads((root/"style_registry.json").read_text(encoding="utf-8"))
        for name in ("style_atlas.schema.json","style_atlas_preview.schema.json","style_atlas_registry.schema.json","style_atlas_release_receipt.schema.json","style_registry_transition_receipt.schema.json","style_publication_trust_policy.schema.json"): self.assertIsInstance(json.loads((root/name).read_text(encoding="utf-8")),dict)
        self.assertEqual([],publication.validate_style_registry(registry)); self.assertEqual(0,registry["revision"])
        broken={**registry,"unexpected":True}
        self.assertTrue(publication._schema_errors(broken,"style_atlas_registry.schema.json"))
        import builtins
        real_import=builtins.__import__
        def without_jsonschema(name, *args, **kwargs):
            if name=="jsonschema" or name.startswith("jsonschema."): raise ImportError(name)
            return real_import(name,*args,**kwargs)
        with patch("builtins.__import__",side_effect=without_jsonschema):
            self.assertTrue(publication._schema_errors(broken,"style_atlas_registry.schema.json"))


if __name__=="__main__": unittest.main()
