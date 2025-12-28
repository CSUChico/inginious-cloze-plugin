# src/inginious_cloze_plugin/__init__.py

def init(plugin_manager, course_factory, client, entry):
    """
    Register backend + frontend problem types and Task Editor hooks
    across multiple INGInious versions (API/Hook variants).
    """
    # Ensure classes are importable
    from . import cloze_problem_backend, cloze_problem_frontend
    try:
        from . import task_editor as te
    except Exception:
        te = None

    # --- BACKEND registration (server-side Problem types) ---
    try:
        from inginious.common.tasks_problems import inspect_problem_types, get_problem_types
        get_problem_types().update(
            inspect_problem_types(__name__ + ".cloze_problem_backend")
        )
    except Exception:
        pass

    # --- FRONTEND registration (DisplayableProblem types) ---
    types_frontend = {}
    try:
        from inginious.frontend.task_problems import inspect_displayable_problem_types
        types_frontend = inspect_displayable_problem_types(__name__ + ".cloze_problem_frontend")
    except Exception:
        pass

    # 1) Preferred explicit APIs (varies by version)
    added = False
    for attr in (
        "add_displayable_problem_types",
        "add_displayable_task_problem_types",
        "register_displayable_problem_types",
    ):
        fn = getattr(plugin_manager, attr, None)
        if callable(fn):
            try:
                fn(types_frontend)
                added = True
                break
            except Exception:
                pass

    # 2) Hook names used across versions/forks
    if hasattr(plugin_manager, "add_hook"):
        for hook_name in (
            "task_problem_types",                  # common
            "displayable_task_problem_types",      # alt
            "get_displayable_problem_types",       # alt
        ):
            try:
                # bind current dict value safely
                def _types(_types=types_frontend):
                    return _types
                plugin_manager.add_hook(hook_name, _types)
                added = True
            except Exception:
                pass

    # 3) Last-resort private-field fallback (read by some TaskFactory builds)
    try:
        if hasattr(plugin_manager, "_task_problem_types") and isinstance(plugin_manager._task_problem_types, dict):
            plugin_manager._task_problem_types.update(types_frontend)
            added = True
    except Exception:
        pass

    # --- Optional Task Editor hooks ---
    if te and hasattr(plugin_manager, "add_hook"):
        for hook in ("task_editor_tabs", "task_editor_tab", "task_editor_submit"):
            fn = getattr(te, hook, None)
            if callable(fn):
                plugin_manager.add_hook(hook, fn)
