# src/inginious_cloze_plugin/task_editor.py
from __future__ import annotations
from typing import Any

# --- Task Editor hook functions ---

def task_editor_tabs(task, language: str):
    """Declare our extra tab in the Task Editor."""
    return [{"key": "cloze", "label": "Cloze"}]

def task_editor_tab(task, key: str, template_helper, language: str):
    """Return the HTML content for our tab."""
    if key != "cloze":
        return ""
    # Render your editor UI (ensure this template exists in your package data)
    return template_helper.render("cloze_editor_tab.html")

def task_editor_submit(task: dict[str, Any], key: str, data: dict[str, Any], language: str):
    """Handle the editor form submission: update the task dictionary."""
    if key != "cloze":
        return {}

    submitted_problems = data.get("problems", {})
    if not isinstance(submitted_problems, dict):
        return {"message": "Cloze problem saved.", "task": task}

    task.setdefault("problems", {})
    if not isinstance(task["problems"], dict):
        task["problems"] = {}

    for pid, problem in submitted_problems.items():
        if not isinstance(problem, dict) or problem.get("type") != "cloze":
            continue

        current = task["problems"].get(pid, {})
        if not isinstance(current, dict):
            current = {}

        current.update(problem)
        current["type"] = "cloze"
        task["problems"][pid] = current

    return {"message": "Cloze problem saved.", "task": task}
