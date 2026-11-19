import unittest
from pathlib import Path

from phase2.staged_port import require_unique_functions


class InventoryTests(unittest.TestCase):
    def test_one_function_cannot_receive_two_boundary_ids(self):
        entries = [
            dict(id='context', file='phase1/app.py', symbol='Agent.run'),
            dict(id='reply', file='./phase1/app.py', symbol='Agent.run'),
        ]
        with self.assertRaisesRegex(ValueError, "context.*reply.*Agent.run"):
            require_unique_functions({'boundaries': entries}, Path.cwd())

    def test_functions_with_distinct_qualified_names_or_files_can_share_a_short_name(self):
        entries = [
            dict(id='agent', file='phase1/app.py', symbol='Agent.run'),
            dict(id='application', file='phase1/app.py', symbol='EnrollmentApplication.run'),
            dict(id='other', file='other/app.py', symbol='Agent.run'),
        ]
        require_unique_functions({'boundaries': entries}, Path.cwd())
