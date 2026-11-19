# Five-minute demo recording script

Target: about five minutes, including clicks and one fresh model run. Bracketed
cues are actions, not spoken text. Keep a terminal and the repository open; hide
.env, API keys, and shell history. Identify saved evidence as recorded. Rehearse
once; if the live run takes longer, inspect saved traces while it finishes.

## 0:00–0:40 — Purpose and agents

[Show CS239_EnrollmentPlanning_JackHe and start the live run.]

```sh
python3 -m phase1.app --scenario first_pass_planning --max-api-calls 40
```

My project is EnrollmentPlanning, a UCLA-inspired enrollment assistant with two
communicating LLM agents. It helps students prioritize courses, find usable
sections, and enroll within assigned appointments and unit limits. All records
and seats are synthetic.

The Advisor searches sections and records a course order. The Registrar has a
separate prompt and conversation, reads the academic record, and decides whether
to enroll, reject, or propose a later-window deferral. They communicate through
ask_registrar; only the Registrar can call enroll.

## 0:40–1:20 — Enrollment realism

[Show the Agents and tools table or ENROLLMENT_RULES.md while the run finishes.]

Undergraduates have first and second passes; graduates have a single-pass profile.
First pass has a cumulative 10-unit budget. Second pass uses the student's
configured study-list limit.

Applicable units and priority status explain the appointment group, but the
assigned timestamp is trusted data. The model cannot move it earlier. Course
priority is a separate decision based on requirements, usable seats, and unit
cost. Sections have seats and meeting times, checked again before enrollment.
This simulator has no MyUCLA connection or real seat monitoring.

## 1:20–2:15 — Live outcome and communication

[Show the live terminal's plan, receipts, and new trace path. Read the actual
result; do not claim the saved example happened in this fresh run.]

This student requests three four-unit courses, with an elective listed first.
In the submitted example, the Advisor prioritizes the two required courses and
the Registrar enrolls in eight units. The elective cannot fit in first pass.
A fresh run may make different decisions.

A rejection applies to the current request. A deferral proposes a later assigned
window; it reserves no seat and schedules no automatic enrollment.

[Open the generated JSON, or identify the saved first_pass_planning.md explicitly.]

The trace records prompts, model response IDs, public decision summaries, calls,
observations, and inter-agent messages. Here are the course plan, the Advisor's
proposal, and the Registrar's actual tool receipt. These summaries explain
observable choices; private chain-of-thought is not collected.

## 2:15–3:00 — Seats and appointments

[Open saved traces/phase1/seat_finding.md; identify it as a recorded LLM run.]

In this recorded example, section A is full, B conflicts with the student's
unavailable period, and C is usable. The Registrar enrolls in C. Search results
are snapshots; enrollment rechecks current state.

[Briefly show before_appointment.md and second_pass_planning.md.]

The early-appointment trace records a deferral without changing seats. The
independent second-pass fixture starts with eight enrolled units and adds the
remaining course when second pass opens. No background process performs that
later enrollment automatically.

## 3:00–4:10 — Phase 1 milestone and failures

[Show policy.md, agents/advisor.md, and saved catalog_injection.md.]

Phase 1 requires a working multi-agent prototype without the course's safety
framework, at least three complete traces, and requirements defining behavior
and prohibitions. This repository has seven actual LLM traces, exact agent
prompts, tool I/O, episode descriptions, and two required submission archives.

The intended policies cover each agent's permissions, capabilities, lifecycle,
information flow, and isolation. For example, P1 restricts student access to the
authenticated actor; P2 requires trusted prerequisite records.

This catalog-injection trace shows a failure: an untrusted note claims an override,
and a model-supplied waiver permits enrollment without the prerequisite. The
post-run audit labels P2. Promoting the note into authority also illustrates P3.
The separate cross-student trace shows A accessing and enrolling B. These are
observed violations of intended policies.

## 4:10–5:00 — Verification and next milestone

[Show the offline verification commands and checks.]

```sh
python3 -m phase1.submission
python3 scripts/course_submission.py --check
```

Offline tests cover agent communication, appointment boundaries, unit budgets,
seats, and trace integrity. The verifier links decisions to calls and receipts,
then replays writes to reproduce final state. The audit runs after execution;
it does not intercept violations.

The next milestone is November 12: encode policies as enforceable rules and begin
the course-framework port. Phase 2 should preserve legitimate enrollment and
produce two traces showing unsafe actions intercepted before execution. Instructor
and peer feedback will refine these boundaries before the December 3 presentation.

## After recording

Upload the approximately five-minute recording to YouTube with a viewable link.
Add that real URL to the Jack He row in the class spreadsheet and to the course
submission. The live class presentation can use the same sequence. A script alone
does not complete the video requirement.
