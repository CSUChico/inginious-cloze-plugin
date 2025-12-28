# INGInious Cloze Plugin

A pip-installable plugin for INGInious that adds a Moodle Cloze-style question type with a Task Editor tab for authoring.

## Installation

```bash
pip install -e .
```

Then register it in `configuration.yaml`:

```yaml
plugins:
  - plugin_module: "inginious_cloze_plugin"
```

Restart INGInious webapp and MCQ agent.

## Development

The `src/inginious_cloze_plugin` directory holds:
- `cloze_problem_backend.py` — grading logic
- `cloze_problem_frontend.py` — rendering logic
- `task_editor.py` — Task Editor tab hooks
- `templates/` — Jinja2 templates
- `static/` — JS/CSS for editor

## License

MIT License — see LICENSE.
