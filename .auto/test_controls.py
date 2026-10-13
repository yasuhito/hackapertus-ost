"""Synthetic offline safety and acceptance-gate tests. Never execute inference."""
import contextlib
import copy
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
        return {'version': 'v4', 'proposed_trials': trials,
                'approved_trials': trials.copy(), 'inference_approved': True,
                'approval_scope': {'candidate': 'v4', **trials}}

    def test_approval_is_candidate_specific(self):
        good = self.metadata()
        run_candidate.validate_metadata('v4', good, True)
        for key, bad in (('inference_approved', False), ('inference_approved', 1),
                         ('approved_trials', {'cases': 54, 'repeats': 1, 'configs': 1}),
                         ('approval_scope', {'candidate': 'v3', 'cases': 54, 'repeats': 5, 'configs': 1}),
                         ('approval_scope', 'old v3 permission'), ('version', 'v3')):
            meta = {**good, key: bad}
            with self.assertRaises(SystemExit):
                run_candidate.validate_metadata('v4', meta, True)
        unapproved = {'version': 'v4', 'proposed_trials': good['proposed_trials']}
        run_candidate.validate_metadata('v4', unapproved, False)
        with self.assertRaises(SystemExit):
            run_candidate.validate_metadata('v4', unapproved, True)

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

    def report(self, fixture):
        totals = results.usage.empty()
        mocked_usage = [{'totals': totals, 'splits': {'train': totals, 'test': totals}} for _ in range(5)]
        with patch.object(results, 'saved', return_value=fixture), patch.object(
                results.usage, 'candidate_usage', return_value=mocked_usage), contextlib.redirect_stdout(io.StringIO()) as output:
            results.report(Path('/synthetic-unused'), 'v4', True)
        self.assertIn('Hit_reference_surrogate_gain', output.getvalue())
        self.assertIn('METRIC candidate_parent_total_tokens=0', output.getvalue())
        self.assertIn('Repair-window usage is a subset', output.getvalue())

    def test_acceptance_and_rejections(self):
        good = self.fixture()
        self.report(good)  # Hit regression reported, not silently an official-score gate.
        bad = copy.deepcopy(good)
        bad[1]['splits']['test']['gain'] = -.01
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
