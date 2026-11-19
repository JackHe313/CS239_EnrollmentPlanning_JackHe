"""Count the paired experiment and verify its required on-disk evidence."""
import argparse
import json
from pathlib import Path
import sys


def check_trajectory(directory, case_id):
    with (directory / 'trajectory.json').open() as stream:
        timeline = json.load(stream)
    if timeline['format'] != 'policyscope-timeline' or timeline['title'] != case_id:
        raise ValueError('trajectory format or scenario differs')
    events = timeline.pop('events')
    with (directory / 'trajectory.jsonl').open() as stream:
        if json.loads(stream.readline()) != timeline:
            raise ValueError('JSON and JSONL headers differ')
        for sequence, event in enumerate(events):
            if event['sequence'] != sequence or json.loads(stream.readline()) != event:
                raise ValueError(f'timeline differs at event {sequence}')
        if stream.readline():
            raise ValueError('extra JSONL events')
    observations = [event.get('data', {}).get('observation') for event in events]
    if not observations or observations[0] != 'run_start' or observations[-1] != 'run_end':
        raise ValueError('missing framework run boundary')


def summarize(cases, root):
    expected = {Path(case['id'], side, f'sample-{sample}', 'result.json')
                for case in cases for side in ('original', 'ported') for sample in range(1, 11)}
    actual = {path.relative_to(root) for path in root.rglob('result.json')}
    if expected != actual:
        raise ValueError(f'expected exactly 200 result files: {len(expected - actual)} missing, '
                         f'{len(actual - expected)} unexpected')
    totals = {'original': 0, 'ported': 0}
    rows = []
    for case in cases:
        counts = {}
        for side in totals:
            passed = 0
            for sample in range(1, 11):
                directory = root / case['id'] / side / f'sample-{sample}'
                try:
                    result = json.loads((directory / 'result.json').read_text())
                    if (not isinstance(result, dict) or set(result) != {'match_expected_outcome'}
                            or type(result['match_expected_outcome']) is not bool):
                        raise ValueError('invalid result schema')
                    if side == 'ported':
                        check_trajectory(directory, case['id'])
                    passed += result['match_expected_outcome']
                except (OSError, ValueError, KeyError, TypeError) as error:
                    raise ValueError(f'{directory}: {error}') from error
            counts[side] = passed
            totals[side] += passed
        rows.append((case['id'], counts))
    return rows, totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path, nargs='?', default=Path('runs'))
    args = parser.parse_args()
    cases = json.loads((Path(__file__).resolve().parents[1] / 'test_cases.json').read_text())['cases']
    try:
        rows, totals = summarize(cases, args.runs)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print('| Scenario | Original | Ported |\n| --- | ---: | ---: |')
    for case_id, counts in rows:
        print(f"| {case_id} | {counts['original']}/10 | {counts['ported']}/10 |")
    print(f"| Total | {totals['original']}/100 | {totals['ported']}/100 |")
    return 0


if __name__ == '__main__':
    sys.exit(main())
