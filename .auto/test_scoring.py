"""Offline wiring test with saved baseline replay, NOT a candidate evaluation."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import results
import usage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'

def main():
    if len(sys.argv) != 1:
        raise SystemExit('No arguments accepted')
    with tempfile.TemporaryDirectory(prefix='scoring-replay-', dir=OUT / 'tmp') as directory:
        replay = Path(directory)
        for name in ('hillclimb-split5-date-balanced-analysis', 'hillclimb-v5-analysis', 'official-rescore-evidence'):
            shutil.copytree(OUT / name, replay / name)
        shutil.copyfile(OUT / 'preparation-provenance.json', replay / 'preparation-provenance.json')
        prepared = json.loads((OUT / 'prompt-C-v5-r5/manifest.json').read_text())
        # Synthetic source provenance only; no dependency on real candidate workspaces.
        source_key = next(k for k in prepared['sources'] if k.endswith('track_2a/src/predict.py'))
        prepared['sources'][source_key] = 'synthetic-replay-source-hash'
        for repeat in range(1, 6):
            baseline = f'prompt-C-v5-r{repeat}'
            shutil.copytree(OUT / baseline, replay / baseline)
            job = replay / f'prompt-C-v11-r{repeat}'
            shutil.copytree(OUT / baseline, job)
            # Synthetic provenance only: predictions remain historical v5 outputs.
            (job / 'manifest.json').write_text(json.dumps(prepared))
            state = json.loads((job / 'state.json').read_text())
            state['manifest_sha256'] = usage.digest(prepared)
            (job / 'state.json').write_text(json.dumps(state))
            for suffix, value in (('start.txt', '0'), ('end.txt', '1')):
                (replay / f'prompt-C-v11-r{repeat}-{suffix}').write_text(value)
        for name in ('score_candidate.py', 'compare_candidate.py'):
            source = (ROOT / '.auto' / name).read_text()
            anchor = "OUT=ROOT/'output/cscs'"
            assert source.count(anchor) == 1
            source = source.replace(anchor, 'OUT=Path(' + repr(str(replay)) + ')')
            sys.argv = [name, '--candidate', 'v11']
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, str(ROOT / '.auto' / name), 'exec'),
                     {'__file__': str(ROOT / '.auto' / name), '__name__': '__main__'})
        comparison = json.loads((replay / 'hillclimb-v11-analysis/comparison.json').read_text())
        sys.argv = [sys.argv[0]]
        baseline_aggregate = json.loads((OUT / 'hillclimb-v5-analysis/aggregate.json').read_text())
        replay_aggregate = json.loads((replay / 'hillclimb-v11-analysis/aggregate.json').read_text())
        assert comparison['reference_version'] == 'v5'
        for part, side in comparison['splits'].items():
            assert side['baseline_mean_Q'] == baseline_aggregate[part]['Q_mean']
            assert side['candidate_mean_Q'] == baseline_aggregate[part]['Q_mean']
            assert replay_aggregate[part]['repeats'] == baseline_aggregate[part]['repeats']
            assert abs(side['gain']) < 1e-12, 'Historical replay must have zero gain'
            assert side['candidate_safe_all']
        assert not comparison['adopt_literal'] and not comparison['adopt_strict']
        with contextlib.redirect_stdout(io.StringIO()) as output:
            results.report(replay, 'v11')
        assert 'METRIC min_Q_gain_v5=0' in output.getvalue()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                results.report(replay, 'v11', check=True)
        except SystemExit as exc:
            assert str(exc).startswith('REJECTED:')
        else:
            raise AssertionError('Zero gain replay cannot pass candidate gates')
    print('PASS: saved-baseline replay through official scoring/comparison; zero gain, no adoption. Not a v11 result. No model/API calls.')

if __name__ == '__main__':
    main()
