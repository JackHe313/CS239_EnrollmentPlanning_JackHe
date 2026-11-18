# Phase 2 enrollment experiment

The Advisor plans courses. The Registrar checks eligibility and can change synthetic
student records. The experiment asks whether PolicyWeave protects those records
while allowing ordinary registration to finish. S02 tests a missing prerequisite.
S03 tests a request for another student's record. S08 and S09 test opposite ends of
an appointment window.

## Inputs and environment

| Component | Experiment setting |
| --- | --- |
| Phase 1 application and policy | Commit `37c63fa872c92d109bf41868b191ed9011346f06` on the original application's history |
| PolicyWeave | Course commit `25a201c287a3927d821e154ed1345b47f97f0b5f` |
| Application runtime | Python 3.12 on Linux x86-64, separate Advisor and Registrar conversations using `gpt-4.1-mini-2025-04-14` |
| Translator | OpenAI `gpt-6.1-sol`, medium reasoning effort, Codex CLI 0.164.0 |
| Enforcement tools | Soufflé 2.5, `prlimit`, and the Docker images built from the pinned course source |

Use a separate, clean checkout at the Phase 1 commit as the input to the translator.
The policy is the original twelve-paragraph [policy.md](../policy.md). Each sample
starts a fresh application with the request, simulation time, student records and
catalog specified in [test_cases.json](../test_cases.json). The course term, assigned
times and student records are synthetic. [Course instructions](https://github.com/thaddywu/CS239-Phase2/blob/25a201c287a3927d821e154ed1345b47f97f0b5f/phase2-instructions.pdf)

## Run the original harness

From this repository's root, provide the application key through the environment or
an owner-only local `.env` as described in the root README. Point `ORIGINAL_APP_DIR`
at the clean checkout when it is stored separately. All live repetitions use the
provider account's token quota. A sample can use up to 60 model calls and 600 seconds.

```sh
python3 -m unittest discover -s phase2_tests -v
python3 run.py --case S01 --side original --output_dir phase2/work/smoke-01 --sample 1
```

The second command requires a fresh output directory for this case and sample.
It writes `S01/original/sample-1/result.json` and, if the application returned a
trace, `artifacts/application.json`. The outcome checker compares Registrar tool
observations with enrollment receipts, replays the writes against the frozen state
and checks the resulting records and seats. It checks section conflicts, pass limits,
and deferral windows at the time of the action. The final-response check uses a
small vocabulary and cannot establish that every statement in a model's prose is
accurate. The separate Inspector review supplies evidence about enforcement.

## Port and evaluate

Install the pinned course framework on Linux and set `ORIGINAL_APP_DIR`,
`PORTED_APP_DIR`, and `CONNECTION_FILE` as directed by the course. Use the same
original commit for all runs. Keep the private connection outside the repository.

```sh
policyweave port --input "$ORIGINAL_APP_DIR" --output "$PORTED_APP_DIR" --connection "$CONNECTION_FILE"
policyweave view-translation --back-translation "$PORTED_APP_DIR/back-translation" --policy "$ORIGINAL_APP_DIR/policy.md"
```

For Codex CLI 0.164.0 on Linux, the coding worker requires
`codex-code-mode-host` next to the resolved `codex` executable. On the project PC
the course installer supplied the main executable alone. The companion came from
OpenAI's matching Linux x86-64 musl release, with archive SHA-256
`feade7026436baa4e82e898050c7ef82a8adbd98163dc504771275b5ef224f2f`.
Running the course controller as an ordinary Linux user also gives the worker
access to its disposable home. [Official CLI release](https://github.com/openai/codex/releases/tag/rust-v0.164.0)

After the translator publishes the app, put the generated folder at
`ported-app/` in this checkout. Run the following commands from the repository root
in the course Python environment. The original app's `phase1/` package is at the root.

```sh
policyweave translate-harness --input run.py --output translated_harness.py --original-app . --ported-app ported-app --connection "$CONNECTION_FILE"
python translated_harness.py --side original --output_dir runs --sample 10
python translated_harness.py --side ported --output_dir runs --sample 10
```

Each side contributes ten attempts per scenario. Retain failed attempts and their
Boolean results. PolicyWeave exports the ported timelines. Inspect a blocked call and
a checked call, record the sample and event IDs, and use Inspector QA for the report.
The student supplies the sentence ratings, reflection and research-consent choice.

## Evidence available

The original S01 live smoke test completed. The original app's 38 offline tests
and the verifier for all seven Phase 1 traces passed on Linux. The first translation
attempt accepted the inventory and policy bindings and stopped during rule generation.
The paired benchmark, enforcement trajectories, human review and final report are pending.
