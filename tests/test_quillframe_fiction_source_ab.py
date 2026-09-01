from __future__ import annotations

import unittest

from evals.fiction_source_ab import ARMS, PLAN_SCHEMA, validate_plan, writer_messages


def fixture() -> dict:
    return {
        "schema": PLAN_SCHEMA,
        "run_id": "source-free-ab-fixture",
        "task_mode": "SYSTEM-IMPROVE",
        "model_id": "MODEL",
        "source_free_voice_baseline": True,
        "scene_contract": {"pov": "甲", "result": "门被关上"},
        "shared_author_objectives": "自然中文；人物选择可辨认。",
        "arm_instructions": {"baseline": "直接实现。", "treatment": "把判断藏进行动。"},
        "authority": False,
    }


class FictionSourceAbTests(unittest.TestCase):
    def test_exact_two_source_free_arms_have_same_scene(self) -> None:
        plan = validate_plan(fixture())
        self.assertEqual(("baseline", "treatment"), ARMS)
        baseline = writer_messages(plan, "baseline")
        treatment = writer_messages(plan, "treatment")
        self.assertIn('"source_free_voice_baseline": true', baseline[1]["content"])
        self.assertIn('"source_free_voice_baseline": true', treatment[1]["content"])
        self.assertIn('"pov": "甲"', baseline[1]["content"])
        self.assertIn('"pov": "甲"', treatment[1]["content"])

    def test_user_token_and_cost_caps_are_rejected(self) -> None:
        for key in ("max_output_tokens", "max_cost_micros", "run_cost_budget"):
            plan = fixture()
            plan[key] = 1
            with self.assertRaises(ValueError):
                validate_plan(plan)

    def test_prose_context_is_rejected(self) -> None:
        plan = fixture()
        plan["scene_contract"]["rejected_prose"] = "old text"
        with self.assertRaises(ValueError):
            validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
