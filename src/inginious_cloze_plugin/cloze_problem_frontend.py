# src/inginious_cloze_plugin/cloze_problem_frontend.py
import html, re
from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    @classmethod
    def get_type(cls): return "cloze"
    @classmethod
    def get_type_name(cls, language): return "Cloze"

    def show_input(self, template_helper, language, seed):
        """
        Render the stem text, replacing tokens with <input> fields.
        We post a dict: name="<problem_id>[<slot>]".
        """
        pid = self.get_id()
        text = self._data.get("text", "")
        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            # literal text before token
            parts.append(html.escape(text[last:m.start()]))
            slot = m.group(1)  # '1', '2', ...
            input_name = f'{pid}[{slot}]'
            # a simple inline input; width adjusts via CSS
            parts.append(f'<input type="text" name="{input_name}" class="form-control" '
                         f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />')
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
        # basic textarea for 'text' field in task editor (optional)
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
