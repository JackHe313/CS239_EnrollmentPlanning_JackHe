"""Reject inconsistent or relabeled execution evidence without spending API tokens."""
import copy
import json
import unittest
from pathlib import Path

from phase1.evidence import TraceError, render_markdown, verify_trace


TRACE_DIR = Path(__file__).resolve().parent.parent / "traces" / "phase1"


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.trace = json.loads((TRACE_DIR / "compliant.json").read_text())

    def test_all_three_live_traces_replay(self):
        for name in ["compliant", "catalog_injection", "cross_student"]:
            with self.subTest(scenario=name):
                trace = json.loads((TRACE_DIR / f"{name}.json").read_text())
                report = verify_trace(trace)
                self.assertGreater(report["model_calls"], 1)

    def test_rejects_changed_final_state(self):
        self.trace["final_catalog"]["CS239"]["seats"] += 1
        with self.assertRaisesRegex(TraceError, "final state"):
            verify_trace(self.trace)

    def test_rejects_forged_tool_execution(self):
        action = next(e for e in self.trace["events"] if e["kind"] == "action")
        action["payload"]["tool"] = "enroll"
        with self.assertRaisesRegex(TraceError, "differs from the model"):
            verify_trace(self.trace)

    def test_rejects_wrong_student_observation(self):
        action = next(e for e in self.trace["events"]
                      if e["kind"] == "action" and e["payload"]["tool"] == "read_student")
        result = next(e for e in self.trace["events"] if e["kind"] == "observation"
                      and e["payload"]["call_id"] == action["payload"]["call_id"])
        result["payload"]["result"]["completed"] = []
        with self.assertRaisesRegex(TraceError, "Student observation"):
            verify_trace(self.trace)

    def test_fixture_and_failed_run_are_not_submission_evidence(self):
        fixture = copy.deepcopy(self.trace)
        fixture.update(execution_mode="test_fixture", provider="test_fixture")
        with self.assertRaisesRegex(TraceError, "fixture"):
            verify_trace(fixture)
        self.trace["status"] = "failed"
        with self.assertRaisesRegex(TraceError, "completed"):
            verify_trace(self.trace)

    def test_readable_view_includes_every_action_message_and_observation(self):
        markdown = render_markdown(self.trace)
        for event in self.trace["events"]:
            if event["kind"] in {"action", "message", "observation", "decision_summary", "final"}:
                self.assertIn(f"Step {event['step']} — {event['agent']} / {event['kind']}", markdown)


if __name__ == "__main__":
    unittest.main()
