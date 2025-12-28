# src/inginious_cloze_plugin/cloze_problem_frontend.py
import html
import re

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

# {slot:TYPE:=ANSWER}
_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    """
    Frontend (rendering + client-side packing).

    We render multiple <input> fields but submit ONE hidden field named "{problem_id}"
    that contains JSON like:
      {"1":"H2O","2":"100"}
    This matches backend input_type() == "string".
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)
        # ensure we keep YAML data available for show_input
        self._data = problem_content

    # --- required by DisplayableProblem/abstract base
    def get_text_fields(self):
        return ["name", "text"]

    def input_type(self):
        # IMPORTANT: must be a supported core type. We'll post JSON as a string.
        return "string"

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        Called by the webapp before it accepts submission.
        We must ensure the field exists and is non-empty.
        """
        pid = self.get_id()
        raw = task_input.get_problem_input(pid)
        return bool(raw and str(raw).strip())

    def check_answer(self, task_input, language):
        """
        Optional "check" path; we don't do frontend checking.
        Return (ok, message). Keep permissive.
        """
        return True, ""

    # --- rendering
    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = self._data.get("text", "") or ""
        title = html.escape(self._data.get("name", "Question") or "Question")

        parts = []
        last = 0

        # Build inline inputs; we store answers into a single hidden JSON field (name=pid)
        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            # visible input - NOT named for submission
            parts.append(
                f'<input type="text" data-slot="{html.escape(slot)}" '
                f'class="form-control cloze-input" '
                f'style="display:inline-block; width:10rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        # hidden field that INGInious will read as the single problem answer
        # name MUST be pid
        return f"""
        <div class="panel panel-default">
          <div class="panel-heading">{title}</div>
          <div class="panel-body" style="line-height:2.2;">
            {''.join(parts)}
            <input type="hidden" name="{html.escape(pid)}" id="{html.escape(pid)}" />
          </div>
        </div>

        <script>
          (function(){{
            // Scope this script to the block that contains it
            const root = document.currentScript.closest('.panel');
            if(!root) return;

            const hidden = root.querySelector('input[name="{pid}"]');
            const inputs = root.querySelectorAll('.cloze-input');

            function update(){{
              const data = {{}};
              inputs.forEach(i => {{
                data[i.dataset.slot] = i.value || "";
              }});
              hidden.value = JSON.stringify(data);
            }}

            inputs.forEach(i => i.addEventListener('input', update));
            update();
          }})();
        </script>
        """

    # --- optional editor support (task editor)
    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key == "name":
            return '<input name="name" class="form-control" type="text" />'
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
