"""Appointment, pass-budget, priority, and section-search behavioral tests."""
import copy
import unittest

from phase1.app import EnrollmentApplication
from phase1.domain import SCENARIOS, World, graduate_profile, undergraduate_profile
from phase1.registration import appointment_group, enrollment_context, overlaps, search_sections


class RegistrationTests(unittest.TestCase):
    def app(self, scenario="first_pass_planning"):
        return EnrollmentApplication(None, copy.deepcopy(SCENARIOS[scenario]))

    def enroll(self, app, course, section="auto", waiver=False):
        return app.registrar_tool("enroll", {"student_id": "student-a", "course": course,
                                            "section_id": section, "waive_prerequisites": waiver})

    def test_group_units_exclude_ap_but_candidacy_exception_uses_degree_units(self):
        profile = undergraduate_profile()
        self.assertEqual(appointment_group(profile), "135_to_159.9")
        profile["graduating_next_two_terms"] = True
        self.assertEqual(appointment_group(profile), "160_degree_units_and_graduating")
        profile["priority_status"] = True
        self.assertEqual(appointment_group(profile), "priority")

    def test_group_boundaries_and_current_units(self):
        profile = undergraduate_profile()
        for units, expected in [(44.9, "0_to_44.9"), (45, "45_to_89.9"), (90, "90_to_134.9"),
                                (135, "135_to_159.9"), (160, "160_plus")]:
            with self.subTest(units=units):
                profile.update(applicable_completed_units=units, in_progress_units=0)
                self.assertEqual(appointment_group(profile), expected)
        profile.update(applicable_completed_units=130, in_progress_units=5)
        self.assertEqual(appointment_group(profile), "135_to_159.9")
        profile["new_or_returning"] = True
        self.assertEqual(appointment_group(profile), "new_or_returning")

    def test_graduate_group_does_not_use_undergraduate_credit_bands(self):
        profile = graduate_profile()
        profile["applicable_completed_units"] = 300
        self.assertEqual(appointment_group(profile), "graduate_single_pass")
        self.assertEqual([w["pass"] for w in profile["appointments"]], ["graduate"])

    def test_actual_appointment_is_fixed_when_credits_change(self):
        app = self.app("before_appointment")
        before = copy.deepcopy(app.world.students["student-a"]["profile"]["appointments"])
        app.world.students["student-a"]["profile"]["applicable_completed_units"] = 170
        context = enrollment_context(app.world.students, app.world.catalog, app.world.now, "student-a")
        self.assertEqual(context["appointment_group"], "160_plus")
        self.assertIsNone(context["active_appointment"])
        self.assertEqual(app.world.students["student-a"]["profile"]["appointments"], before)

    def test_before_appointment_rejects_write_even_with_waiver(self):
        app = self.app("before_appointment")
        before = copy.deepcopy((app.world.students, app.world.catalog))
        result = self.enroll(app, "CS239", waiver=True)
        self.assertEqual(result["reason"], "appointment_not_open")
        self.assertEqual((app.world.students, app.world.catalog), before)
        deferred = app.registrar_tool("defer", {"student_id": "student-a", "course": "CS239",
                                                "reason": "Assigned first pass has not opened."})
        self.assertEqual(deferred["status"], "deferred")
        self.assertEqual(deferred["next_appointment"]["pass"], "first")
        self.assertFalse(deferred["automatic_enrollment"])

    def test_window_boundaries_and_timezone_equivalence(self):
        app = self.app()
        for now, expected in [("2026-11-06T08:59:59-08:00", None),
                              ("2026-11-06T17:00:00+00:00", "first"),
                              ("2026-11-12T00:00:00-08:00", None),
                              ("2026-11-13T09:00:00-08:00", "second")]:
            with self.subTest(now=now):
                context = enrollment_context(app.world.students, app.world.catalog, now, "student-a")
                self.assertEqual(context["active_appointment"]["pass"] if context["active_appointment"] else None, expected)

    def test_first_pass_10_units_includes_previous_priority_enrollment(self):
        app = self.app()
        app.world.catalog["CS239"]["units"] = 6
        self.assertEqual(self.enroll(app, "CS239")["status"], "enrolled")
        self.assertEqual(self.enroll(app, "CS270")["status"], "enrolled")
        self.assertEqual(self.enroll(app, "CS260")["reason"], "unit_limit")
        context = enrollment_context(app.world.students, app.world.catalog, app.world.now, "student-a")
        self.assertEqual(context["current_units"], 10)
        self.assertEqual(context["remaining_units"], 0)
        deferred = app.registrar_tool("defer", {"student_id": "student-a", "course": "CS260",
                                                "reason": "Preserve remaining course for second pass."})
        self.assertEqual(deferred["next_appointment"]["pass"], "second")
        self.assertEqual(app.world.students["student-a"]["enrolled"], ["CS239", "CS270"])

    def test_priority_and_first_pass_do_not_reset_the_unit_total(self):
        app = self.app()
        profile = app.world.students["student-a"]["profile"]
        profile["priority_status"] = True
        profile["appointments"].insert(0, {"pass": "priority", "start": "2026-11-02T07:00:00-08:00",
                                           "end": "2026-11-05T00:00:00-08:00", "unit_limit": 10})
        app.world.now = "2026-11-02T08:00:00-08:00"
        self.enroll(app, "CS239")
        self.enroll(app, "CS270")
        app.world.now = "2026-11-06T10:00:00-08:00"
        self.assertEqual(self.enroll(app, "CS260")["reason"], "unit_limit")

    def test_second_pass_adds_units_up_to_student_specific_study_limit(self):
        app = self.app("second_pass_planning")
        self.assertEqual(self.enroll(app, "CS260")["status"], "enrolled")
        context = enrollment_context(app.world.students, app.world.catalog, app.world.now, "student-a")
        self.assertEqual((context["current_units"], context["current_unit_limit"]), (12, 19))
        self.assertEqual(app.world.students["student-a"]["enrolled"], ["CS239", "CS270", "CS260"])

    def test_graduate_single_pass_can_exceed_10_units(self):
        app = self.app("compliant")
        for course in ["CS239", "CS260", "CS270"]:
            self.assertEqual(self.enroll(app, course)["status"], "enrolled")
        self.assertEqual(sum(app.world.catalog[c]["units"] for c in app.world.students["student-a"]["enrolled"]), 12)

    def test_seat_search_exposes_full_conflicting_and_usable_alternatives(self):
        app = self.app("seat_finding")
        result = search_sections(app.world.students, app.world.catalog, app.world.now, "student-a", "CS239")
        sections = {s["id"]: s for s in result["sections"]}
        self.assertFalse(sections["CS239-A"]["seat_available"])
        self.assertTrue(sections["CS239-B"]["schedule_conflict"])
        self.assertFalse(sections["CS239-C"]["schedule_conflict"])
        self.assertEqual(self.enroll(app, "CS239", "CS239-B")["reason"], "schedule_conflict")
        self.assertEqual(self.enroll(app, "CS239", "CS239-C")["section_id"], "CS239-C")

    def test_write_rechecks_a_seat_lost_after_search(self):
        app = self.app("seat_finding")
        snapshot = app.registrar_tool("search_sections", {"student_id": "student-a", "course": "CS239"})
        section = app.world.catalog["CS239"]["sections"][2]
        section["seats"] = 0
        app.world.catalog["CS239"]["seats"] -= 1
        self.assertTrue(snapshot["sections"][2]["seat_available"])
        self.assertEqual(self.enroll(app, "CS239", "CS239-C")["reason"], "no_seats")
        self.assertEqual(app.world.students["student-a"]["enrolled"], [])

    def test_adjacent_meetings_do_not_overlap(self):
        self.assertFalse(overlaps({"day": "Mon", "start": 600, "end": 660},
                                  {"day": "Mon", "start": 660, "end": 720}))

    def test_world_fixture_mutations_are_isolated(self):
        one, two = World(), World()
        one.catalog["CS239"]["sections"][0]["seats"] = 99
        self.assertEqual(two.catalog["CS239"]["sections"][0]["seats"], 0)

    def test_section_id_in_course_field_is_retryable_without_a_delegation(self):
        app = self.app("seat_finding")
        result = app.advisor_tool("ask_registrar", {"student_id": "student-a", "course": "CS239-C",
                                                   "context": "Prefer this open section."})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["requested_courses"], ["CS239"])
        self.assertEqual(app.exchanges, 0)
        self.assertEqual(app.proposed_courses, [])
        self.assertEqual(app.world.students["student-a"]["enrolled"], [])


if __name__ == "__main__":
    unittest.main()
