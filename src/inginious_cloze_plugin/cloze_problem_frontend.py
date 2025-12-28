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
    Frontend display for ClozeProblem.

    Renders:
      - visible <input> fields for each cloze blank
      - one hidden input containing JSON mapping slot->value (what backend reads)
    """

    # ---- Required by DisplayableProblem (abstract) ----
    def get_text_fields(self):
        """
        Return editable text fields for the task editor/export.
        INGInious uses this to know which fields are 'text-like' and translatable.
        """
        # "text" is the field in task.yaml/problem content that contains the cloze prompt
        return ["text"]

    # ---------------------------------------------------

    def __init__(self, problemid, problem_content, translations, taskfs):
        # IMPORTANT: ClozeProblem already calls Problem.__init__ correctly
        super().__init__(problemid, problem_content, translations, taskfs)

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def _render_prompt_with_inputs(self, text, html_name_prefix):
        """
        Replace tokens like {1:SHORTANSWER:=H2O} with <input ...>.
        """
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

            # Visible input: we DO NOT submit it directly to INGInious;
            # JS copies values into the hidden JSON field.
            parts.append(
                f'<input type="{input_type}" class="form-control cloze-input" '
                f'data-slot="{html.escape(slot)}" '
                f'id="{html_name_prefix}_slot_{html.escape(slot)}" '
                f'{step_attr} style="display:inline-block; width:auto; min-width:120px; vertical-align:middle;">'
            )

            last = m.end()

        parts.append(html.escape(text[last:]))
        return "".join(parts)

    def show_input(self, template_helper, language, seed):
        """
        Render HTML for the task page.
        The backend expects a single field named by problem id containing JSON:
          {"1":"...", "2":"..."}
        """
        data = self._data or {}
        text = data.get("text", "") or ""

        pid = self.get_id()

        # Unique prefix so multiple problems on same page don't collide
        uniq = f"cloze_{pid}_{uuid4().hex}"

        prompt_html = self._render_prompt_with_inputs(text, uniq)

        # Hidden field that INGInious will submit as problem input
        hidden = (
            f'<input type="hidden" name="{html.escape(pid)}" '
            f'id="{uniq}_json" value="{html.escape(json.dumps({}))}">'
        )

        # JS: copy all visible cloze inputs into JSON hidden field before submit,
        # and also on change so the value is always current.
        script = f"""
<script>
(function() {{
  var root = document.getElementById("{uniq}_json");
  if (!root) return;

  function collect() {{
    var inputs = document.querySelectorAll('input.cloze-input[id^="{uniq}_slot_"]');
    var obj = {{}};
    inputs.forEach(function(inp) {{
      var slot = inp.getAttribute("data-slot");
      obj[slot] = inp.value;
    }});
    root.value = JSON.stringify(obj);
  }}

  // Update on input
  document.addEventListener("input", function(ev) {{
    if (ev.target && ev.target.classList && ev.target.classList.contains("cloze-input")
        && ev.target.id.indexOf("{uniq}_slot_") === 0) {{
      collect();
    }}
  }});

  // Ensure update right before submit (covers autofill)
  var form = root.closest("form");
  if (form) {{
    form.addEventListener("submit", function() {{
      collect();
    }});
  }}

  // Initial populate
  collect();
}})();
</script>
"""

        # Wrap in a bootstrap-ish container; INGInious templates expect raw HTML
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
        Called by frontend BEFORE submission to validate required fields.
        Must accept task_input as TaskInput object (normal) OR a dict (some flows).
        """
        pid = self.get_id()

        # Read raw
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid)

        if raw is None or raw == "":
            return False

        # Must be JSON dict
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return False

        if not isinstance(obj, dict):
            return False

        # Must have all slots present and non-empty
        text = (self._data or {}).get("text", "") or ""
        slots = [m.group(1) for m in _TOKEN_RE.finditer(text)]
        for s in slots:
            v = obj.get(str(s), "")
            if v is None or str(v).strip() == "":
                return False

        return True
