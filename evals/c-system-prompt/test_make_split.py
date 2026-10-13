"""Synthetic split checks; no real test fixtures or predictions are inspected."""
import unittest
from make_split import split_cases


class SplitTests(unittest.TestCase):
    def rows(self):
        rows = []
        for label in range(3):
            for i in range(9):
                group = f'fictional-{label}-{i}'
                for task in ['A', 'B']:
                    source = {'booklet': {'path': '/fictional/booklet.pdf'}} if task == 'A' else {
                        'reference': {'text': f'Invented source {label}-{i // 2 if i < 2 else i}', 'language': 'de'}}
                    rows.append({'id': group + '-' + task, 'provenance_group': group,
                                 'source_date': '2020-09-27', 'input': source,
                                 'expect': {'label': label}})
        return rows

    def test_repeatable_balanced_and_group_safe(self):
        rows = self.rows()
        result = split_cases(rows)
        self.assertEqual(result, split_cases(rows))
        self.assertEqual(len(result['train']), 36)
        self.assertEqual(len(result['test']), 18)
        self.assertFalse(set(result['train']) & set(result['test']))
        for group in result['groups'].values():
            self.assertTrue(set(group) <= set(result['train']) or set(group) <= set(result['test']))
        byid = {r['id']: r for r in rows}
        for label in range(3):
            self.assertEqual(sum(byid[id]['expect']['label'] == label for id in result['test']), 6)

    def test_unapproved_date_rejected(self):
        rows = self.rows()
        rows[0]['source_date'] = '1999-01-01'
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED_DATE'):
            split_cases(rows)


if __name__ == '__main__':
    unittest.main()
