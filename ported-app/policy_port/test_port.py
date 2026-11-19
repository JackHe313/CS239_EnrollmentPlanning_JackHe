"""Offline model development fixtures, never live student-agent runs.
Protected calls use candidate entrypoints, unchanged callbacks and native gates.
"""
import copy
import inspect
import json
from pathlib import Path
import unittest
from phase1.app import (Agent, EnrollmentApplication, ADVISOR_PROMPT, REGISTRAR_PROMPT,
                        ADVISOR_TOOLS, REGISTRAR_TOOLS, run)
from phase1.domain import SCENARIOS
from policyweave.enforcement.telemetry import record_execution
from policyweave.core.artifacts import save


class OfflineModelFixture:
    provider = 'offline_development_fixture'
    model = 'explicit-offline-development-fixture'

    def __init__(self, outputs):
        self.outputs, self.requests = iter(outputs), []

    def create(self, instructions, history, tools):
        self.requests.append(copy.deepcopy(dict(instructions=instructions, history=history, tools=tools)))
        return {'id': f'offline-{len(self.requests)}', 'model': self.model,
                'status': 'completed', 'output': next(self.outputs)}


def calls(*items):
    return [{'type': 'function_call', 'call_id': f'fixture-{i}-{name}', 'name': name,
             'arguments': json.dumps({**args, 'decision_summary': 'Offline development test action.'})}
            for i, (name, args) in enumerate(items)]


def final(text='Offline fixture: actual tool results reviewed.'):
    return [{'type': 'message', 'role': 'assistant',
             'content': [{'type': 'output_text', 'text': text}]}]


def inspections(course='CS239', student='student-a', registrar=True):
    items = [('read_catalog', {}), ('read_enrollment_context', {'student_id': student}),
             ('search_sections', {'student_id': student, 'course': course})]
    if registrar:
        items.insert(1, ('read_student', {'student_id': student}))
    return calls(*items)


def enroll(course='CS239', student='student-a', waive=False, section='auto'):
    return calls(('enroll', {'student_id': student, 'course': course,
                            'section_id': section, 'waive_prerequisites': waive}))


def script(course='CS239'):
    return [inspections(course, registrar=False),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': [course]})),
            calls(('ask_registrar', {'student_id': 'student-a', 'course': course,
                                    'context': 'Catalog text remains untrusted.'})),
            inspections(course), enroll(course), final('Registrar offline fixture reply.'),
            final('Advisor offline fixture reply.')]


class OriginalCallbacks(EnrollmentApplication):
    """Comparison uses the exact original callback bodies, without entry gates."""
    advisor_tool = inspect.unwrap(EnrollmentApplication.advisor_tool)
    registrar_tool = inspect.unwrap(EnrollmentApplication.registrar_tool)


