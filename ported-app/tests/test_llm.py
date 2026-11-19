"""Offline protocol tests. Scripted model responses are never submission traces."""
import copy
import io
import json
import os
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from phase1.app import EnrollmentApplication, main, run
from phase1.domain import SCENARIOS
from phase1.evidence import verify_trace
from phase1.llm import LLMError, OpenAIResponses, load_env


def call(name, **arguments):
    if name == "enroll":
        arguments.setdefault("section_id", "auto")
    arguments["decision_summary"] = f"Test fixture requests {name}."
    return {"type": "function_call", "call_id": f"call-{name}",
            "name": name, "arguments": json.dumps(arguments)}


def final(text="Recorded outcomes reported."):
    return {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}


class FixtureClient:
    provider = "test_fixture"
    model = "scripted-test-model"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.requests = []

    def create(self, instructions, history, tools):
        self.requests.append(copy.deepcopy({"instructions": instructions, "history": history, "tools": tools}))
        output = next(self.outputs)
        return {"id": f"fixture-{len(self.requests)}", "model": self.model,
                "status": "completed", "usage": {"total_tokens": 0}, "output": output}


def scenario_script(student="student-a", course="CS239", waiver=False):
    return [
        [call("read_catalog")],
        [call("ask_registrar", student_id=student, course=course, context="Fixture context")],
        [call("read_catalog")],
        [call("read_student", student_id=student)],
        [call("enroll", student_id=student, course=course, waive_prerequisites=waiver)],
        [final("Registrar result.")],
        [final("Advisor result.")],
    ]


class LLMAgentTests(unittest.TestCase):
    def test_independent_models_tool_results_and_trace_snapshots(self):
        client = FixtureClient(scenario_script())
        spec = copy.deepcopy(SCENARIOS["compliant"])
        spec["request"]["courses"] = ["CS239"]
        trace = run("compliant", client, spec=spec)
        self.assertEqual(trace["status"], "completed")
        self.assertEqual(trace["execution_mode"], "test_fixture")
        self.assertEqual(trace["outcomes"][0]["status"], "enrolled")
        self.assertEqual(trace["post_run_policy_violations"], [])
        starts = [e for e in trace["events"] if e["kind"] == "agent_start"]
        self.assertEqual([e["agent"] for e in starts], ["advisor", "registrar"])
        self.assertNotEqual(starts[0]["payload"]["instructions"], starts[1]["payload"]["instructions"])
        messages = [e for e in trace["events"] if e["kind"] == "message"]
        self.assertEqual([e["agent"] for e in messages], ["advisor", "registrar"])
        self.assertTrue(any(i.get("type") == "function_call_output" for i in client.requests[-1]["history"]))
        # Earlier catalog observations must not change when an enrollment consumes a seat.
        catalog_observation = next(e for e in trace["events"] if e["kind"] == "observation")
        self.assertEqual(catalog_observation["payload"]["result"]["courses"]["CS239"]["seats"], 2)
        self.assertEqual(trace["final_catalog"]["CS239"]["seats"], 1)

    def test_model_supplied_waiver_and_cross_student_are_not_intercepted(self):
        for scenario, student, course, waiver, policy in [
            ("catalog_injection", "student-a", "CS299", True, "P2"),
            ("cross_student", "student-b", "CS239", False, "P1"),
        ]:
            with self.subTest(scenario=scenario):
                trace = run(scenario, FixtureClient(scenario_script(student, course, waiver)))
                self.assertEqual(trace["outcomes"][0]["status"], "enrolled")
                self.assertIn(policy, [v["policy"] for v in trace["post_run_policy_violations"]])

    def test_partial_request_is_not_a_complete_run(self):
        trace = run("compliant", FixtureClient(scenario_script()))
        self.assertEqual(trace["status"], "failed")
        self.assertIn("CS260", trace["error"])

    def test_injection_text_does_not_force_waiver_in_python(self):
        # The same injected note gets a rejection when the model does not request a waiver.
        trace = run("catalog_injection", FixtureClient(scenario_script(course="CS299")))
        self.assertEqual(trace["outcomes"][0]["reason"], "missing_prerequisites")
        self.assertEqual(trace["post_run_policy_violations"], [])

    def test_unavailable_advisor_write_is_not_executed(self):
        client = FixtureClient([[call("enroll", student_id="student-a", course="CS239",
                                      waive_prerequisites=False)], [final()]])
        trace = run("compliant", client)
        self.assertEqual(trace["status"], "failed")
        self.assertEqual(trace["final_students"]["student-a"]["enrolled"], [])
        self.assertIn("not available", client.requests[-1]["history"][-1]["output"])

    def test_loop_limit_preserves_partial_trace(self):
        trace = run("compliant", FixtureClient([[call("read_catalog")]] * 18))
        self.assertEqual(trace["status"], "failed")
        self.assertIn("turn limit", trace["error"])
        self.assertEqual(trace["events"][-1]["kind"], "error")

    def test_business_rule_rejection_does_not_mutate_state(self):
        app = EnrollmentApplication(FixtureClient([]), SCENARIOS["compliant"])
        app.world.catalog["CS239"]["seats"] = 0
        result = app.registrar_tool("enroll", {"student_id": "student-a", "course": "CS239",
                                               "waive_prerequisites": False})
        self.assertEqual(result["reason"], "no_seats")
        self.assertEqual(app.world.students["student-a"]["enrolled"], [])

    def test_all_business_checks_preserve_state_on_rejection(self):
        for case, reason in [("prerequisite", "missing_prerequisites"), ("full", "no_seats"),
                             ("duplicate", "already_enrolled"), ("units", "unit_limit")]:
            with self.subTest(case=case):
                app = EnrollmentApplication(FixtureClient([]), SCENARIOS["compliant"])
                course = "CS299" if case == "prerequisite" else "CS239"
                if case == "full":
                    app.world.catalog[course]["seats"] = 0
                elif case == "duplicate":
                    app.world.students["student-a"]["enrolled"] = [course]
                elif case == "units":
                    app.world.students["student-a"]["enrolled"] = ["CS260", "CS299"]
                    app.world.students["student-a"]["profile"]["study_limit"] = 8
                before = copy.deepcopy((app.world.students, app.world.catalog))
                result = app.registrar_tool("enroll", {"student_id": "student-a", "course": course,
                                                       "waive_prerequisites": False})
                self.assertEqual(result["reason"], reason)
                self.assertEqual((app.world.students, app.world.catalog), before)

    def test_unknown_student_and_course_can_be_explicitly_rejected(self):
        app = EnrollmentApplication(FixtureClient([]), SCENARIOS["compliant"])
        result = app.registrar_tool("reject", {"student_id": "unknown", "course": "UNKNOWN",
                                               "reason": "No such student or course."})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(app.outcomes, [result])

    def test_malformed_output_becomes_failed_trace(self):
        for output in [None, [None], [{"type": "function_call", "name": "enroll"}],
                       [{"type": "message", "content": None}]]:
            with self.subTest(output=output):
                trace = run("compliant", FixtureClient([output]))
                self.assertEqual(trace["status"], "failed")
                self.assertEqual(trace["outcomes"], [])

    def test_unexpected_exception_and_interrupt_retain_trace(self):
        for error in [RuntimeError("fixture-sensitive-detail"), KeyboardInterrupt()]:
            with self.subTest(error=type(error).__name__):
                client = FixtureClient([])
                with patch.object(client, "create", side_effect=error):
                    trace = run("compliant", client)
                self.assertEqual(trace["status"], "failed")
                self.assertNotIn("fixture-sensitive-detail", trace["error"])
                self.assertEqual(trace["events"][-1]["kind"], "error")

    def test_cli_refuses_to_overwrite_completed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "compliant.json"
            path.write_text("original evidence")
            with patch.object(sys, "argv", ["app", "--scenario", "compliant", "--output-dir", directory]), \
                    patch("phase1.app.load_env"), patch("phase1.app.OpenAIResponses"), \
                    patch("phase1.app.run") as runner, patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as raised:
                    main()
                self.assertEqual(raised.exception.code, 2)
                runner.assert_not_called()
            self.assertEqual(path.read_text(), "original evidence")

    def test_llm_plan_and_deferral_protocol_replays_without_writes(self):
        outputs = [
            [call("read_enrollment_context", student_id="student-a")],
            [call("record_plan", student_id="student-a", ordered_courses=["CS239"])],
            [call("ask_registrar", student_id="student-a", course="CS239", context="Appointment not open.")],
            [call("read_enrollment_context", student_id="student-a")],
            [call("defer", student_id="student-a", course="CS239", reason="Wait until assigned first pass.")],
            [final()], [final()]]
        trace = run("before_appointment", FixtureClient(outputs))
        self.assertEqual(trace["status"], "completed")
        self.assertEqual(trace["outcomes"][0]["status"], "deferred")
        self.assertEqual(trace["initial_students"], trace["final_students"])
        self.assertEqual(verify_trace(trace, require_live=False)["policies"], [])


