# -*- coding: utf-8 -*-
import html
import re

from inginious.frontend.task_problems import DisplayableProblem
from .cloze_problem_backend import ClozeProblem

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")

def _iter_expected_slots(text: str):
    for m in _TOKEN_RE.finditer(text or ""):
        yield m.group(1)  # slot id string like "1", "2", ...

def _extract_slots_from_request_mapping(pid: str, mapping):
    """
    Extract slot answers from a dict-like mapping that may contain:
      - keys like "p1[1]"  (from <input name="p1[1]">)
      - keys like "p1__1"
      - key "p1" containing nested dict {"1": "...", "2": "..."}
    Returns a dict {slot: str}.
    """
    if mapping is None:
        return {}

    # Case 1: already normalized: {"p1": {"1": "..."}}
    try:
        nested = mapping.get(pid)
        if isinstance(nested, dict):
            # ensure values are strings
            out = {}
            for k, v in nested.items():
                out[str(k)] = "" if v is None else str(v)
            return out
    except Exception:
        pass

    out = {}

    # Case 2: direct bracket keys "p1[1]"
    try:
        # mapping might be werkzeug MultiDict: supports .items()
        for k, v in getattr(mapping, "items", lambda: [])():
            if not isinstance(k, str):
                continue

            # p1[1]
            if k.startswith(pid + "[") and k.endswith("]"):
                slot = k[len(pid) + 1 : -1]
                out[str(slot)] = "" if v is None else str(v)
                continue

            # p1__1
            if k.startswith(pid + "__"):
                slot = k[len(pid) + 2 :]
                out[str(slot)] = "" if v is None else str(v)
                continue
    except Exception:
        pass

    return out

class DisplayableClozeProblem(DisplayableProblem, ClozeProblem):
    """
    Frontend problem type.

    Important:
    - Must NOT be abstract: implement required methods with compatible signatures.
    - Must ensure self._data exists (Problem sets it).
    """

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def __init__(self, problemid, problem_content, translations, task_fs):
        # Explicitly init BOTH bases to ensure _data and DisplayableProblem state exist.
        ClozeProblem.__init__(self, problemid, problem_content, translations, task_fs)
        DisplayableProblem.__init__(self, problemid, problem_content, translations, task_fs)

    # ---- Required by DisplayableProblem / frontend flow ----

    def get_text_fields(self):
        # match backend: fields that are "textual"/translatable
        return ["name", "text"]

    def input_type(self):
        # frontend submits multiple blanks; treat as dict
        return "dict"

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None, *args, **kwargs):
        """
        Called by the webapp with (task_input, allowed_exts, max_size).

        task_input is often a dict / MultiDict of *raw* POST fields at this stage.
        We enforce: every cloze slot found in the text has a non-empty answer.
        """
        pid = self.get_id()
        text = (self._data or {}).get("text", "") or ""
        expected = list(_iter_expected_slots(text))

        # If there are no slots, it's trivially consistent
        if not expected:
            return True

        slots = _extract_slots_from_request_mapping(pid, task_input)

        # All expected slots must exist and be non-empty
        for slot in expected:
            if (slots.get(slot) or "").strip() == "":
                return False

        return True

    def check_answer(self, task_input, language=None, seed=None, *args, **kwargs):
        """
        Some INGInious flows call a frontend "check" method.
        We'll just say "ok" and let real grading happen in the backend container.
        """
        return True, ""

    def show_input(self, template_helper, language, seed):
        """
        Render the statement, replacing tokens with HTML <input> elements.
        Field names use bracket notation: p1[1], p1[2], ...
        """
        pid = self.get_id()
        text = (self._data or {}).get("text", "") or ""

        parts = []
        last = 0
        for m in _TOKEN_RE.finditer(text):
            parts.append(html.escape(text[last:m.start()]))

            slot = m.group(1)
            name = f"{pid}[{slot}]"

            parts.append(
                f'<input type="text" name="{html.escape(name)}" '
                f'class="form-control" '
                f'style="display:inline-block; width:18rem; max-width:100%; margin:0 0.25rem; vertical-align:middle;" />'
            )
            last = m.end()

        parts.append(html.escape(text[last:]))

        label = html.escape((self._data or {}).get("name", "Question") or "Question")

        return (
            f'<div class="panel panel-default">'
            f'  <div class="panel-heading">{label}</div>'
            f'  <div class="panel-body" style="line-height:2.2;">'
            f'    {"".join(parts)}'
            f'  </div>'
            f'</div>'
        )

    # Optional editor support
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
