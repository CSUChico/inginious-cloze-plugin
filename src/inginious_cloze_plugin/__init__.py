# src/inginious_cloze_plugin/__init__.py

# Import at module import time so PluginManager inspection sees the classes
from . import cloze_problem_backend  # defines ClozeProblem (Problem)
from . import cloze_problem_frontend # defines DisplayableClozeProblem (DisplayableProblem)

def init(plugin_manager, course_factory, client, entry):
    """Optional: register Task Editor hooks (after load)."""
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
        # Hooks are optional; don’t block plugin load
        pass
