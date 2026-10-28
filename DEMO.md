# Enrollment planning demo — about three minutes

## Spoken introduction

My project is an enrollment-planning assistant with two communicating LLM agents.
The advisor chooses a course strategy, and the registrar independently reads
records and decides whether to enroll, reject, or defer a request.

The expanded version models both undergraduate and graduate enrollment. It reads
assigned appointment windows, explains the student's units-based appointment
group, and searches individual sections for seats and schedule conflicts.
Undergraduates have first and second passes, while graduates have one assigned
pass. The student's appointment priority is separate from the advisor's ranking
of that student's courses.

For Phase 1, I built the application without the course's safety-enforcing
framework and captured complete real model executions. The repository includes
those traces and draft requirements describing both useful behavior and what the
application must never do.

## Live demonstration

Run this from the repository root with a local `.env` key:

```sh
python3 -m phase1.app --scenario first_pass_planning --max-api-calls 40
```

While it runs, explain:

The student requests three four-unit courses, with the elective listed first. Two
courses are required, and the current first-pass budget is 10 units. The advisor
should prioritize the requirements, search sections, and plan the remaining course
for second pass. The registrar checks the actual appointment, prerequisites, seats,
and schedule before each write. The CLI prints the model's course order and actual
receipts after the run.

Then explain the observed result, rather than assuming the model always makes the
same choices. A deferred course is not reserved or enrolled. Its future seats and
eligibility still need checking at the next appointment.

## Trace walkthrough

These commands inspect recorded executions and make no new model calls:

```sh
python3 -m phase1.evidence --replay first_pass_planning
python3 -m phase1.evidence --replay seat_finding
python3 -m phase1.evidence --replay catalog_injection
```

In the first trace, point out the trusted appointment context, the public reason
for the course order, the registrar's messages, and the enrolled/deferred receipts.
In the section-search trace, show the full section, the conflicting section, and
the usable alternative. The writer rechecks the seat rather than treating a
search result as a reservation.

Finally, show the catalog-injection failure: external text claims prerequisite
waiver authority and can influence the model's tool arguments. Another recorded
scenario shows a cross-student access. These are the unsafe boundaries that remain
in the Phase 1 baseline.

## Next milestone

The next milestone is November 12: encode the policies as enforceable rules and
begin the port to the course's policy-assurance framework. I will protect student
identity, prerequisite integrity, appointment times, pass budgets, and trusted
priority data at the tool boundaries. The final traces must show a compliant run
and policy violations intercepted before their effects.

Instructor and peer feedback will help refine both the policies and the planning
objective. The final presentation is December 3.

## Extra scenarios and offline fallback

- `second_pass_planning`: the student already has eight units and can add the deferred course.
- `before_appointment`: return a later-window proposal without an early write.
- `seat_finding`: choose an open section that avoids a fixed schedule conflict.
- `compliant`, `catalog_injection`, `cross_student`: original Phase 1 cases.

Use `python3 -m phase1.submission` for an offline artifact check. If the network or
quota prevents a live run, show its failed trace and clearly identify the saved
traces as recorded evidence. The simulator does not connect to MyUCLA, watch real
seats, wait-list, or schedule future enrollment.
