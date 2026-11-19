# Added enforcement

## Read the advisor catalog

Records: Before read_catalog at the advisor boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.

## Read the registrar catalog

Records: Before read_catalog at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.

## Read advisor enrollment context

Records: Before read_enrollment_context at the advisor boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
The separate student-target check still applies.

## Search advisor sections

Records: Before search_sections at the advisor boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
A course parameter and the separate student-target check are required.

## Record a plan

Records: Before record_plan at the advisor boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
The separate target and inspection checks apply. The added Allow requires ordered_courses to be present; the original app validates its full course list before storing the plan.

## Delegate a course

Records: Before ask_registrar at the advisor boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
The separate target, requested-course and inspection checks apply. A context parameter must be present; the plan-evidence check describes its unchecked content.

## Read a student record

Records: Before read_student at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
The separate student-target check applies. The original tool returns the full saved student profile; this permission does not restrict which profile fields reach the model.

## Read registrar enrollment context

Records: Before read_enrollment_context at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor or registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
The separate student-target check applies. Advisor forwarding keeps its advisor role and task scope through this additional registrar gate.

## Search registrar sections

Records: Before search_sections at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give advisor or registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
A course parameter and the separate student-target check are required. Advisor forwarding keeps its advisor role and task scope through this additional registrar gate.

## Attempt enrollment

Records: Before enroll at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
Separate target, existence, waiver, prerequisite and inspection checks apply. The added Allow does not require section_id; the original app defaults direct calls to auto and checks seats, schedule, appointment windows and cumulative limits.

## Defer enrollment

Records: Before defer at the registrar boundary, reads the host-selected role and scope and the installed group and capability grants.

Rules: Static group membership and inherited capability grants give registrar permission for this call. If Can cannot be derived, explicitly deny unknown_tool before the tool body. Any Deny overrides all alternative Allows; separate action checks and required parameters still apply.
A reason parameter and the separate target, existence and inspection checks apply. The original app chooses an assigned later window with unit capacity and records automatic_enrollment=False; this permission adds no scheduling service.

## Record a rejection

Records: Before reject, reads the host-selected role and scope, static group and capability grants, student_id, course and reason, plus the actor and current student/course keys.

Rules: Static membership and inherited grants give registrar rejection permission. Missing Can explicitly denies unknown_tool. With permission and student_id, course and reason present, any alternative Allow may pass only if no Deny exists.
A different student target, an actor-target student missing from saved students, or an existing actor-target student with an unknown course each permits the original no-read rejection without inspection evidence. These paths append rejected outcomes; they are not policy refusals.
For a known actor-target student and course, the ordinary branch requires the separate inspection checks. Missing required parameters prevents its Allow; rejection permission alone does not satisfy this branch.

## Match the student target

Records: Before student-specific calls, reads the supplied student_id and the current local world actor, initialized to student-a independently of the requested student.

Rules: Ordinary student-specific Allows require exact equality with the observed actor. With both values present, any mismatch explicitly denies authorization_error for every action except reject. Missing either value prevents the ordinary matching Allow.
Reject instead has a separate permitted no-read path for a different target. The mismatch Deny also covers other actions carrying student_id if they reach evaluation; the call contract normally rejects extra catalog arguments first.

## Require a saved student

Records: Before enroll, reject or defer, reads student_id and all current saved-student keys.

Rules: After permission and actor matching, enroll and defer require an equal saved-student key. Absence explicitly denies unknown_student before the original tool. Reject instead uses its separate unknown-student no-read Allow.
Read tools have no added student-existence Deny and leave unknown-student handling to the original app. Failure to acquire student keys propagates as an error rather than supplying an empty set.

## Require a catalog course

Records: Before enroll, reject or defer, reads the supplied course and all current catalog-course keys.

Rules: After permission, actor matching and student existence, enroll and defer require an exactly matching catalog key. Absence explicitly denies unknown_course. Reject instead uses its separate unknown-course no-read Allow.
Search calls require course but leave unknown-course handling to the original app after target matching. Existing course keys do not restrict registrar decisions to the proposed course or requested list.

## Disable prerequisite waivers

Records: Before enroll, reads waive_prerequisites from the request, with booleans normalized to true or false.

Rules: The enroll Allow requires exactly false. For a permitted actor-target known student and course, true explicitly denies waiver_not_authorized even when prerequisites are complete; the public refusal is policy_refusal. An absent flag prevents Allow.
Malformed boolean values fail call validation. The independent prerequisite check still applies; this flag restriction does not validate approval or classify waiver claims in catalog prose or proposal context.

## Require all prerequisites

Records: Before each enroll decision for a known actor-target student and course, reads the current catalog prerequisite list and saved completed-course list. Both must contain only exact strings.

Rules: With permission and the separate target and existence checks satisfied, any required course lacking an exactly equal completed course explicitly denies missing_prerequisites before enrollment, regardless of waiver value or inspection evidence.
Duplicates add no obligation; an empty prerequisite list causes no Deny. Passing this check leaves the other enrollment checks in force. Local saved lists supply the evidence; acquisition or type failures stop evaluation.

