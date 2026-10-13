"""Pinned official label/evidence scoring; no model calls or predictor changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

URL = 'https://gitlab.com/ifsoftware/hackapertus-starter.git'
COMMIT = '5e6957729b77a126006049305ad1ef241211a5b4'
SAFE_THRESHOLDS = {'A': 0.60, 'B': 0.75}
MINIMUM_GAIN = 0.02


def grade(repo, python, predictions, expected, cases):
    sha = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    if sha != COMMIT:
        raise ValueError('OFFICIAL_EVALUATOR_COMMIT_CHANGED')
    changed = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--', 'evaluate.py'], text=True)
    if changed:
        raise ValueError('OFFICIAL_EVALUATOR_MODIFIED')
    evaluator = repo / 'evaluate.py'
    with tempfile.TemporaryDirectory(prefix='ost-official-grade-') as tmp:
        result_path = Path(tmp) / 'report.json'
        command = [str(python), '-B', str(evaluator), '--predictions', str(predictions),
                   '--expected', str(expected), '--cases', str(cases), '--json', str(result_path)]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        report = json.loads(result_path.read_text())
    a, b = report['tasks']['A']['macro_f1'], report['tasks']['B']['macro_f1']
    return {
        'official_source_url': URL,
        'official_commit': COMMIT,
        'official_evaluate_sha256': hashlib.sha256(evaluator.read_bytes()).hexdigest(),
        'official_report': report,
        'classification_objective': {'name': 'Q_label_norm',
                                     'formula': '(0.30 * F1_A + 0.28 * F1_B) / 0.58',
                                     'value': (0.30 * a + 0.28 * b) / 0.58,
                                     'minimum_gain': MINIMUM_GAIN,
                                     'is_official_total_score': False},
        'primary_evidence_objective': {'name': 'Task A Hit@5',
                                       'value': report['tasks']['A'].get('evidence_score'),
                                       'weight_in_SA': 0.20},
        'Q_task_log_only': 0.6 * a + 0.4 * b,
        'official_label_component': {'formula': '0.30 * F1_A + 0.28 * F1_B',
                                     'value': 0.30 * a + 0.28 * b, 'maximum': 0.58},
        'official_label_component_normalized': {'formula': '(0.30 * F1_A + 0.28 * F1_B) / 0.58',
                                                'value': (0.30 * a + 0.28 * b) / 0.58},
        'objective_confirmed': True,
        'safe_thresholds': SAFE_THRESHOLDS,
        'safe_passes': {task: report['tasks'][task]['macro_f1'] >= threshold
                        for task, threshold in SAFE_THRESHOLDS.items()},
        'notes': ['Unmodified official evaluator supplies label and Hit@5 calculations.',
                  'Safe B threshold 0.75 is separate from upstream CLI threshold 0.70.',
                  'Internal fallback/error metadata does not override official label_of.',
                  'Evidence/validity/tokens/time regressions require review before adoption.'],
    }


def main():
    parser = argparse.ArgumentParser()
    for name in ['official-repo', 'python', 'predictions', 'expected', 'cases', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = grade(args.official_repo, args.python, args.predictions, args.expected, args.cases)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'classification_objective': result['classification_objective'],
                      'safe_passes': result['safe_passes']}))


if __name__ == '__main__':
    main()
