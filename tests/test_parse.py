import sys

sys.path.insert(0, "src")

import inginious_cloze_plugin
from inginious_cloze_plugin.cloze_agent import grade_cloze_problem, parse_submission_payload
from inginious_cloze_plugin.__init__ import _merge_cloze_problem_fields, _parse_simple_task_yaml
from inginious_cloze_plugin.cloze_core import (
    build_variant_record,
    choose_variant_indices,
    grade_answers,
    load_variants_payload,
    normalize_problem_count,
    normalize_inline_variants,
    parse_solutions_from_text,
    renumber_cloze_slots,
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
        "1": (
            "SHORTANSWER",
            [
                {"weight": 1.0, "answer": "Paris", "feedback": None},
                {"weight": 1.0, "answer": "paris", "feedback": None},
            ],
        ),
        "2": ("NUMERICAL", [{"weight": 1.0, "answer": 4.0, "tolerance": 0.1, "feedback": None}]),
    }


def test_parse_solutions_from_text_supports_multichoice():
    solutions = parse_solutions_from_text(
        "Flag={1:MULTICHOICE:%0%none~overflow~=underflow#Correct}"
    )

    assert solutions == {
        "1": (
            "MULTICHOICE",
            {
                "choices": ["none", "overflow", "underflow"],
                "answers": [
                    {"weight": 0.0, "answer": "none", "feedback": None},
                    {"weight": 0.0, "answer": "overflow", "feedback": None},
                    {"weight": 1.0, "answer": "underflow", "feedback": "Correct"},
                ],
            },
        ),
    }


def test_parse_solutions_from_text_supports_partial_credit_and_feedback():
    solutions = parse_solutions_from_text(
        "Capital={1:SHORTANSWER:=Paris#Correct~%50%Lyon#Close~*#Nope} num={2:NUMERICAL:=23.8:0.1#Exact~%50%23.8:2#Close}"
    )

    assert solutions["1"][1][0] == {"weight": 1.0, "answer": "Paris", "feedback": "Correct"}
    assert solutions["1"][1][1] == {"weight": 0.5, "answer": "Lyon", "feedback": "Close"}
    assert solutions["2"][1][0] == {"weight": 1.0, "answer": 23.8, "tolerance": 0.1, "feedback": "Exact"}
    assert solutions["2"][1][1] == {"weight": 0.5, "answer": 23.8, "tolerance": 2.0, "feedback": "Close"}


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
    assert data["random_problem_count"] == ""
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


def test_build_variant_combines_up_to_random_problem_count():
    variant = build_variant(
        {
            "type": "cloze",
            "random_problem_count": "5",
            "variants": [
                {"name": "A", "text": "A={1:SHORTANSWER:=a}"},
                {"name": "B", "text": "B={1:SHORTANSWER:=b}"},
            ],
        },
        None,
        submitted_variant="0,1",
    )

    assert variant["selection"] == "0,1"
    assert variant["slots"] == ["1", "2"]
    assert "A" in variant["text"]
    assert "B" in variant["text"]


def test_choose_variant_indices_caps_problem_count_to_available_variants():
    indices = choose_variant_indices(
        [{"text": "a"}, {"text": "b"}],
        count=5,
        seed="demo",
    )

    assert len(indices) == 2
    assert sorted(indices) == [0, 1]


def test_choose_variant_indices_reuses_submitted_unique_selection():
    indices = choose_variant_indices(
        [{"text": "a"}, {"text": "b"}, {"text": "c"}],
        count=2,
        submitted_variant="2,2,1",
    )

    assert indices == [2, 1]


def test_build_variant_record_combines_multiple_unique_variants():
    variant = build_variant_record(
        [
            {"name": "One", "text": "A={1:SHORTANSWER:=a}"},
            {"name": "Two", "text": "B={1:SHORTANSWER:=b}"},
            {"name": "Three", "text": "C={1:SHORTANSWER:=c}"},
        ],
        submitted_variant="0,2",
        problem_count=2,
    )

    assert variant["selection"] == "0,2"
    assert variant["slots"] == ["1", "2"]
    assert set(variant["solutions"].keys()) == {"1", "2"}
    assert "cloze-random-problem" in variant["text"]
    assert "One" in variant["text"]
    assert "Three" in variant["text"]


def test_normalize_problem_count_defaults_to_one():
    assert normalize_problem_count("") == 1
    assert normalize_problem_count(None) == 1
    assert normalize_problem_count("3") == 3


def test_renumber_cloze_slots_makes_repeated_slots_unique():
    text = (
        "{1:SHORTANSWER:=0}"
        "{1:SHORTANSWER:=0}"
        "{1:SHORTANSWER:=0}"
        "{1:SHORTANSWER:=0}"
        "{1:SHORTANSWER:=0}"
        "{1:SHORTANSWER:=1}"
    )

    renumbered = renumber_cloze_slots(text)

    assert renumbered == (
        "{1:SHORTANSWER:=0}"
        "{2:SHORTANSWER:=0}"
        "{3:SHORTANSWER:=0}"
        "{4:SHORTANSWER:=0}"
        "{5:SHORTANSWER:=0}"
        "{6:SHORTANSWER:=1}"
    )


