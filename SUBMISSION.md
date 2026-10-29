# Phase 1 submission — October 29, 2026

Public repository: [CS239_EnrollmentPlanning_JackHe](https://github.com/JackHe313/CS239_EnrollmentPlanning_JackHe).
The source is MIT licensed. This layout follows the
[October 27 course guidelines](https://docs.google.com/document/d/1-hvS3KpJmbCQphmH4AAWofD073yIP6CCE4MTXoS8joQ/edit).

## Deliverable map

| Assignment item | Artifact and assessment path |
| --- | --- |
| Working multi-agent application | `phase1/`; run `python3 -m phase1.app --scenario first_pass_planning` with a local key. |
| Two communicating agents with distinct roles | Advisor and Registrar have separate prompts, histories, and tools; inspect `agents/*.md` and trace `message` events. |
| No safety-enforcing framework in Phase 1 | Standard-library tool loops retain the documented authorization and waiver weaknesses. The audit runs after execution. |
| At least three complete traces | Seven actual LLM executions in `traces/phase1/`, each with JSON and generated Markdown. |
| Thoughts, actions, messages, observations | Public decision summaries, tool calls/results, proposals/replies, and state snapshots. Private chain-of-thought is not collected. |
| Requirements and policies | `requirements.md`, `policy.md`, and `policies.md`: functionality/prohibitions, twelve consecutive policy paragraphs, and a per-agent matrix of all five required boundaries. |
| Application description | `app.md` explains tasks, agents, coordination, technology, and synthetic-data scope. |
| Callable tool I/O and actual prompts | `tools.md` has one line per implemented tool; `agents/*.md` embed the actual prompts unchanged. Generated descriptions are checked against source. |
| Example episodes and policy connections | `episodes/*.md` label the seven recorded executions and give input, trajectory, observed result, relevant policy IDs, and intended outcome. `traces/README.md` locates full evidence. |
| Two required archives | Description-only and whole-source tarballs with matching name, appName, UID, and checksum manifests. See below. |
| Five-minute YouTube demo | Follow `DEMO_VIDEO_SCRIPT.md`, record, upload, and submit an accessible URL. No video URL has been supplied yet. |
| Class spreadsheet | Use the Jack He entry with the renamed repository and supplied UID. Add the video URL after upload; leave it blank until then. |

## Verify and package

Run from the repository root, or from `src/` after extracting the whole archive:

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s submission_tests -v
python3 -m phase1.submission
python3 scripts/course_submission.py --check
```

All four commands are offline and need no API key. They check seven completed
traces, calls/messages/receipts/state replay, matching producer source hashes,
readable trace views, exact agent prompts and tool documentation, consecutive
policies, safe archive layout, and exclusion of credentials.

Build the required pair using the same nine-digit UID in both filenames:

```sh
python3 scripts/course_submission.py --name JackHe --app-name EnrollmentPlanning --uid YOUR_NINE_DIGIT_UID
```

The outputs are:

```text
JackHe-EnrollmentPlanning-<uid>-requirements.tar.gz
  EnrollmentPlanning/app.md
  EnrollmentPlanning/policy.md
  EnrollmentPlanning/tools.md
  EnrollmentPlanning/agents/*.md
  EnrollmentPlanning/episodes/*.md
  MANIFEST.json

JackHe-EnrollmentPlanning-<uid>-whole.tar.gz
  src/README.md
  src/requirements.md, src/policies.md, src/policy.md
  src/phase1/, src/tests/, src/submission_tests/, src/scripts/
  src/traces/, src/agents/, src/episodes/, and remaining project documentation
  EnrollmentPlanning/ (the same description files)
  tests/README.md (test-case guide; execute the tests under src/)
  MANIFEST.json
```

The allowlist excludes `.env`, caches, Git metadata, history, and local/failed
runs. Packaging checks credentials and refuses to replace an existing archive.
The earlier ZIP helper remains available, but the two tarballs are the course
submission format. Regenerate generated descriptions after a relevant change
using `python3 scripts/course_submission.py --generate --check`.

## Remaining submission steps and milestone boundaries

Record the approximately five-minute demonstration, upload it to YouTube, verify
the link is viewable, and put that URL in the
[class project spreadsheet](https://docs.google.com/spreadsheets/d/1t_35rSHRfDNY3f1S-BS6Fbg4b8v816PJ-2h01Eyxv44/edit?gid=0#gid=0)
and the course submission. The class presentation can use the script for a live
demo. A recording script alone does not complete the video requirement.

This artifact covers Phase 1. The next milestone is November 12: encode the
policies as enforceable rules and begin the course-framework port. Phase 2 must
include a compliant trace and two traces showing violations intercepted before
the protected action. Final presentations are December 3.

Observed failures do not establish an attack-success rate. Model decisions vary,
and fresh runs use the student's own token quota. All fixtures are synthetic.
