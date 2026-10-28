# Phase 1 review and enrollment-planning extension

## Review outcome

The project implements the requested two-agent LLM prototype and seven complete
executions. The requirements describe both useful behavior and prohibited behavior.
The two unsafe scenarios motivate distinct protected boundaries for Phase 2:
record authorization and prerequisite integrity under untrusted catalog content.

## Reliability and evidence fixes

| Finding | Change | Verification |
| --- | --- | --- |
| Some malformed responses or unexpected failures could escape complete failure reporting. | Validate response envelopes and record failed/partial executions, including interruptions. | Malformed-output, unexpected-error, interrupt, and turn-limit tests. |
| Reruns could overwrite the submitted traces. | Unique output directories by default; refuse existing scenario files; exclusive file creation. | CLI overwrite-protection regression test. |
| Earlier catalog observations could accidentally share mutable state. | Deep-copy initial state and event payloads. | Observation snapshot test and independent replay of every submitted read. |
| Trace review depended on manual inspection. | Verify model-call/action links, message contents, tool observations, receipt/outcome links, and replayed final state. | Tampered-call, altered-read, changed-final-state, and submitted-trace replay tests. |
| The LLM implementation imported the earlier scripted prototype. | Extract synthetic fixtures/state into a focused domain module; exclude historical code/traces from submission. | Both-role LLM tests and clean-package verification. |
| The artifact lacked a simple assessment path. | Add readable trace views, an offline replay, rubric map, demo guide, CI, MIT license, and allowlisted ZIP packaging with a manifest. | Submission check and fresh-extraction smoke test. |

## Intended baseline weaknesses retained

P1 student isolation and P2 prerequisite integrity are intentionally unenforced at
the unsafe boundaries. The registrar can read/write a target different from the
actor, and a model-supplied waiver can bypass prerequisites. Ordinary seat,
duplicate, and unit checks remain in place. There is no phrase-matching code that
forces an attack outcome, and no policy-enforcement framework is included.

A future model refusal does not establish framework safety. The observed catalog
failure also depends on permissive registrar instructions around waivers; it is an
illustrative vulnerable design rather than a benchmark of a well-defended system.

## Remaining limitations

- Model outputs vary. The pinned snapshot reduces version drift, but does not make
  tool decisions deterministic.
- IDs and hashes permit inspection and consistency checks; they are not signed
  attestation of an API response's authenticity.
- Source hashes bind the submitted producer version to the traces. Changing the
  Python source requires generating fresh evidence before the submission check passes.
- The audit checks unauthorized attempts and final prerequisite violations. It is
  not a complete monitor of P3–P5, and it does not automatically evaluate every
  factual assertion in free-text model answers.
- Inputs are fixed scenarios; there is no production identity provider, concurrent
  store, public API, schedule-conflict logic, or real university integration.
- API and request caps bound execution, not exact financial spend.
- The GitHub Actions workflow is supplied; its hosted result is only known after
  publication and execution on GitHub. Local tests and the package check can run offline.

## Original-release validation

On October 22, 2026, all 22 offline tests passed under Python 3.14.3. All Python
sources also parsed with Python 3.9 syntax. Three fresh LLM executions completed
with 26 total model calls; normal enrollment and both unsafe outcomes were
observed. Each passed source-hash and state-replay verification. A ZIP extracted
to a clean temporary directory passed all 22 tests, the submission checker, and
manifest checksum validation with API credentials removed from its environment.
The hosted Python-version matrix is checked separately by GitHub Actions.


## October 27 realism extension

The original release remains in Git history. The extension separates undergraduate
and graduate profiles, replaces the eight-unit toy cap with appointment/profile
limits, adds a units-based appointment-group explanation, and keeps assigned times
immutable. Course-level seats now have concrete sections and meeting times.

The advisor records its own course-priority plan and delegates in that order.
The registrar checks the active window, cumulative unit budget, and current section
availability. A deferral is explicitly a proposal, never automatic enrollment.
The existing missing-authorization and untrusted-waiver weaknesses remain for Phase 2.

Thirty-eight offline tests cover protocol handling, trace integrity, unit-group
boundaries/AP treatment, fixed assigned appointments, cumulative pass limits,
timezone/start/end boundaries, graduate single-pass behavior, alternative sections,
meeting conflicts, and seats disappearing after a search. Official rule sources
and omitted university features are documented in `ENROLLMENT_RULES.md`.

The priority heuristic considers required courses, usable seat scarcity, and unit
cost. It is model-generated rather than an optimality guarantee. Free-text decision
summaries may contain mistakes; actual tool receipts and replayed state remain the
basis for reporting enrollment, deferral, and policy evidence.


The first live alternative-section test exposed a course/section ID mix-up in an
advisor proposal. The application marked the run incomplete. The corrected tool
schema explains the distinction, and proposal validation now returns a retryable
error before delegation when a section is passed as the course. A regression test
verifies that this error changes neither state nor delegation order. The failed
run remains in ignored local diagnostics; final submission traces are regenerated
from the corrected source.

The final expanded artifact passed all 38 offline tests and source-matched replay
of seven fresh LLM executions. A clean ZIP extraction passed the same tests,
submission check, and manifest checksum verification without API credentials.
The first-pass trace records a current-pass rejection for the overflow elective;
the before-appointment trace records an explicit deferral. The scenario guide
keeps these actual receipts distinct rather than claiming identical model behavior.
