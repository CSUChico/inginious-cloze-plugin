# -*- coding: utf-8 -*-
from __future__ import annotations

import html

try:
    from inginious.frontend.environment_types.env_type import FrontendEnvType
except ModuleNotFoundError:  # pragma: no cover - local tests without INGInious
    class FrontendEnvType(object):
        pass


class ClozeFrontendEnv(FrontendEnvType):
    @property
    def id(self):
        return "cloze"

    @property
    def name(self):
        return "Cloze grader"

    def check_task_environment_parameters(self, data):
        cleaned = dict(data or {})
        variants_file = cleaned.get("variants_file", "")
        if variants_file is None:
            variants_file = ""
        cleaned["variants_file"] = str(variants_file).strip()
        return cleaned

    def studio_env_template(self, templator, task, allow_html: bool):
        current = {}
        get_params = getattr(task, "get_environment_parameters", None)
        if callable(get_params):
            try:
                current = get_params() or {}
            except Exception:
                current = {}

        variants_file = html.escape(str(current.get("variants_file", "") or ""))
        return """
<div class="form-group row">
  <label for="env-cloze-variants-file" class="col-sm-2 control-label">Variants file</label>
  <div class="col-sm-10">
    <input type="text" class="form-control" id="env-cloze-variants-file"
           name="envparams[cloze][variants_file]" value="{variants_file}"
           placeholder="cloze_variants.json" />
    <p class="help-block">Task file containing the randomized cloze variant definitions.</p>
  </div>
</div>
""".format(variants_file=variants_file)
