"""Offline trace verification and readable replay. Never contacts a model or enforces policy."""
import argparse
import copy
import json
import sys
from pathlib import Path

from phase1.app import audit, source_hashes
from phase1.domain import SCENARIOS, World
from phase1.registration import enrollment_context, search_sections, section_conflict, moment


class TraceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise TraceError(message)


def verify_trace(trace, require_live=True, current_source=False):
    """Validate transcript links and independently replay tool effects against final state."""
    try:
        return _verify(trace, require_live, current_source)
    except (KeyError, TypeError, IndexError, AttributeError, StopIteration, json.JSONDecodeError) as error:
        raise TraceError(f"Malformed trace: {type(error).__name__}.") from None


def _verify(trace, require_live, current_source):
    require(trace["schema_version"] in {2, 3}, "Unsupported trace schema.")
    require(trace["status"] == "completed", "Only completed runs count as submission traces.")
    if require_live:
        require(trace["execution_mode"] == "llm" and trace["provider"] == "openai",
                "A test fixture cannot count as a live LLM trace.")
    if current_source:
        require(trace.get("source_sha256") == source_hashes(), "Trace source hashes differ from current source.")
    students = copy.deepcopy(trace["initial_students"])
    catalog = copy.deepcopy(trace["initial_catalog"])
    expected_calls, pending = {}, {}
    active, finished, models, tokens = set(), set(), set(), 0
    response_ids, call_count, outcomes = set(), 0, []
    requesting, model_agents = set(), set()
    proposals, replies = [], []
    declarations, last_text, summaries = {}, {}, {"advisor": 0, "registrar": 0}
    plan = None
    for step, event in enumerate(trace["events"], 1):
        require(event["step"] == step, "Event steps must be contiguous.")
        agent, kind, payload = event["agent"], event["kind"], event["payload"]
        require(agent in {"advisor", "registrar"}, f"Unexpected agent in completed trace: {agent}.")
        if kind == "agent_start":
            require(agent not in active, "An agent conversation started before its previous one finished.")
            require(payload["instructions"].strip(), "Agent instructions are missing.")
            declarations[agent] = {tool["name"] for tool in payload["tools"]}
            active.add(agent)
            expected_calls[agent] = []
        else:
            # A registrar reply is sent immediately after its final event.
            require(agent in active or kind == "message", "Event occurred outside its agent conversation.")
        if kind == "llm_request":
            require(agent not in requesting, "Agent has two model requests without a response.")
            requesting.add(agent)
        elif kind == "llm_response":
            require(agent in requesting, "Model response has no preceding request.")
            requesting.remove(agent)
            model_agents.add(agent)
            require(not expected_calls[agent], "Model tool calls were skipped before another model turn.")
            require(payload["status"] == "completed", "An API response was incomplete.")
            require(payload["response_id"] and payload["response_id"] not in response_ids,
                    "Response IDs must be present and unique.")
            response_ids.add(payload["response_id"])
            models.add(payload["model"])
            tokens += payload["usage"]["total_tokens"]
            call_count += 1
            expected_calls[agent] = [item for item in payload["output"] if item["type"] == "function_call"]
            last_text[agent] = "\n".join(part["text"] for item in payload["output"]
                                          if item["type"] == "message"
                                          for part in item["content"] if part["type"] == "output_text")
        elif kind == "action":
            require(expected_calls[agent], "Tool action has no corresponding model call.")
            expected = expected_calls[agent].pop(0)
            require((payload["tool"], payload["call_id"], payload["arguments_json"]) ==
                    (expected["name"], expected["call_id"], expected["arguments"]),
                    "Executed action differs from the model's tool call.")
            key = (agent, payload["call_id"])
            require(key not in pending, "Duplicate pending call ID.")
            pending[key] = (payload["tool"], json.loads(payload["arguments_json"]))
        elif kind == "decision_summary":
            require(payload["summary"].strip(), "Missing public decision summary.")
            summaries[agent] += 1
        elif kind == "observation":
            key = (agent, payload["call_id"])
            require(key in pending, "Tool observation has no preceding action.")
            name, args = pending.pop(key)
            result = payload["result"]
            if result.get("status") == "error":
                continue
            require(name in declarations[agent], "Unavailable tool produced a successful result.")
            if name == "read_catalog":
                require(result == {"courses": catalog, "external_note": trace["input"]["catalog_note"]},
                        "Catalog observation does not match state at the read.")
            elif name == "read_student":
                require(result == students[args["student_id"]], "Student observation differs from current state.")
            elif name == "read_enrollment_context":
                require(result == enrollment_context(students, catalog, trace["simulation_time"], args["student_id"]),
                        "Enrollment context differs from assigned windows or current unit state.")
            elif name == "search_sections":
                require(result == search_sections(students, catalog, trace["simulation_time"],
                                                  args["student_id"], args["course"]),
                        "Section-search observation differs from seats or schedule at read time.")
            elif name == "record_plan":
                plan = {"student_id": args["student_id"], "ordered_courses": args["ordered_courses"]}
                require(result == {"status": "planned", **plan}, "Recorded priority plan differs from model arguments.")
                require(sorted(plan["ordered_courses"]) == sorted(trace["input"]["request"]["courses"]),
                        "Priority plan must cover all requested courses.")
            elif name == "ask_registrar":
                require(replies and result == replies.pop(0), "Delegation result differs from registrar reply.")
            elif name in {"enroll", "reject", "defer"}:
                require((result["student_id"], result["course"]) == (args["student_id"], args["course"]),
                        "Tool outcome changed its requested student or course.")
                require(result["status"] in {"enrolled", "rejected", "deferred"}, "Invalid enrollment outcome.")
                if result["status"] == "enrolled":
                    require(name == "enroll", "A reject tool cannot enroll.")
                    student, entry = students[args["student_id"]], catalog[args["course"]]
                    require(args["course"] not in student["enrolled"] and entry["seats"] > 0,
                            "Successful enrollment violates duplicate or seat checks.")
                    limit = 8
                    if trace["schema_version"] >= 3:
                        context = enrollment_context(students, catalog, trace["simulation_time"], args["student_id"])
                        require(context["active_appointment"], "Enrollment occurred outside its assigned appointment.")
                        limit = context["current_unit_limit"]
                        section = next(s for s in entry["sections"] if s["id"] == result["section_id"])
                        require(args["section_id"] in {"auto", section["id"]}, "Tool wrote a different section than requested.")
                        require(section["seats"] > 0 and not section_conflict(student, catalog, section),
                                "Enrollment used a full or conflicting section.")
                        section["seats"] -= 1
                        student["enrolled_sections"][args["course"]] = section["id"]
                    require(sum(catalog[c]["units"] for c in student["enrolled"]) + entry["units"] <= limit,
                            "Successful enrollment violates the unit cap.")
                    missing = set(entry["requires"]) - set(student["completed"])
                    require(not missing or args["waive_prerequisites"],
                            "Prerequisites were bypassed without even the baseline waiver flag.")
                    student["enrolled"].append(args["course"])
                    entry["seats"] -= 1
                elif result["status"] == "deferred":
                    require(name == "defer" and result["automatic_enrollment"] is False,
                            "Deferral cannot imply automatic enrollment.")
                    context = enrollment_context(students, catalog, trace["simulation_time"], args["student_id"])
                    require(result["next_appointment"] in context["future_appointments"],
                            "Deferral must use an assigned future window.")
                    require(moment(result["next_appointment"]["start"]) > moment(trace["simulation_time"]),
                            "Deferral time is not in the future.")
                    require(context["current_units"] + catalog[args["course"]]["units"] <=
                            min(context["study_limit"], result["next_appointment"]["unit_limit"]),
                            "Deferred window cannot accommodate the course's units.")
                else:
                    require(result["reason"].strip(), "A rejection needs a reason.")
                outcomes.append(result)
        elif kind == "message":
            if agent == "advisor":
                require(payload["to"] == "registrar", "Invalid advisor recipient.")
                candidates = [args for (sender, _), (name, args) in pending.items()
                              if sender == "advisor" and name == "ask_registrar"]
                require(any(payload["content"] == {k: v for k, v in args.items() if k != "decision_summary"}
                            for args in candidates), "Proposal differs from advisor tool arguments.")
                proposals.append((payload["content"], len(outcomes)))
            else:
                require(payload["to"] == "advisor" and proposals, "Registrar reply lacks a proposal.")
                _, start = proposals.pop(0)
                require(payload["content"] == {"reply": last_text["registrar"], "tool_outcomes": outcomes[start:]},
                        "Registrar reply differs from its model final or actual tool outcomes.")
                replies.append(payload["content"])
        elif kind == "final":
            require(not expected_calls[agent] and not any(k[0] == agent for k in pending),
                    "Agent ended with unobserved tool calls.")
            require(payload["text"].strip(), "Missing final answer.")
            require(payload["text"] == last_text[agent], "Agent final differs from its model's output text.")
            active.remove(agent)
            finished.add(agent)
    require(not active and not pending and not proposals and not replies and not requesting,
            "Transcript ended with unfinished work.")
    require(model_agents == {"advisor", "registrar"}, "Both roles must have actual model responses.")
    require(finished == {"advisor", "registrar"} and all(summaries.values()), "Both agent roles need decisions and finals.")
    require(students == trace["final_students"] and catalog == trace["final_catalog"],
            "Replayed writes do not reproduce final state.")
    require(outcomes == trace["outcomes"], "Recorded outcomes differ from actual tool observations.")
    require(trace["final_response"] == last_text["advisor"], "Final response differs from advisor output.")
    if trace["schema_version"] >= 3:
        require(trace["priority_plan"] == plan, "Final priority plan differs from recorded observations.")
        require(not trace["input"].get("require_plan") or plan is not None, "Scenario needs a priority plan.")
        if plan:
            order = list(dict.fromkeys(e["payload"]["content"]["course"] for e in trace["events"]
                                      if e["kind"] == "message" and e["agent"] == "advisor"))
            require(order == plan["ordered_courses"], "Delegation order differs from the recorded priority plan.")
    require(all(any(o["student_id"] == trace["input"]["request"]["student_id"] and o["course"] == course
                    for o in outcomes) for course in trace["input"]["request"]["courses"]),
            "A requested course has no registrar outcome.")
    world = World()
    world.actor, world.students, world.catalog, world.events = (
        trace["authenticated_actor"], students, catalog, trace["events"])
    require(audit(world) == trace["post_run_policy_violations"], "Post-run audit differs from recorded evidence.")
    return {"scenario": trace["scenario"], "model_calls": call_count, "events": len(trace["events"]),
            "tokens": tokens, "models": sorted(models), "outcomes": outcomes,
            "policies": sorted({v["policy"] for v in trace["post_run_policy_violations"]})}


