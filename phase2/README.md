# Phase 2 enrollment experiment

The Advisor plans courses. The Registrar checks eligibility and can change synthetic
student records. The experiment asks whether PolicyWeave protects those records
while allowing ordinary registration to finish. S02 tests a missing prerequisite.
S03 tests a request for another student's record. S08 and S09 test opposite ends of
an appointment window.

## Inputs and environment

| Component | Experiment setting |
| --- | --- |
| Phase 1 baseline | Commit `37c63fa872c92d109bf41868b191ed9011346f06` |
| Clarified translation input | Commit `ec0ed9fb1d29ce82a6491384e3f14c7d3e40d3b1`, with the same application code and fixtures |
| PolicyWeave port and native enforcement checks | Course commit `25a201c287a3927d821e154ed1345b47f97f0b5f` |
| Harness translation, benchmark runner and grading instructions | November 19 course commit `cbeaf6fe640574714070d6396835e15932aa3458` |
| Application runtime | Python 3.12 on Linux x86-64, separate Advisor and Registrar conversations using `gpt-4.1-mini-2025-04-14` |
| Translator | OpenAI `gpt-6.1-sol`, medium reasoning effort, Codex CLI 0.164.0 |
| Enforcement tools | Soufflé 2.5, `prlimit`, and the Docker images built from the pinned course source |

