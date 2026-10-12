"""Download only referenced federal PDFs; keep them outside version control."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
from urllib.parse import urlparse


def filename(url):
    return hashlib.sha256(url.encode()).hexdigest()[:16] + ".pdf"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=Path("track_2a/data/source.jsonl"))
    p.add_argument("--output-dir", type=Path, default=Path("/workspace/ost-booklets"))
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    urls = sorted({json.loads(line)["booklet_url"] for line in args.source.open()})
    def download(url):
        dest = args.output_dir / filename(url)
        try:
            if urlparse(url).hostname != "www.bk.admin.ch":
                raise ValueError("not a Federal Chancellery URL")
            if not dest.exists():
                req = urllib.request.Request(url, headers={"User-Agent": "HackApertus-OST/1.0"})
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read(30 * 1024 * 1024 + 1)
                if not data.startswith(b"%PDF") or len(data) > 30 * 1024 * 1024:
                    raise ValueError("not PDF or too large")
                temp = dest.with_suffix(".part")
                temp.write_bytes(data)
                temp.replace(dest)
            return {"url": url, "path": str(dest.resolve()), "bytes": dest.stat().st_size,
                    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
        except Exception as exc:
            return {"url": url, "error": str(exc)}
    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(download, urls))
    (args.output_dir / "manifest.json").write_text(json.dumps(records, indent=2))
    print(json.dumps({"downloaded": sum("error" not in r for r in records), "total": len(records),
                      "bytes": sum(r.get("bytes", 0) for r in records)}, indent=2))

if __name__ == "__main__":
    main()
