from __future__ import annotations

import unittest
from copy import deepcopy

from model_runtime import (
    CapabilityEvidence,
    DiscoveredModel,
    MemorySecretStore,
    MockTransport,
    ModelRuntime,
    ModelRuntimeError,
    ModelServiceSnapshot,
)
from model_runtime.contracts import fingerprint, model_version_fingerprint, now_iso
from model_runtime.fiction_audition import (
    ARTIFACT_SCHEMA,
    PLAN_SCHEMA,
    PRESENTATION_SCHEMA,
    SCHEMA,
    SELECTION_SCHEMA,
    validate_confirmation,
)
from model_runtime.manager import ModelServiceManager
from tests.test_quillframe_model_runtime import MemoryRepository


def signed(value: dict, key: str) -> dict:
    value[key] = fingerprint(value)
    return value


def verified_model(model_id: str) -> DiscoveredModel:
    stamp = now_iso()
    return DiscoveredModel(
        model_id=model_id,
        protocol="openai_chat_completions",
        capabilities={
            "text": CapabilityEvidence(
                "text", "verified", "verified", stamp, evidence_ref="fixture:text"
            )
        },
    )


def confirmation_for(candidates: list[tuple[str, DiscoveredModel]]) -> dict:
    scene = fingerprint("fiction-scene-fixture")
    plan = signed({
        "schema": PLAN_SCHEMA,
        "plan_id": "AUDITION-FIXTURE",
        "candidate_models": [{
            "service_id": service_id,
            "model_id": model.model_id,
            "model_version_fingerprint": model_version_fingerprint(service_id, model),
        } for service_id, model in candidates],
        "scene_fingerprints": [scene],
        "voice_source_fingerprints": [],
        "max_output_tokens": 4000,
        "max_cost_micros": 100_000,
        "approved_call_count": len(candidates),
        "author_cost_authorization_ref": "author-approved-cost:fixture",
        "authority": False,
    }, "plan_fingerprint")
    artifacts = []
    labels = []
    for index, (service_id, model) in enumerate(candidates):
        label = f"Candidate-{index + 1}"
        labels.append(label)
        artifacts.append(signed({
            "schema": ARTIFACT_SCHEMA,
            "plan_fingerprint": plan["plan_fingerprint"],
            "scene_fingerprint": scene,
            "model_version_fingerprint": model_version_fingerprint(service_id, model),
            "blind_label": label,
            "request_fingerprint": fingerprint(["request", index]),
            "output_fingerprint": fingerprint(["output", index]),
            "billing_receipt_fingerprint": fingerprint(["billing", index]),
            "authority": False,
        }, "artifact_fingerprint"))
    presentations = []
    for variant, order in (("forward", list(range(len(labels)))),
                           ("reverse", list(reversed(range(len(labels)))))):
        presentations.append(signed({
            "schema": PRESENTATION_SCHEMA,
            "plan_fingerprint": plan["plan_fingerprint"],
            "scene_fingerprint": scene,
            "order_variant": variant,
            "ordered_blind_labels": [labels[index] for index in order],
            "artifact_fingerprints": [artifacts[index]["artifact_fingerprint"] for index in order],
            "model_identity_hidden": True,
            "authority": False,
        }, "presentation_fingerprint"))
    selected_service, selected_model = candidates[0]
    selection = signed({
        "schema": SELECTION_SCHEMA,
        "plan_fingerprint": plan["plan_fingerprint"],
        "selected_service_id": selected_service,
        "selected_model_id": selected_model.model_id,
        "selected_model_version_fingerprint": model_version_fingerprint(
            selected_service, selected_model
        ),
        "presentation_fingerprints": [
            item["presentation_fingerprint"] for item in presentations
        ],
        "author_confirmation_ref": "author-blind-selection:fixture",
        "author_blind_selection": True,
        "authority": False,
    }, "selection_fingerprint")
    return signed({
        "schema": SCHEMA,
        "plan": plan,
        "artifacts": artifacts,
        "presentations": presentations,
        "selection": selection,
        "authority": False,
    }, "confirmation_fingerprint")


class FictionAuditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = ModelRuntime(
            secret_store=MemorySecretStore(), transport=MockTransport({})
        )
        self.repository = MemoryRepository()
        self.models = [("SERVICE-A", verified_model("MODEL-A")),
                       ("SERVICE-B", verified_model("MODEL-B"))]
        for service_id, model in self.models:
            snapshot = ModelServiceSnapshot(
                service_id=service_id,
                endpoint=f"https://{service_id.lower()}.example/v1",
                credential_ref=None,
                discovered_at=now_iso(),
                auth_style="bearer",
                models=[model],
            )
            self.runtime._snapshots[service_id] = snapshot
            self.repository.save_snapshot(snapshot)

    def test_confirmation_binds_plan_artifacts_swapped_orders_and_author_selection(self) -> None:
        receipt = confirmation_for(self.models)
        self.assertEqual(receipt, validate_confirmation(receipt))
        bad_hex = deepcopy(receipt)
        bad_hex["plan"]["scene_fingerprints"][0] = "sha256:" + "z" * 64
        bad_hex["plan"]["plan_fingerprint"] = fingerprint({
            key: value for key, value in bad_hex["plan"].items()
            if key != "plan_fingerprint"
        })
        bad_hex["confirmation_fingerprint"] = fingerprint({
            key: value for key, value in bad_hex.items() if key != "confirmation_fingerprint"
        })
        with self.assertRaises(ValueError):
            validate_confirmation(bad_hex)
        unswapped = deepcopy(receipt)
        unswapped["presentations"][1]["ordered_blind_labels"] = list(
            unswapped["presentations"][0]["ordered_blind_labels"]
        )
        unswapped["presentations"][1]["presentation_fingerprint"] = fingerprint({
            key: value for key, value in unswapped["presentations"][1].items()
            if key != "presentation_fingerprint"
        })
        unswapped["selection"]["presentation_fingerprints"] = [
            item["presentation_fingerprint"] for item in unswapped["presentations"]
        ]
        unswapped["selection"]["selection_fingerprint"] = fingerprint({
            key: value for key, value in unswapped["selection"].items()
            if key != "selection_fingerprint"
        })
        unswapped["confirmation_fingerprint"] = fingerprint({
            key: value for key, value in unswapped.items() if key != "confirmation_fingerprint"
        })
        with self.assertRaises(ValueError):
            validate_confirmation(unswapped)

    def test_fiction_capability_is_exact_version_bound_and_revalidated_on_selection(self) -> None:
        manager = ModelServiceManager(
            self.runtime, self.repository, self.runtime.secret_store
        )
        receipt = confirmation_for(self.models)
        manager.confirm_fiction_writing(receipt)
        selected = self.runtime.select_model(
            "SERVICE-A", {"text", "fiction_writing"}, allow_probe=False
        )
        self.assertEqual("MODEL-A", selected.model_id)
        selected.protocol = "openai_responses"
        with self.assertRaises(ModelRuntimeError) as stale:
            self.runtime.select_model(
                "SERVICE-A", {"text", "fiction_writing"}, allow_probe=False
            )
        self.assertEqual("no_eligible_model", stale.exception.code)

    def test_restore_strips_verified_fiction_capability_without_exact_receipt(self) -> None:
        model = verified_model("FORGED")
        model.capabilities["fiction_writing"] = CapabilityEvidence(
            "fiction_writing", "verified", "manual_override", now_iso(),
            evidence_ref=fingerprint("forged"),
        )
        snapshot = ModelServiceSnapshot(
            service_id="SERVICE-FORGED",
            endpoint="https://forged.example/v1",
            credential_ref=None,
            discovered_at=now_iso(),
            auth_style="bearer",
            models=[model],
        )
        restored = self.runtime.restore_snapshot(snapshot.to_dict())
        self.assertNotIn("fiction_writing", restored.models[0].capabilities)


if __name__ == "__main__":
    unittest.main()
