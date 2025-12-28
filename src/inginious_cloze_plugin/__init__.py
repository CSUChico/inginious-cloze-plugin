# -*- coding: utf-8 -*-

"""
INGInious Cloze Plugin package.

INGInious discovers problem types by importing the module listed in configuration.yaml
under `plugin_module`. Import the classes here so they are discoverable.
"""

from .cloze_problem_backend import ClozeProblem  # noqa: F401
from .cloze_problem_frontend import DisplayableClozeProblem  # noqa: F401


def init(plugin_manager, course_factory, client, entry):
    # No explicit registration needed if discovery is enabled.
    return
