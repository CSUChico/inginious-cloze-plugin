def init(plugin_manager, course_factory, client, entry):
    # Importing is enough: INGInious inspects modules for subclasses
    from . import cloze_problem_backend, cloze_problem_frontend

    # (Optional) only register hooks that actually exist
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
