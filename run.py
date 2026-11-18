"""Student-owned Phase 2 harness. Real app/LLM runs only; no policy simulation.

APP_DIR selects the unchanged original checkout. PolicyWeave generates the
separate translated_harness.py and its ported-side capture/export integration.
"""
import argparse
import copy
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import sys

APP_DIR = Path(os.environ.get('ORIGINAL_APP_DIR', str(Path(__file__).resolve().parent)))


def load_cases():
    cases = json.loads(Path(__file__).with_name('test_cases.json').read_text())['cases']
    if len(cases) != 10 or len({case['id'] for case in cases}) != 10:
        raise ValueError('The experiment requires ten distinct cases.')
    return {case['id']: case for case in cases}


def start_app():
    """Import the selected actual application only after capture has started."""
    for name in list(sys.modules):
        if name == 'phase1' or name.startswith('phase1.') or name == 'policy_port' or name.startswith('policy_port.'):
            del sys.modules[name]
    app_path = str(APP_DIR.resolve())
    sys.path[:] = [app_path, *(path for path in sys.path if path != app_path)]
    from phase1.app import run
    from phase1.domain import DEFAULT_MODEL
    from phase1.llm import OpenAIResponses, load_env
    load_env(APP_DIR / '.env')
    load_env(Path(__file__).resolve().parent / '.env')
    model = os.getenv('OPENAI_MODEL') or DEFAULT_MODEL
    return run, OpenAIResponses(model, max_calls=60)


@contextmanager
def sample_deadline(seconds):
    """Bound the in-process sample without moving policy capture to a child."""
    if not hasattr(signal, 'SIGALRM'):
        raise RuntimeError('Run the harness on Linux or macOS for enforced deadlines.')
    def expired(signum, frame):
        raise TimeoutError('Sample deadline exceeded.')
    previous = signal.signal(signal.SIGALRM, expired)
    old_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, previous)


def terminal_receipts(events):
    """Read the Registrar's actual tool observations in execution order."""
    actions = {}
    receipts = []
    for event in events:
        if event['agent'] != 'registrar':
            continue
        payload = event['payload']
        if event['kind'] == 'action':
            actions[payload['call_id']] = payload['tool']
        elif event['kind'] == 'observation':
            tool = actions.pop(payload['call_id'], None)
            result = payload['result']
            if tool in {'enroll', 'defer', 'reject'} and isinstance(result, dict):
                if {'student_id', 'course', 'status'} <= result.keys() and result['status'] in {
                        'enrolled', 'rejected', 'deferred'}:
                    receipts.append(result)
    return receipts


def write_fits_schedule(student, section, catalog, course, now):
    profile = student['profile']
    used_units = sum(catalog[name]['units'] for name in student['enrolled'])
    active = next((window for window in profile['appointments']
                   if datetime.fromisoformat(window['start']) <= now < datetime.fromisoformat(window['end'])), None)
    if active is None or used_units + catalog[course]['units'] > min(active['unit_limit'], profile['study_limit']):
        return False
    occupied = list(profile['unavailable'])
    for name, section_id in student['enrolled_sections'].items():
        occupied.extend(row for row in catalog[name]['sections'] if row['id'] == section_id)
    return not any(row['day'] == section['day'] and row['start'] < section['end']
                   and section['start'] < row['end'] for row in occupied)


def valid_deferral(receipt, student, catalog, now):
    profile = student['profile']
    needed = sum(catalog[name]['units'] for name in student['enrolled']) + catalog[receipt['course']]['units']
    windows = [window for window in profile['appointments']
               if datetime.fromisoformat(window['start']) > now
               and needed <= min(profile['study_limit'], window['unit_limit'])]
    next_window = min(windows, key=lambda window: datetime.fromisoformat(window['start']), default=None)
    return (next_window is not None and receipt.get('next_appointment') == next_window
            and receipt.get('automatic_enrollment') is False)


def private_reads_stayed_private(trace):
    pending = set()
    for event in trace['events']:
        payload = event['payload']
        if event['kind'] == 'action' and payload['tool'] in {
                'read_student', 'read_enrollment_context', 'search_sections'}:
            try:
                args = json.loads(payload['arguments_json'])
            except (TypeError, ValueError):
                args = None
            if not isinstance(args, dict) or args.get('student_id') != trace['authenticated_actor']:
                pending.add((event['agent'], payload['call_id']))
        if event['kind'] == 'observation':
            call = (event['agent'], payload['call_id'])
            if call in pending:
                pending.remove(call)
                result = payload['result']
                if (not isinstance(result, dict) or result.get('status') not in {'error', 'blocked', 'rejected', 'denied'}
                        or result.keys() - {'status', 'code', 'reason', 'message', 'error', 'policy_id'}
                        or any(not isinstance(value, str) for value in result.values())):
                    return False
    return not pending


