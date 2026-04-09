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

_TOKEN_RE = re.compile(r"\{(\d+):(SHORTANSWER|NUMERICAL|MULTICHOICE):=([^}]+)\}")


class DisplayableClozeProblem(ClozeProblem, DisplayableProblem):
    def input_type(self):
        return str

    def get_text_fields(self):
        return ["name", "text", "variants_file"]

    def show_editbox_templates(self, template_helper, language):
        return {
            "Cloze (basic)": (
                "type: cloze\n"
                "text: |\n"
                "  Water is {1:SHORTANSWER:=H2O}. Boiling point is {2:NUMERICAL:=100} C. State is {3:MULTICHOICE:=none~overflow~=underflow}.\n"
            )
        }

    @classmethod
    def show_editbox(cls, template_helper, key, language):
        if key != "cloze":
            return ""
        return """
<div class="form-group row">
  <label for="text-PID" class="col-sm-2 control-label">Text</label>
  <div class="col-sm-10">
    <textarea class="form-control" id="text-PID" name="problem[PID][text]" rows="8"
              placeholder="Example: The capital of France is {1:SHORTANSWER:=Paris}."></textarea>
    <p class="help-block">
      Use tokens like <code>{1:SHORTANSWER:=H2O}</code>, <code>{2:NUMERICAL:=100}</code>, or
      <code>{3:MULTICHOICE:=none~overflow~=underflow}</code>.
      HTML is allowed, so you can build tables and formatted layouts directly in the prompt.
    </p>
  </div>
</div>
<div class="form-group row">
  <label for="variants-file-PID" class="col-sm-2 control-label">Variants file</label>
  <div class="col-sm-10">
    <input type="text" class="form-control" id="variants-file-PID" name="problem[PID][variants_file]"
           placeholder="cloze_variants.json" />
    <p class="help-block">Optional task file containing a JSON variants list for randomized prompts.</p>
  </div>
</div>
"""

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
            parts.append((text or "")[last:match.start()])

            slot = match.group(1)
            kind = match.group(2)
            input_type = "text"
            step_attr = ""
            if kind == "NUMERICAL":
                input_type = "number"
                step_attr = ' step="any"'

            label_text = "Blank {}".format(slot)
            parts.append(
                '<label class="sr-only" for="{element_id}">{label_text}</label>'
                '<input type="{input_type}" class="form-control cloze-input" '
                'data-slot="{slot}" id="{element_id}" aria-label="{label_text}"{step_attr} '
                'style="display:inline-block; width:auto; min-width:140px; vertical-align:middle;">'.format(
                    input_type=input_type,
                    slot=html.escape(slot),
                    element_id=html.escape("{}_slot_{}".format(uniq_prefix, slot)),
                    label_text=html.escape(label_text),
                    step_attr=step_attr,
                )
            )
            last = match.end()

        parts.append((text or "")[last:])
        return "".join(parts)

    def show_input(self, template_helper, language, seed):
        pid = self.get_id()
        variants = load_variants(self._data, self._task_fs)
        # Use a deterministic fallback variant in the initial HTML. The live page script
        # can then replace it with the exact submitted or randomized variant once window.input
        # is available, avoiding a misleading random prompt during page load/review.
        default_variant = build_variant(self._data, self._task_fs, seed="")
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
  window.__clozeProblemInstances = window.__clozeProblemInstances || {{}};

  var hidden = document.getElementById("{uniq}_json");
  if (!hidden) return;

  var variants = {variants_json};
  var tokenRe = /\\{{(\\d+):(SHORTANSWER|NUMERICAL|MULTICHOICE):=([^}}]+)\\}}/g;
  var textRoot = document.getElementById("{uniq}_text");
  var titleRoot = document.getElementById("{uniq}_title");

  function escapeHtml(value) {{
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }}

  function renderMultichoice(slot, rhs) {{
    var options = rhs.split("~").map(function (item) {{
      item = item.trim();
      if (!item) return null;
      if (item.charAt(0) === "=") {{
        item = item.slice(1).trim();
      }}
      item = item.split("#", 1)[0].trim();
      return item || null;
    }}).filter(Boolean);

    var labelText = 'Blank ' + slot;
    var html = '<label class="sr-only" for="{uniq}_slot_' + slot + '">' + escapeHtml(labelText) + '</label>';
    html += '<select class="form-control cloze-input" data-slot="' + slot + '" id="{uniq}_slot_' + slot + '"' +
      ' aria-label="' + escapeHtml(labelText) + '"' +
      ' style="display:inline-block; width:auto; min-width:140px; vertical-align:middle;">';
    html += '<option value=""></option>';
    options.forEach(function (option) {{
      html += '<option value="' + escapeHtml(option) + '">' + escapeHtml(option) + '</option>';
    }});
    html += '</select>';
    return html;
  }}

  function collect() {{
    var current = {{}};
    try {{
      current = JSON.parse(hidden.value || "{{}}");
    }} catch (err) {{
      current = {{}};
    }}

    var inputs = document.querySelectorAll('input.cloze-input[id^="{uniq}_slot_"]');
    var selects = document.querySelectorAll('select.cloze-input[id^="{uniq}_slot_"]');
    inputs.forEach(function(inp) {{
      current[inp.getAttribute("data-slot")] = inp.value;
    }});
    selects.forEach(function(inp) {{
      current[inp.getAttribute("data-slot")] = inp.value;
    }});
    hidden.value = JSON.stringify(current);
    return current;
  }}

  function renderVariant(index, current) {{
    var variant = variants[index] || variants[0];
    if (!variant || !textRoot) return;

    if (!current) {{
      try {{
        current = JSON.parse(hidden.value || "{{}}");
      }} catch (err) {{
        current = {{}};
      }}
    }}
    current.__variant = String(variant.index);

    if (titleRoot && variant.name) {{
      titleRoot.textContent = variant.name;
    }}

    var text = variant.text || "";
    textRoot.innerHTML = text.replace(tokenRe, function (_, slot, kind, rhs) {{
      if (kind === "MULTICHOICE") {{
        return renderMultichoice(slot, rhs);
      }}
      var inputType = kind === "NUMERICAL" ? "number" : "text";
      var stepAttr = inputType === "number" ? ' step="any"' : "";
      var labelText = 'Blank ' + slot;
      return '<label class="sr-only" for="{uniq}_slot_' + slot + '">' + escapeHtml(labelText) + '</label>' +
        '<input type="' + inputType + '" class="form-control cloze-input" data-slot="' + slot + '"' +
        ' id="{uniq}_slot_' + slot + '" aria-label="' + escapeHtml(labelText) + '"' + stepAttr +
        ' style="display:inline-block; width:auto; min-width:140px; vertical-align:middle;">';
    }});

    var inputs = textRoot.querySelectorAll("input.cloze-input, select.cloze-input");
    inputs.forEach(function(input) {{
      var slot = input.getAttribute("data-slot");
      input.value = current[slot] || "";
    }});

    hidden.value = JSON.stringify(current);
  }}

  function normalizeAnswers(rawValue) {{
    if (!rawValue) {{
      return {{}};
    }}
    if (typeof rawValue === "string") {{
      try {{
        rawValue = JSON.parse(rawValue);
      }} catch (err) {{
        return {{}};
      }}
    }}
    if (!rawValue || typeof rawValue !== "object") {{
      return {{}};
    }}
    var normalized = {{}};
    Object.keys(rawValue).forEach(function (key) {{
      var value = rawValue[key];
      normalized[String(key)] = value == null ? "" : String(value);
    }});
    return normalized;
  }}

  function setAnswers(rawValue) {{
    var current = normalizeAnswers(rawValue);
    var variantIndex = Number(current.__variant);
    if (Number.isNaN(variantIndex)) {{
      variantIndex = {default_index};
    }}
    renderVariant(variantIndex, current);
  }}

  var instance = {{
    collect: collect,
    setAnswers: setAnswers
  }};
  window.__clozeProblemInstances["{pid}"] = instance;

  window.load_input_cloze = function (problemId, rawValue) {{
    var target = window.__clozeProblemInstances[String(problemId)];
    if (target) {{
      target.setAnswers(rawValue);
    }}
  }};

  window.load_feedback_cloze = function (problemId, rawFeedback) {{
    var target = window.__clozeProblemInstances[String(problemId)];
    if (target) {{
      return;
    }}
  }};

  var variantIndex = {default_index};
  if (window.input && window.input['@state']) {{
    try {{
      var parsedState = window.input['@state'];
      if (typeof parsedState === "string") {{
        parsedState = JSON.parse(parsedState);
      }}
      if (parsedState && parsedState["{pid}"] && parsedState["{pid}"].variant !== undefined) {{
        var stateVariant = Number(parsedState["{pid}"].variant);
        if (!Number.isNaN(stateVariant) && stateVariant >= 0 && stateVariant < variants.length) {{
          variantIndex = stateVariant;
        }}
      }
    }} catch (err) {{
      // Ignore malformed state and fall back below.
    }}
  }}
  if (window.input && Array.isArray(window.input['@random']) && window.input['@random'].length > 0 && variantIndex === {default_index}) {{
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
            pid=pid,
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
