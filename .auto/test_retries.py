"""Synthetic offline fresh-job retry gates. No inference or saved fixture display."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import results
import run_candidate as runner


class RetryControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompts = self.root / 'prompts'
        self.prompts.mkdir()
        self.out = self.root / 'out'
        self.pairs = {}
        for version, (original, run, repeat, _) in runner.RETRIES.items():
            data = (original + ' synthetic SYSTEM\n').encode()
            sha = runner.digest(data)
            self.pairs[version] = (original, run, repeat, sha)
            archive = self.out / 'candidate-archive' / original
            archive.mkdir(parents=True)
            meta = {'version': original, 'candidate_prompt_sha256': sha,
                    'baseline_prompt_sha256': 'synthetic-v5'}
            (archive / f'{original}.json').write_text(json.dumps(meta))
            (archive / f'{original}-system.txt').write_bytes(data)
            job = self.out / f'prompt-C-{original}-r{repeat}'
            job.mkdir()
            (job / 'STOP.json').write_text(json.dumps({'status': 'STOP', 'http_status': 504}))
            (self.prompts / f'{version}-system.txt').write_bytes(data)
        for name, value in [('PROMPTS', self.prompts), ('OUT', self.out), ('RETRIES', self.pairs)]:
            patcher = patch.object(runner, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def metadata(self, version):
        original, run, _, sha = self.pairs[version]
        return {'version': version, 'original_candidate_version': original, 'retry_of_run': run,
                'candidate_prompt_sha256': sha, 'baseline_prompt_sha256': 'synthetic-v5',
                'proposed_trials': runner.TRIALS.copy(), 'approved_trials': runner.TRIALS.copy(),
                'inference_approved': True, 'approval_scope': {'candidate': version, **runner.TRIALS}}

    def test_exact_identity_and_fresh_approval(self):
        for version in self.pairs:
            good = self.metadata(version)
            runner.validate_metadata(version, good, False)
            runner.validate_metadata(version, good, True)
            for key, value in [('original_candidate_version', 'v11'), ('retry_of_run', 10),
                               ('retry_of_run', True), ('candidate_prompt_sha256', 'mutated'),
                               ('baseline_prompt_sha256', 'changed'), ('inference_approved', False),
                               ('approval_scope', {'candidate': good['original_candidate_version'], **runner.TRIALS})]:
                with self.subTest(version=version, key=key), self.assertRaises((AssertionError, SystemExit)):
                    runner.validate_metadata(version, {**good, key: value}, False)
            path = self.prompts / f'{version}-system.txt'
            data = path.read_bytes()
            path.write_bytes(data + b'\n')
            with self.assertRaisesRegex(AssertionError, 'RETRY_SYSTEM_BYTES_CHANGED'):
                runner.validate_metadata(version, good, False)
            path.write_bytes(data)

    def test_duplicate_exception_only_exact_pair(self):
        for version, (original, _, _, sha) in self.pairs.items():
            def previous(v):
                return self.pairs[version][3] if v == 'v4' else 'distinct-' + v
            with patch.object(runner, 'prior_prompt_hash', side_effect=lambda v: 'distinct-' + v):
                runner.refuse_duplicates(version, sha)
                with self.assertRaisesRegex(AssertionError, 'RETRY_PROMPT_HASH_CHANGED'):
                    runner.refuse_duplicates(version, 'mutated')
            with patch.object(runner, 'prior_prompt_hash', side_effect=previous):
                with self.assertRaisesRegex(AssertionError, 'DUPLICATE_CANDIDATE'):
                    runner.refuse_duplicates(version, sha)
            archive = self.out / 'candidate-archive' / original / f'{original}-system.txt'
            archive.write_bytes(b'mutated archive')
            with self.assertRaisesRegex(AssertionError, 'RETRY_ORIGINAL_HASH_CHANGED'):
                runner.original_retry_artifacts(version)
        for version in ('v11-retry1', 'v12-retry2', 'v4-retry1', 'v13-retry2'):
            with self.assertRaises(SystemExit):
                runner.require_future(version)

    def test_original_stop_504_required_and_old_fences_preserved(self):
        for version, (original, _, repeat, _) in self.pairs.items():
            stop = self.out / f'prompt-C-{original}-r{repeat}/STOP.json'
            before = stop.read_bytes()
            runner.refuse_batch(version)
            self.assertEqual(stop.read_bytes(), before)
            with self.assertRaises(SystemExit):
                runner.refuse_batch(original)
            for value in (500, None, '504', 200):
                stop.write_text(json.dumps({'status': 'STOP', 'http_status': value}))
                with self.assertRaisesRegex(AssertionError, 'RETRY_REQUIRES_ORIGINAL_STOP_504'):
                    runner.original_retry_artifacts(version)
            stop.unlink()
            with self.assertRaises(OSError):
                runner.original_retry_artifacts(version)
            stop.write_bytes(before)
            fence = self.out / f'prompt-C-{version}-r3-inflight.json'
            fence.write_text('{}')
            with self.assertRaises(SystemExit):
                runner.refuse_batch(version)
            self.assertEqual(fence.read_text(), '{}')

    def test_retry_window_and_reference(self):
        window = {'timezone': 'Asia/Tokyo', 'started_at': '2026-10-14T11:10:43+09:00',
                  'candidate_start_before': '2026-10-14T12:40:43+09:00',
                  'soft_finish_by': '2026-10-14T13:10:43+09:00',
                  'approved_candidates': list(self.pairs), 'max_new_candidates': 2,
                  'baseline_version': 'v5', 'trials': runner.TRIALS.copy(),
                  'approved': True, 'stop_on_execution_error': True}
        start = datetime.fromisoformat(window['started_at'])
        for version in self.pairs:
            runner.validate_window(version, window, start)
            runner.validate_window(version, window, start + timedelta(minutes=89))
            for now in (start - timedelta(seconds=1), start + timedelta(minutes=90), start.replace(tzinfo=None)):
                with self.assertRaises(SystemExit):
                    runner.validate_window(version, window, now)
            self.assertEqual(results.reference_name(version), 'hillclimb-v5-analysis')
            self.assertIn(version, results.VERSIONS)
        with self.assertRaises(SystemExit):
            runner.validate_window('v11', window, start)

    def test_prepare_strips_credentials_and_does_not_check_clock(self):
        with patch.object(runner, 'ENV', {'API_KEY': 'secret', 'BASE_URL': 'secret',
                                         'OPENAI_API_KEY': 'secret', 'SAFE': 'kept'}):
            env = runner.workspace_env(self.root, False)
            self.assertEqual(set(env), {'SAFE', 'TMPDIR'})
        for version in self.pairs:
            (self.prompts / f'{version}.json').write_text(json.dumps(self.metadata(version)))
            (self.prompts / 'v5-system.txt').write_bytes(b'baseline')
            meta = self.metadata(version)
            meta['baseline_prompt_sha256'] = runner.digest(b'baseline')
            original = self.pairs[version][0]
            archive = self.out / 'candidate-archive' / original / f'{original}.json'
            old = json.loads(archive.read_text())
            old['baseline_prompt_sha256'] = meta['baseline_prompt_sha256']
            archive.write_text(json.dumps(old))
            (self.prompts / f'{version}.json').write_text(json.dumps(meta))
            with patch('sys.argv', ['run_candidate.py', '--candidate', version, '--prepare-only']), patch.object(
                    runner, 'check_window') as clock, patch.object(runner, 'subprocess') as processes, patch.object(
                    runner, 'refuse_duplicates'), patch.object(runner, 'preserve_candidate', side_effect=RuntimeError('offline gate')):
                with self.assertRaisesRegex(RuntimeError, 'offline gate'):
                    runner.main()
                clock.assert_not_called()
                self.assertFalse(processes.mock_calls)


if __name__ == '__main__':
    unittest.main()
