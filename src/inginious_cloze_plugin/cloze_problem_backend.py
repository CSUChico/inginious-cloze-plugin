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
        # we want TaskInput to deliver a dict {slot: str}
        return "dict"

    @classmethod
    def get_text_fields(cls):
        return ["text", "name"]

    def _solutions(self):
        text = self._data.get("text", "")
        sol = {}
        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|")])
            else:
                tol = 0.0
                val = rhs
                if "±" in val:
                    base, t = val.split("±", 1)
                    val, tol = base.strip(), float(t.strip())
                sol[slot] = ("NUMERICAL", (float(val), tol))
        return sol

    # IMPORTANT: must accept extra args from frontend validation path
    def input_is_consistent(self, value, *args, **kwargs):
        return (
            isinstance(value, dict) and
            all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())
        )

    # IMPORTANT: MCQ agent calls check_answer(task_input, language)
    # (it uses "language" where you used "seed")
    def check_answer(self, value, language):
        sols = self._solutions()

        if not isinstance(value, dict):
            # valid=False => counts as a formatting error
            return (False, "Malformed submission.", [], 1, {})

        correct = 0
        total = max(len(sols), 1)
        sub_msgs = []
        state = {}

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

            state[slot] = {"answer": ans, "ok": ok}
            sub_msgs.append(f"{slot}: {'✓' if ok else '✗'}")
            correct += 1 if ok else 0

        score = correct / total

        # For MCQAgent: error_count should be 0 for well-formed submissions
        valid = True
        main_msg = f"Score: {correct}/{total} ({score:.0%})"
        error_count = 0
        return (valid, main_msg, sub_msgs, error_count, state)
