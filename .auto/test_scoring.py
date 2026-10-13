"""Offline wiring test with saved baseline replay, NOT a candidate evaluation."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/cscs'

def main():
    if len(sys.argv) != 1:
        raise SystemExit('No arguments accepted')
    with tempfile.TemporaryDirectory(prefix='scoring-replay-', dir=OUT / 'tmp') as directory:
        replay = Path(directory)
        for name in ('hillclimb-split5-date-balanced-analysis', 'official-rescore-evidence'):
            shutil.copytree(OUT / name, replay / name)
        shutil.copyfile(OUT / 'preparation-provenance.json', replay / 'preparation-provenance.json')
        prepared = json.loads((OUT / 'format-C-r5/manifest.json').read_text())
        # Synthetic source provenance only; no dependency on real candidate workspaces.
        source_key = next(k for k in prepared['sources'] if k.endswith('track_2a/src/predict.py'))
        prepared['sources'][source_key] = 'synthetic-replay-source-hash'
        for repeat in range(1, 6):
            baseline = f'format-C-r{repeat}' if repeat != 4 else 'format-C-r4.'
            shutil.copytree(OUT / baseline, replay / baseline)
            job = replay / f'prompt-C-v4-r{repeat}'
            shutil.copytree(OUT / baseline, job)
            # Synthetic provenance only: predictions remain historical v0 outputs.
            (job / 'manifest.json').write_text(json.dumps(prepared))
            for suffix, value in (('start.txt', '0'), ('end.txt', '1')):
                (replay / f'prompt-C-v4-r{repeat}-{suffix}').write_text(value)
        for name in ('score_candidate.py', 'compare_candidate.py'):
            source = (ROOT / '.auto' / name).read_text()
            anchor = "OUT=ROOT/'output/cscs'"
            assert source.count(anchor) == 1
            source = source.replace(anchor, 'OUT=Path(' + repr(str(replay)) + ')')
            sys.argv = [name, '--candidate', 'v4']
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(source, str(ROOT / '.auto' / name), 'exec'),
                     {'__file__': str(ROOT / '.auto' / name), '__name__': '__main__'})
        comparison = json.loads((replay / 'hillclimb-v4-analysis/comparison.json').read_text())
        sys.argv = [sys.argv[0]]
        for side in comparison['splits'].values():
            assert abs(side['gain']) < 1e-12, 'Historical replay must have zero gain'
            assert side['candidate_safe_all']
        assert not comparison['adopt_literal'] and not comparison['adopt_strict']
    print('PASS: saved-baseline replay through official scoring/comparison; zero gain, no adoption. Not a v4 result. No model/API calls.')

if __name__ == '__main__':
    main()
