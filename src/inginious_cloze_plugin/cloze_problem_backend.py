# -*- coding: utf-8 -*-
"""
Backend (grading) Cloze problem for INGInious 0.9.x.

IMPORTANT: The MCQ agent expects problem.check_answer() to return FIVE values:
  (is_valid, main_message, secondary_messages, mcq_error_count, state)
"""

import json
import re

from inginious.frontend.task_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, taskfs):
        super().__init__(problemid, problem_content, translations, taskfs)
        self._data = problem_content or {}

    def _extract_raw_value(self, raw):
        """Normalize INGInious inputs (string/list/dict) into a single string."""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, (list, tuple)):
            for item in raw:
                s = self._extract_raw_value(item)
                if str(s).strip():
                    return s
            return ""
        if isinstance(raw, dict):
            for k in ("value", "answer", "data", "raw"):
                if k in raw:
                    return self._extract_raw_value(raw.get(k))
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
            # msg.inputdata is often a plain dict
            raw = task_input.get(pid)
        return self._extract_raw_value(raw).strip()

    def _parse_student_answers(self, s):
        """Hidden field should be JSON like {"1":"H2O","2":"50"}."""
        if not s:
            return {}
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return {str(k): ("" if v is None else str(v)) for k, v in obj.items()}
        except Exception:
            pass
        return {}

    def _expected_from_text(self):
        """Return list of (slot, kind, expected_string)."""
        text = (self._data or {}).get("text", "") or ""
        out = []
        for m in _TOKEN_RE.finditer(text):
            slot = m.group(1)
            kind = m.group(2)
            expected = (m.group(3) or "").strip()
            out.append((slot, kind, expected))
        return out

    def _shortanswer_ok(self, student, expected):
        options = [o.strip() for o in expected.split("|") if o.strip()]
        s = (student or "").strip()
        return any(s.lower() == o.lower() for o in options) if options else False

    def _numerical_ok(self, student, expected):
        options = [o.strip() for o in expected.split("|") if o.strip()]
        try:
            s_val = float((student or "").strip())
        except Exception:
            return False

        for opt in options:
            try:
                e_val = float(opt)
            except Exception:
                continue
            if abs(s_val - e_val) <= 1e-9:
                return True
        return False

    def check_answer(self, task_input, language):
        """
        MUST return:
          (is_valid, main_message, secondary_messages, mcq_error_count, state)
        """
        raw = self._get_problem_input_str(task_input)
        answers = self._parse_student_answers(raw)
        expected_items = self._expected_from_text()

        secondary = []
        errors = 0

        if not expected_items:
            return True, "", [], 0, {}

        if not answers:
            return (
                False,
                "Please answer all the questions.",
                ["Your answers were not recorded correctly (empty submission)."],
                1,
                {},
            )

        for slot, kind, expected in expected_items:
            student = (answers.get(str(slot), "") or "").strip()

            if not student:
                errors += 1
                secondary.append(f"Blank {slot}: missing answer.")
                continue

            if kind == "SHORTANSWER":
                ok = self._shortanswer_ok(student, expected)
            elif kind == "NUMERICAL":
                ok = self._numerical_ok(student, expected)
            else:
                ok = False

            if not ok:
                errors += 1
                secondary.append(f"Blank {slot}: incorrect.")

        is_valid = (errors == 0)
        main = "Correct." if is_valid else "Some answers are incorrect."
        mcq_error_count = errors
        state = {}

        return is_valid, main, secondary, mcq_error_count, state
