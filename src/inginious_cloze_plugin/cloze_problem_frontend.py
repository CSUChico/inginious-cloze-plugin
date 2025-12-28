# src/inginious_cloze_plugin/cloze_problem_frontend.py
from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem  # <-- import your backend

class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    """
    Multiple inheritance: reuse backend (Problem) behaviour + frontend (DisplayableProblem).
    Put ClozeProblem first so its methods satisfy the abstract Problem API.
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "cloze"

    # Minimal UI to make it render; you can replace with a proper template later.
    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        # A single-line input bound to this problem id
        return f'<input type="text" name="{pid}" id="{pid}" class="form-control" />'

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        # keep simple for now
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
