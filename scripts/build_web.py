#!/usr/bin/env python3
"""Assemble web/index.html from web/template.html, web/engine.js, and data/*.json.

The page carries its own copy of the data so it works as a single file. This
script is the only way that copy should change; tests/test_web_build.py checks
that the committed page matches what the data files would produce.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILES = ["catalogue", "locations", "machines", "climate", "scenario-default"]


def render() -> str:
    template = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    engine = (ROOT / "web" / "engine.js").read_text(encoding="utf-8")
    data = {name: json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8")) for name in DATA_FILES}
    data["plan"] = json.loads((ROOT / "plans" / "example-plan.json").read_text(encoding="utf-8"))
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    for marker in ("/*__DATA__*/", "/*__ENGINE__*/"):
        if template.count(marker) != 1:
            raise SystemExit(f"template must contain {marker} exactly once")
    return template.replace("/*__DATA__*/", f"const DATA = {blob};").replace("/*__ENGINE__*/", engine)


def main(argv: list[str]) -> int:
    out = ROOT / "web" / "index.html"
    html = render()
    if "--check" in argv:
        current = out.read_text(encoding="utf-8") if out.exists() else ""
        if current != html:
            print("web/index.html is stale; run: make web")
            return 1
        print("web/index.html is current")
        return 0
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
