#!/usr/bin/env python3
"""Generate FluentIcons.qml from FluentSystemIcons-Regular.json.

Usage:
    python kaa/application/ui/scripts/generate_fluent_icons_qml.py

Input:  kaa/application/ui/fonts/FluentSystemIcons-Regular.json
Output: kaa/application/ui/qml/FluentIcons.qml
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_UI_DIR = Path(__file__).resolve().parents[1]
_JSON_PATH = _UI_DIR / "fonts" / "FluentSystemIcons-Regular.json"
_OUT_PATH = _UI_DIR / "qml" / "FluentIcons.qml"

_PREFIX_RE = re.compile(r"^ic_fluent_")


def _to_property_name(key: str) -> str:
    return _PREFIX_RE.sub("", key)


def _to_escape(codepoint: int) -> str:
    return f"\\u{codepoint:04X}"


def generate(json_path: Path = _JSON_PATH, out_path: Path = _OUT_PATH) -> int:
    icons: dict[str, int] = json.loads(json_path.read_text(encoding="utf-8"))

    lines = [
        "// AUTO-GENERATED — do not edit.",
        "// Regenerate: python kaa/application/ui/scripts/generate_fluent_icons_qml.py",
        "pragma Singleton",
        "import QtQuick",
        "",
        "QtObject {",
        '    readonly property string family: "FluentSystemIcons-Regular"',
    ]

    for key, codepoint in sorted(icons.items()):
        name = _to_property_name(key)
        lines.append(f'    readonly property string {name}: "{_to_escape(codepoint)}"')

    lines.append("}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(icons)


if __name__ == "__main__":
    count = generate()
    print(f"Wrote {_OUT_PATH} ({count} icons)")