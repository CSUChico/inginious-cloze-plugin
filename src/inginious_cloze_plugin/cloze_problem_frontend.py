# -*- coding: utf-8 -*-
"""
Frontend (webapp/UI) Cloze problem for INGInious.

IMPORTANT (INGInious 0.9.x):
- Custom problems must submit ONE field per problem id.
- We render multiple visible blanks for the student, but maintain a single hidden
  <input name="<problemid>"> containing JSON of all blank values.
- This satisfies INGInious' frontend validation and removes the red banner.

Token syntax supported:
  {1:SHORTANSWER:=H2O|h2o}
  {2:NUMERICAL:=100±0.5}
"""

import html
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
        # DisplayableProblem's init wires translations + task fs and stores data
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

        # Ensure both sides have access to the YAML dict in the same attribute name.
        # (Some INGInious classes use _data; we make sure it's always set.)
        self._data = problem_content or {}

    # ===== Required by INGInious frontend plumbing =====

    def input_type(self):
        # Must be a single string field so platform validation works.
        return "string"

    def get_text_fields(self):
        return ["name", "text"]

    def check_answer(self, task_input, language):
        """
        Optional quick-check hook; keep permissive.
        Real grading happens in backend container evaluation.
        """
        return True, ""

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        INGInious calls this with (task_input, allowed_exts, max_size).

        task_input may be a TaskInput-like object OR a raw dict, depending on code path.
        We consider consistent if the single hidden field for this problem is non-empty.
        """
        pid = self.get_id()

        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid)

        return bool(raw and str(raw).strip())

    # ===== Rendering =====

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        data = getattr(self, "_data", {}) or {}
        text = data.get("text", "") or ""

        parts = []
        last = 0
        slots = []

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            slots.append(slot)

            # visible blank - NO name attribute!
            # (We only submit via the hidden JSON field named pid.)
            parts.append(
                f'<input type="text" class="form-control cloze-input" '
                f'data-slot="{html.escape(slot)}" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        label = html.escape(data.get("name", "Question"))

        # One hidden field that will be submitted as the problem answer
        # hidden[name=pid] must exist for INGInious consistency checks to pass.
        return f"""
<div class="panel panel-default">
  <div class="panel-heading">{label}</div>
  <div class="panel-body" style="line-height:2.2;">
    {''.join(parts)}
    <input type="hidden" name="{html.escape(pid)}" id="{html.escape(pid)}" />
  </div>
</div>

<script>
(function(){{
  // Find the panel body that contains this script tag
  const root = document.currentScript.closest('.panel');
  if (!root) return;

  const hidden = root.querySelector('input[type="hidden"][name="{pid}"]');
  const inputs = root.querySelectorAll('input.cloze-input');

  function updateHidden(){{
    const obj = {{}};
    inputs.forEach((inp) => {{
      obj[inp.dataset.slot] = inp.value || "";
    }});
    hidden.value = JSON.stringify(obj);
  }}

  inputs.forEach((inp) => inp.addEventListener("input", updateHidden));
  updateHidden();
}})();
</script>
"""

    # ===== Optional editor support (can be minimal) =====

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
