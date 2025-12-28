# inginious_cloze_plugin/__init__.py
def init(plugin_manager, course_factory, client, entry):
    # Import side effects register the classes via module inspection
    from . import cloze_problem_backend, cloze_problem_frontend, task_editor

    # (optional) add your task editor tab hook here if you have one:
    plugin_manager.add_hook("task_editor_tab", task_editor.task_editor_tab)
    plugin_manager.add_hook("task_editor_submit", task_editor.task_editor_submit)
