# Test cases

The runnable application tests are in tests/test_*.py in the repository. In the
whole course archive, they are under src/tests/test_*.py; the top-level tests/
directory contains this test-case guide. Run all commands from src/ after extracting
the whole archive, or from the repository root in a checkout.

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s submission_tests -v
python3 -m phase1.submission
python3 scripts/course_submission.py --check
```

- test_llm.py: independent roles, model/tool-result feedback, snapshots, unsafe
  baseline outcomes, partial completion, malformed outputs, limits, interruption,
  credential handling, transport behavior, and overwrite protection. Responses are
  explicit offline fixtures, not evidence of actual model behavior.
- test_registration.py: appointment groups/AP treatment, fixed assigned times,
  graduate single-pass behavior, first/second pass unit budgets, timezone/window
  boundaries, deferral, full/conflicting/usable sections, seat loss after a search,
  and course-versus-section ID recovery.
- test_evidence.py: replay of real saved traces and rejection of tampered calls,
  reads, final state, mislabeled fixtures, or incomplete execution evidence.
- submission_tests/: archive layout, exact prompts, tool coverage, consecutive
  policy numbering, safe file allowlisting, and archive manifest verification.

All tests and verification commands are offline and need no API key. Live agent
runs require network access and the student's own API quota. The source-matched
seven JSON traces are inspected separately by the submission checker, which also
verifies readable Markdown views, replayed state, and credential exclusion.
