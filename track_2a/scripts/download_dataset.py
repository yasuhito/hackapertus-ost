"""Reproduce the public, train-only source. No authentication or test access."""
import hashlib
from pathlib import Path
import urllib.request

URL = 'https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets/resolve/main/v1.1.jsonl'
EXPECTED = '87ee4afd9c0ee8861106c50f05884481402ca668aecf927df68fc52d915b02fd'
if __name__ == '__main__':
    dest = Path(__file__).resolve().parents[1] / 'data/source.jsonl'
    req = urllib.request.Request(URL, headers={'User-Agent': 'HackApertus-OST/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = response.read(50 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'Dataset unavailable (HTTP {exc.code}); 401/403 may indicate gating. No signup attempted.')
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise SystemExit('Source changed: checksum mismatch. Review before replacing dataset.')
    dest.write_bytes(data)
    print(f'Downloaded {len(data)} bytes (checksum verified)')
