# src/inginious_cloze_plugin/cloze_problem_backend.py
import re
import json

from inginious.common.tasks_problems import Problem

# {slot:TYPE:=ANSWER}
_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class ClozeProblem(Problem):
    """
    Backend/grading side.

    Important: INGInious expects the submission value to match input_type().
    We use input_type() == "string", but that string is JSON encoding of a dict:
        {"1": "H2O", "2": "100"}
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def input_type(cls):
        # Must be a supported core type. We'll encode dict as JSON string.
        return "string"

    @classmethod
    def get_text_fields(cls):
        # Fields that can be translated/edited
        return ["name", "text"]

    def _solutions(self):
        """
        Parse expected answers from the stem once.
        SHORTANSWER: multiple variants allowed separated by |
        NUMERICAL: allows "100" or "100±0.5"
        """
        text = self._data.get("text", "") or ""
        sol = {}

        for slot, kind, rhs in _TOKEN_RE.findall(text):
            rhs = rhs.strip()
            if kind == "SHORTANSWER":
                sol[slot] = ("SHORTANSWER", [s.strip() for s in rhs.split("|") if s.strip()])
            else:
                # NUMERICAL
                tol = 0.0
                val_str = rhs
                if "±" in rhs:
                    base, t = rhs.split("±", 1)
                    val_str = base.strip()
                    tol = float(t.strip())
                sol[slot] = ("NUMERICAL", (float(val_str), tol))

        return sol

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        Called by the webapp before it accepts submission.
        task_input can be either:
          - a TaskInput-like object with get_problem_input(pid)
          - a plain dict of submitted fields
        """
        pid = self.get_id()
    
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            # plain dict case
            raw = task_input.get(pid)
    
            # sometimes INGInious stores fields under their HTML names;
            # for safety, also try stringified pid
            if raw is None:
                raw = task_input.get(str(pid))
    
        return bool(raw and str(raw).strip())


    def check_answer(self, value, seed):
        """
        Return format for Problem.check_answer in INGInious:
          (success: bool, feedback: str, problems_feedback: list, grade: float/int, result_data: dict)

        Note: Some INGInious versions treat 'grade' differently; returning a float 0..1 is typical.
        """
        sols = self._solutions()

        try:
            answers = json.loads(value) if isinstance(value, str) else {}
        except Exception:
            return (False, "Malformed submission.", [], 0.0, {"score": 0.0})

        if not isinstance(answers, dict):
            return (False, "Malformed submission.", [], 0.0, {"score": 0.0})

        correct = 0
        total = len(sols)
        per_slot = {}

        for slot, (kind, rhs) in sols.items():
            ans = (answers.get(slot) or "").strip()
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

            per_slot[slot] = {"answer": ans, "correct": ok}
            correct += 1 if ok else 0

        score = (correct / total) if total > 0 else 1.0
        msg = f"{correct}/{total} correct" if total > 0 else "No blanks found."

        # success=True means "grading completed", not "full marks"
        return (True, msg, [], score, {"score": score, "details": per_slot})
