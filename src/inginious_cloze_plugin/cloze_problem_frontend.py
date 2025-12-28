# -*- coding: utf-8 -*-

import html
import json
import re
from uuid import uuid4

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    """
    Displayable version of ClozeProblem for INGInious frontend (0.9.x).

    - Renders visible blanks for tokens in "text"
    - Stores all answers into ONE hidden field named by problem id as JSON:
        {"1": "...", "2": "..."}
    """

    # ---- DisplayableProblem abstract requirements ----

    @property
    def input_type(self):
        # Used by the task editor UI; "text" is safe/neutral here.
        return "text"

    def get_text_fields(self):
        # Editor/export: which fields contain text
        return ["text"]

    def show_editbox_templates(self, template_helper, language):
        """
        Return templates for the task editor (problem creation UI).
        Minimal implementation: provide a default skeleton.
        """
        # Key is template name, value is YAML snippet (string)
        return {
            "Cloze (basic)": (
                "type: cloze\n"
                "text: |\n"
                "  Water is {1:SHORTANSWER:=H2O}. Boiling point is {2:NUMERICAL:=100} C.\n"
            )
        }

    def show_editbox(self, template_helper, language, seed):
        """
        Render the edit box shown in task editor.
        Minimal: just a textarea bound to 'text'.
        """
        pid = self.get_id()
        text = (self._data or {}).get("text", "") or ""
        return f"""
<div class="form-group">
  <label for="cloze_text_{html.escape(pid)}">Cloze text</label>
  <textarea class="form-control" id="cloze_text_{html.escape(pid)}"
            name="problems[{html.escape(pid)}][text]" rows="8">{html.escape(text)}</textarea>
  <p class="help-block">
    Use tokens like <code>{{1:SHORTANSWER:=H2O}}</code> or <code>{{2:NUMERICAL:=100}}</code>.
  </p>
</div>
"""

    # -------------------------------------------------

    def __init__(self, problemid, problem_content, translations, taskfs):
        # ClozeProblem calls the correct base Problem.__init__(..., translations, taskfs)
        super().__init__(problemid, problem_content, translations, taskfs)

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def _render_prompt_with_inputs(self, text, uniq_prefix):
        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            kind = m.group(2)

            input_type = "text"
            step_attr = ""
            if kind == "NUMERICAL":
                input_type = "number"
                step_attr = ' step="any"'

            parts.append(
                f'<input type="{input_type}" class="form-control cloze-input" '
                f'data-slot="{html.escape(slot)}" '
                f'id="{uniq_prefix}_slot_{html.escape(slot)}" '
                f'{step_attr} '
                f'style="display:inline-block; width:auto; min-width:140px; vertical-align:middle;">'
            )

            last = m.end()

        parts.append(html.escape(text[last:]))
        return "".join(parts)

    def show_input(self, template_helper, language, seed):
        """
        Render student-facing input.
        """
        data = self._data or {}
        text = data.get("text", "") or ""

        pid = self.get_id()
        uniq = f"cloze_{pid}_{uuid4().hex}"

        prompt_html = self._render_prompt_with_inputs(text, uniq)

        # The *only* submitted field for this problem:
        hidden = (
            f'<input type="hidden" name="{html.escape(pid)}" '
            f'id="{uniq}_json" value="{html.escape(json.dumps({}))}">'
        )

        script = f"""
<script>
(function() {{
  var hidden = document.getElementById("{uniq}_json");
  if (!hidden) return;

  function collect() {{
    var inputs = document.querySelectorAll('input.cloze-input[id^="{uniq}_slot_"]');
    var obj = {{}};
    inputs.forEach(function(inp) {{
      var slot = inp.getAttribute("data-slot");
      obj[slot] = inp.value;
    }});
    hidden.value = JSON.stringify(obj);
  }}

  document.addEventListener("input", function(ev) {{
    if (ev.target && ev.target.classList && ev.target.classList.contains("cloze-input")
        && ev.target.id.indexOf("{uniq}_slot_") === 0) {{
      collect();
    }}
  }});

  var form = hidden.closest("form");
  if (form) {{
    form.addEventListener("submit", function() {{
      collect();
    }});
  }}

  collect();
}})();
</script>
"""

        return f"""
<div class="cloze-problem">
  <div class="cloze-text" style="line-height:2.2;">
    {prompt_html}
  </div>
  {hidden}
</div>
{script}
"""

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        Frontend pre-submit validation.
        Must handle TaskInput object OR dict-like (some paths).
        """
        pid = self.get_id()

        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid)

        if raw is None or raw == "":
            return False

        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return False

        if not isinstance(obj, dict):
            return False

        text = (self._data or {}).get("text", "") or ""
        slots = [m.group(1) for m in _TOKEN_RE.finditer(text)]
        for s in slots:
            v = obj.get(str(s), "")
            if v is None or str(v).strip() == "":
                return False

        return True
