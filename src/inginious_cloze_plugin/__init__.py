# -*- coding: utf-8 -*-

from .cloze_problem_backend import ClozeProblem  # noqa: F401
from .cloze_env import ClozeFrontendEnv  # noqa: F401
from .cloze_problem_frontend import DisplayableClozeProblem  # noqa: F401


def init(plugin_manager, course_factory, client, entry):
    register_env_type = getattr(plugin_manager, "register_env_type", None)
    if callable(register_env_type):
        register_env_type(ClozeFrontendEnv())
    return
