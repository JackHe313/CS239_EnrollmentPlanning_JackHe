"""Host-generated fixed policy factory. Do not edit."""
from pathlib import Path
from policyweave.enforcement import Policy as _Policy

CONTRACT = {'fields': {'authenticated_actor': {'cardinality': 'one', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'student_key': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'course_key': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'completed_course': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'required_prerequisite': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'requested_course': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'catalog_receipt': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'student_receipt': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'context_receipt': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'section_receipt': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}, 'plan_receipt': {'cardinality': 'many', 'type': 'symbol', 'unit': None, 'observedAt': None}}}
CALLS = {'read_catalog': {}, 'read_enrollment_context': {'student_id': 'symbol'}, 'search_sections': {'student_id': 'symbol', 'course': 'symbol'}, 'record_plan': {'student_id': 'symbol', 'ordered_courses': 'json'}, 'ask_registrar': {'student_id': 'symbol', 'course': 'symbol', 'context': 'symbol'}, 'registrar_read_catalog': {}, 'read_student': {'student_id': 'symbol'}, 'registrar_read_enrollment_context': {'student_id': 'symbol'}, 'registrar_search_sections': {'student_id': 'symbol', 'course': 'symbol'}, 'enroll': {'student_id': 'symbol', 'course': 'symbol', 'section_id': 'symbol', 'waive_prerequisites': 'boolean'}, 'reject': {'student_id': 'symbol', 'course': 'symbol', 'reason': 'symbol'}, 'defer': {'student_id': 'symbol', 'course': 'symbol', 'reason': 'symbol'}, 'observe_public_event': {}}
MECHANISMS = ('capability', 'observations')
INVARIANTS = ()

def make_policy(**options):
    if {'bundle', 'mechanisms', 'invariants', 'observation_contract', 'call_contract'} & options.keys():
        raise ValueError('Cannot override the frozen policy binding.')
    return _Policy(Path(__file__).with_name('rules.dl'), mechanisms=MECHANISMS,
                   invariants=INVARIANTS, observation_contract=CONTRACT, call_contract=CALLS, **options)
