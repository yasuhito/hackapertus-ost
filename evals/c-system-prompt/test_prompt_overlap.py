import unittest
from check_prompt_overlap import check


class OverlapTests(unittest.TestCase):
    def rows(self):
        return [{'source_date': '2020-09-27' if i < 36 else '2021-03-07',
                 'input': {'claim': {'text': 'Fictional cobalt lanterns circle silent violet moons near painted clouds.'}},
                 'expect': {}} for i in range(54)]

    def test_detects_normalized_copy(self):
        self.assertFalse(check('FICTIONAL cobalt lanterns circle silent violet moons near painted clouds', self.rows())['pass'])

    def test_generic_policy_does_not_overlap(self):
        self.assertTrue(check('Verify the logical relationship of source and claim before choosing a label.', self.rows())['pass'])

    def test_only_approved_dates(self):
        rows = self.rows()
        rows[0]['source_date'] = '1999-01-01'
        with self.assertRaises(ValueError):
            check('Generic policy', rows)


if __name__ == '__main__':
    unittest.main()
