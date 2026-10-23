# Phase 1 submission — October 29, 2026

## Deliverable map

| Assignment item | Artifact | Assessment path |
| --- | --- | --- |
| Working multi-agent application | `phase1/app.py`, `phase1/llm.py`, `phase1/domain.py` | Run `python3 -m phase1.app --scenario all` with a local key. |
| At least two communicating agents with distinct roles | Advisor and registrar, separate LLM loops and tools | Inspect architecture in README and each `agent_start` / `message` event. |
| No safety-enforcing framework in Phase 1 | Standard-library Python tool loop | Baseline vulnerabilities are preserved; the audit runs after execution. |
| At least three complete agentic traces | `traces/phase1/compliant.json`, `catalog_injection.json`, `cross_student.json` | Each JSON has a generated Markdown companion. All three are actual LLM executions. |
| Thoughts, actions, messages, observations | Public decision summaries plus complete visible call/result and communication events | See `traces/FORMAT.md`; private chain-of-thought is not requested. |
| Draft `requirements.md` stating behavior and prohibitions | `requirements.md` | Functional F1–F9, safety S1–S5, trust model, acceptance scenarios, and limits. |
| Draft policies and scenario explanations | `policies.md`, `traces/README.md` | Rules P1–P5 and precise trace evidence. |
| Public GitHub repository | Repository hosting these files | Source, traces, setup, tests, demo guide, and MIT license are included. |

## Verify the artifact

Run these from a fresh checkout or extracted submission ZIP:

```sh
python3 -m unittest discover -s tests -v
python3 -m phase1.submission
```

Both commands are offline and need no API key. The submission check requires
three completed live traces, tool/message/state consistency, source hashes matching
the checked-in producer, and readable trace views that match the JSON. It also
scans the explicit submission file list for credential-like strings.

For an uploadable snapshot:

```sh
python3 -m phase1.submission --package artifacts/phase1-submission.zip
```

The ZIP includes a SHA-256 manifest. It excludes the local `.env`, caches, Git
metadata, history, and newly generated/failed local runs. Do not upload the entire
working directory indiscriminately.

## Milestone boundaries

This artifact covers Phase 1. Policies are drafts for the November 12 policy
encoding/early-port milestone. Framework integration, Phase 2 source and intercepted
traces, and the December 3 presentation remain later deliverables.

The current three observations demonstrate concrete failures; they do not establish
an attack-success rate. The source is a classroom prototype using synthetic data.
Live reruns may produce different decisions and require the student's own quota.