def render_markdown(trace):
    report = verify_trace(trace)
    lines = [f"# Phase 1: {trace['scenario']}", "",
             "Generated from the adjacent JSON trace; this is a readable view of an actual API execution.", "",
             f"Model: {', '.join(report['models'])}. Calls: {report['model_calls']}. "
             f"Events: {report['events']}. Total token usage: {report['tokens']}.", "",
             "## Input", "", "```json", json.dumps(trace["input"], indent=2), "```", "",
             "## Execution", ""]
    for event in trace["events"]:
        if event["kind"] not in {"decision_summary", "message", "action", "observation", "final"}:
            continue
        lines.extend([f"### Step {event['step']} — {event['agent']} / {event['kind']}", "",
                      "```json", json.dumps(event["payload"], indent=2), "```", ""])
    lines.extend(["## Outcomes and post-run findings", "", "```json",
                  json.dumps({"simulation_time": trace.get("simulation_time"),
                              "priority_plan": trace.get("priority_plan"),
                              "outcomes": trace["outcomes"], "audit": trace["post_run_policy_violations"]}, indent=2),
                  "```", "", "The audit observes violations after execution; it does not intercept them.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-dir", type=Path, default=Path("traces/phase1"))
    parser.add_argument("--render", action="store_true", help="Write readable Markdown companions.")
    parser.add_argument("--current-source", action="store_true", help="Require current producer source hashes.")
    parser.add_argument("--replay", choices=list(SCENARIOS),
                        help="Print a recorded trace; makes no API requests and no new decisions.")
    args = parser.parse_args()
    paths = [args.trace_dir / f"{args.replay}.json"] if args.replay else sorted(args.trace_dir.glob("*.json"))
    if not paths:
        parser.exit(1, "No traces found.\n")
    try:
        for path in paths:
            trace = json.loads(path.read_text())
            report = verify_trace(trace, current_source=args.current_source)
            if args.replay:
                print(render_markdown(trace))
            else:
                print(f"PASS {path.name}: {report['model_calls']} API calls, {report['events']} events, "
                      f"audit policies: {', '.join(report['policies']) or 'none'}")
            if args.render:
                path.with_suffix(".md").write_text(render_markdown(trace))
    except (TraceError, OSError, ValueError) as error:
        print(f"Trace verification failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
