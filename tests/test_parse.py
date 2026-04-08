import sys

sys.path.insert(0, "src")

import inginious_cloze_plugin
from inginious_cloze_plugin.cloze_agent import grade_cloze_problem, parse_submission_payload
from inginious_cloze_plugin.cloze_core import (
    build_variant_record,
    grade_answers,
    load_variants_payload,
    normalize_inline_variants,
    parse_solutions_from_text,
)
from inginious_cloze_plugin.cloze_problem_backend import ClozeProblem, build_variant, load_variants


class DummyTaskFS:
    def __init__(self, files):
        self._files = files

    def get(self, path):
        return self._files[path]


class DummyPluginManager:
    def __init__(self):
        self.env_types = []

    def register_env_type(self, env_type):
        self.env_types.append(env_type)


def test_package_exports_problem_classes():
    assert hasattr(inginious_cloze_plugin, "ClozeProblem")
    assert hasattr(inginious_cloze_plugin, "DisplayableClozeProblem")
    assert hasattr(inginious_cloze_plugin, "ClozeFrontendEnv")


def test_parse_solutions_from_text_supports_shortanswer_and_numerical():
    solutions = parse_solutions_from_text(
        "The capital is {1:SHORTANSWER:=Paris|paris} and 2+2={2:NUMERICAL:=4±0.1}"
    )

    assert solutions == {
        "1": ("SHORTANSWER", ["Paris", "paris"]),
        "2": ("NUMERICAL", (4.0, 0.1)),
    }


def test_load_variants_payload_accepts_object_wrapper():
    variants = load_variants_payload({
        "variants": [
            {"name": "A", "text": "2+2={1:NUMERICAL:=4}"},
            {"name": "B", "text": "3+3={1:NUMERICAL:=6}"},
        ]
    })

    assert [variant["name"] for variant in variants] == ["A", "B"]


def test_normalize_inline_variants_decodes_json_and_sets_defaults():
    data = normalize_inline_variants({
        "type": "cloze",
        "variants": '[{"text": "x={1:SHORTANSWER:=x}"}]',
    })

    assert data["name"] == ""
    assert data["text"] == ""
    assert data["variants_file"] == ""
    assert data["variants"] == [{"text": "x={1:SHORTANSWER:=x}"}]


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


def test_build_variant_record_can_randomize_without_seed():
    variants = [
        {"name": "A", "text": "a={1:SHORTANSWER:=a}"},
        {"name": "B", "text": "b={1:SHORTANSWER:=b}"},
        {"name": "C", "text": "c={1:SHORTANSWER:=c}"},
    ]

    seen = {build_variant_record(variants, randomize=True)["name"] for _ in range(20)}

    assert len(seen) >= 2


def test_grade_answers_reports_fractional_score():
    solutions = {"1": ("SHORTANSWER", ["Paris"]), "2": ("NUMERICAL", (4.0, 0.0))}

    result = grade_answers(solutions, {"1": "paris", "2": "5"})

    assert result == {"correct": 1, "total": 2, "errors": 1, "valid": False, "score": 0.5}


def test_parse_submission_payload_reads_hidden_json():
    answers = parse_submission_payload('{"__variant":"1","1":"Paris","2":"4"}')

    assert answers == {"__variant": "1", "1": "Paris", "2": "4"}


def test_grade_cloze_problem_returns_fractional_result():
    task_fs = DummyTaskFS({
        "variants.json": """
        [
          {"text": "water={1:SHORTANSWER:=H2O|h2o} and 2+2={2:NUMERICAL:=4}"}
        ]
        """
    })

    result = grade_cloze_problem(
        {"type": "cloze", "variants_file": "variants.json"},
        task_fs,
        '{"__variant":"0","1":"H2O","2":"5"}',
    )

    assert result == {
        "status": "failed",
        "message": "Some answers are incorrect. You got 1/2 blanks right.",
        "variant": 0,
        "correct": 1,
        "total": 2,
        "score": 0.5,
    }


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

    assert problem.check_answer({"__variant": "1", "1": "blue"}, "en") == (
        True,
        "Correct. You got 1/1 blanks right.",
        [],
        0,
        {"variant": 1, "correct": 1, "total": 1},
    )
    assert problem.check_answer({"__variant": "1", "1": "red"}, "en") == (
        False,
        "Some answers are incorrect. You got 0/1 blanks right.",
        ["Blank 1: incorrect."],
        1,
        {"variant": 1, "correct": 0, "total": 1},
    )


def test_init_registers_cloze_environment():
    plugin_manager = DummyPluginManager()

    inginious_cloze_plugin.init(plugin_manager, None, None, {})

    assert [env.id for env in plugin_manager.env_types] == ["cloze"]
