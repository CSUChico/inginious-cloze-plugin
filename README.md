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

## Task configuration

Basic inline cloze:

```yaml
problems:
  p1:
    type: cloze
    name: Capitals
    text: "The capital of France is {1:SHORTANSWER:=Paris}."
```

JSON-backed variants:

```yaml
problems:
  p1:
    type: cloze
    name: Randomized cloze
    variants_file: variants.json
```

`variants.json` can be either a list or an object with a `variants` list:

```json
{
  "variants": [
    { "name": "Easy", "text": "2 + 2 = {1:NUMERICAL:=4}" },
    { "name": "Harder", "text": "3 + 5 = {1:NUMERICAL:=8}" }
  ]
}
```

The selected variant is sent back with the submission, so the backend grades against the same problem text the student saw.

## Development

The `src/inginious_cloze_plugin` directory holds:
- `cloze_problem_backend.py` — grading logic
- `cloze_problem_frontend.py` — rendering logic
- `task_editor.py` — Task Editor tab hooks
- `templates/` — Jinja2 templates
- `static/` — JS/CSS for editor

## License

MIT License — see LICENSE.
