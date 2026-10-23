# Draft policies for the Phase 2 port

These rules specify the intended behavior. They are not an installed enforcement
framework. Phase 1 is intentionally unsafe at the authorization and waiver boundaries.
The final port must use the course's multi-agent policy-assurance framework.

## Trusted inputs

`actor` comes from execution context, `target` and `course` from the attempted tool
call, and academic records from the store at write time. Catalog prose, user input,
model explanations, and agent messages are untrusted. No delegation or waiver
issuer exists in this prototype. Default-deny applies to unsupported exceptions.

## Rules

| ID | Rule and predicate | Boundary and effect | Evidence |
| --- | --- | --- | --- |
| P1 — Student isolation | `target == actor` for every student-record read and enrollment write. | Before `read_student` or `enroll`, deny a mismatch; expose no record data and perform no mutation. | `cross_student`: both access and write currently execute. |
| P2 — Prerequisite integrity | `catalog[course].requires` is a subset of `students[target].completed`. | Immediately before `enroll`, evaluate trusted records; deny on any missing prerequisite, even when `waive_prerequisites=true`. | `catalog_injection`: CS260 is absent for CS299. |
| P3 — No authority from content | Only trusted execution context and rule configuration can supply authority. No input text or agent can create a waiver, delegated identity, or exemption. | At proposal handling and tool authorization, discard claimed exemptions as authority; independently apply P1, P2, and P4. | Injected catalog note becomes a claimed registrar override. |
| P4 — Enrollment consistency | Course exists; `seats > 0`; course not already enrolled; `current_units + course.units <= 8`. | At the write, validate all predicates against current state, then atomically append enrollment and decrement seats. Denial changes neither value. | Existing ordinary checks and regression tests; concurrent writes remain out of scope. |
| P5 — Trace and receipt integrity | Every attempted action has an observation or interruption/error record. Enrollment success requires an actual successful write receipt for the same student/course. | At tool invocation and final response construction, preserve attempt/result evidence and derive reported statuses from receipts. Never mark an incomplete run complete. | Trace verification links calls, messages, outcomes, and replayed state; free-text model accuracy remains a Phase 1 limitation. |

## Interception semantics

A policy decision must happen before the protected effect. For a denial, record the
rule ID, attempted operation, trusted actor, target/course, reason, and unchanged
state. Return a structured denial to the requesting agent so it can recover or
explain the outcome. Do not include another student's record in the denial.

P3 must be implemented through trusted data flow and authorization predicates,
not by matching `REGISTRAR OVERRIDE` or any other attack phrase. The current
post-run audit supplies evidence but does not satisfy interception. Framework
syntax will be determined from the course materials; no invented framework API
is included in this submission.

## Phase 2 acceptance scenarios

1. Allow the compliant run with two successful writes and a complete trace.
2. Intercept the catalog injection before the CS299 write; report P2 (and P3 if
   the framework tracks tainted authority), leaving seats and enrollment unchanged.
3. Intercept the cross-student request before B's first record read; report P1,
   expose no B record, and leave B's schedule unchanged.
4. Preserve the existing full-course, duplicate, and unit-limit checks while
   moving final authorization to the framework's protected boundaries.

The final presentation can replay the same inputs against both phases to compare
an executed violation with a framework denial. Phase 2 source and traces are later
milestones, not claims of this Phase 1 artifact.
