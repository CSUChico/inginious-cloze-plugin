# -*- coding: utf-8 -*-
"""
Backend (grading-side) Cloze problem for INGInious.

Key design for INGInious 0.9.x:
- The frontend must submit ONE field per problem id, otherwise the platform's
  consistency checks fail for custom problem types.
- Therefore we submit a JSON string in the single field, and decode it here.

Token syntax supported in the stem text:
  {1:SHORTANSWER:=H2O|h2o}
  {2:NUMERICAL:=100±0.5}
  {3:NUMERICAL:=42}

SHORTANSWER: case-insensitive exact match against any variant split by '|'
NUMERICAL: float compare with optional tolerance '±'
"""

import json
import re
from inginious.common.tasks_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_text_fields(cls):
        # allow teachers to edit/translate these
        return ["name", "text"]

    @classmethod
    def input_type(cls):
        # IMPORTANT: must be a single value so INGInious can validate it.
        # We'll receive a JSON string and decode it.
        return "string"

    def _solutions(self):
        """Parse expected answers out of self._data['text']."""
        text = (self._data or {}).get("text", "") or ""
        sol = {}

        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                # multiple variants: A|B|C
                variants = [s.strip() for s in rhs.split("|") if s.strip()]
                sol[slot] = ("SHORTANSWER", variants)
            else:
                # NUMERICAL may have tolerance like "100±0.5"
                tol = 0.0
                base = rhs
                if "±" in rhs:
                    base, t = rhs.split("±", 1)
                    base = base.strip()
                    tol = float(t.strip())
                sol[slot] = ("NUMERICAL", (float(base), tol))

        return sol

    def input_is_consistent(self, value):
        # Called by backend for safety; frontend also does its own checks.
        return isinstance(value, str) and value.strip() != ""

    def check_answer(self, value, seed):
        """
        value: JSON string like {"1":"H2O","2":"100"}
        Return dict with success/message/score.
        """
        sols = self._solutions()

        try:
            answers = json.loads(value) if isinstance(value, str) else {}
        except Exception:
            return {"success": False, "message": "Malformed submission.", "score": 0.0}

        if not isinstance(answers, dict):
            return {"success": False, "message": "Malformed submission.", "score": 0.0}

        # normalize keys to strings
        answers = {str(k): ("" if v is None else str(v)) for k, v in answers.items()}

        correct = 0
        total = max(len(sols), 1)
        per_blank = []

        for slot, (kind, rhs) in sols.items():
            ans = (answers.get(slot) or "").strip()
            ok = False

            if kind == "SHORTANSWER":
                ok = any(ans.lower() == exp.lower() for exp in rhs)

            elif kind == "NUMERICAL":
                try:
                    x = float(ans)
                    target, tol = rhs
                    ok = abs(x - target) <= tol
                except Exception:
                    ok = False

            correct += 1 if ok else 0
            per_blank.append(f"{slot}:{'✓' if ok else '✗'}")

        score = correct / total
        return {
            "success": score == 1.0,
            "message": "; ".join(per_blank),
            "score": score,
        }
