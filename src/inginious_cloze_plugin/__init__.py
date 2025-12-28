# src/inginious_cloze_plugin/__init__.py

# Make classes visible on the package object so the inspector finds them
from .cloze_problem_backend import ClozeProblem       # backend Problem
from .cloze_problem_frontend import DisplayableClozeProblem  # frontend DisplayableProblem

def init(plugin_manager, course_factory, client, entry):
    # Optional: task editor hooks
    try:
        from . import task_editor as te
        if hasattr(plugin_manager, "add_hook"):
            if hasattr(te, "task_editor_tabs"):
                plugin_manager.add_hook("task_editor_tabs", te.task_editor_tabs)
            if hasattr(te, "task_editor_tab"):
                plugin_manager.add_hook("task_editor_tab", te.task_editor_tab)
            if hasattr(te, "task_editor_submit"):
                plugin_manager.add_hook("task_editor_submit", te.task_editor_submit)
    except Exception:
        pass
