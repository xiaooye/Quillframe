from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "harness" / "semantic_workers"))
from registered_contract_binding import validate_registered_job
from semantic_worker_router import make_contract_job

FP="sha256:"+"a"*64

class SemanticContextContractTests(unittest.TestCase):
    def test_profile_derive_registered_contract_is_valid(self):
        job=make_contract_job("context.profile_derive","CHAR-1",{
            "source":{"object_id":"CHAR-1","object_type":"Character","source_fingerprint":FP,"model_view":{},"stage_hints":["character_simulation"]},
            "manual_override_present":False,
        },source_session_id="SES-TEST")
        self.assertEqual(job["kind"],"artifact_analyze")
        self.assertEqual(validate_registered_job(job),[])

    def test_stage_select_registered_contract_is_valid(self):
        job=make_contract_job("context.stage_select","RUN-1",{
            "task":{},"stage_id":"draft","candidate_universe_fingerprint":FP,
            "candidates":[{"profile_id":"PROF-1","object_id":"CHAR-1","authority":"accepted","lifecycle":"active","source_fingerprint":FP,"profile_fingerprint":FP,"description":"d","trigger_when":"t","estimated_tokens":8,"semantic_tags":[],"required_for_grounding":True}],
            "hard_budget":128,
        },source_session_id="SES-TEST")
        self.assertEqual(job["kind"],"artifact_audit")
        self.assertEqual(validate_registered_job(job),[])

if __name__ == "__main__":
    unittest.main()
