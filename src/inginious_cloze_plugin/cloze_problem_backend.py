# -*- coding: utf-8 -*-
import re
from inginious.common.tasks_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class ClozeProblem(Problem):
    """
    Backend grading logic (used by the grader).
    Displayable (frontend) class will reuse the same parsing helpers.
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        # The grader receives a dict: {"1": "...", "2": "..."}
        return "dict"

    @classmethod
    def get_text_fields(cls):
        # fields that can be translated/edited in task editor
        return ["name", "text"]

    def _solutions(self):
        """Parse expected answers out of the cloze text."""
        text = (self._data or {}).get("text", "") or ""
        sol = {}
        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|") if s.strip()])
            else:
                # NUMERICAL supports "100" or "100±0.5"
                tol = 0.0
                if "±" in rhs:
                    base, t = rhs.split("±", 1)
                    rhs = base.strip()
                    tol = float(t.strip())
                sol[slot] = ("NUMERICAL", (float(rhs), tol))
        return sol

    def input_is_consistent(self, value):
        # value must be dict[str,str]
        if not isinstance(value, dict):
            return False
        for k, v in value.items():
            if not isinstance(k, str) or not isinstance(v, str):
                return False
        return True

    def check_answer(self, value, seed):
        sols = self._solutions()
        if not isinstance(value, dict):
            return {"success": False, "message": "Malformed submission.", "score": 0.0}

        correct = 0
        total = max(len(sols), 1)
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
        return {"success": score == 1.0, "message": "; ".join(messages), "score": score}
