from inginious.frontend.task_problems import DisplayableProblem

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type(cls) -> str:
        return "cloze"

    @classmethod
    def get_type_name(cls, language: str) -> str:
        return "cloze (embedded answers)"

    @classmethod
    def get_renderer(cls, template_helper):
        return template_helper.get_renderer(pkg_name=__package__, use_default=False)

    def show_input(self, template_helper, language: str, seed: str) -> str:
        text = self._problem.get("_display_text", self._problem.get("text", ""))
        return template_helper.render("cloze_input.html", text=text)
