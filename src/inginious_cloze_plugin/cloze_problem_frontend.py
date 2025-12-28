# inginious_cloze_plugin/cloze_problem_frontend.py
from inginious.frontend.task_problems import DisplayableProblem
from inginious.frontend.parsable_text import ParsableText

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type(cls):              # <- REQUIRED so the inspector returns "cloze"
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "cloze"

    def show_input(self, template_helper, language, seed):
        header = ParsableText(self.gettext(language, self._header or ""), "rst",
                              translation=self.get_translation_obj(language))
        # Render a minimal input (for now just a textarea bound to this problem id)
        return template_helper.render(
            "tasks/text.html",
            inputId=self.get_id(),
            header=header,
            optional=self._optional,
            maxChars=0,
            default=self._default if hasattr(self, "_default") else ""
        )

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        # Reuse a simple edit box for prototype
        return template_helper.render("course_admin/subproblems/text.html", key=key)

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
