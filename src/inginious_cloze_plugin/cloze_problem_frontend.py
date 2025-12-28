from inginious.frontend.tasks_problems import DisplayableProblem

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type_name(cls, language):
        return "cloze (embedded answers)"

    def show_input(self, template_helper, language, seed):
        return "<input name='1' />"
