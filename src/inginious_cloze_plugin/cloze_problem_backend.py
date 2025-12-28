# -*- coding: utf-8 -*-
import re
from inginious.common.tasks_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        # backend expects a dict: {slot: answer_string}
        return "dict"

    @classmethod
    def get_text_fields(cls):
        # allow authoring/translation
        return ["name", "text"]

    def _solutions(self):
        text = (self._data or {}).get("text", "") or ""
        sol = {}
        for slot, kind, rhs in _TOKEN_RE.findall(text):
            if kind == "SHORTANSWER":
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|") if s.strip()])
            else:
                tol = 0.0
                val = rhs.strip()
                if "±" in val:
                    base, t = val.split("±", 1)
                    val, tol = base.strip(), float(t.strip())
                sol[slot] = ("NUMERICAL", (float(val), tol))
        return sol

    def input_is_consistent(self, value):
        return (
            isinstance(value, dict)
            and all(isinstance(k, str) for k in value.keys())
            and all(isinstance(v, str) for v in value.values())
        )

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