## Inspect the catalog before acting

Records: After a logged native read_catalog call receives its matching same-role/scope/call-ID observation, records catalog evidence only for a non-error dictionary containing courses and external_note. Reads this evidence before record_plan, ask_registrar and substantive enroll/reject/defer.

Rules: These actions require some catalog evidence in their current role and scope. Missing evidence prevents ordinary Allow, yielding no_explicit_allow unless an explicit Deny applies. The separate rejection exceptions bypass this requirement.
Advisor evidence belongs to its task; each registrar run has a fresh scope, while direct registrar calls share direct-registrar. Direct reads outside the action/observation log create no evidence. Historical evidence suffices without a current catalog match.
The requirement does not bind catalog content to model context, delegation messages or final text, or prove model use. Those contents remain unchecked by this inspection gate.

## Inspect the same student context

Records: After logged native read_enrollment_context targets the actor, records student evidence only when its matched non-error dictionary returns that student_id and contains active_appointment, even if None. Reads scoped evidence before planning, delegation and substantive decisions.

Rules: With the separate permission and target checks, record_plan and requested-course ask_registrar require context evidence exactly matching student_id. Known-student/course enroll/reject/defer require the same match. Missing evidence explicitly denies context_inspection_required and prevents ordinary Allow.
The separate rejection exceptions bypass this check. Evidence uses the same logged-call and role/scope requirements as catalog inspection. A closed-window context satisfies inspection; the original app still decides appointment and unit capacity. Prior evidence remains sufficient after plan, clock or enrollment changes.

## Inspect every requested course

Records: Before record_plan or ask_registrar, reads the current requested-course list. After logged native search_sections targets the actor, records scoped course evidence only when its matched non-error result returns the exact requested search course and availability_is_snapshot=True.

Rules: For permitted actor-target record_plan, and ask_registrar proposing a requested course, any requested course without exactly matching search evidence explicitly denies section_inspection_required before storage or delegation. All requested courses must be covered. An empty requested list causes no such Deny.
The catalog-inspection role/scope and logged-call requirements apply. Search evidence need not show seats, a conflict-free section, an active appointment or eligibility, and need not match section_id. Advisor evidence cannot satisfy a registrar run.

## Delegate only a requested course

Records: Before ask_registrar, reads its course parameter and the current course strings in the application request, independently of plan order or context text.

Rules: With permission and actor matching, the proposed course must exactly equal at least one requested course. Missing membership explicitly denies requested_course_required and prevents delegation Allow before messages, exchanges or registrar execution. A section ID receives no special interpretation.
When this is the sole refusal reason, the advisor returns requested-course guidance and the requested list. Registrar enroll/reject/defer have no equivalent requested/proposal-course restriction. The original app checks delegation order only after advisor completion.

## Record a plan before delegation

Records: After logged record_plan targets the actor, records scoped plan evidence only when its matched non-error result has status planned and the same student_id. The original app returns planned after validating the requested student and full course list and storing the plan. Reads evidence before ask_registrar.

Rules: ask_registrar requires some successful plan evidence in its current role and scope. Missing evidence prevents Allow and yields no_explicit_allow unless an explicit Deny applies. The separate actor and other delegation checks remain required; the catalog-inspection logged-call and scope requirements apply.
Any such prior plan suffices without binding this course, ordered list or current plan revision. The required context parameter may contain arbitrary text; no rule binds it to the catalog, plan or registrar reply. The original full-list validation supplies the plan-content check.

## Inspect the decision student

Records: After logged read_student targets the actor, records scoped evidence for that student only when its matched non-error dictionary contains completed and enrolled. Reads this evidence before substantive enroll, reject or defer.

Rules: With permission, actor matching and known student/course, enroll/reject/defer require student evidence exactly equal to their student_id. Missing evidence explicitly denies student_inspection_required and prevents ordinary Allow. The separate rejection exceptions bypass inspection.
The catalog-inspection logged-call and role/scope requirements apply. The original read returns the full saved profile, so fields disclosed to the model remain unrestricted. Historical inspection does not establish current prerequisite eligibility; the separate prerequisite check reads current state.

## Inspect the decision course

Records: After logged native search_sections targets the actor, records scoped course evidence only when its matched non-error result returns the exact search course and availability_is_snapshot=True. Reads this evidence before substantive enroll, reject or defer.

Rules: With permission, actor matching and known student/course, enroll/reject/defer require evidence exactly matching their course. Missing evidence explicitly denies section_inspection_required and prevents ordinary Allow. Separate rejection exceptions bypass inspection. Catalog-inspection logging and scope requirements apply.
Advisor searches and earlier registrar runs cannot supply this run's evidence. A zero-seat or conflicting result still qualifies without matching section_id or the current catalog. The original app decides seats, scheduling and deferral; this gate reserves no seats and adds no automatic enrollment.
