# -*- coding: utf-8 -*-
import html
import logging
import re

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    """
    Frontend display + input parsing/validation.

    IMPORTANT:
    - Must be instantiable by frontend Task() code:
        (problemid, problem_content, translations, task_fs)
    - Must implement DisplayableProblem abstract methods.
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        # This MUST be called so self._data exists and translations/taskfs are wired.
        super().__init__(problemid, problem_content, translations, task_fs)

    # ---------- helpers (frontend side) ----------

    def _expected_slots(self):
        """Slots that exist in the text (e.g., {'1','2'})."""
        text = (self._data or {}).get("text", "") or ""
        return [m.group(1) for m in _TOKEN_RE.finditer(text)]

    def _extract_from_task_input(self, task_input):
        """
        task_input is sometimes a TaskInput-like object, sometimes a dict.
        We normalize it into dict[slot] = answer.
        """
        pid = self.get_id()
        slots = self._expected_slots()
        out = {}

        # Case A: TaskInput-like (has get_problem_input)
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
            # Depending on INGI version/plugins, raw may already be a dict,
            # OR it may be None and we must reconstruct from the flat form dict.
            if isinstance(raw, dict):
                for s in slots:
                    out[s] = (raw.get(s) or "").strip()
                return out

        # Case B: dict-like: keys may be "p1[1]" or "p1__1" or even nested dict at pid
        if isinstance(task_input, dict):
            # nested dict under pid?
            nested = task_input.get(pid)
            if isinstance(nested, dict):
                for s in slots:
                    out[s] = (nested.get(s) or "").strip()
                return out

            # flat form keys: p1[1] and p1[2]
            for s in slots:
                v = task_input.get(f"{pid}[{s}]")
                if v is None:
                    # fallback style: p1__1
                    v = task_input.get(f"{pid}__{s}")
                out[s] = (v or "").strip()

        return out

    # ---------- required frontend hooks ----------

    def input_type(self):
        # Must match backend: we want a dict of slot->answer
        return "dict"

    def get_text_fields(self):
        return ["name", "text"]

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        """
        Frontend validation that decides whether the submission is "complete".
        This is what controls the red banner.
        """
        try:
            answers = self._extract_from_task_input(task_input)
            slots = self._expected_slots()

            # Debug if you're still seeing the red banner:
            log.debug("CLOZE input_is_consistent pid=%s slots=%s answers=%s task_input_type=%s",
                      self.get_id(), slots, answers, type(task_input))

            # require every slot to be filled (non-empty)
            for s in slots:
                if not (answers.get(s) or "").strip():
                    return False
            return True
        except Exception:
            log.exception("CLOZE input_is_consistent crashed")
            return False

    def check_answer(self, task_input, language):
        """
        Optional frontend-side check (some INGI flows call it).
        We just say OK and let the backend grade.
        """
        return True, ""

    def show_input(self, template_helper, language, seed):
        """
        Render the stem text, replacing tokens with <input> fields.
        IMPORTANT: names are p1[1], p1[2], ... so they naturally form a dict.
        """
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