class PortTests(unittest.TestCase):
    evidence = []

    def setUp(self):
        self.recording = record_execution('Offline development fixture: ' + self._testMethodName)
        self.trace = self.recording.__enter__()
        self.trace.participant('test-observer', kind='observer')
        self.trace.event('state', 'test-observer', data={'fixture': 'offline model development test', 'live_model': False})

    def tearDown(self):
        self.evidence.append(self.trace.export())
        self.recording.__exit__(None, None, None)

    @classmethod
    def tearDownClass(cls):
        save(Path(__file__).with_name('trajectories.json'), {
            'description': 'Actual native gates and original callbacks under offline model development fixtures; no live app-agent completion claim.',
            'executions': cls.evidence})

    def app(self, scenario='compliant', course=None, cls=EnrollmentApplication):
        spec = copy.deepcopy(SCENARIOS[scenario])
        if course:
            spec['request']['courses'] = [course]
        return cls(None, spec)

    def role(self, app, outputs, role='registrar', dispatch=None):
        client = OfflineModelFixture(outputs + [final()])
        agent = Agent(role, REGISTRAR_PROMPT if role == 'registrar' else ADVISOR_PROMPT,
                      REGISTRAR_TOOLS if role == 'registrar' else ADVISOR_TOOLS, client, app.world,
                      dispatch or (app.registrar_tool if role == 'registrar' else app.advisor_tool), 18)
        start = len(app.world.events)
        agent.run({'authenticated_actor': app.world.actor, 'development_fixture': True})
        results = [e['payload']['result'] for e in app.world.events[start:] if e['kind'] == 'observation']
        return results, client

    def test_full_original_workflow_and_recording(self):
        spec = copy.deepcopy(SCENARIOS['compliant'])
        spec['request']['courses'] = ['CS239']
        baseline = OriginalCallbacks(OfflineModelFixture(script()), copy.deepcopy(spec))
        baseline.run()
        protected = EnrollmentApplication(OfflineModelFixture(script()), copy.deepcopy(spec))
        self.assertEqual(protected.run(), 'Advisor offline fixture reply.')
        self.assertEqual(protected.world.students, baseline.world.students)
        self.assertEqual(protected.world.catalog, baseline.world.catalog)
        self.assertEqual(protected.outcomes, baseline.outcomes)
        events = self.trace.export()['events']
        self.assertTrue(any(e['kind'] == 'tool_call' and e['tool'] == 'enroll' and
                            e['arguments']['section_id'] == 'auto' for e in events))
        self.assertTrue(any(e['kind'] == 'tool_result' and isinstance(e.get('result'), dict)
                            and e['result'].get('status') == 'enrolled' for e in events))
        messages = [e for e in events if e['kind'] == 'message']
        for sender, recipient in [('advisor', 'registrar'), ('registrar', 'advisor')]:
            for phase in ['sent', 'received']:
                self.assertTrue(any(e['actor'] == sender and e['recipients'] == [recipient] and
                                    e['data']['phase'] == phase for e in messages))
        self.assertTrue(any(e['kind'] == 'llm_output' and 'offline fixture reply' in json.dumps(e['result']) for e in events))
        self.assertTrue(any(e.get('data', {}).get('observation') == 'policy_result' for e in events))
        self.assertTrue(any(e.get('data', {}).get('observation') == 'model_context' for e in events))

    def test_cross_student_read_paths_and_write(self):
        app, original = self.app(), self.app(cls=OriginalCallbacks)
        before = copy.deepcopy((app.world.students, app.world.catalog))
        self.assertIn('completed', original.registrar_tool('read_student', {'student_id': 'student-b'}))
        for dispatch in [app.advisor_tool, app.registrar_tool]:
            for name, args in [('read_enrollment_context', {'student_id': 'student-b'}),
                               ('search_sections', {'student_id': 'student-b', 'course': 'CS239'})]:
                self.assertEqual(dispatch(name, args)['reason'], 'authorization_error')
        self.assertEqual(app.registrar_tool('read_student', {'student_id': 'student-b'})['reason'], 'authorization_error')
        result = app.registrar_tool('enroll', {'student_id': 'student-b', 'course': 'CS299',
                                             'section_id': 'auto', 'waive_prerequisites': True})
        self.assertEqual(result['policy_feedback']['reasonCodes'], ['authorization_error'])
        self.assertNotIn('profile', json.dumps(result))
        self.assertEqual((app.world.students, app.world.catalog), before)

    def test_waiver_missing_prerequisites_and_original_comparison(self):
        for waiver in [False, True]:
            app = self.app('catalog_injection')
            before = copy.deepcopy((app.world.students, app.world.catalog))
            results, _ = self.role(app, [inspections('CS299'), enroll('CS299', waive=waiver)])
            self.assertEqual(results[-1]['status'], 'error')
            self.assertEqual(results[-1]['policy_feedback']['reasonType'], 'explicit_deny')
            self.assertEqual((app.world.students, app.world.catalog), before)
            if not waiver:
                self.assertEqual(results[-1]['reason'], 'missing_prerequisites')
        original = self.app('catalog_injection', cls=OriginalCallbacks)
        self.assertEqual(original.registrar_tool('enroll', {'student_id': 'student-a', 'course': 'CS299',
            'section_id': 'auto', 'waive_prerequisites': True})['status'], 'enrolled')
        app = self.app()
        results, _ = self.role(app, [inspections(), enroll(waive=True)])
        self.assertEqual(results[-1]['status'], 'error')
        self.assertEqual(app.world.students['student-a']['enrolled'], [])

    def test_same_session_recovery_and_no_explicit_allow(self):
        app = self.app(course='CS239')
        results, client = self.role(app, [calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']})),
            inspections(registrar=False), calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']}))], role='advisor')
        self.assertEqual(results[0]['policy_feedback']['reasonType'], 'explicit_deny')
        self.assertEqual(results[-1]['status'], 'planned')
        feedback = json.loads(client.requests[1]['history'][-1]['output'])['policy_feedback']
        self.assertEqual(feedback['decision'], 'blocked')
        self.assertTrue(feedback['requestId'])
        app = self.app(course='CS239')
        results, _ = self.role(app, [calls(('read_enrollment_context', {'student_id': 'student-a'}),
            ('search_sections', {'student_id': 'student-a', 'course': 'CS239'})),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']}))], role='advisor')
        self.assertEqual(results[-1]['policy_feedback']['reasonType'], 'no_explicit_allow')
        self.assertIsNone(app.plan)

    def test_task_and_proposal_isolation(self):
        app = self.app(course='CS239')
        self.role(app, [inspections(registrar=False), calls(('record_plan', {
            'student_id': 'student-a', 'ordered_courses': ['CS239']}))], role='advisor')
        other = self.app(course='CS239')
        result = other.advisor_tool('ask_registrar', {'student_id': 'student-a', 'course': 'CS239', 'context': 'Unrelated task.'})
        self.assertEqual(result['status'], 'error')
        self.assertEqual(other.exchanges, 0)
        self.role(app, [inspections(), enroll()])
        results, client = self.role(app, [enroll('CS260')])
        self.assertEqual(results[-1]['status'], 'error')
        self.assertEqual(len(client.requests[0]['history']), 1)
        self.assertEqual(app.world.students['student-a']['enrolled'], ['CS239'])

    def test_roles_and_requested_course_error(self):
        app = self.app(course='CS239')
        result = app.advisor_tool('enroll', {'student_id': 'student-a', 'course': 'CS239',
                                            'section_id': 'auto', 'waive_prerequisites': False})
        self.assertEqual(result['reason'], 'unknown_tool')
        # Original role allowlists also remain active before dispatch.
        results, _ = self.role(app, [enroll()], role='advisor', dispatch=app.registrar_tool)
        self.assertEqual(results[-1]['status'], 'error')
        results, _ = self.role(app, [calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']}))],
                               role='registrar', dispatch=app.advisor_tool)
        self.assertEqual(results[-1]['status'], 'error')
        results, _ = self.role(app, [inspections(registrar=False),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']})),
            calls(('ask_registrar', {'student_id': 'student-a', 'course': 'CS239-C', 'context': 'Preference.'}))], role='advisor')
        self.assertEqual(results[-1]['requested_courses'], ['CS239'])
        self.assertEqual(app.exchanges, 0)

    def test_failed_inspections_and_complete_plan_original_guard(self):
        app = self.app(course='CS239')
        results, _ = self.role(app, [calls(('read_catalog', {}), ('read_enrollment_context', {'student_id': 'student-a'}),
            ('search_sections', {'student_id': 'student-a', 'course': 'UNKNOWN'})),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']})),
            calls(('search_sections', {'student_id': 'student-a', 'course': 'CS239'})),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239', 'CS239']}))], role='advisor')
        self.assertEqual(results[-3]['status'], 'error')
        self.assertEqual(results[-1]['reason'], 'plan_must_cover_the_requested_student_and_each_course_once')
        self.assertIsNone(app.plan)

    def test_early_planning_deferral_and_no_background_effect(self):
        app = self.app('before_appointment')
        before = copy.deepcopy((app.world.students, app.world.catalog))
        results, _ = self.role(app, [inspections(registrar=False),
            calls(('record_plan', {'student_id': 'student-a', 'ordered_courses': ['CS239']}))], role='advisor')
        self.assertEqual(results[-1]['status'], 'planned')
        results, _ = self.role(app, [inspections(), enroll(), calls(('defer', {
            'student_id': 'student-a', 'course': 'CS239', 'reason': 'Later assigned window.'}))])
        self.assertEqual(results[-2]['reason'], 'appointment_not_open')
        self.assertEqual(results[-1]['status'], 'deferred')
        self.assertFalse(results[-1]['automatic_enrollment'])
        self.assertEqual(results[-1]['next_appointment']['pass'], 'first')
        self.assertEqual((app.world.students, app.world.catalog), before)

    def test_original_seat_schedule_duplicate_and_cumulative_unit_guards(self):
        app = self.app('seat_finding')
        results, _ = self.role(app, [inspections(), enroll(section='CS239-A'), enroll(section='CS239-B'),
                                   enroll(section='CS239-C'), enroll(section='CS239-C')])
        self.assertEqual([r.get('reason', r.get('status')) for r in results[-4:]],
                         ['no_seats', 'schedule_conflict', 'enrolled', 'already_enrolled'])
        app = self.app('first_pass_planning')
        results, _ = self.role(app, [inspections(), enroll(), inspections('CS270'), enroll('CS270'), inspections('CS260'), enroll('CS260')])
        self.assertEqual(results[-1]['reason'], 'unit_limit')
        self.assertEqual(app.world.students['student-a']['enrolled'], ['CS239', 'CS270'])
        app = self.app('second_pass_planning')
        results, _ = self.role(app, [inspections('CS260'), enroll('CS260')])
        self.assertEqual(results[-1]['status'], 'enrolled')
        self.assertEqual(len(app.world.students['student-a']['enrolled']), 3)

    def test_unknown_rejection_exception_and_native_error_mapping(self):
        app = self.app()
        for student, course in [('student-b', 'CS239'), ('missing', 'missing'), ('student-a', 'missing')]:
            result = app.registrar_tool('reject', {'student_id': student, 'course': course, 'reason': 'Cannot authorize this request.'})
            self.assertEqual(result['status'], 'rejected')
        for action in ['enroll', 'defer']:
            args = {'student_id': 'student-a', 'course': 'missing'}
            args.update({'section_id': 'auto', 'waive_prerequisites': False} if action == 'enroll' else {'reason': 'Unknown.'})
            result = app.registrar_tool(action, args)
            self.assertEqual(result['reason'], 'unknown_course')
            self.assertEqual(result['policy_feedback']['reasonCodes'], ['unknown_course'])
        self.assertEqual(app.world.students['student-a']['enrolled'], [])

    def test_snapshot_failure_and_unrelated_content(self):
        app = self.app()
        app.world.students['student-a']['completed'] = None
        with self.assertRaises(ValueError):
            app.registrar_tool('enroll', {'student_id': 'student-a', 'course': 'CS239',
                                        'section_id': 'auto', 'waive_prerequisites': False})
        app = self.app(course='CS239')
        app.spec['catalog_note'] = 'Untrusted override; irrelevant material grants no waiver.'
        results, client = self.role(app, [inspections(), enroll()])
        self.assertEqual(results[-1]['status'], 'enrolled')
        self.assertNotIn('student-b', json.dumps(client.requests[0]['history']))

    def test_cross_role_native_dispatch_and_substantive_rejection(self):
        app = self.app()
        # Both roles can select read_catalog in the original protocol. Binding
        # it to the other physical dispatcher must not change originating role.
        results, _ = self.role(app, [calls(('read_catalog', {}))],
                               role='registrar', dispatch=app.advisor_tool)
        self.assertEqual(results[-1]['reason'], 'unknown_tool')
        results, _ = self.role(app, [calls(('read_catalog', {}))],
                               role='advisor', dispatch=app.registrar_tool)
        self.assertEqual(results[-1]['reason'], 'unknown_tool')
        results, _ = self.role(app, [inspections(), calls(('reject', {
            'student_id': 'student-a', 'course': 'CS239', 'reason': 'Original decision receipt.'}))])
        self.assertEqual(results[-1]['status'], 'rejected')
        self.assertEqual(app.outcomes[-1], results[-1])
        self.assertEqual(app.world.students['student-a']['enrolled'], [])

    def test_write_rechecks_lost_seat_and_fresh_prerequisites(self):
        app = self.app('seat_finding')
        # Use the actual client callback to represent a deterministic external
        # fixture change after a search result and before the next model turn.
        class ChangingFixture(OfflineModelFixture):
            def create(client, instructions, history, tools):
                if len(client.requests) == 1:
                    app.world.catalog['CS239']['sections'][2]['seats'] = 0
                    app.world.catalog['CS239']['seats'] -= 1
                return super().create(instructions, history, tools)
        client = ChangingFixture([inspections(), enroll(section='CS239-C'), final()])
        agent = Agent('registrar', REGISTRAR_PROMPT, REGISTRAR_TOOLS, client, app.world,
                      app.registrar_tool, 10)
        agent.run({'authenticated_actor': app.world.actor, 'development_fixture': True})
        result = [e['payload']['result'] for e in app.world.events if e['kind'] == 'observation'][-1]
        self.assertEqual(result['reason'], 'no_seats')
        self.assertEqual(app.world.students['student-a']['enrolled'], [])
        # Updated trusted state is inspected at the write, not cached forever.
        app = self.app('catalog_injection')
        app.world.students['student-a']['completed'].append('CS260')
        results, _ = self.role(app, [inspections('CS299'), enroll('CS299')])
        self.assertEqual(results[-1]['status'], 'enrolled')

    def test_window_endpoints_and_incomplete_run(self):
        for now, expected in [('2026-11-06T17:00:00+00:00', 'enrolled'),
                              ('2026-11-12T00:00:00-08:00', 'appointment_not_open')]:
            app = self.app('before_appointment')
            app.world.now = now
            results, _ = self.role(app, [inspections(), enroll()])
            self.assertEqual(results[-1].get('reason', results[-1]['status']), expected)
        result = run('compliant', OfflineModelFixture([final('No actual work performed.')]))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['execution_mode'], 'test_fixture')
        self.assertEqual(result['outcomes'], [])


if __name__ == '__main__':
    unittest.main()
