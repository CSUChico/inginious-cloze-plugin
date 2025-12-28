# inginious_cloze_plugin/__init__.py

def init(plugin_manager, course_factory, client, entry):
    """
    Register problem types and (optionally) the Task Editor hooks.
    """

    # Import modules so classes are defined
    from . import cloze_problem_backend, cloze_problem_frontend
    try:
        from . import task_editor as te
    except Exception:
        te = None

    # --- Register BACKEND problem types globally ---
    # (so the server-side checker knows about "cloze")
    try:
        from inginious.common.tasks_problems import inspect_problem_types, get_problem_types
        get_problem_types().update(
            inspect_problem_types(__name__ + ".cloze_problem_backend")
        )
    except Exception:
        # Fallback: just importing often registers in older versions
        pass

    # --- Register FRONTEND (displayable) problem types ---
    # (so the UI knows how to render "cloze")
    try:
        from inginious.frontend.task_problems import inspect_displayable_problem_types
        types_frontend = inspect_displayable_problem_types(__name__ + ".cloze_problem_frontend")

        add_types = getattr(plugin_manager, "add_displayable_problem_types", None)
        if callable(add_types):
            add_types(types_frontend)
        else:
            # Fallback via hook
            def _cloze_displayable_types():
                return types_frontend
            plugin_manager.add_hook("task_problem_types", _cloze_displayable_types)
    except Exception:
        pass

    # --- Optional Task Editor hooks (only if present) ---
    if te and hasattr(plugin_manager, "add_hook"):
        for hook_name in ("task_editor_tabs", "task_editor_tab", "task_editor_submit"):
            fn = getattr(te, hook_name, None)
            if callable(fn):
                plugin_manager.add_hook(hook_name, fn)
