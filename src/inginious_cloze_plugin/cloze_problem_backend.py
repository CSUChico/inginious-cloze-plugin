# src/inginious_cloze_plugin/cloze_problem_backend.py
from inginious.common.tasks_problems import Problem

class ClozeProblem(Problem):
    @classmethod
    def get_type(cls):
        return "cloze"

    # Minimal stubs to satisfy the abstract interface; improve as needed.
    @classmethod
    def input_type(cls):
        # store a single string for now
        return "string"

    @classmethod
    def get_text_fields(cls):
        # fields that can be translated / edited
        return ["text"]

    def input_is_consistent(self, value):
        # accept any string for now
        return isinstance(value, str)

    def check_answer(self, value, seed):
        # placeholder checker: just accept anything so the page works
        # Return the standard dict structure (success, message, score)
        return {"success": True, "message": "", "score": 1.0}