def test_build_variant_record_renumbers_duplicate_slots_before_grading():
    variant = build_variant_record(
        [{"text": "{1:SHORTANSWER:=a} {1:SHORTANSWER:=b} {1:SHORTANSWER:=c}"}]
    )

    assert variant["slots"] == ["1", "2", "3"]
    assert set(variant["solutions"].keys()) == {"1", "2", "3"}


def test_parse_simple_task_yaml_keeps_multiple_cloze_problems():
    parsed = _parse_simple_task_yaml(
        """
name: clozetest3
problems:
    test:
        name: test
        text: ''
        type: cloze
        variants_file: cloze_variants.json
    bitops:
        name: BitOps
        text: ''
        type: cloze
        variants_file: bitops.json
"""
    )

    assert parsed["problems"] == {
        "test": {
            "name": "test",
            "text": "",
            "type": "cloze",
            "variants_file": "cloze_variants.json",
        },
        "bitops": {
            "name": "BitOps",
            "text": "",
            "type": "cloze",
            "variants_file": "bitops.json",
        },
    }


def test_merge_cloze_problem_fields_adds_missing_cloze_problems():
    target_task_data = {
        "problems": {
            "test": {"type": "cloze", "name": "test", "text": "", "variants_file": "cloze_variants.json"}
        }
    }
    source_task_data = {
        "problems": {
            "test": {"type": "cloze", "name": "test", "text": "Prompt A", "variants_file": "cloze_variants.json"},
            "bitops": {"type": "cloze", "name": "BitOps", "text": "Prompt B", "variants_file": "bitops.json"},
        }
    }

    _merge_cloze_problem_fields(target_task_data, source_task_data)

    assert target_task_data["problems"] == {
        "test": {
            "type": "cloze",
            "name": "test",
            "text": "Prompt A",
            "variants_file": "cloze_variants.json",
        },
        "bitops": {
            "type": "cloze",
            "name": "BitOps",
            "text": "Prompt B",
            "variants_file": "bitops.json",
        },
    }


def test_build_variant_record_can_randomize_without_seed():
    variants = [
        {"name": "A", "text": "a={1:SHORTANSWER:=a}"},
        {"name": "B", "text": "b={1:SHORTANSWER:=b}"},
        {"name": "C", "text": "c={1:SHORTANSWER:=c}"},
    ]

    seen = {build_variant_record(variants, randomize=True)["name"] for _ in range(20)}

    assert len(seen) >= 2


def test_grade_answers_reports_fractional_score():
    solutions = {
        "1": ("SHORTANSWER", [{"weight": 1.0, "answer": "Paris", "feedback": None}]),
        "2": ("NUMERICAL", [{"weight": 1.0, "answer": 4.0, "tolerance": 0.0, "feedback": None}]),
    }

    result = grade_answers(solutions, {"1": "paris", "2": "5"})

    assert result == {"correct": 1, "total": 2, "errors": 1, "valid": False, "score": 0.5}


def test_grade_answers_supports_multichoice():
    solutions = {
        "1": (
            "MULTICHOICE",
            {"choices": ["none", "overflow", "underflow"], "answers": [{"weight": 1.0, "answer": "underflow", "feedback": None}]},
        )
    }

    assert grade_answers(solutions, {"1": "underflow"}) == {
        "correct": 1,
        "total": 1,
        "errors": 0,
        "valid": True,
        "score": 1.0,
    }


def test_grade_answers_supports_partial_credit():
    solutions = {
        "1": (
            "SHORTANSWER",
            [
                {"weight": 1.0, "answer": "Paris", "feedback": None},
                {"weight": 0.5, "answer": "Lyon", "feedback": None},
            ],
        ),
        "2": (
            "MULTICHOICE",
            {
                "choices": ["none", "overflow", "underflow"],
                "answers": [
                    {"weight": 0.0, "answer": "none", "feedback": None},
                    {"weight": 1.0, "answer": "underflow", "feedback": None},
                ],
            },
        ),
    }

    assert grade_answers(solutions, {"1": "Lyon", "2": "underflow"}) == {
        "correct": 1,
        "total": 2,
        "errors": 1,
        "valid": False,
        "score": 0.75,
        "feedback": {},
    }


def test_grade_answers_returns_feedback_for_partial_numerical_match():
    solutions = parse_solutions_from_text(
        "2 + 3 = {1:NUMERICAL:=5#Exact~%50%5:0.1#Close}."
    )

    assert grade_answers(solutions, {"1": "5.05"}) == {
        "correct": 0,
        "total": 1,
        "errors": 1,
        "valid": False,
        "score": 0.5,
        "feedback": {"1": "Close"},
    }


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


def test_grade_cloze_problem_returns_partial_credit_and_feedback():
    result = grade_cloze_problem(
        {"type": "cloze", "text": "2 + 3 = {1:NUMERICAL:=5#Exact~%50%5:0.1#Close}."},
        None,
        '{"1":"5.05"}',
    )

    assert result == {
        "status": "failed",
        "message": "Some answers are incorrect. You got 0/1 blanks right. Close",
        "variant": 0,
        "correct": 0,
        "total": 1,
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
