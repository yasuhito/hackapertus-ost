#!/usr/bin/env python3
"""Future v4/v5 batch only. Offline by default; execution requires explicit scoped approval."""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'
PYTHON = '/tmp/hackapertus-ost-contract/.venv/bin/python'
ENV = dict(os.environ, PI_PACKAGE_ROOT='/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent', PI_SUBAGENTS_ROOT='/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents', PYTHONDONTWRITEBYTECODE='1')
PROMPTS = ROOT / 'evals/c-system-prompt/prompts'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def system(text):
    ns = {}
    for node in ast.parse(text).body:
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'SYSTEM', 'NEUTRAL_GUARD', 'FINAL_VERIFICATION', 'PARAPHRASE_GUARD'} for t in node.targets)) or (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == 'SYSTEM'):
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<prompt constants>', 'exec'), ns)
    return ns['SYSTEM']


def refuse_batch(version):
    # Include every sidecar, including STOP/fences, before any request.
    for repeat in range(1, 6):
        if list(OUT.glob(f'prompt-C-{version}-r{repeat}*')):
            raise SystemExit('PREEXISTING_CANDIDATE_PATH: NO EXECUTION OR RESUME')
    if (OUT / f'hillclimb-{version}-analysis').exists():
        raise SystemExit('PREEXISTING_CANDIDATE_ANALYSIS: NO EXECUTION')


def validate_metadata(version, meta, execute):
    trials = {'cases': 54, 'repeats': 5, 'configs': 1}
    if meta.get('version') != version or meta.get('proposed_trials') != trials:
        raise SystemExit('REFUSED: candidate version/proposed_trials must match 54 x 5 x 1')
    if execute:
        # A candidate-specific machine-readable scope cannot inherit v3 permission.
        scope = {'candidate': version, 'cases': 54, 'repeats': 5, 'configs': 1}
        if (meta.get('inference_approved') is not True
                or meta.get('approved_trials') != trials
                or meta.get('approval_scope') != scope):
            raise SystemExit('REFUSED: explicit selected-candidate approval and fixed approved_trials/scope required')


def sources(m):
    return {k[k.index('track_2a/'):]: v for k, v in m['sources'].items()}


