# -*- coding: utf-8 -*-
from __future__ import annotations

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
        return {}

    def studio_env_template(self, templator, task, allow_html: bool):
        return """
<p class="help-block">
  The cloze environment grades cloze subproblems with per-blank partial credit.
  Configure the prompt text and optional variants file in the Subproblems tab.
</p>
"""
