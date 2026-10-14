"""Fictional inputs only. No public row text or model calls."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prep', Path(__file__).with_name('prepare_public_validation.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def row(n, label=None):
    return {'booklet_publish_date': '2019-01-01', 'booklet_url': f'https://www.bk.admin.ch/fake-{n}.pdf',
            'claim': f'Fictional claim {n}', 'claim_language': 'de',
            'reference_string': f'Fictional reference {n}', 'reference_language': 'de',
            'vote': 'Fictional vote', 'entailment_label': n % 3 if label is None else label,
            'baseline_score': 0.123}


class RecipeTests(unittest.TestCase):
    def test_determinism_no_scores_in_rank(self):
        rows = [row(n) for n in range(90)]
        a, audit = p.select(rows)
        changed = copy.deepcopy(rows)
        for r in changed:
            r['baseline_score'] = {'model_prediction': 2, 'score': 999}
        b, _ = p.select(changed)
        self.assertEqual([i for i, _, _ in a], [i for i, _, _ in b])
        self.assertEqual(len(a), 30)
        self.assertEqual(audit['selected_reference_duplicates'], 0)
        self.assertEqual([r['entailment_label'] for _, r, _ in a], [0, 1, 2] * 10)

    def test_used_only_crossdate_groups_and_dates_allowed(self):
        rows = [row(n) for n in range(90)]
        rows[0]['booklet_publish_date'] = '2024-06-09'
        for i in (1, 2):
            rows[i]['booklet_publish_date'] = '2024-06-09'
            rows[i]['booklet_url'] = rows[0]['booklet_url']
        rows[91-2]['claim'] = '  FICTIONAL CLAIM 0 '
        rows[88]['reference_string'] = '  FICTIONAL REFERENCE 0 '
        chosen, audit = p.select(rows, used={0})
        self.assertEqual(audit['excluded_union'], 3)
        self.assertEqual(audit['eligible_rows'], 87)
        self.assertEqual(audit['selected_used_group_overlaps'], {'reference': 0, 'claim': 0})
        self.assertTrue({0, 88, 89}.isdisjoint(i for i, _, _ in chosen))
        # No date/booklet exclusion, even all 1488 public rows on the four dates.
        for i, r in enumerate(rows):
            r['booklet_publish_date'] = p.DATES[i % 4]
            r['booklet_url'] = rows[0]['booklet_url']
        self.assertEqual(p.select(rows, used={0})[1]['eligible_rows'], 87)

    def test_used_pair_parser(self):
        ids = [f'ost-dev54-{i:04d}-{t}' for i in range(27) for t in ('A', 'B')]
        split = {'train': ids[:36], 'test': ids[36:]}
        self.assertEqual(p.used_indices(split, 90), set(range(27)))
        for altered in (ids[:-1], ids[:-1] + [ids[0]], ids[:-1] + ['ost-dev54-0099-B'],
                        ids[:-1] + ['ost-dev54-0027-B'], ids[:-1] + ['wrong']):
            with self.assertRaises(ValueError):
                p.used_indices({'train': altered, 'test': []}, 90)

    def test_all54_input_mapping_without_gold(self):
        rows = [row(n) for n in range(90)]
        fixtures, ids = [], []
        for i in range(27):
            for case, _ in p.cases_for(i, rows[i], Path('/fake') / (p.sha(rows[i]['booklet_url'].encode())[:16] + '.pdf')):
                cid = f'ost-dev54-{i:04d}-{case["id"][-1]}'
                case['id'] = cid
                fixtures.append({'id': cid, 'input': case})
                ids.append(cid)
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)):
            directory = Path(tmp) / 'evals/c-system-prompt'
            directory.mkdir(parents=True)
            (directory / 'split.json').write_bytes(p.encoded({'train': ids[:36], 'test': ids[36:]}))
            path = directory / 'cases.jsonl'
            def write(values):
                path.write_bytes(b''.join(p.encoded(v) for v in values))
            write(fixtures)
            used, audit = p.verify_used(rows)
            self.assertEqual(used, set(range(27)))
            self.assertEqual(len(audit['mapping']), 54)
            for item, key in ((0, 'claim'), (1, 'reference'), (53, 'reference')):
                changed = copy.deepcopy(fixtures)
                changed[item]['input'][key]['text'] = 'wrong mapping'
                write(changed)
                with self.assertRaisesRegex(ValueError, 'mapping mismatch'):
                    p.verify_used(rows)

    def test_representative_before_label_balance(self):
        rows = [row(n) for n in range(6)]
        rows[1]['reference_string'] = rows[0]['reference_string']
        low = min((0, 1), key=lambda i: p.ranked(i, rows[i]))
        rows[low]['entailment_label'] = 0
        rows[1 - low]['entailment_label'] = 2
        selected, audit = p.select(rows, quota=1)
        self.assertEqual(audit['eligible_reference_groups'], 5)
        self.assertNotIn(1 - low, [i for i, _, _ in selected])
        self.assertEqual(p.ranked(0, rows[0]), p.ranked(0, {**rows[0], 'entailment_label': 2}))

    def test_normalization(self):
        self.assertEqual(p.normalize('Ｆoo-\nBAR\t baz'), 'foobar baz')
        self.assertEqual(p.normalize('F\u00adoo'), 'foo')

    def test_pair_expected_and_gold_isolation(self):
        for label in (0, 1, 2):
            paired = p.cases_for(42, row(42, label), Path('/fictional/booklet.pdf'))
            for case, gold in paired:
                self.assertEqual(set(case), {'id', 'claim', 'vote', 'booklet' if case['id'].endswith('A') else 'reference'})
                self.assertEqual(gold['label'], label)
                self.assertEqual(set(gold), {'id', 'label'} if label == 1 else {'id', 'label', 'reference'})
                self.assertEqual(case['id'], gold['id'])
                self.assertNotIn('baseline_score', case)
            self.assertEqual(paired[0][1].get('reference'), paired[1][1].get('reference'))

    def test_invalid_labels_and_insufficient_stop(self):
        for bad in (True, '0', -1, 3, None):
            with self.assertRaises(ValueError):
                p.select([row(0, bad) if bad is not None else {**row(0), 'entailment_label': None}])
        with self.assertRaisesRegex(ValueError, 'insufficient'):
            p.select([row(n, 0) for n in range(90)])

    def test_source_hash_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            p.check_source(b'fictional', p.SOURCE_SHA)
        with patch.object(p, 'SOURCE_SHA', p.sha(b'fictional')):
            p.check_source(b'fictional', p.sha(b'fictional'))
            with self.assertRaises(ValueError):
                p.check_source(b'fictional', 'wrong revision SHA')

    def test_existing_manifest_readonly_and_partial_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'cases.jsonl').write_bytes(b'fictional')
            with self.assertRaisesRegex(ValueError, 'partial'):
                p.execute(d)
            manifest = {'artifact_sha256': {'cases.jsonl': p.sha(b'fictional')}}
            manifest['freeze_sha256'] = p.digest(manifest)
            (d / 'selection-manifest.json').write_bytes(p.encoded(manifest))
            before = {f.name: f.read_bytes() for f in d.iterdir()}
            with patch.object(p.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')):
                self.assertEqual(p.execute(d)['status'], 'complete-read-only')
            self.assertEqual(before, {f.name: f.read_bytes() for f in d.iterdir()})
            (d / 'cases.jsonl').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                p.execute(d)
            with self.assertRaises(FileExistsError):
                p.exclusive(d / 'cases.jsonl', b'overwrite')

    def test_bad_url_and_redirect(self):
        for url in ('http://www.bk.admin.ch/x', 'https://localhost/x', 'https://127.0.0.1/x',
                    'file:///x', 'https://evil.example/x', 'https://user@www.bk.admin.ch/x'):
            with self.assertRaises(ValueError):
                p.validate_url(url)
            with self.assertRaises(ValueError):
                p.GovernmentRedirect().redirect_request(None, None, 302, '', {}, url)

    def pdf_bytes(self):
        import io
        from pypdf import PdfWriter
        stream = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(stream)
        return stream.getvalue()

    def test_pdf_header_eof_parser_size(self):
        valid = self.pdf_bytes()
        self.assertEqual(p.validate_pdf(valid), 1)
        for invalid in (b'HTML', valid.split(b'%%EOF')[0], b'%PDF bad %%EOF'):
            with self.assertRaises(Exception):
                p.validate_pdf(invalid)
        with patch.object(p, 'MAX_PDF', 8):
            with self.assertRaises(ValueError):
                p.validate_pdf(valid)

    def test_fullfetch_wronglength_retry_same_url_and_immutable(self):
        valid = self.pdf_bytes()
        url = 'https://www.bk.admin.ch/fake.pdf'
        class Response:
            status = 200
            def __init__(self, body, length, final=url):
                self.body, self.final = body, final
                self.headers = {'Content-Length': str(length)}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return self.final
            def read(self, size):
                result, self.body = self.body[:min(size, 17)], self.body[min(size, 17):]
                return result
        from unittest.mock import Mock
        opener = Mock()
        opener.open.side_effect = [Response(b'%PDF partial', len(valid)), Response(valid, len(valid))]
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p.urllib.request, 'build_opener', return_value=opener), patch.object(p.time, 'sleep'):
            dest = Path(tmp) / 'good.pdf'
            receipt = p.download_pdf(url, dest)
            self.assertEqual(dest.read_bytes(), valid)
            self.assertEqual(receipt['attempt'], 2)
            self.assertEqual([c.args[0].full_url for c in opener.open.call_args_list], [url, url])
            self.assertEqual((Path(tmp) / 'good.pdf.attempt-1.failed').read_bytes(), b'%PDF partial')
            with self.assertRaises(FileExistsError):
                p.download_pdf(url, dest)
            self.assertEqual(opener.open.call_count, 2)
            with self.assertRaises(FileExistsError):
                p.atomic_exclusive(dest, b'wrong')
            self.assertEqual(dest.read_bytes(), valid)

    def test_bad_response_never_canonical_bounded_attempts(self):
        from unittest.mock import Mock
        url = 'https://www.bk.admin.ch/fake.pdf'
        for body, length, final, error, calls in ((b'%PDF partial', 999, url, p.IncompletePDF, 3),
                                                (b'%PDF partial', 12, url, p.IncompletePDF, 3),
                                                (b'HTML', 4, url, ValueError, 1),
                                                (b'', p.MAX_PDF + 1, url, ValueError, 1),
                                                (b'valid', 5, 'https://evil.example/x', ValueError, 1)):
            class Response:
                status = 200
                headers = {'Content-Length': str(length)}
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def geturl(self): return final
                def read(self, size):
                    if getattr(self, 'done', False): return b''
                    self.done = True
                    return body
            opener = Mock()
            opener.open.side_effect = lambda *a, **k: Response()
            with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p.urllib.request, 'build_opener', return_value=opener), patch.object(p.time, 'sleep'):
                dest = Path(tmp) / 'bad.pdf'
                with self.assertRaises(error):
                    p.download_pdf(url, dest)
                self.assertFalse(dest.exists())
                self.assertEqual(opener.open.call_count, calls)

    def test_http_errors_do_not_retry(self):
        from unittest.mock import Mock
        opener = Mock()
        url = 'https://www.bk.admin.ch/fake.pdf'
        from io import BytesIO
        body = BytesIO()
        error = p.urllib.error.HTTPError(url, 404, 'fictional', {}, body)
        self.addCleanup(error.close)
        opener.open.side_effect = error
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(p.urllib.error.HTTPError):
                p.download_pdf(url, Path(tmp) / 'bad.pdf')
            self.assertEqual(opener.open.call_count, 1)
            self.assertTrue(body.closed)

    def test_stream_cap_status_range_encoding(self):
        from unittest.mock import Mock
        url = 'https://www.bk.admin.ch/fake.pdf'
        for status, headers in ((206, {}), (200, {'Content-Range': 'bytes 0-9/90'}),
                                (200, {'Content-Encoding': 'gzip'}), (200, {})):
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def geturl(self): return url
                def read(self, n): return b'%PDFxxxxxxxx'[:n]
            response = Response()
            response.status, response.headers = status, headers
            opener = Mock()
            opener.open.return_value = response
            with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p, 'MAX_PDF', 8), patch.object(p.urllib.request, 'build_opener', return_value=opener):
                dest = Path(tmp) / 'bad.pdf'
                with self.assertRaises(ValueError):
                    p.download_pdf(url, dest)
                self.assertFalse(dest.exists())
                self.assertEqual(opener.open.call_count, 1)

    def test_curl_full_bytes_failure_redirect_size_nooverwrite(self):
        import subprocess
        valid = self.pdf_bytes()
        url = 'https://www.bk.admin.ch/fake.pdf'
        for status, body, code, length, success in (
                (200, valid, 0, len(valid), True),
                (200, b'%PDF partial', 18, len(valid), False),
                (302, valid, 0, len(valid), False),
                (200, valid, 0, p.MAX_PDF + 1, False),
                (200, valid, 0, len(valid) + 1, False)):
            def run(args, **kwargs):
                Path(args[args.index('--output') + 1]).write_bytes(body)
                Path(args[args.index('--dump-header') + 1]).write_bytes(
                    f'HTTP/1.1 {status} Fictional\r\nContent-Length: {length}\r\n\r\n'.encode())
                self.assertIn('--max-redirs', args)
                self.assertEqual(args[-1], url)
                return subprocess.CompletedProcess(args, code, b'', b'')
            with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p.subprocess, 'run', side_effect=run), patch.object(p.time, 'sleep'):
                dest = Path(tmp) / 'booklet.pdf'
                if success:
                    record = p.download_pdf_curl(url, dest)
                    self.assertEqual(record['sha256'], p.sha(valid))
                    self.assertEqual(dest.read_bytes(), valid)
                    with self.assertRaises(FileExistsError):
                        p.download_pdf_curl(url, dest)
                else:
                    with self.assertRaises(Exception):
                        p.download_pdf_curl(url, dest)
                    self.assertFalse(dest.exists())
                    self.assertTrue(list(Path(tmp).glob('*.failed')))

    def test_resume_freeze_mismatch_never_selects(self):
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp) / 'old', Path(tmp) / 'new'
            old.mkdir()
            (old / 'selection-freeze.json').write_bytes(b'{}')
            with patch.object(p, 'select', side_effect=AssertionError('no reselection')), patch.object(p.urllib.request, 'urlopen', side_effect=AssertionError('no network')):
                with self.assertRaisesRegex(ValueError, 'freeze'):
                    p.verify_resume(old)
            self.assertFalse(new.exists())

    def test_resume_recomputed_mapping_recipe_and_rank_must_match(self):
        rows = [row(n) for n in range(1488)]
        audit = {'split_sha256': 'fictional-split', 'mapping': [], 'used_rows': []}
        with tempfile.TemporaryDirectory() as tmp, patch.object(p, 'ROOT', Path(tmp)), patch.object(p, 'verify_used', return_value=(set(), audit)), patch.object(p, 'check_source'):
            old = Path(tmp) / 'old'
            old.mkdir()
            source = Path(tmp) / 'source.jsonl'
            source.write_bytes(b''.join(p.encoded(r) for r in rows))
            chosen, _, frozen = p.selection_from_source(source.read_bytes())
            raw = p.encoded(frozen)
            (old / 'selection-freeze.json').write_bytes(raw)
            (old / 'official-source-metadata.json').write_bytes(p.encoded({'url': p.METADATA_URL, 'revision': p.REVISION, 'file': {'lfs': {'oid': p.SOURCE_SHA}}}))
            with patch.object(p, 'SOURCE', source), patch.object(p, 'FROZEN_FILE', p.sha(raw)), patch.object(p, 'FROZEN_SELECTION', frozen['selection_freeze_sha256']), patch.object(p.subprocess, 'run', side_effect=AssertionError('no transfers during verification')):
                verified, _, manifest = p.verify_resume(old)
                self.assertEqual([i for i, _, _ in chosen], [i for i, _, _ in verified])
                self.assertFalse(manifest['completion']['original_code_hash_recorded'])
                for key, value in (('seed', 'wrong'), ('recipe', 'wrong'), ('ranking_input_fields', []), ('used_source', {'split_sha256': 'changed'})):
                    changed = copy.deepcopy(frozen)
                    changed[key] = value
                    raw_changed = p.encoded(changed)
                    (old / 'selection-freeze.json').write_bytes(raw_changed)
                    with patch.object(p, 'FROZEN_FILE', p.sha(raw_changed)):
                        with self.assertRaisesRegex(ValueError, 'recomputed'):
                            p.verify_resume(old)

    def test_context_source_only_and_failure_no_replacement(self):
        import sys
        sys.path.insert(0, str(p.ROOT / 'track_2a/src'))
        import predict
        import source_spans
        case, _ = p.cases_for(2, row(2), Path('/fake'))[1]
        with patch.object(predict.Backend, 'complete', side_effect=AssertionError('no inference')):
            prepared, audit = p.prepare_context(case, predict, source_spans)
        payload = json.loads(prepared['messages'][1]['content'])
        self.assertEqual(audit['candidate_ids'], [s['span_id'] for s in source_spans.candidates((case['reference']['text'],), True)])
        self.assertNotIn('label', payload)
        with patch.object(predict, 'context', side_effect=ValueError('fictional failure')) as ctx:
            with self.assertRaises(ValueError):
                p.prepare_context(case, predict, source_spans)
            self.assertEqual(ctx.call_count, 1)


if __name__ == '__main__':
    unittest.main()
