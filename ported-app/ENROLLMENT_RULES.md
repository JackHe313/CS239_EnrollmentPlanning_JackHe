# UCLA-inspired enrollment model

## Verified university rules

UCLA undergraduates normally have first and second enrollment passes. First pass
allows up to 10 units; second pass uses the student's College/school study-list
maximum. Applicable completed and in-progress units affect appointment groups.
AP/IB credit is excluded from ordinary grouping, with a degree-unit exception for
students at 160 units who declare graduation in the next two terms. Priority
status is a separate entitlement. Exact times are assigned within groups, not
computed by an advisor from a unit count.

Source: [UCLA undergraduate enrollment passes](https://registrar.ucla.edu/registration-classes/enrollment-appointments-and-passes/undergraduate-student-enrollment-passes).

Most UCLA graduate students receive one appointment/pass. A 12-unit normal graduate
load is not an across-the-board maximum; professional programs have separate
arrangements.

Source: [UCLA graduate enrollment](https://registrar.ucla.edu/registration-classes/enrollment-appointments/graduate-student-enrollment).

The registrar publishes term-wide windows and directs students to MyUCLA for
individual times. Alternative study lists and avoiding meeting conflicts are part
of its planning guidance.

Source: [UCLA appointment information](https://registrar.ucla.edu/registration-classes/enrollment-appointments/enrollment-appointments).

Sources checked October 27, 2026. This simulator is an instructional adaptation,
not an implementation of every university rule or a source of individual enrollment advice.

## Implemented simulation

- Separate undergraduate and graduate profiles. Appointment windows, priority
  status, academic units, degree requirements, and study limits are trusted fixture data.
- An informational unit-group calculation with separate applicable and AP/IB units.
  Recomputing a group never changes an already assigned appointment timestamp.
- Timezone-aware, fixed simulation time. Writes require an active assigned window;
  intervals include the start and exclude the end. The LLM cannot advance the clock.
- A cumulative pass budget over the term's current enrollments. Moving from a
  priority window to first pass does not reset previously enrolled units.
- Second-pass limits from the student's profile. The undergraduate example uses
  a configured 19-unit study limit; the graduate example uses a configured 16-unit
  cap. These fixture values are not claims about every UCLA student's limit.
- Multiple sections, individual seat counts, meeting times, and hard unavailable
  periods. Both agents can search; the registrar rechecks availability/conflicts at write time.
- A model-generated priority plan: required courses first, scarce usable sections
  next, accounting for unit cost and the current pass budget. This orders a
  student's own courses; it does not change institutional priority among students.
- Explicit deferral to an actual later assigned window with enough unit capacity.
  Deferral does not reserve a seat, guarantee future eligibility, enroll later,
  schedule an automation, or create a wait-list position.

## Demonstrations

`first_pass_planning` requests an elective before two required courses. The advisor
should reorder them, use at most 10 units, and leave the overflow course for second pass.
`second_pass_planning` starts from the first-pass schedule and adds the deferred
course under the larger study limit. `before_appointment` plans without an early
write. `seat_finding` has a full section, a conflicting section, and a usable alternative.

The original compliant, catalog-injection, and cross-student scenarios remain.
Their authorization and waiver weaknesses are intentional Phase 1 failures.

## Boundaries

All course IDs, requirements, individual appointments, seats, profiles, and schedules
are synthetic. No MyUCLA connection or real seat monitoring occurs. There are no
wait-list writes, PTE processing, swaps/drops, priority-group seat-percentage quotas,
major/class-level restrictions, linked discussion sections, final-exam scheduling,
professional-school exceptions, or automatic retries. Meeting times represent one
weekly block per section. A fresh search is a snapshot, not a seat guarantee.
