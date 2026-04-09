#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _normalize_spec(raw: dict) -> dict:
    title = raw.get("title", "")
    intro = raw.get("intro", [])
    if isinstance(intro, str):
        intro = [intro]

    instructions = raw.get("instructions", "")
    left_items = raw.get("left_items", [])
    right_items = raw.get("right_items", [])
    variants = int(raw.get("variants", 1))
    shuffle_left = bool(raw.get("shuffle_left", False))
    shuffle_right = bool(raw.get("shuffle_right", True))
    wrap_in_object = bool(raw.get("wrap_in_object", True))

    if not left_items:
        raise ValueError("left_items must contain at least one entry.")
    if not right_items:
        raise ValueError("right_items must contain at least one entry.")

    right_by_id = {}
    for item in right_items:
        item_id = item.get("id")
        text = item.get("text")
        if not item_id or text is None:
            raise ValueError("Each right_items entry needs both 'id' and 'text'.")
        if item_id in right_by_id:
            raise ValueError(f"Duplicate right_items id: {item_id}")
        right_by_id[item_id] = item

    for index, item in enumerate(left_items, start=1):
        if item.get("text") is None:
            raise ValueError(f"left_items[{index - 1}] is missing 'text'.")
        answer_id = item.get("answer_id")
        if answer_id not in right_by_id:
            raise ValueError(
                f"left_items[{index - 1}] answer_id={answer_id!r} does not match any right_items id."
            )

    return {
        "title": title,
        "intro": intro,
        "instructions": instructions,
        "left_items": left_items,
        "right_items": right_items,
        "variants": variants,
        "shuffle_left": shuffle_left,
        "shuffle_right": shuffle_right,
        "wrap_in_object": wrap_in_object,
    }


def _cloze_choice(choice_letter: str, is_correct: bool) -> str:
    prefix = "=" if is_correct else "%0%"
    return f"{prefix}{choice_letter}"


def _build_cloze_token(slot: int, correct_letter: str, all_letters: list[str]) -> str:
    pieces = [_cloze_choice(letter, letter == correct_letter) for letter in all_letters]
    return "{" + f"{slot}:MULTICHOICE:" + "~".join(pieces) + "}"


def _build_variant_text(spec: dict, left_items: list[dict], right_items: list[dict], variant_index: int) -> str:
    letters = [f"{chr(ord('a') + idx)})" for idx in range(len(right_items))]
    letter_by_id = {item["id"]: letters[idx][0] for idx, item in enumerate(right_items)}
    answer_letters = [letters[idx][0] for idx in range(len(right_items))]

    parts = []
    if spec["title"]:
        parts.append(f"<p><strong>{_html_escape(spec['title'])}</strong></p>")

    for paragraph in spec["intro"]:
        parts.append(f"<p>{_html_escape(paragraph)}</p>")

    if spec["instructions"]:
        parts.append(f"<p>{_html_escape(spec['instructions'])}</p>")

    parts.append(
        '<table style="width:100%; border-collapse:collapse;">'
        '<tr style="vertical-align:top;">'
        '<td style="width:48%; padding-right:24px;">'
        '<ol style="margin-top:0;">'
    )

    for slot, item in enumerate(left_items, start=1):
        token = _build_cloze_token(slot, letter_by_id[item["answer_id"]], answer_letters)
        parts.append(
            "<li style=\"margin-bottom:12px;\">"
            f"{_html_escape(item['text'])} {token}"
            "</li>"
        )

    parts.append("</ol></td>")
    parts.append('<td style="width:52%;">')
    parts.append('<ol style="list-style:none; padding-left:0; margin-top:0;">')

    for idx, item in enumerate(right_items):
        parts.append(
            "<li style=\"margin-bottom:12px;\">"
            f"{_html_escape(letters[idx])} {_html_escape(item['text'])}"
            "</li>"
        )

    parts.append("</ol></td></tr></table>")
    return "".join(parts)


def generate_variants(spec: dict) -> list[dict]:
    rng = random.Random(spec.get("seed", 0))
    base_left = list(spec["left_items"])
    base_right = list(spec["right_items"])
    variants = []

    for index in range(spec["variants"]):
        left_items = list(base_left)
        right_items = list(base_right)

        if spec["shuffle_left"]:
            rng.shuffle(left_items)
        if spec["shuffle_right"]:
            rng.shuffle(right_items)

        variant_name = f"Variant {index + 1}"
        variants.append(
            {
                "name": variant_name,
                "text": _build_variant_text(spec, left_items, right_items, index),
            }
        )

    return variants


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate cloze variants JSON for left/right matching questions."
    )
    parser.add_argument("spec", help="Path to the input JSON spec file.")
    parser.add_argument(
        "-o",
        "--output",
        default="cloze_variants.json",
        help="Path to the output JSON file. Default: cloze_variants.json",
    )
    args = parser.parse_args()

    spec_path = Path(args.spec)
    output_path = Path(args.output)

    raw_spec = _read_json(spec_path)
    spec = _normalize_spec(raw_spec)
    spec["seed"] = raw_spec.get("seed", 0)
    variants = generate_variants(spec)

    payload = {"variants": variants} if spec["wrap_in_object"] else variants
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote {len(variants)} variant(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
