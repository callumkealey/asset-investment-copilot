from __future__ import annotations

import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data" / "documents"
MANIFEST = DOCS / "source_manifest.json"


def main() -> None:
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    DOCS.mkdir(parents=True, exist_ok=True)
    for source in sources:
        target = DOCS / source["filename"]
        if target.exists():
            print(f"Already exists: {target.name}")
            continue
        print(f"Downloading {source['name']} ...")
        request = urllib.request.Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            target.write_bytes(response.read())
        print(f"Saved {target}")


if __name__ == "__main__":
    main()
