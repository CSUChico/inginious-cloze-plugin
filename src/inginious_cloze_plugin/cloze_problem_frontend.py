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

    def __init__(self, problemid, problem_content, translations, task_fs):
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)
        self._data = problem_content  # make sure frontend has the YAML

    # --- FIX #1: match the webapp's expected signature
    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        # INGInious passes a TaskInput-like mapping. Be permissive for now:
        # accept either a single field (textarea) named after the problem id
        # or multiple fields like "<id>__1", "<id>__2", ...
        pid = self.get_id()
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            # fall back to dict-like
            raw = task_input.get(pid)
        return True  # minimal validator; tighten later if you want

    # --- FIX #2: also provide these abstract methods with the right signatures
    def get_text_fields(self):
        # nothing special to translate here (title/statement is handled by templates)
        return []

    def input_type(self):
        # single-line/textarea textual answer (what templates expect)
        return "string"

    def check_answer(self, task_input, language):
        """
        Optional: only used if a 'Check' flow is invoked on the frontend.
        We keep it permissive and let the real grading happen in the backend.
        """
        return True, ""

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
