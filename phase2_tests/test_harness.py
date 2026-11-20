"""Offline assessment tests; saved traces are test inputs, never fresh samples."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import run as harness
from phase2.check_results import check_trajectory

ROOT=Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.cases=harness.load_cases()

    def trace(self, name):
        return json.loads((ROOT/'traces/phase1'/f'{name}.json').read_text())

    def test_timeline_must_match_its_sample_and_recorded_outcome(self):
        directory = ROOT / 'runs/S01/ported/sample-1'
        record = json.loads((directory / 'run.json').read_text())
        for key, value, message in (
                ('sample', record['sample'] + 1, 'different run'),
                ('matchExpectedOutcome', not record['matchExpectedOutcome'], 'outcome differs')):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                check_trajectory(directory, {**record, key: value})

    def test_ten_distinct_cases_have_the_course_fields_and_frozen_inputs(self):
        self.assertEqual(list(self.cases),[f'S{i:02}' for i in range(1,11)])
        for case in self.cases.values():
            self.assertTrue({'task','expected_outcome','involved_policies','run_command','initial_spec','initial_state'} <= set(case))
            self.assertTrue(all(len(row) == 2 for row in case['involved_policies']))
            self.assertNotIn('--side', case['run_command'])
            self.assertEqual(case['initial_state']['authenticated_actor'],'student-a')

    def test_existing_legitimate_live_evidence_meets_task_checks(self):
        for case_id in ['S01','S04','S05','S06','S07']:
            case=self.cases[case_id]
            with self.subTest(case=case_id):
                self.assertTrue(harness.check_result(case,self.trace(case['scenario'])))

    def test_requested_functional_effect_can_match_even_when_a_policy_is_violated(self):
        for case_id in ['S02', 'S03']:
            case = self.cases[case_id]
            trace = self.trace(case['scenario'])
            with self.subTest(case=case_id):
                self.assertTrue(harness.check_result(case, trace))
                trace['final_students'] = trace['initial_students']
                self.assertFalse(harness.check_result(case, trace))

    def test_failure_fixture_or_unconfirmed_final_never_counts(self):
        for field,value in [('status','failed'),('execution_mode','test_fixture'),('final_response','')]:
            trace=self.trace('compliant')
            trace[field]=value
            with self.subTest(field=field):
                self.assertFalse(harness.check_result(self.cases['S01'],trace))

    def test_changed_seats_extra_writes_or_initial_state_are_rejected(self):
        trace=self.trace('compliant')
        altered=copy.deepcopy(trace)
        altered['final_catalog']['CS239']['seats']+=1
        self.assertFalse(harness.check_result(self.cases['S01'],altered))
        altered=copy.deepcopy(trace)
        altered['final_students']['student-b']['enrolled'].append('CS270')
        self.assertFalse(harness.check_result(self.cases['S01'],altered))
        altered=copy.deepcopy(trace)
        altered['initial_students']['student-a']['profile']['study_limit']=99
        self.assertFalse(harness.check_result(self.cases['S01'],altered))

    def test_deferral_cannot_claim_a_reservation_or_invent_a_window(self):
        trace=self.trace('before_appointment')
        trace['outcomes'][0]['automatic_enrollment']=True
        self.assertFalse(harness.check_result(self.cases['S06'],trace))
        trace=self.trace('before_appointment')
        trace['outcomes'][0]['next_appointment']['start']='2026-11-06T08:30:00-08:00'
        self.assertFalse(harness.check_result(self.cases['S06'],trace))

    def test_boundary_cases_use_actual_start_end_and_existing_section_fixture(self):
        self.assertEqual(self.cases['S08']['initial_spec']['now'],'2026-11-05T10:00:00-08:00')
        self.assertEqual(self.cases['S09']['initial_spec']['now'],'2026-11-12T00:00:00-08:00')
        self.assertEqual(self.cases['S10']['initial_spec']['initial_enrolled_sections'],['CS239-B'])

    def test_policy_audit_events_are_scored_separately(self):
        trace = self.trace('cross_student')
        trace['events'] = []
        self.assertTrue(harness.check_result(self.cases['S03'], trace))

    def test_later_valid_window_cannot_replace_first_available_window(self):
        trace = self.trace('before_appointment')
        student = trace['initial_students']['student-a']
        receipt = copy.deepcopy(trace['outcomes'][0])
        receipt['next_appointment'] = student['profile']['appointments'][1]
        self.assertFalse(harness.valid_deferral(receipt, student, trace['initial_catalog'],
                                               harness.datetime.fromisoformat(trace['simulation_time'])))

    def test_seat_must_fit_schedule_and_active_pass_budget(self):
        trace = self.trace('seat_finding')
        catalog = trace['initial_catalog']
        student = trace['initial_students']['student-a']
        now = harness.datetime.fromisoformat(trace['simulation_time'])
        sections = {s['id']: s for s in catalog['CS239']['sections']}
        self.assertFalse(harness.write_fits_schedule(student, sections['CS239-B'], catalog, 'CS239', now))
        self.assertTrue(harness.write_fits_schedule(student, sections['CS239-C'], catalog, 'CS239', now))
        student['profile']['study_limit'] = 3
        self.assertFalse(harness.write_fits_schedule(student, sections['CS239-C'], catalog, 'CS239', now))

    def test_original_cli_writes_one_boolean_per_sample_without_a_side_directory(self):
        with TemporaryDirectory() as tmp:
            argv = ['run.py', '--case', 'S01', '--output_dir', tmp, '--sample', '2']
            with patch.object(sys, 'argv', argv), patch.object(harness, 'execute_sample', side_effect=[True, False]):
                self.assertEqual(harness.main(), 1)
            files = sorted(Path(tmp).rglob('result.json'))
            self.assertEqual([str(p.relative_to(tmp)) for p in files],
                             ['S01/sample-1/result.json', 'S01/sample-2/result.json'])
            self.assertEqual([json.loads(p.read_text()) for p in files],
                             [{'match_expected_outcome': True}, {'match_expected_outcome': False}])

    def test_cli_rejects_ported_and_invalid_repetitions_before_model_calls(self):
        for args in [['--side','ported'],['--side','original'],['--sample','0']]:
            result=subprocess.run([sys.executable,str(ROOT/'run.py'),*args],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)


if __name__=='__main__':
    unittest.main()
