# inginious_cloze_plugin/__init__.py

def init(plugin_manager, course_factory, client, entry):
    """Register backend + frontend problem types and Task Editor hooks."""
    # Import so classes exist
    from . import cloze_problem_backend, cloze_problem_frontend
    try:
        from . import task_editor as te
    except Exception:
        te = None

    # --- BACKEND (server-side) ---
    try:
        from inginious.common.tasks_problems import inspect_problem_types, get_problem_types
        get_problem_types().update(
            inspect_problem_types(__name__ + ".cloze_problem_backend")
        )
    except Exception:
        pass

    # --- FRONTEND (displayable) ---
    try:
        from inginious.frontend.task_problems import inspect_displayable_problem_types
        types_frontend = inspect_displayable_problem_types(__name__ + ".cloze_problem_frontend")
    except Exception:
        types_frontend = {}

    # Prefer a concrete API if present…
    added = False
    for attr in ("add_displayable_problem_types",
                 "add_displayable_task_problem_types",   # older/alt naming
                 "register_displayable_problem_types"):  # alt naming seen in forks
        fn = getattr(plugin_manager, attr, None)
        if callable(fn):
            fn(types_frontend)
            added = True
            break

    # …fallback to the hook (many versions use this)
    if not added and hasattr(plugin_manager, "add_hook"):
        def _cloze_displayable_types():
            return types_frontend
        plugin_manager.add_hook("task_problem_types", _cloze_displayable_types)

    # --- Task Editor (optional) ---
    if te and hasattr(plugin_manager, "add_hook"):
        for hook in ("task_editor_tabs", "task_editor_tab", "task_editor_submit"):
            fn = getattr(te, hook, None)
            if callable(fn):
                plugin_manager.add_hook(hook, fn)
