# -*- coding: utf-8 -*-
import html
import re

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem  # ✅ REQUIRED (fixes your NameError)

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        # initialize both parents properly (INGInious expects Problem to get translations/taskfs)
        ClozeProblem.__init__(self, problemid, problem_content, translations, task_fs)
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

        # always preserve raw YAML
        self._data = problem_content

    # ---------- helper: translated field safe getter ----------
    def _get_field(self, key, language, default=""):
        data = getattr(self, "_data", None) or {}
        val = data.get(key)

        if isinstance(val, dict):
            if language in val and val[language]:
                return val[language]
            if "en" in val and val["en"]:
                return val["en"]
            for _, v in val.items():
                if v:
                    return v
            return default

        return val if val else default

    # ---------- webapp validation hook ----------
    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        INGInious frontend calls: problem.input_is_consistent(task_input, allowed_ext, max_size)
        task_input is a dict-like mapping of submitted fields.
        Our inputs are named:  <problemid>[<slot>]
        """
        pid = self.get_id()

        # accept either mapping or TaskInput-like
        if hasattr(task_input, "get"):
            keys = list(task_input.keys())
        else:
            return False

        prefix = f"{pid}["
        has_any = any(k.startswith(prefix) for k in keys)
        return has_any  # require at least one cloze field submitted

    # ---------- abstract methods required by DisplayableProblem ----------
    def get_text_fields(self):
        return ["name", "text"]

    def input_type(self):
        return "dict"

    def check_answer(self, task_input, language):
        # frontend “check” is optional; let backend grading do the real work
        return True, ""

    # ---------- rendering ----------
    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = self._get_field("text", language, default="")
        label = self._get_field("name", language, default="Question")

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            input_name = f"{pid}[{slot}]"
            parts.append(
                f'<input type="text" name="{html.escape(input_name)}" class="form-control" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        return f"""
<div class="panel panel-default">
  <div class="panel-heading">{html.escape(label)}</div>
  <div class="panel-body" style="line-height:2.2;">
    {''.join(parts)}
  </div>
</div>
"""

    # ---------- optional editor support ----------
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
