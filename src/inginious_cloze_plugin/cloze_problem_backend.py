# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

try:
    from inginious.common.tasks_problems import Problem
except ModuleNotFoundError:  # pragma: no cover - enables local tests without INGInious installed
    class Problem(object):
        def __init__(self, problemid=None, problem_content=None, translations=None, task_fs=None):
            self._id = problemid
            self._data = problem_content or {}
            self._task_fs = task_fs

        def get_id(self):
            return self._id


_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")
_SUPPORTED_VARIANT_KEYS = {"id", "name", "text"}


def _coerce_problem_mapping(problem_content: Any) -> dict[str, Any]:
    if isinstance(problem_content, dict):
        return dict(problem_content)
    return {}


def parse_solutions_from_text(text: str) -> dict[str, tuple[str, Any]]:
    solutions: dict[str, tuple[str, Any]] = {}
    for slot, kind, rhs in _TOKEN_RE.findall(text or ""):
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
    return [match.group(1) for match in _TOKEN_RE.finditer(text or "")]


def _normalize_variant(index: int, variant: Any) -> dict[str, Any]:
    if isinstance(variant, str):
        return {"id": str(index), "text": variant, "name": None}

    if not isinstance(variant, dict):
        raise ValueError("Each cloze variant must be a string or object.")

    unknown = set(variant.keys()) - _SUPPORTED_VARIANT_KEYS
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


def _load_variants_payload(raw_payload: Any) -> list[dict[str, Any]]:
    if raw_payload is None:
        return []

    if isinstance(raw_payload, dict):
        raw_payload = raw_payload.get("variants", [])

    if not isinstance(raw_payload, list):
        raise ValueError("Cloze variants JSON must be a list or an object with a variants list.")

    return [_normalize_variant(index, variant) for index, variant in enumerate(raw_payload)]


def _read_task_file(task_fs: Any, path: str) -> str:
    if task_fs is None:
        raise ValueError("A variants_file was configured but no task filesystem is available.")

    for method_name in ("read", "read_file", "get_content"):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            data = method(path)
            return data.decode("utf-8") if isinstance(data, bytes) else str(data)

    if hasattr(task_fs, "open"):
        with task_fs.open(path, "r") as handle:
            return handle.read()

    raise ValueError("Task filesystem does not expose a readable API for variants_file.")


def load_variants(problem_content: Any, task_fs: Any = None) -> list[dict[str, Any]]:
    data = _coerce_problem_mapping(problem_content)
    variants: list[dict[str, Any]] = []

    if data.get("variants_file"):
        payload = json.loads(_read_task_file(task_fs, data["variants_file"]))
        variants.extend(_load_variants_payload(payload))

    if data.get("variants"):
        variants.extend(_load_variants_payload(data["variants"]))

    if variants:
        return variants

    return [{
        "id": "0",
        "name": data.get("name"),
        "text": data.get("text", "") or "",
    }]


def select_variant_index(problem_content: Any, task_fs: Any = None, seed: str | None = None,
                         submitted_variant: Any = None) -> int:
    variants = load_variants(problem_content, task_fs)
    if not variants:
        return 0

    if submitted_variant not in (None, ""):
        try:
            index = int(submitted_variant)
            if 0 <= index < len(variants):
                return index
        except (TypeError, ValueError):
            pass

    digest = hashlib.sha256((seed or "").encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % len(variants)


def build_variant(problem_content: Any, task_fs: Any = None, seed: str | None = None,
                  submitted_variant: Any = None) -> dict[str, Any]:
    variants = load_variants(problem_content, task_fs)
    index = select_variant_index(problem_content, task_fs, seed=seed, submitted_variant=submitted_variant)
    variant = dict(variants[index])
    variant["index"] = index
    variant["slots"] = expected_slots_from_text(variant["text"])
    variant["solutions"] = parse_solutions_from_text(variant["text"])
    return variant


def grade_answers(solutions: dict[str, tuple[str, Any]], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"correct": 0, "total": max(len(solutions), 1), "errors": len(solutions), "valid": False}

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

    return {"correct": correct, "total": max(len(solutions), 1), "errors": errors, "valid": errors == 0}


class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        return dict

    @classmethod
    def get_text_fields(cls):
        return {"name": True, "text": True}

    def parse_problem(self, problem_content):
        data = _coerce_problem_mapping(problem_content)
        if isinstance(data.get("variants"), str):
            data["variants"] = json.loads(data["variants"])

        # Validate eagerly so bad task data fails when loaded, not during student attempts.
        load_variants(data, getattr(self, "_task_fs", None))
        return data

    def _current_variant(self, seed=None, value=None):
        submitted_variant = None
        if isinstance(value, dict):
            submitted_variant = value.get("__variant")
        return build_variant(self._data, getattr(self, "_task_fs", None), seed=seed, submitted_variant=submitted_variant)

    def input_is_consistent(self, value):
        if not isinstance(value, dict):
            return False
        variant = self._current_variant(value=value)
        return all(isinstance(value.get(slot, ""), str) for slot in variant["slots"])

    def check_answer(self, value, language):
        variant = self._current_variant(value=value)
        result = grade_answers(variant["solutions"], value)
        if result["valid"]:
            return True, "", "", 0
        return False, "", "One or more blanks are incorrect.", result["errors"]
