# -*- coding: utf-8 -*-
import re
from inginious.common.tasks_problems import Problem

# Token format: {<slot>:(SHORTANSWER|NUMERICAL):=<rhs>}
_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    @classmethod
    def get_text_fields(cls):
        # allow teachers to edit/translate these
        return ["name", "text"]

    @classmethod
    def input_type(cls):
        # We expect a dict mapping slot -> string, e.g. {"1": "H2O", "2": "100"}
        return "dict"

    def _solutions(self):
        """
        Parse expected answers from self._data['text'].

        SHORTANSWER supports multiple correct answers separated by |:
            {1:SHORTANSWER:=H2O|h2o|water}

        NUMERICAL supports optional tolerance with ±:
            {2:NUMERICAL:=100±0.5}
            {2:NUMERICAL:=100}
        """
        text = (self._data or {}).get("text", "") or ""
        sol = {}

        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                variants = [s.strip() for s in rhs.split("|") if s.strip()]
                sol[slot] = ("SHORTANSWER", variants)
            else:
                tol = 0.0
                base = rhs
                if "±" in rhs:
                    base, t = rhs.split("±", 1)
                    base = base.strip()
                    tol = float(t.strip())
                sol[slot] = ("NUMERICAL", (float(base), tol))

        return sol

    def input_is_consistent(self, value):
        # Backend grading expects a dict of slot->string
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

            if ok:
                correct += 1
            messages.append(f"{slot}: {'✓' if ok else '✗'}")

        score = correct / total
        return {"success": score == 1.0, "message": "; ".join(messages), "score": score}
