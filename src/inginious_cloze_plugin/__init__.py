# src/inginious_cloze_plugin/__init__.py
from .cloze_problem_backend import ClozeProblem
from .cloze_problem_frontend import DisplayableClozeProblem

def init(plugin_manager, course_factory, client, entry):
    # (optional) editor hooks if you add them later
    try:
        from . import task_editor as te
        if hasattr(plugin_manager, "add_hook"):
            for hook in ("task_editor_tabs", "task_editor_tab", "task_editor_submit"):
                fn = getattr(te, hook, None)
                if callable(fn):
                    plugin_manager.add_hook(hook, fn)
    except Exception:
        pass
