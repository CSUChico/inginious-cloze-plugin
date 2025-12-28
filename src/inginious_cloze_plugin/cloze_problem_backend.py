# src/inginious_cloze_plugin/cloze_problem_backend.py
import re
from inginious.common.tasks_problems import Problem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        # We'll receive a dict of slot -> str
        return "dict"

    @classmethod
    def get_text_fields(cls):
        # let teachers edit/translate the stem text
        return ["text", "name"]

    def _solutions(self):
        """Parse expected answers from self._data['text'] once."""
        text = self._data.get("text", "")
        sol = {}
        for slot, kind, rhs in _TOKEN_RE.findall(text):
            if kind == "SHORTANSWER":
                # allow multiple correct variants split by |
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|")])
            else:
                # NUMERICAL may have tolerance like 100±0.5 or just 100
                tol = 0.0
                val = rhs.strip()
                if "±" in val:
                    base, t = val.split("±", 1)
                    val, tol = base.strip(), float(t.strip())
                sol[slot] = ("NUMERICAL", (float(val), tol))
        return sol

    def input_is_consistent(self, value):
        # value should be a dict of strings keyed by slot ids
        return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())

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
