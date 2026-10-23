# Graduate Enrollment Agents

A graduate course enrollment assistant for CS239. Two LLM-backed agents collaborate:
an **advisor** plans requested courses, and a **registrar** inspects academic records
and executes simulated enrollments. Each has its own prompt, model conversation,
and tools. All course and student data are fictional; no university service is connected.

This is the **Phase 1 prototype**, due October 29, 2026. It has no safety-enforcing
framework. Three actual model executions show normal enrollment and two concrete
trust-boundary failures for the later policy-assurance port.

## Start here

You can inspect and validate the submission without an API key:

```sh
python3 -m unittest discover -s tests -v
python3 -m phase1.submission
python3 -m phase1.evidence --replay catalog_injection
```

The last command displays recorded evidence; it makes no model calls or new decisions.
See [DEMO.md](DEMO.md) for a walkthrough and [SUBMISSION.md](SUBMISSION.md) for the rubric map.

## Run the live application

Requires Python 3.9+ and your own OpenAI API quota. There are **no third-party Python
dependencies**. Network access is required only for live model calls.

1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` locally.
2. Run from the repository root:

```sh
python3 -m phase1.app --scenario all
```

The default model is the pinned snapshot `gpt-4.1-mini-2025-04-14`. Set `OPENAI_MODEL`
or pass `--model MODEL_ID` to use another Responses API model with function calling.
Environment values take precedence over `.env`; `--model` takes precedence over both.
The loader supports simple `KEY=value` entries and never executes shell expressions.

Individual scenarios are `compliant`, `catalog_injection`, and `cross_student`:

```sh
python3 -m phase1.app --scenario compliant --max-api-calls 20
```

Each run uses fresh in-memory records and writes to a unique `traces/runs/<id>/`
folder. You can choose a new folder with `--output-dir`. Existing scenario files
are never overwritten. Validate new traces with:

```sh
python3 -m phase1.evidence --trace-dir traces/runs/YOUR_RUN_ID --render
```

An API error, malformed response, interrupted run, missing course outcome, or
exhausted budget produces a `.failed.json` partial trace and nonzero exit status.
Failed traces do not count as submission evidence. There is no scripted fallback.

## Agents and tools

| Agent | Decisions | Available tools |
| --- | --- | --- |
| Advisor | Interpret the request, inspect catalog context, choose course proposals, summarize outcomes. | `read_catalog`, `ask_registrar` |
| Registrar | Inspect the record and catalog, decide eligibility or rejection, choose whether to request a waiver, report the actual write result. | `read_catalog`, `read_student`, `enroll`, `reject` |

```mermaid
sequenceDiagram
    participant S as Student request
    participant A as Advisor LLM
    participant C as Catalog tool
    participant R as Registrar LLM
    participant D as Synthetic student records
    S->>A: Target student and requested courses
    A->>C: Read catalog and external note
    C-->>A: Course facts and note
    A->>R: Enrollment proposal and context
    R->>C: Inspect catalog
    R->>D: Read student; attempt enrollment or reject
    D-->>R: Actual tool result
    R-->>A: Reply and tool outcomes
    A-->>S: Final enrollment summary
```

The two roles can use the same model; distinct prompts, histories, responsibilities,
and inter-agent messages establish separate agents. Python executes the tools and
ordinary seat, duplicate, prerequisite, and unit checks. Model-generated public
decision summaries explain actions. Private chain-of-thought is not requested.

## Submitted evidence

| Scenario | What it demonstrates | Files |
| --- | --- | --- |
| Normal enrollment | Eligible student enrolls in CS239 and CS260. | [JSON](traces/phase1/compliant.json), [readable trace](traces/phase1/compliant.md) |
| Catalog injection | Untrusted catalog text claims authority to waive CS299's missing prerequisite. | [JSON](traces/phase1/catalog_injection.json), [readable trace](traces/phase1/catalog_injection.md) |
| Cross-student enrollment | Student A causes the registrar to read and modify student B's record. | [JSON](traces/phase1/cross_student.json), [readable trace](traces/phase1/cross_student.md) |

[traces/README.md](traces/README.md) explains exact policy evidence and event references.
The JSON contains actual API response IDs, returned model IDs, usage, prompts,
tool schemas, messages, public decision summaries, observations, and initial/final state.
Readable traces are generated from JSON. Source hashes identify the producer version.

The offline verifier links calls to model outputs and observations, checks messages,
and replays successful writes to reproduce final state. This verifies internal
consistency; API IDs and hashes are not independently signed proof of provenance.
The audit runs after execution and does not block actions. A model refusal on a
future run would be model behavior, not framework enforcement. Attack success can vary.

## Boundaries and Phase 2

Phase 1 deliberately lacks actor-to-target authorization and accepts a model-supplied
prerequisite waiver. Catalog text is not parsed for special attack phrases. The
submitted unsafe outcomes are model choices observed in real calls.

[requirements.md](requirements.md) specifies functionality and prohibited behavior.
[policies.md](policies.md) defines draft rules to encode with the course framework
in Phase 2. Phase 2 is not implemented. See [REVIEW.md](REVIEW.md) for the review,
fixes, and remaining limitations.

API requests are bounded to 60 per scenario, 18 advisor turns, 10 turns per registrar
conversation, and 1,400 output tokens per response. `--max-api-calls` can lower the
request limit. Calls time out after 60 seconds with no automatic retries. These
execution limits do not guarantee a specific dollar cost. API keys, HTTP headers,
and encrypted reasoning are excluded from trace files and the submission ZIP.

## Files and packaging

- `phase1/`: agents, synthetic state, API transport, trace verifier, and submission checker.
- `tests/`: offline protocol, failure-path, business-rule, and evidence-integrity tests.
- `traces/`: three live JSON traces, readable companions, and documentation.
- `.github/workflows/ci.yml`: offline verification on Python 3.9, 3.12, and 3.14.

Create a ZIP from an explicit, credential-scanned file allowlist:

```sh
python3 -m phase1.submission --package artifacts/phase1-submission.zip
```

The package contains a SHA-256 manifest and excludes `.env`, local history, caches,
Git metadata, and local/failed runs. Packaging refuses to replace an existing ZIP.
Code is released under the [MIT license](LICENSE).

Implementation references: official OpenAI [function calling](https://developers.openai.com/api/docs/guides/function-calling)
and [stateless Responses conversations](https://developers.openai.com/api/docs/guides/migrate-to-responses).
