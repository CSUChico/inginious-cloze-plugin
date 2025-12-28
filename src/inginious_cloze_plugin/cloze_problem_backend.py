# -*- coding: utf-8 -*-
import re
from inginious.common.tasks_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class ClozeProblem(Problem):
    """
    Backend/grading representation of the problem.
    INGInious will instantiate this class in the grading container.
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        # We want a mapping: slot -> user answer
        return "dict"

    @classmethod
    def get_text_fields(cls):
        # Fields visible in editor / subject to translation if applicable
        return ["name", "text"]

    def _solutions(self):
        """
        Parse expected answers from self._data['text'].
        Supports:
          {1:SHORTANSWER:=H2O}
          {2:SHORTANSWER:=H2O|h2o|Water}
          {3:NUMERICAL:=100}
          {4:NUMERICAL:=100±0.5}
        """
        text = (self._data or {}).get("text", "") or ""
        sol = {}
        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|") if s.strip()])
            else:
                tol = 0.0
                val = rhs
                if "±" in rhs:
                    base, t = rhs.split("±", 1)
                    val = base.strip()
                    tol = float(t.strip())
                sol[slot] = ("NUMERICAL", (float(val), tol))
        return sol

    def input_is_consistent(self, value):
        # Grader receives what frontend submitted after normalization
        if not isinstance(value, dict):
            return False
        for k, v in value.items():
            if not isinstance(k, str):
                return False
            if not isinstance(v, str):
                return False
        return True

    def check_answer(self, value, seed):
        sols = self._solutions()
        if not isinstance(value, dict):
            return {"success": False, "message": "Malformed submission.", "score": 0.0}

        total = max(len(sols), 1)
        correct = 0
        messages = []

        for slot, (kind, rhs) in sols.items():
            ans = (value.get(slot) or "").strip()
            ok = False

            if kind == "SHORTANSWER":
                ok = any(ans.lower() == exp.lower() for exp in rhs)
            else:
                try:
                    x = float(ans)
                    target, tol = rhs
                    ok = abs(x - target) <= tol
                except Exception:
                    ok = False

            correct += 1 if ok else 0
            messages.append(f"{slot}: {'✓' if ok else '✗'}")

        score = correct / total
        return {
            "success": score == 1.0,
            "message": "; ".join(messages),
            "score": float(score),
        }
