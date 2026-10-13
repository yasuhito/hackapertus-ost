#!/usr/bin/env python3
"""Explicit approved source-only C batch. Default is offline preparation."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time

SOURCE_PATHS = ['track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format']
SUFFIXES = ['start.txt', 'end.txt', 'run.log', 'stderr.log', 'exit-code.txt',
            'provenance.json', 'prepare.log']


def positive(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError('positive integer required')
    return n


def write_target(value):
    p = Path(value)
    if any(x not in ('.', '..') and x.endswith(('.', ' ')) for x in p.parts):
        raise ValueError('AMBIGUOUS_WRITE_PATH')
    p = p.resolve()
    if any(x.endswith(('.', ' ')) for x in p.parts):
        raise ValueError('AMBIGUOUS_WRITE_PATH')
    return p


def prompt_constants(text):
    """Evaluate only literal strings, string lists, joins and concatenation; no exec."""
    values = {}
    names = {'SYSTEM', 'NEUTRAL_GUARD', 'PARAPHRASE_GUARD', 'FINAL_VERIFICATION'}
    def expr(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.List):
            return [expr(x) for x in node.elts]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return expr(node.left) + expr(node.right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'join' and len(node.args) == 1 and not node.keywords):
            separator = expr(node.func.value)
            items = expr(node.args[0])
            if isinstance(separator, str) and isinstance(items, list):
                return separator.join(items)
        raise ValueError('UNSAFE_PROMPT_CONSTANT')
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ValueError('UNSAFE_PROMPT_ASSIGNMENT')
            values[node.targets[0].id] = expr(node.value)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            if not isinstance(node.op, ast.Add):
                raise ValueError('UNSAFE_PROMPT_ASSIGNMENT')
            values[node.target.id] += expr(node.value)
    return values


def designated(job):
    return [job] + [Path(str(job) + '-' + suffix) for suffix in SUFFIXES]


def refuse_existing(jobs):
    paths = [p for job in jobs for p in designated(job)]
    if len(set(paths)) != len(paths) or any(p.exists() or p.is_symlink() for p in paths):
        raise ValueError('PREEXISTING_DESIGNATED_PATH: preserve jobs/fences; no execution')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--python', type=Path, required=True)
    p.add_argument('--count', type=positive, required=True)
    p.add_argument('--start-index', type=positive, default=1)
    targets = p.add_mutually_exclusive_group(required=True)
    targets.add_argument('--prefix')
    targets.add_argument('--jobs', nargs='+')
    p.add_argument('--prompt-file', type=Path, help='UTF-8 SYSTEM addition, not Python')
    p.add_argument('--metadata', type=Path, help='baseline_prompt_sha256 and candidate_prompt_sha256')
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--user-run', action='store_true')
    p.add_argument('--approval', help='explicit user approval reference documented in runbook')
    args = p.parse_args()
    if args.user_run and (args.prepare_only or not args.approval):
        p.error('live requires --user-run --approval; not --prepare-only')
    if bool(args.prompt_file) != bool(args.metadata):
        p.error('--prompt-file and --metadata must be supplied together')
    repo = args.repo.resolve()
    # Preserve the venv executable path; resolve() loses pyvenv.cfg/site-packages.
    python = args.python.absolute()
    indices = list(range(args.start_index, args.start_index + args.count))
    jobs = [write_target(x) for x in (args.jobs or [f'{args.prefix}-r{i}' for i in indices])]
    if len(jobs) != args.count:
        p.error('job count must equal --count')
    refuse_existing(jobs)  # Whole batch, before even preparation.
    original = (repo / 'track_2a/src/predict.py').read_bytes()
    # Archive only tracked source, never gold/evals or broad repo contents.
    archive = subprocess.check_output(['git', 'archive', 'HEAD', *SOURCE_PATHS], cwd=repo)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    # CLI-only bugfix may be uncommitted while owner validates the patch.
    runner = repo / 'track_2a/dev/format/run_comparison.py'
    fixture = repo / 'track_2a/dev/cscs/fixtures/cases-portable.jsonl'
    inputs = [json.loads(line) for line in fixture.read_text().splitlines()]
    pdfs = sorted({(repo / 'booklets' / Path(r['booklet']['path']).name).resolve()
                   for r in inputs if 'booklet' in r})
    if len(inputs) != 54 or len(pdfs) != 6 or not all(x.is_file() for x in pdfs):
        raise ValueError('APPROVED_54_SIX_PDFS_REQUIRED')
    added = args.prompt_file.read_text() if args.prompt_file else ''
    metadata = json.loads(args.metadata.read_text()) if args.metadata else None
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    prepared = []
    # Preflight every workspace before the first live request.
    for index, job in zip(indices, jobs):
        workspace = Path(tempfile.mkdtemp(prefix=f'ost-source-r{index}-'))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(workspace, filter='data')
        (workspace / 'booklets').mkdir()
        for pdf in pdfs:
            (workspace / 'booklets' / pdf.name).symlink_to(pdf)
        (workspace / 'track_2a/dev/format/run_comparison.py').write_bytes(runner.read_bytes())
        target = workspace / 'track_2a/src/predict.py'
        if target.read_bytes() != original:
            raise ValueError('PRODUCTION_DIFFERS_FROM_ARCHIVE')
        base = prompt_constants(target.read_text())['SYSTEM']
        if added:
            anchor = 'SYSTEM += "\\n\\n" + NEUTRAL_GUARD + "\\n\\n" + PARAPHRASE_GUARD'
            text = target.read_text()
            if text.count(anchor) != 1:
                raise ValueError('PROMPT_ANCHOR_CHANGED')
            target.write_text(text.replace(anchor, anchor + '\nSYSTEM += ' + repr('\n\n' + added)))
        sha = hashlib.sha256(prompt_constants(target.read_text())['SYSTEM'].encode()).hexdigest()
        if metadata and (metadata['baseline_prompt_sha256'] != hashlib.sha256(base.encode()).hexdigest()
                         or metadata['candidate_prompt_sha256'] != sha):
            raise ValueError('PROMPT_SHA_CHANGED')
        command = [str(python), '-B', 'track_2a/dev/format/run_comparison.py',
                   '--strategy', 'C', '--repeat', str(index), '--job', str(job)]
        result = subprocess.run(command + ['--prepare-only'], cwd=workspace, env=env,
                                capture_output=True, text=True)
        if result.returncode:
            raise ValueError('PREPARE_FAILED: no live request')
        prepared.append((index, job, workspace, command, sha, result.stdout))
    if not args.user_run:
        print(json.dumps({'prepared': [{'index': i, 'job': str(j), 'workspace': str(w),
                          'prompt_sha256': sha, 'preflight': json.loads(out)}
                         for i, j, w, cmd, sha, out in prepared], 'remote_calls': 0, 'credential_reads': 0}))
        return
    refuse_existing(jobs)
    for index, job, workspace, command, sha, preflight in prepared:
        job.parent.mkdir(parents=True, exist_ok=True)
        def save(suffix, value):
            with Path(str(job) + '-' + suffix).open('x') as f:
                f.write(value)
        provenance = {'version': 1, 'repeat': index, 'job': str(job), 'workspace': str(workspace),
                      'archive_commit': commit, 'approval': args.approval, 'prompt_sha256': sha,
                      'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
                      'candidate_source_changes': ['track_2a/src/predict.py'] if added else [],
                      'cli_only_overlay': 'track_2a/dev/format/run_comparison.py',
                      'start': None, 'end': None, 'exit': None}
        save('provenance.json', json.dumps(provenance, indent=2) + '\n')
        save('prepare.log', preflight)
        start = time.time()
        save('start.txt', str(start) + '\n')
        with Path(str(job) + '-run.log').open('x') as stdout, Path(str(job) + '-stderr.log').open('x') as stderr:
            result = subprocess.run(command + ['--user-run'], cwd=workspace, env=env, stdout=stdout, stderr=stderr)
        end = time.time()
        save('end.txt', str(end) + '\n')
        save('exit-code.txt', str(result.returncode) + '\n')
        provenance.update(start=start, end=end, exit=result.returncode,
                          production_unchanged=(repo / 'track_2a/src/predict.py').read_bytes() == original)
        Path(str(job) + '-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        if result.returncode or not provenance['production_unchanged']:
            raise ValueError('STOP: preserve job/fences; no retry or next repeat')
        print(json.dumps({'index': index, 'job': str(job), 'exit': result.returncode}))


if __name__ == '__main__':
    main()
