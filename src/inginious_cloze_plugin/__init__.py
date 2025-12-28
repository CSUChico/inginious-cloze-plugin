# -*- coding: utf-8 -*-

"""
INGInious Cloze Plugin

The frontend PluginManager will import this module and call:
    init(plugin_manager, course_factory, client, entry)

Even if you don't need initialization logic, the function must exist
with the correct signature.
"""

def init(plugin_manager, course_factory, client, entry):
    # No explicit registration required: INGInious discovers Problem and
    # DisplayableProblem subclasses via get_problem_types/get_displayable_problem_types.
    # Keep this for future hooks/pages if needed.
    return
