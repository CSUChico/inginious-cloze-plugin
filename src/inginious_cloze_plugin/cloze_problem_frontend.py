# src/inginious_cloze_plugin/cloze_problem_frontend.py
import html, re
from inginious.frontend.task_problems import DisplayableProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type(cls): 
        return "cloze"

    @classmethod
    def get_type_name(cls, language): 
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        super().__init__(problemid, problem_content, translations, task_fs)
        # DisplayableProblem already stores problem_content; but keeping _data is fine if you rely on it:
        self._data = problem_content

    # Webapp calls: problem.input_is_consistent(task_input, default_exts, default_max_size)
    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        # We generate fields named: "<pid>__<slot>"
        pid = self.get_id()
        if hasattr(task_input, "get_problem_input"):
            value = task_input.get_problem_input(pid)
        else:
            value = task_input.get(pid)

        # "value" is often a dict prepared by the TaskInput layer; accept if dict-ish.
        return isinstance(value, dict)

    def get_text_fields(self):
        return ["text", "name"]

    def input_type(self):
        # IMPORTANT: tell TaskInput layer we want a dict
        return "dict"

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = self._data.get("text", "")

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)  # "1", "2", ...
            # CRITICAL: use a naming convention the TaskInput builder can group into a dict
            # Common safe pattern in INGInious plugins: "<pid>__<slot>"
            input_name = f"{pid}__{slot}"

            parts.append(
                f'<input type="text" name="{html.escape(input_name)}" class="form-control" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        label = html.escape(self._data.get("name", "Question"))
        return f"""
            <div class="panel panel-default">
              <div class="panel-heading">{label}</div>
              <div class="panel-body" style="line-height:2.2;">
                {''.join(parts)}
              </div>
            </div>
        """

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        if key == "name":
            return '<input name="name" class="form-control" />'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""

    # Must exist (and match ABC expectation) or class stays abstract.
    def check_answer(self, *args, **kwargs):
        """
        Frontend-side optional check. We don't do real grading here.
        Just report "ok" and let the backend/container do the real grading.
        """
        # Some INGInious versions expect a tuple (success: bool, message: str)
        return True, ""

