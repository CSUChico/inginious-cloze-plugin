# inginious_cloze_plugin/__init__.py
from . import cloze_problem_backend, cloze_problem_frontend, task_editor

def init(plugin_manager, client, plugin_config):
    """
    Register problem types and editor hooks.
    Works across recent INGInious versions that expect explicit registration.
    """

    # --- Register BACKEND problem types globally ---
    # These are used server-side when parsing/validating inputs.
    from inginious.common.tasks_problems import inspect_problem_types, get_problem_types
    get_problem_types().update(
        inspect_problem_types(__name__ + ".cloze_problem_backend")
    )

    # --- Register FRONTEND displayable problem types with the plugin manager ---
    # These are used by the TaskFactory to instantiate DisplayableProblem classes.
    from inginious.frontend.task_problems import inspect_displayable_problem_types
    types_frontend = inspect_displayable_problem_types(__name__ + ".cloze_problem_frontend")

    # Newer plugin managers expose 'add_displayable_problem_types'; fall back to a hook if absent.
    add_types = getattr(plugin_manager, "add_displayable_problem_types", None)
    if callable(add_types):
        add_types(types_frontend)
    else:
        # Fallback: expose a hook so the app can retrieve our map
        def _cloze_displayable_types():
            return types_frontend
        plugin_manager.add_hook("task_problem_types", _cloze_displayable_types)

    # --- Task editor tabs (optional) ---
    if hasattr(task_editor, "task_editor_tab"):
        plugin_manager.add_hook("task_editor_tab", task_editor.task_editor_tab)
    if hasattr(task_editor, "task_editor_submit"):
        plugin_manager.add_hook("task_editor_submit", task_editor.task_editor_submit)
