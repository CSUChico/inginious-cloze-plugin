#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def _read_quiz_root(path: Path) -> ET.Element:
    # Some exported quiz banks have blank lines before the XML declaration.
    text = path.read_text(encoding="utf-8").lstrip()
    return ET.fromstring(text)


def _sanitize_moodle_html(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</span>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\salign="left"', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\swidth=(["\'])?100%\1?', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s(width|height)="[^"]*"', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<p>\s*<p>", "<p>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</p>\s*</p>", "</p>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<br\s*/?>", "<div class=\"cloze-converted-break\"></div>", cleaned, flags=re.IGNORECASE)
    cleaned = _normalize_moodle_cloze_tokens(cleaned)
    cleaned = re.sub(r"<table\b([^>]*)>", _decorate_table_tag, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<pre\b([^>]*)>", _decorate_pre_tag, cleaned, flags=re.IGNORECASE)
    return cleaned


def _append_html_class(attrs: str, class_name: str) -> str:
    class_match = re.search(r'class="([^"]*)"', attrs, flags=re.IGNORECASE)
    if class_match:
        existing = class_match.group(1).strip()
        replacement = 'class="{} {}"'.format(existing, class_name).strip()
        return attrs[:class_match.start()] + replacement + attrs[class_match.end():]
    return '{} class="{}"'.format(attrs, class_name)


def _decorate_table_tag(match: re.Match[str]) -> str:
    attrs = _append_html_class(match.group(1), "cloze-converted-table")
    return "<table{}>".format(attrs)


def _decorate_pre_tag(match: re.Match[str]) -> str:
    attrs = _append_html_class(match.group(1), "cloze-converted-code")
    return "<pre{}>".format(attrs)


def _normalize_moodle_cloze_tokens(text: str) -> str:
    shorthand_map = {
        "MC": "MULTICHOICE",
        "MCH": "MULTICHOICE",
        "NM": "NUMERICAL",
        "SA": "SHORTANSWER",
    }

    def repl(match: re.Match[str]) -> str:
        kind = shorthand_map.get(match.group(1).upper())
        if not kind:
            return match.group(0)
        rhs = match.group(2).strip()
        return "{1:%s:%s}" % (kind, rhs)

    return re.sub(r"\{:(MC|MCH|NM|SA):?((?:\\.|[^{}])*)\}", repl, text)


def convert_moodle_cloze_xml(path: Path, keep_names: bool = False) -> dict[str, list[dict[str, str]]]:
    root = _read_quiz_root(path)
    variants = []

    cloze_index = 0
    for index, question in enumerate(root.findall("question"), start=1):
        question_type = question.get("type")
        if question_type != "cloze":
            continue

        cloze_index += 1
        name = (question.findtext("name/text") or "").strip() or f"Question {cloze_index}"
        text = question.findtext("questiontext/text")
        if text is None or not text.strip():
            raise ValueError(f"Question {cloze_index} ({name!r}) is missing questiontext/text.")

        variants.append({
            "id": str(cloze_index - 1),
            "name": name if keep_names else "",
            "text": _sanitize_moodle_html(text),
        })

    return {"variants": variants}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Moodle quiz XML cloze questions into the cloze variants JSON format."
    )
    parser.add_argument("input", help="Path to the Moodle quiz XML file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output JSON file. Defaults to the input filename with a .json suffix.",
    )
    parser.add_argument(
        "--keep-names",
        action="store_true",
        help="Keep Moodle question names as variant names instead of stripping them from student-facing output.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".json")

    payload = convert_moodle_cloze_xml(input_path, keep_names=args.keep_names)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['variants'])} variant(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
