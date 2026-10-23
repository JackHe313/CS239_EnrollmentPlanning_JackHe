# Observable trace format (schema version 2)

## Top-level fields

| Field | Meaning |
| --- | --- |
| `schema_version`, `phase`, `scenario` | Format version, assignment phase, scenario identity. |
| `run_id`, `started_at`, `finished_at` | Unique local execution ID and UTC timestamps. |
| `execution_mode`, `provider`, `requested_model` | `llm`/`openai` for submitted executions; test fixtures are explicitly labeled. |
| `authenticated_actor`, `input` | Trusted actor plus untrusted request and catalog-note fixtures. |
| `initial_students`, `initial_catalog` | State before any agent action. |
| `events` | Contiguous one-based ordered event sequence. |
| `outcomes`, `final_response` | Actual registrar tool outcomes and the advisor's final text. |
| `status`, optional `error` | Completion or failure; failed runs are not submission traces. |
| `final_students`, `final_catalog` | State after the last recorded action. |
| `post_run_policy_violations` | Audit evidence calculated after execution, not interceptions. |
| `source_sha256`, `runtime` | Producer Python-file hashes, Python version, and execution limits. |

## Event kinds

Each event has `step`, `agent`, `kind`, and `payload`.

| Kind | Payload |
| --- | --- |
| `agent_start` | Instructions, available tool schemas, and conversation input. Registrar conversations start separately for proposals. |
| `llm_request` | Local turn number and requested model; history is reconstructible from prior outputs and observations. |
| `llm_response` | API response ID, returned model ID, status, usage, and public response items. |
| `action` | Tool name, native call ID, and the exact JSON argument string chosen by the model. |
| `decision_summary` | A short model-generated public explanation taken from the tool arguments. This is not private chain-of-thought. |
| `observation` | Matching call ID and actual tool result. |
| `message` | Sender is the event's agent; payload identifies recipient and proposal/reply content. |
| `final` | The agent's public final text. |
| `error` | An interruption or failure retained in a partial trace. |

`function_call_output` is constructed from the observation and fed back to the
same model conversation. `ask_registrar` remains pending while the registrar's
conversation runs; nested events therefore appear between its action and its
observation. The registrar returns its final text plus actual tool outcomes.

Encrypted reasoning is retained in memory only when necessary for stateless API
continuation. It is omitted from logs. Credentials and HTTP headers are never logged.
Readable Markdown companions display all actions, decisions, messages, observations,
and finals; JSON retains the full prompt/API metadata as well.

## Validation contract

`python3 -m phase1.evidence --current-source` checks completed LLM executions,
contiguous events, both roles' model responses and finals, unique response IDs,
model/tool/action links, matched observations, message links, unchanged read
snapshots, successful write effects, course coverage, and reproduced final state
and audit. `python3 -m phase1.submission` also requires current producer hashes,
matching readable views, required documentation, and the credential scan.

The checks establish internal consistency, not an external cryptographic proof of
API provenance or an exhaustive semantic verification of free-text model output.
