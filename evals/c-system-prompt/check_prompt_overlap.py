"""Read approved dev54 only; output counts, never case text or test transcripts."""
import argparse
import json
from pathlib import Path
import re
import unicodedata


def windows(text, size=8):
    tokens = re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold())
    return {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def check(added_text, rows):
    if len(rows) != 54 or {r['source_date'] for r in rows} != {'2020-09-27', '2021-03-07'}:
        raise ValueError('ONLY_APPROVED_DEV54_ALLOWED')
    phrases = windows(added_text)
    collisions = 0
    for row in rows:
        texts = [row['input']['claim']['text'], row['input'].get('reference', {}).get('text', ''),
                 row['expect'].get('reference', '')]
        collisions += any(phrases & windows(text) for text in texts)
    return {'method': 'NFKC/casefold Unicode word 8-gram overlap',
            'checked_cases': len(rows), 'overlapping_cases': collisions,
            'pass': collisions == 0,
            'limitation': 'Lexical overlap cannot establish absence of semantic paraphrase.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--added-text', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('cases.jsonl'))
    args = parser.parse_args()
    result = check(args.added_text.read_text(), [json.loads(x) for x in args.cases.read_text().splitlines()])
    print(json.dumps(result))
    if not result['pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
