# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
from typing import Any

try:
    from inginious.agent import Agent, CannotCreateJobException
    from inginious.common.messages import BackendKillJob, BackendNewJob
except ModuleNotFoundError:  # pragma: no cover - local tests without INGInious
    Agent = object
    CannotCreateJobException = Exception
    BackendKillJob = object
    BackendNewJob = object

from .cloze_core import grade_answers
from .cloze_problem_backend import build_variant


def parse_submission_payload(raw_value: Any) -> dict[str, str]:
    if raw_value is None:
        return {}
    if isinstance(raw_value, dict):
        return {str(k): ("" if v is None else str(v)) for k, v in raw_value.items()}
    if isinstance(raw_value, (bytes, bytearray)):
        raw_value = raw_value.decode("utf-8")
    if isinstance(raw_value, str):
        if not raw_value.strip():
            return {}
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                return {str(k): ("" if v is None else str(v)) for k, v in parsed.items()}
        except Exception:
            return {}
    return {}


def grade_cloze_problem(problem_content: dict[str, Any], task_fs: Any, raw_submission: Any) -> dict[str, Any]:
    answers = parse_submission_payload(raw_submission)
    variant = build_variant(problem_content, task_fs, submitted_variant=answers.get("__variant"))
    result = grade_answers(variant["solutions"], answers)

    if result["valid"]:
        message = "Correct. You got {}/{} blanks right.".format(result["correct"], result["total"])
        status = "success"
    else:
        message = "Some answers are incorrect. You got {}/{} blanks right.".format(
            result["correct"], result["total"]
        )
        status = "failed"

    return {
        "status": status,
        "message": message,
        "variant": variant["index"],
        "correct": result["correct"],
        "total": result["total"],
        "score": result["score"],
        "feedback": result.get("feedback", {}),
    }


class ClozeAgent(Agent):
    def __init__(self, context, backend_addr, friendly_name, concurrency, tasks_filesystem):
        super().__init__(context, backend_addr, friendly_name, concurrency, tasks_filesystem)
        self._logger = logging.getLogger("inginious.agent.cloze")

    @property
    def environments(self):
        return {"cloze": {"cloze": {"id": "cloze", "created": 0}}}

    async def new_job(self, msg: BackendNewJob):
        course_fs = self._fs.from_subfolder(msg.course_id)
        task_fs = course_fs.from_subfolder(msg.task_id)
        task_problems = msg.task_problems or {}

        if not task_problems:
            await self.send_job_result(msg.job_id, "crashed", "No cloze subproblems defined.", 0.0, {}, {}, {}, "", None)
            return

        problem_feedback = {}
        states = {}
        total_correct = 0
        total_blanks = 0
        total_earned = 0.0
        for problem_id, problem_content in task_problems.items():
            if problem_content.get("type") != "cloze":
                raise CannotCreateJobException(
                    "Task uses non-cloze subproblem '{}' with the cloze environment.".format(problem_id)
                )

            graded = grade_cloze_problem(problem_content, task_fs, msg.inputdata.get(problem_id))
            total_correct += graded["correct"]
            total_blanks += graded["total"]
            total_earned += graded["score"] * graded["total"]
            problem_feedback[problem_id] = (graded["status"], graded["message"], graded.get("feedback", {}))
            states[problem_id] = {
                "variant": graded["variant"],
                "correct": graded["correct"],
                "total": graded["total"],
            }

        grade = 100.0 * float(total_earned) / float(max(total_blanks, 1))
        result = "success" if total_correct == total_blanks else "failed"
        text = "You got {}/{} blanks right.".format(total_correct, total_blanks)

        await self.send_job_result(
            msg.job_id,
            result,
            text,
            grade,
            problem_feedback,
            {},
            {},
            json.dumps(states),
            None,
        )

    async def kill_job(self, message: BackendKillJob):
        return
