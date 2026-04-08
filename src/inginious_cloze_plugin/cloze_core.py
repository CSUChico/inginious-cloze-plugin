# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import secrets
import re
from typing import Any

TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")
SUPPORTED_VARIANT_KEYS = {"id", "name", "text"}


def coerce_problem_mapping(problem_content: Any) -> dict[str, Any]:
    if isinstance(problem_content, dict):
        return dict(problem_content)
    return {}


def parse_solutions_from_text(text: str) -> dict[str, tuple[str, Any]]:
    solutions: dict[str, tuple[str, Any]] = {}
    for slot, kind, rhs in TOKEN_RE.findall(text or ""):
        rhs = rhs.strip()
        if kind == "SHORTANSWER":
            solutions[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|") if s.strip()])
            continue

        tolerance = 0.0
        if "±" in rhs:
            base, tol = rhs.split("±", 1)
            rhs = base.strip()
            tolerance = float(tol.strip())
        solutions[slot] = ("NUMERICAL", (float(rhs), tolerance))
    return solutions


def expected_slots_from_text(text: str) -> list[str]:
    return [match.group(1) for match in TOKEN_RE.finditer(text or "")]


def normalize_variant(index: int, variant: Any) -> dict[str, Any]:
    if isinstance(variant, str):
        return {"id": str(index), "text": variant, "name": None}

    if not isinstance(variant, dict):
        raise ValueError("Each cloze variant must be a string or object.")

    unknown = set(variant.keys()) - SUPPORTED_VARIANT_KEYS
    if unknown:
        raise ValueError("Unsupported keys in cloze variant: {}".format(", ".join(sorted(unknown))))

    text = variant.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Each cloze variant must define a non-empty text field.")

    name = variant.get("name")
    if name is not None and not isinstance(name, str):
        raise ValueError("Variant name must be a string when provided.")

    variant_id = variant.get("id", str(index))
    return {"id": str(variant_id), "name": name, "text": text}


def load_variants_payload(raw_payload: Any) -> list[dict[str, Any]]:
    if raw_payload is None:
        return []

    if isinstance(raw_payload, dict):
        raw_payload = raw_payload.get("variants", [])

    if not isinstance(raw_payload, list):
        raise ValueError("Cloze variants JSON must be a list or an object with a variants list.")

    return [normalize_variant(index, variant) for index, variant in enumerate(raw_payload)]


def normalize_inline_variants(problem_content: Any) -> dict[str, Any]:
    data = coerce_problem_mapping(problem_content)
    data.setdefault("name", "")
    data.setdefault("text", "")
    data.setdefault("variants_file", "")
    if isinstance(data.get("variants"), str):
        data["variants"] = json.loads(data["variants"])
    return data


def choose_variant_index(variants: list[dict[str, Any]], seed: str | None = None,
                         submitted_variant: Any = None, randomize: bool = False) -> int:
    if not variants:
        return 0

    if submitted_variant not in (None, ""):
        try:
            index = int(submitted_variant)
            if 0 <= index < len(variants):
                return index
        except (TypeError, ValueError):
            pass

    if randomize and seed in (None, ""):
        return secrets.randbelow(len(variants))

    digest = hashlib.sha256((seed or "").encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % len(variants)


def build_variant_record(variants: list[dict[str, Any]], seed: str | None = None,
                         submitted_variant: Any = None, randomize: bool = False) -> dict[str, Any]:
    index = choose_variant_index(variants, seed=seed, submitted_variant=submitted_variant, randomize=randomize)
    variant = dict(variants[index])
    variant["index"] = index
    variant["slots"] = expected_slots_from_text(variant["text"])
    variant["solutions"] = parse_solutions_from_text(variant["text"])
    return variant


def grade_answers(solutions: dict[str, tuple[str, Any]], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "correct": 0,
            "total": max(len(solutions), 1),
            "errors": len(solutions),
            "valid": False,
            "score": 0.0,
        }

    correct = 0
    errors = 0
    for slot, (kind, rhs) in solutions.items():
        answer = (value.get(slot) or "").strip()
        is_correct = False

        if kind == "SHORTANSWER":
            is_correct = any(answer.lower() == expected.lower() for expected in rhs)
        else:
            try:
                submitted = float(answer)
                target, tolerance = rhs
                is_correct = abs(submitted - target) <= tolerance
            except (TypeError, ValueError):
                is_correct = False

        if is_correct:
            correct += 1
        else:
            errors += 1

    total = max(len(solutions), 1)
    return {
        "correct": correct,
        "total": total,
        "errors": errors,
        "valid": errors == 0,
        "score": correct / total,
    }
