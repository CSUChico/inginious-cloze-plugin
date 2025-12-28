from inginious.frontend.task_problems import DisplayableProblem

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"        # <-- REQUIRED

    @classmethod
    def get_type_name(cls, language):
        return "cloze"

    def show_input(self, template_helper, language, seed):
        # minimal, render something simple for now
        return "<div>cloze placeholder input</div>"

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
