# INGInious Cloze Plugin

A pip-installable plugin for INGInious that adds a Moodle-style cloze question type and a dedicated `cloze` grading environment for per-blank partial credit.

## Versioning

The current release is `v0.1.1`.

Any changes moving forward should be released as `v0.1.2` or later.

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

## Dedicated cloze environment

When a task uses the `cloze` environment type, the custom cloze agent computes the grade as:

```txt
100 * (correct blanks / total blanks)
```

instead of the MCQ environment's all-or-nothing subproblem scoring.

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

For the dedicated `cloze` environment, keep the task's subproblems as `type: cloze` and switch the Environment tab from `mcq` to `cloze`.

## Matching-question generator

For left/right matching layouts, you can generate a `variants.json` file from a simpler spec:

```bash
python3 scripts/generate_matching_variants.py examples/matching_spec.json -o cloze_variants.json
```

The generator:
- builds an HTML two-column layout
- turns each left-side item into a cloze `MULTICHOICE` blank
- shuffles the right-side choices per variant when requested

Input spec shape:

```json
{
  "title": "Optional heading",
  "intro": ["Paragraph 1", "Paragraph 2"],
  "instructions": "Match each description on the left with a line of code on the right.",
  "variants": 4,
  "shuffle_left": false,
  "shuffle_right": true,
  "left_items": [
    { "text": "x > 0", "answer_id": "e" }
  ],
  "right_items": [
    { "id": "e", "text": "((x >> W) & 0x1) | !x" }
  ]
}
```

Use the generated file as your cloze subproblem's `variants_file`.

## Development

The `src/inginious_cloze_plugin` directory holds:
- `cloze_problem_backend.py` — grading logic
- `cloze_problem_frontend.py` — rendering logic
- `task_editor.py` — Task Editor tab hooks
- `templates/` — Jinja2 templates
- `static/` — JS/CSS for editor

## License

MIT License — see LICENSE.