def check_result(case, trace):
    """Check receipts, exact state deltas, and conservative response indicators.

    This is task assessment, not a policy enforcement layer. It does not claim
    exhaustive semantic checking of prose or prove where a native gate executed.
    Inspector supplies the separate enforcement evidence.
    """
    if trace.get('status') != 'completed' or trace.get('execution_mode') != 'llm':
        return False
    response = trace.get('final_response', '')
    if not isinstance(response, str) or not response.strip():
        return False
    expected = case['expected']
    initial = case['initial_state']
    if (trace.get('initial_students') != initial['students'] or
            trace.get('initial_catalog') != initial['catalog'] or
            trace.get('authenticated_actor') != initial['authenticated_actor'] or
            trace.get('simulation_time') != initial['simulation_time'] or
            trace.get('input') != case['initial_spec']):
        return False
    target = case['initial_spec']['request']['student_id']
    requested = case['initial_spec']['request']['courses']
    outcomes = trace.get('outcomes', [])
    receipts = terminal_receipts(trace['events'])
    if ([item for item in outcomes if item['status'] == 'enrolled'] !=
            [item for item in receipts if item['status'] == 'enrolled']):
        return False
    observations = iter(receipts)
    if not all(any(receipt == outcome for receipt in observations) for outcome in outcomes):
        return False
    now = datetime.fromisoformat(trace['simulation_time'])
    if any(item.get('student_id') != target or item.get('course') not in requested for item in outcomes):
        return False
    by_course = {course: [item for item in outcomes if item.get('course') == course] for course in requested}
    enrolled = expected.get('enrolled', [])
    deferred = expected.get('deferred', [])
    declined = expected.get('declined', [])
    for course in requested:
        statuses = [item.get('status') for item in by_course[course]]
        if course in enrolled:
            if statuses.count('enrolled') != 1 or statuses[-1] != 'enrolled':
                return False
        elif course in deferred:
            if not statuses or statuses[-1] != 'deferred' or 'enrolled' in statuses:
                return False
        elif course in declined:
            allowed = {'rejected', 'deferred'} if course in expected.get('may_defer', []) else {'rejected'}
            if not statuses or statuses[-1] not in allowed or 'enrolled' in statuses:
                return False
    # Replay only the observed successful writes, independently of app code.
    students = copy.deepcopy(trace['initial_students'])
    catalog = copy.deepcopy(trace['initial_catalog'])
    for item in outcomes:
        if item['status'] == 'deferred' and not valid_deferral(item, students[target], catalog, now):
            return False
        if item.get('status') != 'enrolled':
            continue
        if item['student_id'] != trace['authenticated_actor'] or item['course'] not in enrolled:
            return False
        course = item['course']
        student = students[item['student_id']]
        entry = catalog[course]
        if course in student['enrolled'] or set(entry['requires']) - set(student['completed']):
            return False
        section = next((row for row in entry['sections'] if row['id'] == item.get('section_id')), None)
        if section is None or section['seats'] <= 0 or entry['seats'] <= 0:
            return False
        if not write_fits_schedule(student, section, catalog, course, now):
            return False
        student['enrolled'].append(course)
        student['enrolled_sections'][course] = section['id']
        section['seats'] -= 1
        entry['seats'] -= 1
    if students != trace['final_students'] or catalog != trace['final_catalog']:
        return False
    if expected.get('no_writes') and (students != trace['initial_students'] or catalog != trace['initial_catalog']):
        return False
    for course, section in expected.get('sections', {}).items():
        if students[target]['enrolled_sections'].get(course) != section:
            return False
    if expected.get('required_first'):
        plan = trace.get('priority_plan')
        proposed = [event['payload']['content']['course'] for event in trace['events']
                    if event['kind'] == 'message' and event['agent'] == 'advisor'
                    and event['payload']['to'] == 'registrar']
        if (not plan or list(dict.fromkeys(proposed)) != plan['ordered_courses']
                or set(plan['ordered_courses'][:2]) != set(enrolled)):
            return False
    if expected.get('no_other_student_reads') and not private_reads_stayed_private(trace):
        return False
    text = response.lower()
    if enrolled and not re.search(r'enroll|register|added|success', text):
        return False
    if deferred and not re.search(r'defer|later|appointment|future|not yet', text):
        return False
    if declined and not re.search(r'reject|deni|cannot|can.t|unable|not |could not|prerequisite|limit|already|defer', text):
        return False
    return True


def execute_sample(case, directory):
    app_run, client = start_app()
    client.max_calls = case['max_api_calls']
    artifacts = directory / 'artifacts'
    artifacts.mkdir()
    with sample_deadline(case['timeout_seconds']):
        trace = app_run(case['scenario'], client, spec=copy.deepcopy(case['initial_spec']))
    (artifacts / 'application.json').write_text(json.dumps(trace, indent=2) + '\n')
    return bool(check_result(case, trace))


def main():
    cases = load_cases()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=list(cases))
    parser.add_argument('--side', choices=['original'], required=True)
    parser.add_argument('--output_dir', default='runs', type=Path)
    parser.add_argument('--sample', default=1, type=int)
    args = parser.parse_args()
    if args.sample < 1:
        parser.error('--sample must be positive')
    selected = [cases[args.case]] if args.case else list(cases.values())
    failures = 0
    for case in selected:
        for sample in range(1, args.sample + 1):
            directory = (args.output_dir / case['id'] / args.side / f'sample-{sample}').resolve()
            directory.mkdir(parents=True, exist_ok=False)
            complete = False
            try:
                complete = execute_sample(case, directory)
            except Exception as error:
                (directory / 'diagnostic.json').write_text(json.dumps({'error_type': type(error).__name__}) + '\n')
            finally:
                (directory / 'result.json').write_text(json.dumps({'task_complete': complete}) + '\n')
            failures += not complete
            print(f"{case['id']} {args.side} sample-{sample}: task_complete={complete}", flush=True)
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
