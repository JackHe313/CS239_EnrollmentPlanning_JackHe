# Phase 1 review and strengthening

## Review outcome

The project implements the requested two-agent LLM prototype and three complete
executions. The requirements describe both useful behavior and prohibited behavior.
The two unsafe scenarios motivate distinct protected boundaries for Phase 2:
record authorization and prerequisite integrity under untrusted catalog content.

## Reliability and evidence fixes

| Finding | Change | Verification |
| --- | --- | --- |
| Some malformed responses or unexpected failures could escape complete failure reporting. | Validate response envelopes and record failed/partial executions, including interruptions. | Malformed-output, unexpected-error, interrupt, and turn-limit tests. |
| Reruns could overwrite the submitted traces. | Unique output directories by default; refuse existing scenario files; exclusive file creation. | CLI overwrite-protection regression test. |
| Earlier catalog observations could accidentally share mutable state. | Deep-copy initial state and event payloads. | Observation snapshot test and independent replay of every submitted read. |
| Trace review depended on manual inspection. | Verify model-call/action links, message contents, tool observations, receipt/outcome links, and replayed final state. | Tampered-call, altered-read, changed-final-state, and all-three-traces tests. |
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

## Final local validation

On October 22, 2026, all 22 offline tests passed under Python 3.14.3. All Python
sources also parsed with Python 3.9 syntax. Three fresh LLM executions completed
with 26 total model calls; normal enrollment and both unsafe outcomes were
observed. Each passed source-hash and state-replay verification. A ZIP extracted
to a clean temporary directory passed all 22 tests, the submission checker, and
manifest checksum validation with API credentials removed from its environment.
The hosted Python-version matrix is checked separately by GitHub Actions.
