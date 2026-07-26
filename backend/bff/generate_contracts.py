from __future__ import annotations

import json
from pathlib import Path

from bff.schemas import PageDocument

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "contracts" / "page-document.schema.json"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(
        PageDocument.model_json_schema(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    OUTPUT.write_text(f"{rendered}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
