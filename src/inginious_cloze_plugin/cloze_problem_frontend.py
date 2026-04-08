# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import logging
import re

try:
    from inginious.frontend.task_problems import DisplayableProblem
except ModuleNotFoundError:  # pragma: no cover - enables local tests without INGInious installed
    class DisplayableProblem(object):
        def __init__(self, problemid=None, problem_content=None, translations=None, task_fs=None):
            self._id = problemid
            self._data = problem_content or {}
            self._task_fs = task_fs

        def get_id(self):
            return self._id

from .cloze_problem_backend import (
    ClozeProblem,
    build_variant,
    expected_slots_from_text,
    load_variants,
)

log = logging.getLogger(__name__)

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
        self._data = self.parse_problem(problem_content or {})
        self._task_fs = task_fs

    def _extract_answers(self, task_input):
        pid = self.get_id()
        variant = build_variant(self._data, self._task_fs, submitted_variant=None)
        out = {}

        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
            if isinstance(raw, dict):
                for slot in variant["slots"]:
                    out[slot] = (raw.get(slot) or "").strip()
                if raw.get("__variant") is not None:
                    out["__variant"] = str(raw["__variant"])
                return out

        if isinstance(task_input, dict):
            nested = task_input.get(pid)
            if isinstance(nested, dict):
                for slot in variant["slots"]:
                    out[slot] = (nested.get(slot) or "").strip()
                if nested.get("__variant") is not None:
                    out["__variant"] = str(nested["__variant"])
                return out

            for slot in variant["slots"]:
                value = task_input.get(f"{pid}[{slot}]")
                if value is None:
                    value = task_input.get(f"{pid}__{slot}")
                out[slot] = (value or "").strip()

            variant_value = task_input.get(f"{pid}[__variant]")
            if variant_value is None:
                variant_value = task_input.get(f"{pid}__variant")
            if variant_value is not None:
                out["__variant"] = str(variant_value)

        return out

    def adapt_input_for_backend(self, task_input):
        return self._extract_answers(task_input)

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        try:
            answers = self._extract_answers(task_input)
            variant = build_variant(
                self._data,
                self._task_fs,
                submitted_variant=answers.get("__variant"),
            )

            log.debug("CLOZE consistent? pid=%s variant=%s slots=%s answers=%s input_type=%s",
                      self.get_id(), variant["index"], variant["slots"], answers, type(task_input))

            return all((answers.get(slot) or "").strip() for slot in variant["slots"])
        except Exception:
            log.exception("CLOZE input_is_consistent crashed")
            return False

    def check_answer(self, task_input, language):
        return ClozeProblem.check_answer(self, self._extract_answers(task_input), language)

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        variant = build_variant(self._data, self._task_fs, seed=seed)
        variants = load_variants(self._data, self._task_fs)

        # We keep the default render deterministic from the server seed, but also expose the
        # full variant payload so the browser can honor INGInious random inputs if present.
        variant_payload = json.dumps([
            {
                "index": index,
                "name": item.get("name"),
                "text": item.get("text", ""),
                "slots": expected_slots_from_text(item.get("text", "")),
            }
            for index, item in enumerate(variants)
        ])

        label = html.escape(variant.get("name") or (self._data or {}).get("name", "Question") or "Question")
        default_markup = self._render_variant_markup(pid, variant["text"])
        default_index = variant["index"]

        return """
            <div class="panel panel-default cloze-panel" id="{panel_id}">
              <div class="panel-heading">{label}</div>
              <div class="panel-body" style="line-height:2.2;">
                <input type="hidden" name="{pid}[__variant]" value="{default_index}" />
                <div class="cloze-problem-content">{markup}</div>
              </div>
            </div>
            <script>
            (function() {{
              var panel = document.getElementById({panel_id_json});
              if (!panel) return;

              var hidden = panel.querySelector('input[name="{pid}[__variant]"]');
              var content = panel.querySelector('.cloze-problem-content');
              var variants = {variants_json};
              if (!hidden || !content || !variants.length) return;

              var randomInputs = window.input && window.input['@random'];
              var variantIndex = {default_index};

              if (Array.isArray(randomInputs) && randomInputs.length > 0) {{
                var numeric = Number(randomInputs[0]);
                if (!Number.isNaN(numeric)) {{
                  variantIndex = Math.floor(Math.abs(numeric) * variants.length) % variants.length;
                }}
              }}

              var variant = variants[variantIndex] || variants[{default_index}] || variants[0];
              hidden.value = String(variant.index);
              content.innerHTML = '';

              var tokenRe = /\\{{(\\d+):(SHORTANSWER|NUMERICAL):=([^}}]+)\\}}/g;
              var text = variant.text || '';
              var lastIndex = 0;
              var match;

              while ((match = tokenRe.exec(text)) !== null) {{
                if (match.index > lastIndex) {{
                  content.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
                }}

                var input = document.createElement('input');
                input.type = 'text';
                input.name = '{pid}[' + match[1] + ']';
                input.className = 'form-control';
                input.style.display = 'inline-block';
                input.style.width = '12rem';
                input.style.margin = '0 0.25rem';
                content.appendChild(input);
                lastIndex = tokenRe.lastIndex;
              }}

              if (lastIndex < text.length) {{
                content.appendChild(document.createTextNode(text.slice(lastIndex)));
              }}
            }})();
            </script>
        """.format(
            panel_id=html.escape("{}-panel".format(pid)),
            panel_id_json=json.dumps("{}-panel".format(pid)),
            pid=html.escape(pid),
            label=label,
            markup=default_markup,
            default_index=default_index,
            variants_json=variant_payload,
        )

    def _render_variant_markup(self, pid, text):
        parts = []
        last = 0
        for match in _TOKEN_RE.finditer(text or ""):
            parts.append(html.escape(text[last:match.start()]))
            slot = match.group(1)
            parts.append(
                '<input type="text" name="{name}" class="form-control" '
                'style="display:inline-block; width:12rem; margin:0 0.25rem;" />'.format(
                    name=html.escape("{}[{}]".format(pid, slot))
                )
            )
            last = match.end()

        parts.append(html.escape((text or "")[last:]))
        return "".join(parts)

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key == "text":
            return '<textarea name="text" class="form-control" rows="6"></textarea>'
        if key == "name":
            return '<input type="text" name="name" class="form-control" />'
        if key == "variants_file":
            return '<input type="text" name="variants_file" class="form-control" />'
        return ""

    @classmethod
    def show_editbox_templates(cls, template_helper, key, language):
        return ""
