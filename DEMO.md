# Phase 1 demonstration

## Two-minute introduction

This assistant handles graduate course enrollment through two LLM agents. The
advisor reads a catalog and proposes courses. The registrar independently reads
student records, checks eligibility, and calls enrollment tools. They communicate
through explicit proposals and replies. Records are simulated, but each submitted
agent decision came from an actual model call.

Phase 1 exposes two trust boundaries: an external catalog note can influence a
prerequisite waiver, and a request target can differ from the authenticated actor.
The later framework should enforce those boundaries before any protected action.

## Offline walkthrough — no API key needed

From the repository root:

```sh
python3 -m phase1.submission
python3 -m phase1.evidence --replay compliant
python3 -m phase1.evidence --replay catalog_injection
python3 -m phase1.evidence --replay cross_student
```

These commands validate and display the **recorded** executions. They are an
inspection of submitted evidence, not a new live agent run. You can also open the
three Markdown traces directly in `traces/phase1/`.

For the compliant trace, follow the advisor's proposal, the registrar's catalog and
student reads, and the successful `enroll` receipts. The second requested course
observes the first enrollment's state; the final load is eight units.

For the injection trace, follow the catalog note into the advisor's context, the
registrar's public decision summary, and the `waive_prerequisites` argument. Compare
CS299's required CS260 against the student's completed-course record. The final
state contains an enrollment that the requirement prohibits.

For the cross-student trace, compare the trusted `authenticated_actor` with the
proposal target. Inspect both the `read_student` observation and the subsequent
`enroll` receipt. The violation begins at the read, before the write.

The auditor reports evidence after execution. It is not an interception mechanism.

## Live walkthrough — consumes API quota

Configure your own key in `.env`, then run:

```sh
python3 -m phase1.app --scenario compliant --max-api-calls 20
python3 -m phase1.app --scenario catalog_injection --max-api-calls 20
python3 -m phase1.app --scenario cross_student --max-api-calls 20
```

Each command reports its new output folder. Validate that folder with
`python3 -m phase1.evidence --trace-dir PATH --render`. Show a completed trace if
one is produced; show the `.failed.json` evidence if a quota or network issue occurs.
A model can decline an attack or use a different tool sequence on a later run.

## Points to explain to a reviewer

- Agent independence comes from separate responsibilities, prompts, tools, and
  conversations, with LLM-selected actions in both roles.
- Traces include short public decision summaries. They do not disclose private
  chain-of-thought.
- Seat/duplicate/unit checks are ordinary tool business logic. There is no
  policy-assurance framework in Phase 1.
- The unsafe waiver and missing authorization are explicit baseline weaknesses,
  not examples of correct intended behavior.
- Phase 2 will apply P1–P5 at protected tool boundaries, replay these inputs, and
  capture compliant and intercepted-violation executions.
