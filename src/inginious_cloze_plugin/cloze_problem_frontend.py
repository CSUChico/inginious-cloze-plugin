# -*- coding: utf-8 -*-
import html
import logging
import re

from inginious.frontend.task_problems import DisplayableProblem

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class DisplayableClozeProblem(DisplayableProblem):
    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        # IMPORTANT: explicitly call DisplayableProblem init (do NOT rely on super/MRO)
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

        # Belt+suspenders: ensure _data always exists
        self._data = problem_content or {}

    # --- required by DisplayableProblem / frontend expectations
    def input_type(self):
        return "dict"

    def get_text_fields(self):
        return ["name", "text"]

    def check_answer(self, task_input, language):
        # Frontend "quick check" is optional. Let backend grade.
        return True, ""

    # ---------- helpers ----------
    def _expected_slots(self):
        text = (self._data or {}).get("text", "") or ""
        return [m.group(1) for m in _TOKEN_RE.finditer(text)]

    def _extract_answers(self, task_input):
        """
        Normalize form submission into {"1": "...", "2": "..."}.
        task_input may be dict-like or TaskInput-like depending on flow/version.
        """
        pid = self.get_id()
        slots = self._expected_slots()
        out = {}

        # TaskInput-like
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
            if isinstance(raw, dict):
                for s in slots:
                    out[s] = (raw.get(s) or "").strip()
                return out

        # dict-like
        if isinstance(task_input, dict):
            # nested dict under pid?
            nested = task_input.get(pid)
            if isinstance(nested, dict):
                for s in slots:
                    out[s] = (nested.get(s) or "").strip()
                return out

            # flat form: p1[1] / p1[2]
            for s in slots:
                v = task_input.get(f"{pid}[{s}]")
                if v is None:
                    # fallback: p1__1
                    v = task_input.get(f"{pid}__{s}")
                out[s] = (v or "").strip()

        return out

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        Controls the red banner ("Please answer all questions...").
        Must return True when all blanks are filled.
        """
        try:
            slots = self._expected_slots()
            answers = self._extract_answers(task_input)

            log.debug("CLOZE consistent? pid=%s slots=%s answers=%s input_type=%s",
                      self.get_id(), slots, answers, type(task_input))

            # require all slots non-empty
            for s in slots:
                if not (answers.get(s) or "").strip():
                    return False
            return True
        except Exception:
            log.exception("CLOZE input_is_consistent crashed")
            return False

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        text = (self._data or {}).get("text", "") or ""

        parts = []
        last = 0

        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            input_name = f"{pid}[{slot}]"

            parts.append(
                f'<input type="text" name="{input_name}" class="form-control" '
                f'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        label = html.escape((self._data or {}).get("name", "Question") or "Question")
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
            return '<input type="text" name="name" class="form-control" />'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
