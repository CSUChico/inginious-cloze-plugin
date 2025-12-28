# -*- coding: utf-8 -*-
"""
Frontend (webapp/UI) Cloze problem for INGInious 0.9.x.

- Renders multiple visible blanks.
- Submits ONE hidden input named <problemid> containing JSON of all blank values.
- Forces hidden field update on input AND on form submit.
- input_is_consistent() accepts string/list/dict shapes returned by INGInious.
"""

import html
import json
import re

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)
        # Make sure _data always exists (several places expect it)
        self._data = problem_content or {}

    # INGInious expects a single field for custom types to pass consistency checks
    def input_type(self):
        return "string"

    def _extract_raw_value(self, raw):
        """
        INGInious 0.9.x may provide:
          - string
          - list of strings
          - dict-like payloads in some paths
        Normalize to a single string (or "").
        """
        if raw is None:
            return ""

        # Most common: already a string
        if isinstance(raw, str):
            return raw

        # Sometimes: list (take first non-empty)
        if isinstance(raw, (list, tuple)):
            for item in raw:
                s = self._extract_raw_value(item)
                if str(s).strip():
                    return s
            return ""

        # Sometimes: dict-ish
        if isinstance(raw, dict):
            # try typical keys
            for k in ("value", "answer", "data", "raw"):
                if k in raw:
                    return self._extract_raw_value(raw.get(k))
            # fallback: JSON dump (at least non-empty)
            try:
                return json.dumps(raw)
            except Exception:
                return ""

        # fallback
        return str(raw)

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        pid = self.get_id()

        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid)

        s = self._extract_raw_value(raw).strip()
        return bool(s)

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = (self._data or {}).get("text", "") or ""
        label = html.escape((self._data or {}).get("name", "Question") or "Question")

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            # Visible inputs have NO name attribute (we only submit the hidden one).
            parts.append(
                f'<input type="text" class="form-control cloze-input" '
                f'data-slot="{html.escape(slot)}" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        # Use a unique DOM id so multiple cloze problems on a page don't collide
        root_id = f"cloze-root-{pid}"

        return f"""
<div class="panel panel-default" id="{html.escape(root_id)}">
  <div class="panel-heading">{label}</div>
  <div class="panel-body" style="line-height:2.2;">
    {''.join(parts)}
    <input type="hidden" name="{html.escape(pid)}" id="cloze-hidden-{html.escape(pid)}" />
  </div>
</div>

<script>
(function() {{
  // Find our container deterministically
  var root = document.getElementById("{root_id}");
  if (!root) return;

  var hidden = root.querySelector('input[type="hidden"][name="{pid}"]');
  var inputs = root.querySelectorAll('input.cloze-input');

  function updateHidden() {{
    var obj = {{}};
    for (var i = 0; i < inputs.length; i++) {{
      var inp = inputs[i];
      obj[inp.getAttribute("data-slot")] = inp.value || "";
    }}
    hidden.value = JSON.stringify(obj);
  }}

  // Update on every keystroke/change
  for (var i = 0; i < inputs.length; i++) {{
    inputs[i].addEventListener("input", updateHidden);
    inputs[i].addEventListener("change", updateHidden);
  }}

  // CRITICAL: update right before the form submits
  var form = root.closest("form");
  if (form) {{
    form.addEventListener("submit", function() {{
      updateHidden();
    }});
  }}

  // Set initial value so consistency passes even if user edits quickly
  updateHidden();
}})();
</script>
"""

    # editor support (minimal)
    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key == "name":
            return '<input name="name" class="form-control" />'
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
