# -*- coding: utf-8 -*-

"""
INGInious Cloze Plugin package.

Important:
INGInious discovers problem types by inspecting/importing the module you list in
configuration.yaml under `plugin_module`.

Many INGInious setups only inspect the top-level module, so we must import the
submodules that define our Problem / DisplayableProblem classes here.
"""

# Ensure the classes are imported at package import time so type discovery finds them.
from .cloze_problem_backend import ClozeProblem  # noqa: F401
from .cloze_problem_frontend import DisplayableClozeProblem  # noqa: F401


def init(plugin_manager, course_factory, client, entry):
    # Signature must match plugin_manager.load(...): init(pm, course_factory, client, entry)
    # No explicit registration needed; discovery happens via get_problem_types/get_displayable_problem_types.
    return
