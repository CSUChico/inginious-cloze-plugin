# inginious_cloze_plugin/__init__.py
def init(plugin_manager, course_factory, client, entry):
    # Import side effects register the classes via module inspection
    from . import cloze_problem_backend, cloze_problem_frontend
    from . import task_editor as te


     # Only register hooks that exist (avoids AttributeError)
    if hasattr(plugin_manager, "add_hook"):
        if hasattr(te, "task_editor_tabs"):
            plugin_manager.add_hook("task_editor_tabs", te.task_editor_tabs)
        if hasattr(te, "task_editor_tab"):
            plugin_manager.add_hook("task_editor_tab", te.task_editor_tab)
        if hasattr(te, "task_editor_submit"):
            plugin_manager.add_hook("task_editor_submit", te.task_editor_submit)
