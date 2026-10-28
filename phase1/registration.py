"""UCLA-inspired synthetic appointment and section logic; no live university access."""
import copy
from datetime import datetime


def moment(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Enrollment times must include a timezone offset.")
    return parsed


def appointment_group(profile):
    """Explain group eligibility; never calculate or change an assigned appointment time."""
    if profile["level"] == "graduate":
        return "graduate_single_pass"
    if profile["priority_status"]:
        return "priority"
    if profile["degree_units_completed"] >= 160 and profile["graduating_next_two_terms"]:
        return "160_degree_units_and_graduating"
    units = profile["applicable_completed_units"] + profile["in_progress_units"]
    if units >= 160:
        return "160_plus"
    if profile["new_or_returning"]:
        return "new_or_returning"
    for threshold, label in [(135, "135_to_159.9"), (90, "90_to_134.9"), (45, "45_to_89.9")]:
        if units >= threshold:
            return label
    return "0_to_44.9"


def enrollment_context(students, catalog, now, student_id):
    student = students[student_id]
    profile = student["profile"]
    current = moment(now)
    active = next((w for w in profile["appointments"]
                   if moment(w["start"]) <= current < moment(w["end"])), None)
    future = sorted((w for w in profile["appointments"] if moment(w["start"]) > current),
                    key=lambda w: moment(w["start"]))
    units = sum(catalog[c]["units"] for c in student["enrolled"])
    limit = min(profile["study_limit"], active["unit_limit"]) if active else 0
    return copy.deepcopy({
        "student_id": student_id, "now": now, "level": profile["level"],
        "appointment_group": appointment_group(profile),
        "eligible_group_units": profile["applicable_completed_units"] + profile["in_progress_units"],
        "ap_ib_units": profile["ap_ib_units"], "degree_units_completed": profile["degree_units_completed"],
        "appointment_source": "trusted synthetic assignment; time is not inferred from unit count",
        "active_appointment": active, "next_appointment": future[0] if future else None,
        "future_appointments": future, "current_units": units,
        "current_unit_limit": limit, "remaining_units": max(0, limit - units),
        "study_limit": profile["study_limit"], "required_courses": profile["required_courses"],
        "enrolled": student["enrolled"], "enrolled_sections": student["enrolled_sections"],
        "unavailable": profile["unavailable"],
    })


def overlaps(left, right):
    return left["day"] == right["day"] and left["start"] < right["end"] and right["start"] < left["end"]


def section_conflict(student, catalog, section):
    meetings = list(student["profile"]["unavailable"])
    for course, section_id in student["enrolled_sections"].items():
        meetings.extend(s for s in catalog[course]["sections"] if s["id"] == section_id)
    return any(overlaps(section, meeting) for meeting in meetings)


def search_sections(students, catalog, now, student_id, course):
    student, entry = students[student_id], catalog[course]
    context = enrollment_context(students, catalog, now, student_id)
    missing = sorted(set(entry["requires"]) - set(student["completed"]))
    rows = []
    for section in entry["sections"]:
        rows.append({**section, "schedule_conflict": section_conflict(student, catalog, section),
                     "seat_available": section["seats"] > 0})
    return {"course": course, "units": entry["units"], "required_for_student": course in context["required_courses"],
            "missing_prerequisites": missing, "appointment_open": context["active_appointment"] is not None,
            "remaining_units": context["remaining_units"], "sections": rows,
            "availability_is_snapshot": True, "waitlist_supported": False}


def enrollment_block(students, catalog, now, student_id, course, section_id, waive=False):
    """Ordinary business checks. Phase 1 still lacks actor authorization and trusted waiver approval."""
    student, entry = students[student_id], catalog[course]
    context = enrollment_context(students, catalog, now, student_id)
    if course in student["enrolled"]:
        return "already_enrolled", None
    if set(entry["requires"]) - set(student["completed"]) and not waive:
        return "missing_prerequisites", None
    if not context["active_appointment"]:
        return "appointment_not_open", None
    if context["current_units"] + entry["units"] > context["current_unit_limit"]:
        return "unit_limit", None
    sections = entry["sections"]
    if section_id == "auto":
        section = next((s for s in sections if s["seats"] > 0 and not section_conflict(student, catalog, s)), None)
        if section is None:
            return ("no_seats" if not any(s["seats"] > 0 for s in sections) else "schedule_conflict"), None
    else:
        section = next((s for s in sections if s["id"] == section_id), None)
        if section is None:
            return "unknown_section", None
    if entry["seats"] <= 0 or section["seats"] <= 0:
        return "no_seats", None
    if section_conflict(student, catalog, section):
        return "schedule_conflict", None
    return None, section
