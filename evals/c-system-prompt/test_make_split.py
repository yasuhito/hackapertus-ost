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
                                 'source_date': '2020-09-27' if i < 6 else '2021-03-07', 'input': source,
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
        for part, count2020, count2021 in [('train', 24, 12), ('test', 12, 6)]:
            self.assertEqual(sum(byid[id]['source_date'] == '2020-09-27' for id in result[part]), count2020)
            self.assertEqual(sum(byid[id]['source_date'] == '2021-03-07' for id in result[part]), count2021)

    def test_infeasible_joint_constraints_rejected(self):
        rows = self.rows()
        # Each label/date cell is an indivisible source group (size 6 or 3).
        # No source-safe subset can pick exactly 3 per label and 6/3 by date.
        for row in rows:
            if 'reference' in row['input']:
                row['input']['reference']['text'] = f"Invented indivisible {row['expect']['label']} {row['source_date']}"
        with self.assertRaisesRegex(ValueError, 'NO_GROUP_SAFE_LABEL_DATE_BALANCED_SPLIT'):
            split_cases(rows)

    def test_unapproved_date_rejected(self):
        rows = self.rows()
        rows[0]['source_date'] = '1999-01-01'
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED_DATE'):
            split_cases(rows)


if __name__ == '__main__':
    unittest.main()
