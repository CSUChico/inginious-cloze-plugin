# -*- coding: utf-8 -*-

from __future__ import annotations


def _register_problem_type(plugin_manager, problem_type):
    factories = [
        getattr(plugin_manager, "_task_factory", None),
        getattr(plugin_manager, "task_factory", None),
    ]

    for factory in factories:
        add_problem_type = getattr(factory, "add_problem_type", None)
        if callable(add_problem_type):
            add_problem_type(problem_type)
            return True

    add_problem_type = getattr(plugin_manager, "add_problem_type", None)
    if callable(add_problem_type):
        add_problem_type(problem_type)
        return True

    return False


def init(plugin_manager, course_factory, client, entry):
    from .cloze_problem_frontend import DisplayableClozeProblem

    registered = _register_problem_type(plugin_manager, DisplayableClozeProblem)
    if not registered:
        raise RuntimeError("Could not register cloze problem type: no task factory exposes add_problem_type().")
