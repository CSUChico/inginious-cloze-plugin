# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

try:
    from inginious.frontend.task_problems import Problem
except ModuleNotFoundError:  # pragma: no cover - local tests without INGInious
    class Problem(object):
        def __init__(self, problemid=None, problem_content=None, translations=None, taskfs=None):
            self._id = problemid
            self._data = problem_content or {}
            self._task_fs = taskfs

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
    def get_type_name(cls, language):
        return "Cloze"

    @classmethod
    def get_text_fields(cls):
        return {"name": True, "text": True}

    def __init__(self, problemid, problem_content, translations, taskfs):
        super().__init__(problemid, problem_content, translations, taskfs)
        self._data = self.parse_problem(problem_content or {})
        self._task_fs = taskfs

    def parse_problem(self, problem_content):
        data = _coerce_problem_mapping(problem_content)
        if isinstance(data.get("variants"), str):
            data["variants"] = json.loads(data["variants"])
        load_variants(data, getattr(self, "_task_fs", None))
        return data

    def _extract_raw_value(self, raw):
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, (list, tuple)):
            for item in raw:
                value = self._extract_raw_value(item)
                if str(value).strip():
                    return value
            return ""
        if isinstance(raw, dict):
            if "__variant" in raw:
                return json.dumps(raw)
            for key in ("value", "answer", "data", "raw"):
                if key in raw:
                    return self._extract_raw_value(raw.get(key))
            try:
                return json.dumps(raw)
            except Exception:
                return ""
        return str(raw)

    def _get_problem_input_str(self, task_input):
        pid = self.get_id()
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid) if isinstance(task_input, dict) else None
        return self._extract_raw_value(raw).strip()

    def _parse_student_answers(self, raw_value):
        if not raw_value:
            return {}
        if isinstance(raw_value, dict):
            return {str(k): ("" if v is None else str(v)) for k, v in raw_value.items()}
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                return {str(k): ("" if v is None else str(v)) for k, v in parsed.items()}
        except Exception:
            pass
        return {}

    def _current_variant(self, task_input=None, seed=None):
        answers = {}
        if isinstance(task_input, dict) and "__variant" in task_input:
            answers = task_input
        else:
            answers = self._parse_student_answers(self._get_problem_input_str(task_input))

        return build_variant(
            self._data,
            self._task_fs,
            seed=seed,
            submitted_variant=answers.get("__variant"),
        )

    def input_is_consistent(self, value):
        answers = value if isinstance(value, dict) else self._parse_student_answers(self._get_problem_input_str(value))
        if not isinstance(answers, dict):
            return False
        variant = self._current_variant(answers)
        return all(isinstance(answers.get(slot, ""), str) and answers.get(slot, "").strip() for slot in variant["slots"])

    def check_answer(self, task_input, language):
        answers = task_input if isinstance(task_input, dict) and "__variant" in task_input else self._parse_student_answers(
            self._get_problem_input_str(task_input)
        )
        variant = self._current_variant(answers)
        result = grade_answers(variant["solutions"], answers)

        if result["valid"]:
            return True, "Correct.", [], 0, {"variant": variant["index"]}

        main = "Please answer all the questions." if not answers else "Some answers are incorrect."
        secondary = []
        for slot in variant["slots"]:
            answer = (answers.get(slot) or "").strip()
            if not answer:
                secondary.append("Blank {}: missing answer.".format(slot))
                continue
            slot_result = grade_answers({slot: variant["solutions"][slot]}, {slot: answer})
            if not slot_result["valid"]:
                secondary.append("Blank {}: incorrect.".format(slot))

        return False, main, secondary, result["errors"], {"variant": variant["index"]}
