"""Offline checks for the exact Oct 27 archive contract and agent descriptions."""
import json
from pathlib import Path
import re
import tarfile
import tempfile
import unittest

from scripts.course_submission import (
    ROOT, check, description_files, generated_descriptions, package,
    safe_identity, verify_archive, write_archive,
)
from phase1.app import ADVISOR_PROMPT, REGISTRAR_PROMPT


class CourseSubmissionTests(unittest.TestCase):
    def test_descriptions_and_traces_are_current(self):
        files=check()
        self.assertIn(ROOT/'tools.md',files)
        self.assertNotIn(ROOT/'.env',files)

    def test_actual_prompts_are_preserved_byte_for_byte(self):
        generated=generated_descriptions()
        for name,prompt in [('advisor',ADVISOR_PROMPT),('registrar',REGISTRAR_PROMPT)]:
            text=generated[ROOT/'agents'/f'{name}.md']
            self.assertEqual(re.search(r'```text\n([\s\S]*?)```',text).group(1),prompt)

    def test_both_archives_have_required_layout_and_same_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=package('Example','EnrollmentPlanning','123456789',Path(directory))
            identities=[verify_archive(path)['identity'] for path in paths]
            self.assertEqual(identities[0],identities[1])
            with tarfile.open(paths[0],'r:gz') as archive:
                names=set(archive.getnames())
                self.assertIn('EnrollmentPlanning/app.md',names)
                self.assertIn('EnrollmentPlanning/policy.md',names)
                self.assertIn('EnrollmentPlanning/agents/advisor.md',names)
                self.assertIn('EnrollmentPlanning/episodes/catalog_injection.md',names)
                self.assertFalse(any(name.startswith('src/') for name in names))
            with tarfile.open(paths[1],'r:gz') as archive:
                names=set(archive.getnames())
                for name in ['src/README.md','src/phase1/app.py','src/traces/phase1/compliant.json',
                             'src/tests/test_llm.py','src/scripts/course_submission.py','tests/README.md',
                             'EnrollmentPlanning/policy.md']:
                    self.assertIn(name,names)
                self.assertFalse(any(Path(name).name=='.env' for name in names))
            with self.assertRaises(ValueError):
                package('Example','EnrollmentPlanning','123456789',Path(directory))

    def test_invalid_identity_cannot_escape_output_directory(self):
        for name,app,uid in [('../bad','App','123456789'),('Name','../App','123456789'),
                             ('Name','App','123'),('Name','App','not-a-uid')]:
            with self.subTest(name=name,app=app,uid=uid), self.assertRaises(ValueError):
                safe_identity(name,app,uid)

    def test_archive_writer_rejects_path_traversal_and_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'bad.tar.gz'
            with self.assertRaises(ValueError):
                write_archive(target,{'../outside':b'bad'},safe_identity('A','B','123456789'))
            credential=('sk-'+'x'*30).encode()
            with self.assertRaises(ValueError):
                write_archive(target,{'safe':credential},safe_identity('A','B','123456789'))

    def test_policy_numbers_are_consecutive_separate_paragraphs(self):
        paragraphs=(ROOT/'policy.md').read_text().strip().split('\n\n')
        self.assertGreaterEqual(len(paragraphs),3)
        self.assertEqual([int(re.match(r'P(\d+)\.',p).group(1)) for p in paragraphs],list(range(1,len(paragraphs)+1)))


if __name__=='__main__':
    unittest.main()
