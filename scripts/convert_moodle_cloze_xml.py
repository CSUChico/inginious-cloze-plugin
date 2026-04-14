#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _read_quiz_root(path: Path) -> ET.Element:
    # Some exported quiz banks have blank lines before the XML declaration.
    text = path.read_text(encoding="utf-8").lstrip()
    return ET.fromstring(text)


def convert_moodle_cloze_xml(path: Path) -> dict[str, list[dict[str, str]]]:
    root = _read_quiz_root(path)
    variants = []

    for index, question in enumerate(root.findall("question"), start=1):
        question_type = question.get("type")
        if question_type != "cloze":
            raise ValueError(
                f"Unsupported question type at position {index}: {question_type!r}. "
                "This converter only handles Moodle cloze questions."
            )

        name = (question.findtext("name/text") or "").strip() or f"Question {index}"
        text = question.findtext("questiontext/text")
        if text is None or not text.strip():
            raise ValueError(f"Question {index} ({name!r}) is missing questiontext/text.")

        variants.append({"id": str(index - 1), "name": name, "text": text.strip()})

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
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".json")

    payload = convert_moodle_cloze_xml(input_path)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['variants'])} variant(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
