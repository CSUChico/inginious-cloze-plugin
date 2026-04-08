# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from uuid import uuid4

try:
    from inginious.frontend.task_problems import DisplayableProblem
except ModuleNotFoundError:  # pragma: no cover - local tests without INGInious
    class DisplayableProblem(object):
        def __init__(self, problemid=None, problem_content=None, translations=None, taskfs=None):
            self._id = problemid
            self._data = problem_content or {}
            self._task_fs = taskfs

        def get_id(self):
            return self._id

from .cloze_problem_backend import ClozeProblem, build_variant, expected_slots_from_text, load_variants

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL):=([^}]+)\}")


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    def input_type(self):
        return str

    def get_text_fields(self):
        return ["text"]

    def show_editbox_templates(self, template_helper, language):
        return {
            "Cloze (basic)": (
                "type: cloze\n"
                "text: |\n"
                "  Water is {1:SHORTANSWER:=H2O}. Boiling point is {2:NUMERICAL:=100} C.\n"
            )
        }

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key == "name":
            return '<input type="text" name="name" class="form-control" />'
        if key == "text":
            return '<textarea name="text" class="form-control" rows="8"></textarea>'
        if key == "variants_file":
            return '<input type="text" name="variants_file" class="form-control" />'
        if key == "variants":
            return '<textarea name="variants" class="form-control" rows="10"></textarea>'
        return ""

    def __init__(self, problemid, problem_content, translations, taskfs):
        ClozeProblem.__init__(self, problemid, problem_content, translations, taskfs)
        self._task_fs = taskfs

    @classmethod
    def get_type(cls):
        return "cloze"

    @classmethod
    def get_type_name(cls, language):
        return "Cloze"

    def _render_prompt_with_inputs(self, text, uniq_prefix):
        parts = []
        last = 0

        for match in _TOKEN_RE.finditer(text or ""):
            parts.append(html.escape(text[last:match.start()]))

            slot = match.group(1)
            kind = match.group(2)
            input_type = "text"
            step_attr = ""
            if kind == "NUMERICAL":
                input_type = "number"
                step_attr = ' step="any"'

            parts.append(
                '<input type="{input_type}" class="form-control cloze-input" '
                'data-slot="{slot}" id="{element_id}"{step_attr} '
                'style="display:inline-block; width:auto; min-width:140px; vertical-align:middle;">'.format(
                    input_type=input_type,
                    slot=html.escape(slot),
                    element_id=html.escape("{}_slot_{}".format(uniq_prefix, slot)),
                    step_attr=step_attr,
                )
            )
            last = match.end()

        parts.append(html.escape((text or "")[last:]))
        return "".join(parts)

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        default_variant = build_variant(self._data, self._task_fs, seed=seed)
        variants = load_variants(self._data, self._task_fs)
        uniq = "cloze_{}_{}".format(pid, uuid4().hex)

        variant_payload = json.dumps([
            {
                "index": index,
                "name": item.get("name"),
                "text": item.get("text", ""),
                "slots": expected_slots_from_text(item.get("text", "")),
            }
            for index, item in enumerate(variants)
        ])

        prompt_html = self._render_prompt_with_inputs(default_variant["text"], uniq)
        label = html.escape(default_variant.get("name") or (self._data or {}).get("name", "Question") or "Question")
        hidden = '<input type="hidden" name="{name}" id="{element_id}" value="{value}">'.format(
            name=html.escape(pid),
            element_id=html.escape("{}_json".format(uniq)),
            value=html.escape(json.dumps({"__variant": default_variant["index"]})),
        )

        script = """
<script>
(function() {{
  var hidden = document.getElementById("{uniq}_json");
  if (!hidden) return;

  var variants = {variants_json};
  var tokenRe = /\\{{(\\d+):(SHORTANSWER|NUMERICAL):=([^}}]+)\\}}/g;
  var textRoot = document.getElementById("{uniq}_text");
  var titleRoot = document.getElementById("{uniq}_title");

  function collect() {{
    var current = {{}};
    try {{
      current = JSON.parse(hidden.value || "{{}}");
    }} catch (err) {{
      current = {{}};
    }}

    var inputs = document.querySelectorAll('input.cloze-input[id^="{uniq}_slot_"]');
    inputs.forEach(function(inp) {{
      current[inp.getAttribute("data-slot")] = inp.value;
    }});
    hidden.value = JSON.stringify(current);
  }}

  function renderVariant(index) {{
    var variant = variants[index] || variants[0];
    if (!variant || !textRoot) return;

    var current = {{}};
    try {{
      current = JSON.parse(hidden.value || "{{}}");
    }} catch (err) {{
      current = {{}};
    }}
    current.__variant = String(variant.index);

    if (titleRoot && variant.name) {{
      titleRoot.textContent = variant.name;
    }}

    textRoot.innerHTML = "";
    var text = variant.text || "";
    var lastIndex = 0;
    var match;

    while ((match = tokenRe.exec(text)) !== null) {{
      if (match.index > lastIndex) {{
        textRoot.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      }}

      var input = document.createElement("input");
      input.type = match[2] === "NUMERICAL" ? "number" : "text";
      if (input.type === "number") input.step = "any";
      input.className = "form-control cloze-input";
      input.setAttribute("data-slot", match[1]);
      input.id = "{uniq}_slot_" + match[1];
      input.style.display = "inline-block";
      input.style.width = "auto";
      input.style.minWidth = "140px";
      input.style.verticalAlign = "middle";
      input.value = current[match[1]] || "";
      textRoot.appendChild(input);
      lastIndex = tokenRe.lastIndex;
    }}

    if (lastIndex < text.length) {{
      textRoot.appendChild(document.createTextNode(text.slice(lastIndex)));
    }}

    hidden.value = JSON.stringify(current);
  }}

  var variantIndex = {default_index};
  if (window.input && Array.isArray(window.input['@random']) && window.input['@random'].length > 0) {{
    var numeric = Number(window.input['@random'][0]);
    if (!Number.isNaN(numeric) && variants.length > 0) {{
      variantIndex = Math.floor(Math.abs(numeric) * variants.length) % variants.length;
    }}
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

  renderVariant(variantIndex);
}})();
</script>
""".format(
            uniq=uniq,
            variants_json=variant_payload,
            default_index=default_variant["index"],
        )

        return """
<div class="panel panel-default cloze-problem">
  <div class="panel-heading" id="{uniq}_title">{label}</div>
  <div class="panel-body">
    <div class="cloze-text" id="{uniq}_text" style="line-height:2.2;">{prompt_html}</div>
    {hidden}
  </div>
</div>
{script}
""".format(
            uniq=html.escape(uniq),
            label=label,
            prompt_html=prompt_html,
            hidden=hidden,
            script=script,
        )

    def input_is_consistent(self, task_input, default_allowed_extension=None, default_max_size=None):
        pid = self.get_id()
        if hasattr(task_input, "get_problem_input"):
            raw = task_input.get_problem_input(pid)
        else:
            raw = task_input.get(pid) if isinstance(task_input, dict) else None

        if raw is None or raw == "":
            return False

        try:
            answers = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return False

        if not isinstance(answers, dict):
            return False

        variant = build_variant(self._data, self._task_fs, submitted_variant=answers.get("__variant"))
        for slot in variant["slots"]:
            value = answers.get(str(slot), "")
            if value is None or str(value).strip() == "":
                return False

        return True