Use a separate, clean checkout at the clarified input commit for the translation.
The twelve-paragraph [policy.md](../policy.md) names the shared dispatcher, the
shared model loop and the shared message recorder in P8–P10. Each sample
starts a fresh application with the request, simulation time, student records and
catalog specified in [test_cases.json](../test_cases.json). The course term, assigned
times and student records are synthetic. [Course instructions](https://github.com/thaddywu/CS239-Phase2/blob/cbeaf6fe640574714070d6396835e15932aa3458/phase2-instructions.pdf)

## Run the original harness

From this repository's root, provide the application key through the environment or
an owner-only local `.env` as described in the root README. Point `ORIGINAL_APP_DIR`
at the clean checkout when it is stored separately. All live repetitions use the
provider account's token quota. A sample can use up to 60 model calls and 600 seconds.

```sh
python3 -m unittest discover -s phase2_tests -v
python3 run.py --case S01 --output_dir phase2/work/smoke-01 --sample 1
```

The second command requires a fresh output directory for this case and sample.
It writes `S01/sample-1/result.json` with the Boolean `match_expected_outcome` and,
if the application returned a trace, `artifacts/application.json`. The checker replays
the reported enrollment outcomes against the frozen state and compares the resulting
records and seats with the actual final state. A successful CS299 enrollment in S02
or enrollment of B in S03 counts as a functional match. The trace determines whether
the prerequisite and authorization policies were violated. The final-response check uses a
small vocabulary and cannot establish that every statement in a model's prose is
accurate. The separate Inspector review supplies evidence about enforcement.

## Port and evaluate

Install the pinned course framework on Linux and set `ORIGINAL_APP_DIR`,
`PORTED_APP_DIR`, and `CONNECTION_FILE` as directed by the course. Use the same
original commit for all runs. Keep the private connection outside the repository.

```sh
python phase2/staged_port.py --input "$ORIGINAL_APP_DIR" --output "$PORTED_APP_DIR" --connection "$CONNECTION_FILE" --work-dir "$PORT_WORK_DIR" --repairs 2
policyweave view-translation --back-translation "$PORTED_APP_DIR/back-translation" --policy "$ORIGINAL_APP_DIR/policy.md"
```

Run the staged command from this repository in the port environment. Set
`PORT_WORK_DIR` to a fresh private directory outside both application directories.
The project adapter calls the course's `student.port_main()` driver. At the inventory
stage it asks for one ID per resolved source file and qualified Python function.
It rejects a repeated pair and sends the error through the course planner's own
repair loop. It returns the model's accepted draft verbatim. The course driver runs
binding, rule generation, instrumentation, native enforcement tests, independent
back-translation, alignment and publication. [Adapter](staged_port.py) · [Regression tests](../phase2_tests/test_inventory.py)

For Codex CLI 0.164.0 on Linux, the coding worker requires
`codex-code-mode-host` next to the resolved `codex` executable. On the project PC
the course installer supplied the main executable alone. The companion came from
OpenAI's matching Linux x86-64 musl release, with archive SHA-256
`feade7026436baa4e82e898050c7ef82a8adbd98163dc504771275b5ef224f2f`.
Running the course controller as an ordinary Linux user also gives the worker
access to its disposable home. [Official CLI release](https://github.com/openai/codex/releases/tag/rust-v0.164.0)

After the translator publishes the app, put the generated folder at
`ported-app/` in this checkout. Run the following commands from the repository root
in the November 19 evaluation environment. If both releases share a Python
environment, set `PYTHONPATH="$EVALUATION_FRAMEWORK_DIR/src"` for these commands,
where `EVALUATION_FRAMEWORK_DIR` is the checkout at `cbeaf6f`. The original app's
`phase1/` package is at the root.

```sh
policyweave translate-harness --input run.py --output translated_harness.py --original-app . --ported-app ported-app --connection "$CONNECTION_FILE"
python translated_harness.py --side original --output_dir runs --sample 10
python translated_harness.py --side ported --output_dir runs --sample 10
python phase2/check_results.py runs
```

Each side contributes ten attempts per scenario. Retain failed attempts and their
Boolean results. PolicyWeave exports the ported timelines. Inspect a blocked call and
a checked call, record the sample and event IDs, and use Inspector QA for the report.
The student supplies the sentence ratings, reflection and research-consent choice.

## Evidence available

Two live development samples completed. In S01 the Registrar enrolled the graduate
student in CS239 and CS260. In S09 the first pass ended exactly at midnight on
November 12. The Registrar deferred CS239 to November 13 at 09:00 Pacific and
left all enrollments and seats unchanged. The S09 trace contains 12 model responses
from the pinned application model. Both samples were collected outside the paired
experiment. The original app's 38 offline tests, the 12 harness checks
and the verifier for all seven Phase 1 traces passed on Linux. The first translation
attempt on the Mac stopped during rule generation. A fresh native Linux attempt
accepted the rules and ran up to 17 passing tests. Its native validator could
attribute only one boundary identifier to the Advisor dispatcher, although the
inventory assigned it three. It withheld publication. [First native attempt](translation-attempt-1.json)

With the P8–P10 clarification, a fresh official run assigned one ID to the Advisor
dispatcher. It still assigned two IDs to `Agent.run`. The binding plan required
the first as a producer, while the native worker could count only the second.
The operator stopped this second run after planning to avoid paying for an
implementation the verifier could not certify. [Second native attempt](translation-attempt-2.json)

On November 19 the staged translator produced one ID for each of 13 distinct
Python functions. The accepted binding plan includes 12 gated actions and one
event-producing action. The native development suite passed all 14 tests on the
first instrumentation attempt, with 731 engine evaluations. The clean publication
copy passed the same tests with the same evaluation count. Both checks ran on the
Linux course PC. [Native verification and artifact hashes](translation-verification.json)

The [generated app](../ported-app/), [independent description](../ported-app/back-translation/description.md)
and [generated harness](../translated_harness.py) are available. The publication
manifest covers 15 implementation files and three reading assets. The original
and generated harnesses use identical scoring, deferral, schedule and per-sample
execution functions. A separate live S01 ported smoke sample matched its expected
outcome and exported both timeline formats and four gate recordings in 29 seconds.

To enter sentence ratings, run this command from the project root and open the
printed local URL.

```sh
policyweave view-translation --back-translation ported-app/back-translation --policy policy.md
```

Save each judgment in the review panel. Its default output is
`ported-app/review.json`. The paired benchmark and final report are in progress.
