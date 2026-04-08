from inginious_cloze_plugin import init
from inginious_cloze_plugin.cloze_problem_backend import (
    ClozeProblem,
    build_variant,
    grade_answers,
    load_variants,
    parse_solutions_from_text,
)


class DummyTaskFS:
    def __init__(self, files):
        self._files = files

    def read(self, path):
        return self._files[path]


class DummyTaskFactory:
    def __init__(self):
        self.registered = []

    def add_problem_type(self, problem_type):
        self.registered.append(problem_type)


class DummyPluginManager:
    def __init__(self):
        self._task_factory = DummyTaskFactory()


def test_parse_solutions_from_text_supports_shortanswer_and_numerical():
    solutions = parse_solutions_from_text(
        "The capital is {1:SHORTANSWER:=Paris|paris} and 2+2={2:NUMERICAL:=4±0.1}"
    )

    assert solutions == {
        "1": ("SHORTANSWER", ["Paris", "paris"]),
        "2": ("NUMERICAL", (4.0, 0.1)),
    }


def test_load_variants_reads_json_file():
    task_fs = DummyTaskFS({
        "variants.json": """
        {
          "variants": [
            {"name": "A", "text": "2+2={1:NUMERICAL:=4}"},
            {"name": "B", "text": "3+3={1:NUMERICAL:=6}"}
          ]
        }
        """
    })

    variants = load_variants({"variants_file": "variants.json"}, task_fs)

    assert [variant["name"] for variant in variants] == ["A", "B"]
    assert [variant["text"] for variant in variants] == [
        "2+2={1:NUMERICAL:=4}",
        "3+3={1:NUMERICAL:=6}",
    ]


def test_build_variant_uses_submitted_variant_index():
    task_fs = DummyTaskFS({
        "variants.json": """
        [
          {"text": "red={1:SHORTANSWER:=red}"},
          {"text": "blue={1:SHORTANSWER:=blue}"}
        ]
        """
    })

    variant = build_variant({"variants_file": "variants.json"}, task_fs, seed="ignored", submitted_variant="1")

    assert variant["index"] == 1
    assert variant["text"] == "blue={1:SHORTANSWER:=blue}"
    assert variant["slots"] == ["1"]


def test_grade_answers_reports_validity():
    solutions = {"1": ("SHORTANSWER", ["Paris"]), "2": ("NUMERICAL", (4.0, 0.0))}

    result = grade_answers(solutions, {"1": "paris", "2": "4"})

    assert result == {"correct": 2, "total": 2, "errors": 0, "valid": True}


def test_cloze_problem_check_answer_uses_variant_from_submission():
    task_fs = DummyTaskFS({
        "variants.json": """
        [
          {"text": "red={1:SHORTANSWER:=red}"},
          {"text": "blue={1:SHORTANSWER:=blue}"}
        ]
        """
    })
    problem = ClozeProblem("p1", {"variants_file": "variants.json"}, None, task_fs)
    problem._data = problem.parse_problem(problem._data)
    problem._task_fs = task_fs

    assert problem.check_answer({"__variant": "1", "1": "blue"}, "en") == (True, "", "", 0)
    assert problem.check_answer({"__variant": "1", "1": "red"}, "en") == (
        False,
        "",
        "One or more blanks are incorrect.",
        1,
    )


def test_init_registers_problem_type():
    plugin_manager = DummyPluginManager()

    init(plugin_manager, None, None, {})

    assert len(plugin_manager._task_factory.registered) == 1
    assert plugin_manager._task_factory.registered[0].get_type() == "cloze"