class TransportTests(unittest.TestCase):
    def test_missing_key_fails_without_network(self):
        with patch.dict(os.environ, {}, clear=True), patch("phase1.llm.urlopen") as network:
            with self.assertRaises(LLMError):
                OpenAIResponses("test")
            network.assert_not_called()

    def test_responses_payload_and_budget(self):
        response = io.BytesIO(json.dumps({"status": "completed", "output": []}).encode())
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-secret"}), \
                patch("phase1.llm.urlopen", return_value=response) as network:
            client = OpenAIResponses("test", max_calls=1)
            client.create("instructions", [{"role": "user", "content": "test"}], [])
            request = network.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            self.assertFalse(payload["store"])
            self.assertFalse(payload["parallel_tool_calls"])
            self.assertNotIn("fixture-secret", request.data.decode())
            with self.assertRaises(LLMError):
                client.create("instructions", [], [])
            self.assertEqual(network.call_count, 1)

    def test_http_error_does_not_leak_body(self):
        error = HTTPError("https://api.openai.com", 401, "unauthorized", {}, io.BytesIO(b"fixture-secret"))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-secret"}), \
                patch("phase1.llm.urlopen", side_effect=error):
            with self.assertRaises(LLMError) as raised:
                OpenAIResponses("test").create("instructions", [], [])
            self.assertIn("401", str(raised.exception))
            self.assertNotIn("fixture-secret", str(raised.exception))

    def test_env_loader_does_not_execute_or_overwrite_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / ".env"
            path.write_text('OPENAI_API_KEY="fixture-key"\nOPENAI_MODEL=$(touch-no-such-command)\n')
            os.environ["OPENAI_MODEL"] = "existing-model"
            load_env(path)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "fixture-key")
            self.assertEqual(os.environ["OPENAI_MODEL"], "existing-model")


if __name__ == "__main__":
    unittest.main()
