# -*- coding: utf-8 -*-
import html
import re

from inginious.frontend.task_problems import DisplayableProblem
from inginious.common.tasks_problems import Problem

from .cloze_problem_backend import ClozeProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

def _coerce_problem_inputs(task_input, pid):
    """
    Normalize whatever INGInious passes into {slot: value}.
    - Sometimes task_input is a TaskInput (has get_problem_input)
    - Sometimes it's a dict-like mapping
    """
    # TaskInput object path
    if hasattr(task_input, "get_problem_input"):
        raw = task_input.get_problem_input(pid)
        if isinstance(raw, dict):
            return {str(k): ("" if v is None else str(v)) for k, v in raw.items()}
        if raw is None:
            return {}
        return {"1": str(raw)}

    # Dict-like path (Flask form dict)
    if not hasattr(task_input, "get"):
        return {}

    out = {}

    # Preferred naming: p1[1], p1[2], ...
    prefix = f"{pid}["
    for k in task_input.keys():
        if k.startswith(prefix) and k.endswith("]"):
            slot = k[len(prefix):-1]
            out[str(slot)] = "" if task_input.get(k) is None else str(task_input.get(k))

    # Fallback: p1__1, p1__2, ...
    if not out:
        prefix2 = f"{pid}__"
        for k in task_input.keys():
            if k.startswith(prefix2):
                slot = k[len(prefix2):]
                out[str(slot)] = "" if task_input.get(k) is None else str(task_input.get(k))

    # Last fallback: p1 (single field)
    if not out and pid in task_input:
        out["1"] = "" if task_input.get(pid) is None else str(task_input.get(pid))

    return out


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        # CRITICAL: Problem sets self._data
        Problem.__init__(self, problemid, problem_content)

        # DisplayableProblem sets frontend-specific things
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

    # Must match frontend call signature
    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        pid = self.get_id()
        values = _coerce_problem_inputs(task_input, pid)
        return isinstance(values, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in values.items())

    def get_text_fields(self):
        return ["name", "text"]

    def input_type(self):
        return "dict"

    # Needed so class is not abstract (some versions treat DisplayableProblem as abstract)
    def check_answer(self, task_input, language):
        return True, ""

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        data = getattr(self, "_data", None) or {}
        text = data.get("text", "") or ""

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            input_name = f"{pid}[{slot}]"
            parts.append(
                f'<input type="text" name="{html.escape(input_name)}" '
                f'class="form-control" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        label = html.escape(data.get("name", "Question"))
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
        if key == "name":
            return '<input type="text" name="name" class="form-control" />'
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
