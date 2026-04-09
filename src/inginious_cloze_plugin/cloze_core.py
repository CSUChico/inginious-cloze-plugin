# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import secrets
import re
from typing import Any

TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL|MULTICHOICE):((?:\\.|[^}])*)\}")
SUPPORTED_VARIANT_KEYS = {"id", "name", "text"}


def _split_unescaped(text: str, separator: str) -> list[str]:
    parts = []
    current = []
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == separator:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def _split_feedback(text: str) -> tuple[str, str | None]:
    parts = _split_unescaped(text, "#")
    if len(parts) == 1:
        return parts[0], None
    return parts[0], "#".join(parts[1:])


def _unescape_moodle_text(text: str) -> str:
    return re.sub(r"\\([~#}:=%\\\\])", r"\1", text)


def _parse_weighted_option(raw_option: str) -> tuple[float, str, str | None]:
    option = raw_option.strip()
    if not option:
        raise ValueError("Empty cloze answer option.")

    weight = None
    if option.startswith("="):
        weight = 100.0
        option = option[1:].strip()
    else:
        weighted_match = re.match(r"%(-?\d+(?:\.\d+)?)%(.*)$", option)
        if weighted_match:
            weight = float(weighted_match.group(1))
            option = weighted_match.group(2).strip()

    answer_text, feedback = _split_feedback(option)
    answer_text = _unescape_moodle_text(answer_text.strip())
    feedback = _unescape_moodle_text(feedback.strip()) if feedback is not None else None
    return (0.0 if weight is None else weight / 100.0), answer_text, feedback


def _parse_numerical_value(answer_text: str) -> tuple[float, float]:
    tolerance = 0.0
    if "±" in answer_text:
        base, tol = answer_text.split("±", 1)
        answer_text = base.strip()
        tolerance = float(tol.strip())
    elif ":" in answer_text:
        base, tol = answer_text.split(":", 1)
        answer_text = base.strip()
        tolerance = float(tol.strip())
    return float(answer_text), tolerance


def coerce_problem_mapping(problem_content: Any) -> dict[str, Any]:
    if isinstance(problem_content, dict):
        return dict(problem_content)
    return {}


def parse_solutions_from_text(text: str) -> dict[str, tuple[str, Any]]:
    solutions: dict[str, tuple[str, Any]] = {}
    for slot, kind, rhs in TOKEN_RE.findall(text or ""):
        rhs = rhs.strip()
        if kind == "SHORTANSWER":
            options = []
            for raw_option in _split_unescaped(rhs, "~"):
                raw_option = raw_option.strip()
                if not raw_option:
                    continue
                if "|" in raw_option and not raw_option.startswith("%") and not raw_option.startswith("="):
                    for alias in _split_unescaped(raw_option, "|"):
                        alias = alias.strip()
                        if alias:
                            options.append({"weight": 1.0, "answer": _unescape_moodle_text(alias), "feedback": None})
                    continue
                weight, answer, feedback = _parse_weighted_option(raw_option)
                if answer:
                    options.append({"weight": weight, "answer": answer, "feedback": feedback})
            solutions[slot] = ("SHORTANSWER", options)
            continue
        if kind == "MULTICHOICE":
            choices = []
            answers = []
            for raw_choice in _split_unescaped(rhs, "~"):
                raw_choice = raw_choice.strip()
                if not raw_choice:
                    continue
                weight, label, feedback = _parse_weighted_option(raw_choice)
                if not label:
                    continue
                choices.append(label)
                answers.append({"weight": weight, "answer": label, "feedback": feedback})
            if not choices or not any(option["weight"] > 0 for option in answers):
                raise ValueError("MULTICHOICE tokens must define at least one choice and one positive-credit answer.")
            solutions[slot] = ("MULTICHOICE", {"choices": choices, "answers": answers})
            continue

        options = []
        for raw_option in _split_unescaped(rhs, "~"):
            raw_option = raw_option.strip()
            if not raw_option:
                continue
            if "|" in raw_option and not raw_option.startswith("%") and not raw_option.startswith("="):
                for alias in _split_unescaped(raw_option, "|"):
                    alias = alias.strip()
                    if alias:
                        value, tolerance = _parse_numerical_value(_unescape_moodle_text(alias))
                        options.append({"weight": 1.0, "answer": value, "tolerance": tolerance, "feedback": None})
                continue
            weight, answer, feedback = _parse_weighted_option(raw_option)
            value, tolerance = _parse_numerical_value(answer)
            options.append({"weight": weight, "answer": value, "tolerance": tolerance, "feedback": feedback})
        solutions[slot] = ("NUMERICAL", options)
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
            "feedback": {},
        }

    correct = 0
    errors = 0
    slot_scores = []
    slot_feedback = {}
    for slot, (kind, rhs) in solutions.items():
        answer = (value.get(slot) or "").strip()
        slot_score = 0.0
        matched_feedback = None

        if kind == "SHORTANSWER":
            for option in rhs:
                if answer.lower() == option["answer"].lower():
                    if option["weight"] >= slot_score:
                        slot_score = option["weight"]
                        matched_feedback = option["feedback"]
        elif kind == "MULTICHOICE":
            for option in rhs["answers"]:
                if answer.lower() == option["answer"].lower():
                    if option["weight"] >= slot_score:
                        slot_score = option["weight"]
                        matched_feedback = option["feedback"]
        else:
            try:
                submitted = float(answer)
                for option in rhs:
                    if abs(submitted - option["answer"]) <= option["tolerance"]:
                        if option["weight"] >= slot_score:
                            slot_score = option["weight"]
                            matched_feedback = option["feedback"]
            except (TypeError, ValueError):
                slot_score = 0.0

        slot_score = max(min(slot_score, 1.0), -1.0)
        slot_scores.append(slot_score)
        if matched_feedback:
            slot_feedback[slot] = matched_feedback
        if slot_score >= 1.0:
            correct += 1
        else:
            errors += 1

    total = max(len(solutions), 1)
    total_score = max(sum(slot_scores), 0.0)
    return {
        "correct": correct,
        "total": total,
        "errors": errors,
        "valid": errors == 0,
        "score": min(total_score / total, 1.0),
        "feedback": slot_feedback,
    }
