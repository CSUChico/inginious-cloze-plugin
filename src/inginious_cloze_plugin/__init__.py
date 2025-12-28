- def init(plugin_manager, client, plugin_config):
+ def init(plugin_manager, course_factory, client, entry):
     """
     Register problem types and editor hooks.
     """
     from . import cloze_problem_backend, cloze_problem_frontend
-    from . import task_editor
+    from . import task_editor

     # --- Register BACKEND types globally ---
     from inginious.common.tasks_problems import inspect_problem_types, get_problem_types
     get_problem_types().update(
         inspect_problem_types(__name__ + ".cloze_problem_backend")
     )

     # --- Register FRONTEND displayable types ---
     from inginious.frontend.task_problems import inspect_displayable_problem_types
     types_frontend = inspect_displayable_problem_types(__name__ + ".cloze_problem_frontend")

     add_types = getattr(plugin_manager, "add_displayable_problem_types", None)
     if callable(add_types):
         add_types(types_frontend)
     else:
         def _cloze_displayable_types():
             return types_frontend
         plugin_manager.add_hook("task_problem_types", _cloze_displayable_types)

     # --- Task editor tabs (optional) ---
     if hasattr(task_editor, "task_editor_tabs"):
         plugin_manager.add_hook("task_editor_tabs", task_editor.task_editor_tabs)
     if hasattr(task_editor, "task_editor_tab"):
         plugin_manager.add_hook("task_editor_tab", task_editor.task_editor_tab)
     if hasattr(task_editor, "task_editor_submit"):
         plugin_manager.add_hook("task_editor_submit", task_editor.task_editor_submit)
