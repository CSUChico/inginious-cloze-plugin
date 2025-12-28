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
    text = data.get("text", "")
    # Ensure problems is a mapping (not a list), and write our problem
    task.setdefault("problems", {})
    task["problems"]["p1"] = {
        "type": "cloze",
        "text": text,
    }
    return {"message": "Cloze problem saved.", "task": task}