def audit(manifest, baseline, mapping):
    assert len(manifest['frozen']) == len(baseline['frozen']) == 54
    for key in baseline:
        if key not in {'sources', 'frozen'}:
            assert manifest[key] == baseline[key], 'PROTOCOL_CHANGED: ' + key
    bs, cs = sources(baseline), sources(manifest)
    assert bs.keys() == cs.keys()
    assert [k for k in bs if bs[k] != cs[k]] == ['track_2a/src/predict.py'], 'NON_PROMPT_SOURCE_CHANGE'
    for actual, old in zip(manifest['frozen'], baseline['frozen']):
        case = dict(old['case'])
        if 'booklet' in case:
            case['booklet'] = {**case['booklet'], 'path': mapping[case['booklet']['path']]}
        assert actual['case'] == case, 'CASE_CHANGED'
        assert actual['messages'][1:] == old['messages'][1:], 'MODEL_INPUT_CHANGED'
        assert actual['messages'][0]['content'].endswith('\n\n' + baseline['protocol_reminder'])
        for key in ('pages', 'candidate_ids', 'schema_sha256'):
            assert actual[key] == old[key], 'FROZEN_INPUT_CHANGED: ' + key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, choices=('v3', 'v4', 'v5'))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare-only', action='store_true')
    modes.add_argument('--execute-approved', action='store_true', help='Only after human approval for this candidate, exactly 54 x 5 x 1')
    args = parser.parse_args()
    version = args.candidate
    if version == 'v3':
        raise SystemExit('REFUSED: archived v3 was evaluated; no preparation, execution or resume')
    refuse_batch(version)
    if not all((PROMPTS / name).is_file() for name in (f'{version}.json', f'{version}-system.txt')):
        raise SystemExit('CANDIDATE_ARTIFACTS_MISSING: selected metadata/system required; no requests or jobs created')
    meta = json.loads((PROMPTS / f'{version}.json').read_text())
    validate_metadata(version, meta, args.execute_approved)
    candidate = (PROMPTS / f'{version}-system.txt').read_text()
    assert digest(candidate.encode()) == meta['candidate_prompt_sha256']
    assert digest((PROMPTS / 'v0-system.txt').read_bytes()) == meta['baseline_prompt_sha256']
    for previous in range(1, int(version[1:])):
        prior = json.loads((PROMPTS / f'v{previous}.json').read_text())
        prior_hash = digest((PROMPTS / f'v{previous}-system.txt').read_bytes())
        assert prior_hash == prior['candidate_prompt_sha256'], 'PREVIOUS_PROMPT_HASH_CHANGED'
        assert meta['candidate_prompt_sha256'] != prior_hash, 'DUPLICATE_CANDIDATE'
    original = (ROOT / 'track_2a/src/predict.py').read_bytes()
    archive = subprocess.check_output(['/usr/bin/git', 'archive', 'HEAD', 'track_2a/src', 'track_2a/dev/cscs', 'track_2a/dev/format'], cwd=ROOT)
    baseline = json.loads((OUT / 'format-C-r5/manifest.json').read_text())
    provenance = json.loads((OUT / 'preparation-provenance.json').read_text())
    pdfs = {x['case']['booklet']['path'] for x in baseline['frozen'] if 'booklet' in x['case']}
    assert len(pdfs) == 6 and pdfs == set(provenance['pdf_mapping'])
    workroot = OUT / 'workspaces'
    workroot.mkdir(parents=True, exist_ok=True)
    workspaces = []
    # Preflight the entire batch before execution, never create designated jobs offline.
    for repeat in range(1, 6):
        workspace = Path(tempfile.mkdtemp(prefix=f'{version}-r{repeat}-', dir=workroot))
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(workspace, filter='data')
        (workspace / 'booklets').mkdir()
        (workspace / 'output/cscs/tmp').mkdir(parents=True)
        mapping = {}
        for old, local in provenance['pdf_mapping'].items():
            source = ROOT / local
            assert source.resolve().is_relative_to(ROOT) and not source.is_symlink()
            target = workspace / 'booklets' / Path(old).name
            shutil.copyfile(source, target)
            assert digest(target.read_bytes()) == digest(source.read_bytes())
            mapping[old] = str(target)
        target = workspace / 'track_2a/src/predict.py'
        text = target.read_text()
        assert digest(system(text).encode()) == meta['baseline_prompt_sha256'], 'ARCHIVE_V0_CHANGED'
        anchor = 'SYSTEM += "\\n\\n" + NEUTRAL_GUARD + "\\n\\n" + PARAPHRASE_GUARD'
        assert text.count(anchor) == 1
        target.write_text(text.replace(anchor, anchor + '\nSYSTEM = ' + repr(candidate)))
        assert digest(system(target.read_text()).encode()) == meta['candidate_prompt_sha256']
        env = dict(ENV, TMPDIR=str(workspace / 'output/cscs/tmp'))
        if not args.execute_approved:
            # Offline preparation must not receive credentials.
            for key in ('API_KEY', 'BASE_URL', 'OPENAI_API_KEY'):
                env.pop(key, None)
        command = [PYTHON, '-B', 'track_2a/dev/format/run_comparison.py', '--prepare-only', '--strategy', 'C']
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True, text=True)
        (workspace / 'prepare.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('PREPARE_FAILED: NO API REQUEST; SEE WORKSPACE prepare.log')
        # Existing prepare-only prints only a hash. Capture actual preparation separately,
        # using the unchanged runner's prepare(), without invoking main or Transport.
        export = "import runpy,json; m=runpy.run_path('track_2a/dev/format/run_comparison.py'); m['legacy'].c.protect(); open('prepared.json','w').write(json.dumps(m['prepare']('C')))"
        result = subprocess.run([PYTHON, '-B', '-c', export], cwd=workspace, env=env, capture_output=True, text=True)
        (workspace / 'audit.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise SystemExit('PREPARED_ARTIFACT_FAILED: NO API REQUEST')
        manifest = json.loads((workspace / 'prepared.json').read_text())
        audit(manifest, baseline, mapping)
        assert all(x['messages'][0]['content'] == candidate + '\n\n' + baseline['protocol_reminder'] for x in manifest['frozen'])
        workspaces.append((workspace, env, manifest, mapping))
    assert (ROOT / 'track_2a/src/predict.py').read_bytes() == original
    if not args.execute_approved:
        print(f'Prepared {version}: 5 isolated workspaces, 54 cases each; hashes/inputs/pages/IDs/source audit passed; zero requests. No candidate jobs created.')
        return
    refuse_batch(version)
    for repeat, (workspace, env, prepared, mapping) in enumerate(workspaces, 1):
        # Revocation or artifact changes during preparation must stop before requests.
        current_meta = json.loads((PROMPTS / f'{version}.json').read_text())
        validate_metadata(version, current_meta, True)
        assert current_meta == meta, 'APPROVAL_OR_METADATA_CHANGED'
        assert digest((PROMPTS / f'{version}-system.txt').read_bytes()) == meta['candidate_prompt_sha256'], 'CANDIDATE_PROMPT_CHANGED'
        for previous in range(1, int(version[1:])):
            prior = json.loads((PROMPTS / f'v{previous}.json').read_text())
            assert digest((PROMPTS / f'v{previous}-system.txt').read_bytes()) == prior['candidate_prompt_sha256'], 'PREVIOUS_PROMPT_HASH_CHANGED'
        job = OUT / f'prompt-C-{version}-r{repeat}'
        prefix = OUT / f'prompt-C-{version}-r{repeat}'
        # Refuse future batch paths too, while preserving completed repeats.
        for future in range(repeat, 6):
            assert not list(OUT.glob(f'prompt-C-{version}-r{future}*')), 'PREEXISTING_BATCH_PATH'
        with Path(str(prefix) + '-start.txt').open('x') as f:
            f.write(str(time.time()) + '\n')
        with Path(str(prefix) + '-run.log').open('x') as stdout, Path(str(prefix) + '-stderr.log').open('x') as stderr:
            result = subprocess.run([PYTHON, '-B', 'track_2a/dev/format/run_comparison.py', '--user-run', '--strategy', 'C', '--repeat', '1', '--job', str(job)], cwd=workspace, env=env, stdout=stdout, stderr=stderr)
        for suffix, value in (('end.txt', time.time()), ('exit-code.txt', result.returncode)):
            with Path(str(prefix) + '-' + suffix).open('x') as f:
                f.write(str(value) + '\n')
        assert (ROOT / 'track_2a/src/predict.py').read_bytes() == original
        if result.returncode:
            raise SystemExit('CANDIDATE_STOP: PRESERVE FENCES; NO RETRY OR NEXT REPEAT')
        assert json.loads((job / 'manifest.json').read_text()) == prepared
        assert json.loads((job / 'summary.json').read_text())['status'] == 'completed'
        Path(str(prefix) + '-provenance.json').write_text(json.dumps({'workspace': str(workspace), 'version': version, 'repeat': repeat, 'prompt_sha256': meta['candidate_prompt_sha256'], 'pdf_mapping': mapping, 'production_unchanged': True, 'archive_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'only_source_change': 'track_2a/src/predict.py SYSTEM assignment'}, indent=2) + '\n')
        print(f'{version} repeat {repeat}: completed', flush=True)


if __name__ == '__main__':
    main()
