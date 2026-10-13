"""Synthetic offline safety and acceptance-gate tests. Never execute inference."""
import contextlib
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import results
import run_candidate


class Controls(unittest.TestCase):
    def metadata(self):
        trials = {'cases': 54, 'repeats': 5, 'configs': 1}
        return {'version': 'v5', 'proposed_trials': trials,
                'approved_trials': trials.copy(), 'inference_approved': True,
                'approval_scope': {'candidate': 'v5', **trials}}

    def test_approval_is_candidate_specific(self):
        good = self.metadata()
        run_candidate.validate_metadata('v5', good, True)
        for key, bad in (('inference_approved', False), ('inference_approved', 1),
                         ('approved_trials', {'cases': 54, 'repeats': 1, 'configs': 1}),
                         ('approved_trials', {'cases': 54, 'repeats': 5, 'configs': True}),
                         ('approval_scope', {'candidate': 'v3', 'cases': 54, 'repeats': 5, 'configs': 1}),
                         ('approval_scope', 'old v3 permission'), ('version', 'v3')):
            meta = {**good, key: bad}
            with self.assertRaises(SystemExit):
                run_candidate.validate_metadata('v5', meta, True)
        unapproved = {'version': 'v5', 'proposed_trials': good['proposed_trials']}
        run_candidate.validate_metadata('v5', unapproved, False)
        with self.assertRaises(SystemExit):
            run_candidate.validate_metadata('v5', unapproved, True)

    def window(self):
        return {'timezone': 'Asia/Tokyo',
                'candidate_start_before': '2026-10-14T11:00:00+09:00',
                'soft_finish_by': '2026-10-14T12:00:00+09:00',
                'approved_candidates': list(run_candidate.FUTURE),
                'max_new_candidates': 6, 'trials': run_candidate.TRIALS.copy(),
                'approved': True, 'stop_on_execution_error': True}

    def test_window_cutoff_and_rollover(self):
        for version in run_candidate.FUTURE:
            run_candidate.validate_window(version, self.window(),
                                          datetime.fromisoformat('2026-10-14T01:59:59+00:00'))
        for timestamp in ('2026-10-14T02:00:00+00:00', '2026-10-14T12:00:00+09:00',
                          '2026-10-14T12:00:01+09:00', '2026-10-14T10:59:59'):
            with self.assertRaises(SystemExit):
                run_candidate.validate_window('v5', self.window(), datetime.fromisoformat(timestamp))
        with self.assertRaises(SystemExit):
            run_candidate.validate_window('v5', self.window(), None)

    def test_window_scope_fails_closed(self):
        now = datetime.fromisoformat('2026-10-14T00:00:00+00:00')
        for key, value in (('timezone', None), ('max_new_candidates', 7),
                           ('approved_candidates', ['v5']), ('approved', 1),
                           ('stop_on_execution_error', False),
                           ('candidate_start_before', '2026-10-14T11:00:00'),
                           ('soft_finish_by', '2026-10-14T12:00:00'),
                           ('trials', {'cases': 54, 'repeats': 1, 'configs': 1}),
                           ('trials', {'cases': 54, 'repeats': 5, 'configs': True})):
            with self.assertRaises(SystemExit):
                run_candidate.validate_window('v5', {**self.window(), key: value}, now)
        with self.assertRaises(SystemExit):
            run_candidate.validate_window('v11', self.window(), now)
        for window in ({}, None):
            with self.assertRaises(SystemExit):
                run_candidate.validate_window('v5', window, now)
        with tempfile.TemporaryDirectory() as directory, patch.object(
                run_candidate, 'WINDOW', Path(directory) / 'missing.json'):
            with self.assertRaises(SystemExit):
                run_candidate.check_window('v5')

    def test_prepare_needs_no_approval_or_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            prompts = Path(directory)
            candidate, baseline = b'synthetic new SYSTEM', b'synthetic baseline'
            meta = {'version': 'v5', 'proposed_trials': run_candidate.TRIALS,
                    'candidate_prompt_sha256': run_candidate.digest(candidate),
                    'baseline_prompt_sha256': run_candidate.digest(baseline)}
            (prompts / 'v5.json').write_text(json.dumps(meta))
            (prompts / 'v5-system.txt').write_bytes(candidate)
            (prompts / 'v0-system.txt').write_bytes(baseline)
            with patch.object(run_candidate, 'PROMPTS', prompts), patch.object(
                    run_candidate, 'refuse_batch'), patch.object(run_candidate, 'refuse_duplicates'), patch.object(
                    run_candidate, 'check_window') as clock, patch.object(
                    run_candidate, 'preserve_candidate', side_effect=RuntimeError('offline preservation reached')), patch(
                    'sys.argv', ['run_candidate.py', '--candidate', 'v5', '--prepare-only']):
                with self.assertRaisesRegex(RuntimeError, 'offline preservation reached'):
                    run_candidate.main()
                clock.assert_not_called()

    def test_archived_v4_refused_before_io(self):
        for mode in ('--prepare-only', '--execute-approved'):
            with patch('sys.argv', ['run_candidate.py', '--candidate', 'v4', mode]), patch.object(
                    run_candidate, 'check_window') as gate, patch.object(run_candidate, 'refuse_batch') as paths:
                with self.assertRaises(SystemExit):
                    run_candidate.main()
                gate.assert_not_called()
                paths.assert_not_called()

    def test_archive_fallback_duplicate_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts, out = root / 'prompts', root / 'out'
            prompts.mkdir()
            with patch.object(run_candidate, 'PROMPTS', prompts), patch.object(run_candidate, 'OUT', out):
                for number in range(1, 5):
                    version = f'v{number}'
                    archive = out / 'candidate-archive' / version
                    archive.mkdir(parents=True)
                    data = f'SYSTEM {number}'.encode()
                    (archive / f'{version}-system.txt').write_bytes(data)
                    (archive / f'{version}.json').write_text(json.dumps({
                        'version': version, 'candidate_prompt_sha256': run_candidate.digest(data)}))
                run_candidate.refuse_duplicates('v5', run_candidate.digest(b'new SYSTEM'))
                with self.assertRaisesRegex(AssertionError, 'DUPLICATE_CANDIDATE'):
                    run_candidate.refuse_duplicates('v5', run_candidate.digest(b'SYSTEM 4'))
                archive = out / 'candidate-archive/v4'
                (archive / 'v4-system.txt').write_bytes(b'tampered')
                with self.assertRaisesRegex(AssertionError, 'PREVIOUS_PROMPT_HASH_CHANGED'):
                    run_candidate.refuse_duplicates('v5', run_candidate.digest(b'new SYSTEM'))
                (archive / 'v4-system.txt').write_bytes(b'SYSTEM 4')
                (archive / 'v4.json').write_text(json.dumps({
                    'version': 'v3', 'candidate_prompt_sha256': run_candidate.digest(b'SYSTEM 4')}))
                with self.assertRaisesRegex(AssertionError, 'PREVIOUS_METADATA_VERSION_CHANGED'):
                    run_candidate.prior_prompt_hash('v4')

    def test_preserve_once_and_freeze_all_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompts, out = root / 'prompts', root / 'out'
            prompts.mkdir()
            with patch.object(run_candidate, 'PROMPTS', prompts), patch.object(run_candidate, 'OUT', out):
                for suffix in run_candidate.ARTIFACT_SUFFIXES:
                    (prompts / ('v5' + suffix)).write_bytes(suffix.encode())
                payload = run_candidate.preserve_candidate('v5')
                self.assertEqual(run_candidate.preserve_candidate('v5'), payload)
                run_candidate.refuse_batch('v5')  # Archive is not an execution fence.
                run_candidate.verify_candidate_artifacts('v5', payload)
                (prompts / 'v5.patch').write_bytes(b'changed')
                with self.assertRaisesRegex(AssertionError, 'CANDIDATE_ARTIFACT_CHANGED'):
                    run_candidate.verify_candidate_artifacts('v5', payload)
                with self.assertRaisesRegex(AssertionError, 'CANDIDATE_ARCHIVE_CHANGED'):
                    run_candidate.preserve_candidate('v5')
                self.assertEqual((out / 'candidate-archive/v5/v5.patch').read_bytes(), b'.patch')

    def test_existing_paths_refused_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with patch.object(run_candidate, 'OUT', out):
                run_candidate.refuse_batch('v4')
                fence = out / 'prompt-C-v4-r5-STOP.json'
                fence.write_text('synthetic fence')
                with self.assertRaises(SystemExit):
                    run_candidate.refuse_batch('v4')
                self.assertEqual(fence.read_text(), 'synthetic fence')

    def test_jobs_exact_ids_fences_and_completion(self):
        split = json.loads((results.ROOT / 'evals/c-system-prompt/split.json').read_text())
        ids = split['train'] + split['test']
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            for repeat in range(1, 6):
                job = out / f'prompt-C-v4-r{repeat}'
                job.mkdir()
                (job / 'summary.json').write_text(json.dumps({'status': 'completed'}))
                (job / 'manifest.json').write_text(json.dumps({'frozen': [{'case': {'id': id}} for id in ids]}))
                (job / '70b-canonical.jsonl').write_text(''.join(json.dumps({'id': id}) + '\n' for id in ids))
            self.assertEqual(len(results.completed_jobs(out, 'v4')), 5)
            job = out / 'prompt-C-v4-r5'
            (job / 'STOP.json').write_text('{}')
            with self.assertRaises(AssertionError):
                results.completed_jobs(out, 'v4')
            (job / 'STOP.json').unlink()
            (job / 'summary.json').write_text('{"status":"pending"}')
            with self.assertRaises(AssertionError):
                results.completed_jobs(out, 'v4')
            (job / 'summary.json').write_text('{"status":"completed"}')
            (job / '70b-canonical.jsonl').write_text(''.join(json.dumps({'id': ids[0]}) + '\n' for _ in ids))
            with self.assertRaises(AssertionError):
                results.completed_jobs(out, 'v4')

    def fixture(self):
        aggregate, comparison = {}, {'splits': {}, 'operations': []}
        for part, count in (('train', 36), ('test', 18)):
            aggregate[part] = {'cases': count, 'Q_mean': .85, 'repeats': [
                {'repeat': i, 'Q': .85, 'F1_A': .8, 'F1_B': .9, 'Hit_A': .5, 'safe_passes': {'A': True, 'B': True}}
                for i in range(1, 6)]}
            comparison['splits'][part] = {'gain': .03, 'baseline_noise': .01,
                'candidate_Hit_A_mean': .5, 'baseline_Hit_A_mean': .6,
                'candidate_operations': [{'valid': count, 'fallback_neutral': 0} for _ in range(5)]}
        comparison['operations'] = [{'repeat': i} for i in range(1, 6)]
        summaries = [{'models': {'synthetic': {'output_valid': 54}}} for _ in range(5)]
        return aggregate, comparison, summaries

    def report(self, fixture, check=True):
        totals = results.usage.empty()
        mocked_usage = [{'totals': totals, 'splits': {'train': totals, 'test': totals}} for _ in range(5)]
        with patch.object(results, 'saved', return_value=fixture), patch.object(
                results.usage, 'candidate_usage', return_value=mocked_usage), contextlib.redirect_stdout(io.StringIO()) as output:
            results.report(Path('/synthetic-unused'), 'v4', check)
        self.assertIn('Hit_reference_surrogate_gain', output.getvalue())
        self.assertIn('METRIC candidate_parent_total_tokens=0', output.getvalue())
        self.assertIn('Repair-window usage is a subset', output.getvalue())

    def test_acceptance_and_rejections(self):
        good = self.fixture()
        self.report(good)  # Hit regression reported, not silently an official-score gate.
        bad = copy.deepcopy(good)
        bad[1]['splits']['test']['gain'] = -.01
        self.report(bad, check=False)  # Completed measurement is not an execution error.
        with self.assertRaises(SystemExit):
            self.report(bad)
        bad = copy.deepcopy(good)
        bad[1]['splits']['train']['baseline_noise'] = .03
        with self.assertRaises(SystemExit):
            self.report(bad)
        for key, value in (('F1_A', .59), ('F1_B', .74), ('safe_passes', {'A': False, 'B': True})):
            bad = copy.deepcopy(good)
            bad[0]['test']['repeats'][4][key] = value
            with self.assertRaises(SystemExit):
                self.report(bad)
        bad = copy.deepcopy(good)
        bad[1]['splits']['train']['candidate_operations'][0]['fallback_neutral'] = 1
        self.report(bad)  # Count separately; canonical neutral stays officially scored.
        bad[1]['splits']['train']['candidate_operations'][0]['valid'] = 35
        with self.assertRaises(SystemExit):
            self.report(bad)


if __name__ == '__main__':
    unittest.main()
