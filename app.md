# EnrollmentPlanning

EnrollmentPlanning is a UCLA-inspired, synthetic academic enrollment assistant with
two LLM agents. The Advisor reads enrollment context, searches sections, ranks
requested courses, and delegates proposals. The Registrar independently reads
academic records and decides whether to enroll, reject, or record a later-window
deferral. It is a workflow-oriented application with centralized coordination in
EnrollmentApplication and a single CLI entry point.

Supported tasks include undergraduate first/second-pass planning, a separate
graduate single-pass profile, explanation of units-based appointment grouping,
searching available sections, avoiding meeting conflicts, respecting pass/study
limits, and reporting enrollment receipts. Assigned times are trusted fixture
values; the model cannot choose an earlier institutional appointment. A deferral
is a proposal, not a seat reservation or automatic future action.

Run with Python 3.9+ and your own OPENAI_API_KEY using
`python3 -m phase1.app --scenario first_pass_planning --max-api-calls 40`.
There are no third-party Python dependencies. Both agents use separate prompts,
histories, and tool sets through OpenAI Responses API calls. Their actual API
instructions are provided in agents/advisor.md and agents/registrar.md.

All profiles, course details, appointments, and seats are synthetic. There is no
MyUCLA integration, real seat monitoring, wait-list write, or scheduled enrollment.
The Phase 1 baseline contains ordinary business checks but no safety-enforcing
framework. It intentionally permits cross-student access and model-asserted
prerequisite waivers, demonstrating requirements for the Phase 2 assurance port.

Seven real LLM executions cover normal enrollment, catalog injection, cross-student
access, first-pass planning, second-pass enrollment, early-appointment deferral, and
alternative-section search. Example episodes summarize these actual runs and
separate intended outcomes from observed unsafe behavior. Policies describe the
intended permissions and boundaries even where Phase 1 does not enforce them.
