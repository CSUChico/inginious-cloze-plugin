# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
import secrets
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


from .cloze_core import (
    build_variant_record,
    coerce_problem_mapping,
    expected_slots_from_text,
    grade_answers,
    load_variants_payload,
    normalize_inline_variants,
    parse_solutions_from_text,
)


def _read_task_file(task_fs: Any, path: str) -> str:
    if task_fs is None:
        raise ValueError("A variants_file was configured but no task filesystem is available.")

    for method_name in ("get",):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            try:
                data = method(path)
                if hasattr(data, "read"):
                    data = data.read()
                return data.decode("utf-8") if isinstance(data, bytes) else str(data)
            except Exception:
                pass

    for method_name in ("get_fd",):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            try:
                handle = method(path)
                try:
                    data = handle.read()
                finally:
                    close = getattr(handle, "close", None)
                    if callable(close):
                        close()
                return data.decode("utf-8") if isinstance(data, bytes) else str(data)
            except Exception:
                pass

    for method_name in ("read", "read_file", "get_content"):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            data = method(path)
            return data.decode("utf-8") if isinstance(data, bytes) else str(data)

    if hasattr(task_fs, "open"):
        for mode in ("r", "rt", "rb"):
            try:
                with task_fs.open(path, mode) as handle:
                    data = handle.read()
                    return data.decode("utf-8") if isinstance(data, bytes) else str(data)
            except Exception:
                pass

    for method_name in ("opentext", "open_text"):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            with method(path) as handle:
                return handle.read()

    for method_name in ("openbin", "open_bin"):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            with method(path) as handle:
                data = handle.read()
                return data.decode("utf-8") if isinstance(data, bytes) else str(data)

    for method_name in ("get_path", "get_absolute_path", "realpath", "getsyspath", "get_sys_path"):
        method = getattr(task_fs, method_name, None)
        if callable(method):
            file_path = method(path)
            with open(file_path, "r", encoding="utf-8") as handle:
                return handle.read()

    root_path = None
    for attr_name in (
        "path", "root", "root_path", "base_path", "prefix", "_path", "_root", "_root_path", "_folder", "_dir"
    ):
        candidate = getattr(task_fs, attr_name, None)
        if isinstance(candidate, str) and candidate:
            root_path = candidate
            break

    if root_path is not None:
        with open(os.path.join(root_path, path), "r", encoding="utf-8") as handle:
            return handle.read()

    if isinstance(task_fs, str):
        with open(os.path.join(task_fs, path), "r", encoding="utf-8") as handle:
            return handle.read()

    fspath = getattr(task_fs, "__fspath__", None)
    if callable(fspath):
        with open(os.path.join(os.fspath(task_fs), path), "r", encoding="utf-8") as handle:
            return handle.read()

    raise ValueError(
        "Task filesystem does not expose a readable API for variants_file "
        "(task_fs_type={}, available_attrs={}).".format(
            type(task_fs).__name__,
            ", ".join(sorted(name for name in dir(task_fs) if not name.startswith("__")))
        )
    )


def load_variants(problem_content: Any, task_fs: Any = None) -> list[dict[str, Any]]:
    data = coerce_problem_mapping(problem_content)
    variants: list[dict[str, Any]] = []

    if data.get("variants_file"):
        payload = json.loads(_read_task_file(task_fs, data["variants_file"]))
        variants.extend(load_variants_payload(payload))

    if data.get("variants"):
        variants.extend(load_variants_payload(data["variants"]))

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
    return build_variant_record(
        variants,
        seed=seed,
        submitted_variant=submitted_variant,
        randomize=(submitted_variant in (None, "") and seed is None),
    )


class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    @classmethod
    def get_text_fields(cls):
        return {"name": True, "text": True, "variants_file": True}

    def __init__(self, problemid, problem_content, translations, taskfs):
        super().__init__(problemid, problem_content, translations, taskfs)
        self._data = self.parse_problem(problem_content or {}, taskfs)
        self._task_fs = taskfs

    @classmethod
    def parse_problem(cls, problem_content, taskfs=None):
        data = normalize_inline_variants(problem_content)
        if data.get("variants"):
            load_variants({"variants": data.get("variants")}, taskfs)
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
            return True, "Correct. You got {}/{} blanks right.".format(result["correct"], result["total"]), [], 0, {
                "variant": variant["index"],
                "correct": result["correct"],
                "total": result["total"],
            }

        main = "Please answer all the questions." if not answers else (
            "Some answers are incorrect. You got {}/{} blanks right.".format(result["correct"], result["total"])
        )
        secondary = []
        for slot in variant["slots"]:
            answer = (answers.get(slot) or "").strip()
            if not answer:
                secondary.append("Blank {}: missing answer.".format(slot))
                continue
            slot_result = grade_answers({slot: variant["solutions"][slot]}, {slot: answer})
            if not slot_result["valid"]:
                secondary.append("Blank {}: incorrect.".format(slot))

        return False, main, secondary, result["errors"], {
            "variant": variant["index"],
            "correct": result["correct"],
            "total": result["total"],
        }
