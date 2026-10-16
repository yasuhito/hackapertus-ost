"""Translate claims into the booklet language with Apertus 8B, cached to JSON.

Research helper for the retrieval audit. Uses the pinned CSCS client (key read
through its private-file guard, never printed). One short completion per
distinct (claim, target language); results are appended to the cache file so
reruns only translate what is missing.
"""
import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'track_2a/dev/cscs'))
import cscs_check as c  # noqa: E402

LANG = {'de': 'German', 'fr': 'French', 'it': 'Italian'}
MODEL_8B = 'swiss-ai/Apertus-v1.5-8B'


def prompt(claim, target):
    return [{'role': 'system', 'content': f'Translate the user text into {LANG[target]}. Output only the translation, nothing else.'},
            {'role': 'user', 'content': claim}]


def translate(client, claim, target):
    response = client.request('POST', '/v1/chat/completions', {'model': MODEL_8B, 'messages': prompt(claim, target),
                                                              'temperature': 0, 'max_tokens': 256, 'stream': False})
    text = response['choices'][0]['message']['content'].strip()
    usage = response.get('usage') or {}
    return text, usage.get('prompt_tokens'), usage.get('completion_tokens')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'track_2a/data/source.jsonl')
    parser.add_argument('--booklet-dirs', nargs='+', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=ROOT / 'output/validation/claim-translations.json')
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    local = set()
    for directory in args.booklet_dirs:
        local.update(p.name for p in directory.glob('*.pdf'))
    rows = [json.loads(line) for line in args.source.open(encoding='utf-8')]
    cache = json.loads(args.cache.read_text()) if args.cache.exists() else {}
    todo = {}
    for row in rows:
        name = hashlib.sha256(row['booklet_url'].encode()).hexdigest()[:16] + '.pdf'
        if name not in local or row['claim_language'] == row['reference_language']:
            continue
        key = row['reference_language'] + '\n' + row['claim']
        if key not in cache:
            todo[key] = (row['claim'], row['reference_language'])
    print(json.dumps({'cached': len(cache), 'to_translate': len(todo)}), flush=True)
    c.protect()
    key = c.read_key(c.DEFAULT_KEY_FILE)
    clients = [c.Client(key, model=MODEL_8B) for _ in range(args.workers)]
    items = list(todo.items())

    def work(i):
        k, (claim, target) = items[i]
        try:
            text, pin, pout = translate(clients[i % args.workers], claim, target)
            return k, {'translation': text, 'target': target, 'prompt_tokens': pin, 'completion_tokens': pout}
        except Exception as exc:
            return k, {'error': type(exc).__name__}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for k, value in pool.map(work, range(len(items))):
            if 'error' not in value:
                cache[k] = value
            done += 1
            if done % 50 == 0:
                args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    args.cache.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    tokens = sum((v.get('prompt_tokens') or 0) + (v.get('completion_tokens') or 0) for v in cache.values())
    print(json.dumps({'cached': len(cache), 'failed': len(todo) - sum(1 for k in todo if k in cache), 'tokens_total': tokens}))


if __name__ == '__main__':
    main()
