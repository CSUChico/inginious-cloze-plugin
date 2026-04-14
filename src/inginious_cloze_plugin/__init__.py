# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover - yaml is available on the target server
    yaml = None

from .cloze_problem_backend import ClozeProblem  # noqa: F401
from .cloze_agent import ClozeAgent  # noqa: F401
from .cloze_env import ClozeFrontendEnv  # noqa: F401
from .cloze_problem_frontend import DisplayableClozeProblem  # noqa: F401
from .cloze_problem_backend import _read_task_file

_AGENT_TASKS = []


async def _restart_on_cancel(agent):
    while True:
        try:
            await agent.run()
        except asyncio.CancelledError:
            continue


def _get_tasks_fs(course_factory):
    for method_name in ("get_fs", "get_filesystem"):
        method = getattr(course_factory, method_name, None)
        if callable(method):
            return method()
    return getattr(course_factory, "_filesystem", None)


def _get_task_fs(course_factory, courseid, taskid):
    tasks_fs = _get_tasks_fs(course_factory)
    if tasks_fs is None:
        return None
    try:
        return tasks_fs.from_subfolder(courseid).from_subfolder(taskid)
    except Exception:
        return None


def _load_task_descriptor_from_task_fs(task_fs):
    if task_fs is None:
        return {}

    for descriptor_name in ("task.yaml", "task.yml", "task.json"):
        try:
            raw = _read_task_file(task_fs, descriptor_name)
        except Exception:
            continue

        if descriptor_name.endswith(".json"):
            try:
                return json.loads(raw)
            except Exception:
                continue

        if yaml is not None:
            try:
                parsed = yaml.safe_load(raw)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                continue

    return {}


def _load_task_descriptor_from_known_paths(courseid, taskid):
    candidate_roots = [
        "/var/www/inginious/tasks",
        "/var/lib/inginious/tasks",
        "/srv/inginious/tasks",
        "./tasks",
    ]

    for root in candidate_roots:
        task_dir = Path(root) / courseid / taskid
        for descriptor_name in ("task.yaml", "task.yml", "task.json"):
            descriptor_path = task_dir / descriptor_name
            if not descriptor_path.exists():
                continue
            try:
                raw = descriptor_path.read_text(encoding="utf-8")
            except Exception:
                continue

            if descriptor_name.endswith(".json"):
                try:
                    parsed = json.loads(raw)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    continue

            if yaml is not None:
                try:
                    parsed = yaml.safe_load(raw)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    continue

            try:
                parsed = _parse_simple_task_yaml(raw)
                if isinstance(parsed, dict) and parsed:
                    return parsed
            except Exception:
                continue

    return {}


def _parse_yaml_scalar(value):
    if value in ("''", '""'):
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except Exception:
        return value


def _parse_simple_task_yaml(raw):
    parsed = {}
    problems = {}
    current_problem = None
    in_problems = False

    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped == "problems:":
            in_problems = True
            current_problem = None
            parsed["problems"] = problems
            continue

        if indent == 0:
            in_problems = False
            current_problem = None
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                parsed[key.strip()] = _parse_yaml_scalar(value.strip())
            continue

        if in_problems:
            if indent == 4 and stripped.endswith(":"):
                current_problem = stripped[:-1].strip()
                problems[current_problem] = {}
                continue

            if indent >= 8 and current_problem and ":" in stripped:
                key, value = stripped.split(":", 1)
                problems[current_problem][key.strip()] = _parse_yaml_scalar(value.strip())

    return parsed


def _merge_cloze_problem_fields(target_task_data, source_task_data):
    target_problems = target_task_data.get("problems", {})
    source_problems = source_task_data.get("problems", {})
    if not isinstance(target_problems, dict) or not isinstance(source_problems, dict):
        return

    for pid, source_problem in source_problems.items():
        if pid in target_problems:
            continue
        if not isinstance(source_problem, dict) or source_problem.get("type") != "cloze":
            continue
        target_problems[pid] = dict(source_problem)

    for pid, target_problem in target_problems.items():
        if not isinstance(target_problem, dict) or target_problem.get("type") != "cloze":
            continue

        source_problem = source_problems.get(pid)
        if not isinstance(source_problem, dict):
            continue

        for field in ("text", "variants_file"):
            if not target_problem.get(field) and source_problem.get(field):
                target_problem[field] = source_problem.get(field)


def _restore_cloze_editor_data(course_factory, course, taskid, task_data, template_helper=None):
    task_fs = _get_task_fs(course_factory, course.get_id(), taskid)
    source_task_data = _load_task_descriptor_from_task_fs(task_fs)
    known_path_task_data = _load_task_descriptor_from_known_paths(course.get_id(), taskid)
    if isinstance(source_task_data, dict) and isinstance(known_path_task_data, dict):
        _merge_cloze_problem_fields(source_task_data, known_path_task_data)
    elif not source_task_data:
        source_task_data = known_path_task_data
    if isinstance(task_data, dict) and isinstance(source_task_data, dict):
        _merge_cloze_problem_fields(task_data, source_task_data)
    return None


def _preserve_cloze_submit_data(course_factory, course, taskid, task_data, task_fs=None):
    # Do not preserve blanks on submit. If the user intentionally clears text or variants_file,
    # that change should be reflected in the saved task descriptor.
    return None


def _patch_task_editor_get_auth():
    try:
        from werkzeug.exceptions import NotFound
        from inginious.common.base import id_checker
        from inginious.common.exceptions import TaskNotFoundException
        from inginious.frontend.pages.course_admin.task_edit import CourseEditTask
        from inginious.frontend.pages.course_admin.task_edit_file import CourseTaskFiles
        from inginious.frontend.tasks import _migrate_from_v_0_6
    except Exception:
        return

    current = getattr(CourseEditTask, "GET_AUTH", None)
    if current is None or getattr(current, "_cloze_patched", False):
        return

    def patched_get_auth(self, courseid, taskid):  # pylint: disable=unused-argument
        if not id_checker(taskid):
            raise NotFound(description=_("Invalid task id"))

        course, __ = self.get_course_and_check_rights(courseid, allow_all_staff=False)

        try:
            task_data = self.task_factory.get_task_descriptor_content(courseid, taskid)
        except TaskNotFoundException:
            raise NotFound()

        task_data = _migrate_from_v_0_6(task_data)
        source_task_data = _load_task_descriptor_from_known_paths(courseid, taskid)
        if isinstance(source_task_data, dict):
            _merge_cloze_problem_fields(task_data, source_task_data)

        environment_types = self.environment_types
        environments = self.environments

        current_filetype = None
        try:
            current_filetype = self.task_factory.get_task_descriptor_extension(courseid, taskid)
        except Exception:
            pass
        available_filetypes = self.task_factory.get_available_task_file_extensions()

        additional_tabs = self.plugin_manager.call_hook(
            'task_editor_tab',
            course=course,
            taskid=taskid,
            task_data=task_data,
            template_helper=self.template_helper,
        )

        rendered = self.template_helper.render(
            "course_admin/task_edit.html",
            course=course,
            taskid=taskid,
            problem_types=self.task_factory.get_problem_types(),
            task_data=task_data,
            environment_types=environment_types,
            environments=environments,
            problemdata=json.dumps(task_data.get('problems', {})),
            contains_is_html=self.contains_is_html(task_data),
            current_filetype=current_filetype,
            available_filetypes=available_filetypes,
            file_list=CourseTaskFiles.get_task_filelist(self.task_factory, courseid, taskid),
            additional_tabs=additional_tabs,
        )
        hydrator = _inject_task_editor_cloze_hydrator()
        if isinstance(rendered, str) and "</body>" in rendered:
            return rendered.replace("</body>", hydrator + "\n</body>", 1)
        return rendered + hydrator

    patched_get_auth._cloze_patched = True  # type: ignore[attr-defined]
    CourseEditTask.GET_AUTH = patched_get_auth


def _start_cloze_agent(client, course_factory):
    context = getattr(client, "_context", None)
    backend_addr = getattr(client, "_router_addr", None)
    tasks_fs = _get_tasks_fs(course_factory)

    if context is None or backend_addr is None or tasks_fs is None:
        return

    # The frontend client speaks to the backend on the client socket. Agents must connect
    # to the agent socket instead.
    if backend_addr == "inproc://backend_client":
        backend_addr = "inproc://backend_agent"

    # Avoid starting duplicate agents when the plugin is initialized multiple times in one process.
    if any(not task.done() for task in _AGENT_TASKS):
        return

    agent = ClozeAgent(context, backend_addr, "Cloze - Local agent", 1, tasks_fs)
    task = asyncio.ensure_future(_restart_on_cancel(agent))
    _AGENT_TASKS.append(task)


def _get_evaluation_mode(course_factory, courseid, taskid):
    if course_factory is None:
        return None

    try:
        get_course = getattr(course_factory, "get_course", None)
        if callable(get_course):
            course = get_course(courseid)
            if course is not None:
                dispenser = course.get_task_dispenser()
                if dispenser is not None:
                    return dispenser.get_evaluation_mode(taskid)
    except Exception:
        return None

    return None


def _looks_like_cloze_state(raw_state):
    try:
        state = json.loads(raw_state or "")
    except Exception:
        return False

    if not isinstance(state, dict) or not state:
        return False

    for value in state.values():
        if not isinstance(value, dict):
            return False
        if "correct" not in value or "total" not in value:
            return False
    return True


def _sync_cloze_user_task_cache(database, course_factory, submission):
    if database is None or not _looks_like_cloze_state(submission.get("state")):
        return

    evaluation_mode = _get_evaluation_mode(course_factory, submission["courseid"], submission["taskid"])
    for username in submission.get("username", []):
        query = {
            "username": username,
            "courseid": submission["courseid"],
            "taskid": submission["taskid"],
        }
        current = database.user_tasks.find_one(query) or {}

        should_update = current.get("submissionid") in (None, submission["_id"])
        if evaluation_mode == "last":
            should_update = True
        elif evaluation_mode == "best":
            should_update = current.get("grade", 0.0) <= submission.get("grade", 0.0)
        elif evaluation_mode is None:
            # Fall back to a conservative heuristic for plugin-managed cloze tasks:
            # update the cache unless it already points to a strictly better submission.
            should_update = current.get("grade", 0.0) <= submission.get("grade", 0.0) or current.get("submissionid") in (None, submission["_id"])

        if should_update:
            database.user_tasks.find_one_and_update(
                query,
                {
                    "$set": {
                        "succeeded": submission.get("result") == "success",
                        "grade": submission.get("grade", 0.0),
                        "state": submission.get("state", ""),
                        "submissionid": submission["_id"],
                    }
                },
                upsert=True,
            )


def _inject_task_status_fix(course, task, template_helper):
    return """
<script>
(function () {
    "use strict";

    if (typeof window.load_feedback_cloze !== "function") {
        window.load_feedback_cloze = function () {
            return;
        };
    }

    if (typeof window.load_input_cloze !== "function") {
        window.load_input_cloze = function () {
            return;
        };
    }

    function normalizeText(node) {
        return (node && node.textContent ? node.textContent : "").replace(/\\s+/g, " ").trim();
    }

    function extractFeedbackText() {
        var alerts = document.querySelectorAll(".alert");
        for (var i = 0; i < alerts.length; i += 1) {
            var text = normalizeText(alerts[i]);
            if (text.indexOf("Your score is ") !== -1 || text.indexOf("Your submission timed out.") !== -1) {
                return text;
            }
        }
        return "";
    }

    function inferStatus(text) {
        if (!text) {
            return null;
        }
        if (text.indexOf("Your answer passed the tests!") !== -1) {
            return "Succeeded";
        }
        if (
            text.indexOf("There are some errors in your answer.") !== -1 ||
            text.indexOf("Your submission timed out.") !== -1 ||
            text.indexOf("Your submission made an overflow.") !== -1 ||
            text.indexOf("Your submission was killed.") !== -1
        ) {
            return "Failed";
        }
        return null;
    }

    function inferGrade(text) {
        var match = text.match(/Your score is ([0-9]+(?:\\.[0-9]+)?)%/);
        return match ? match[1] : null;
    }

    function syncSidebarFromFeedback() {
        var feedbackText = extractFeedbackText();
        if (!feedbackText) {
            return;
        }

        var status = inferStatus(feedbackText);
        var grade = inferGrade(feedbackText);

        var statusNode = document.getElementById("task_status");
        if (statusNode && status) {
            statusNode.textContent = status;
        }

        var gradeNode = document.getElementById("task_grade");
        if (gradeNode && grade !== null) {
            gradeNode.textContent = grade;
        }
    }

    function init() {
        syncSidebarFromFeedback();

        var observer = new MutationObserver(function () {
            syncSidebarFromFeedback();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });

        var taskForm = document.getElementById("task");
        if (taskForm) {
            taskForm.addEventListener("submit", function () {
                window.setTimeout(syncSidebarFromFeedback, 250);
                window.setTimeout(syncSidebarFromFeedback, 1000);
                window.setTimeout(syncSidebarFromFeedback, 2500);
            });
        }

        window.setInterval(syncSidebarFromFeedback, 1000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
</script>
"""


def _inject_task_editor_cloze_hydrator():
    return """
<script>
(function () {
    "use strict";

    function getProblemData() {
        if (window.__clozeHydratorProblemData) {
            return window.__clozeHydratorProblemData;
        }

        var raw = window.problem_data;
        if (!raw) {
            return null;
        }

        if (typeof raw === "string") {
            try {
                raw = JSON.parse(raw);
            } catch (err) {
                return null;
            }
        }

        if (!raw || typeof raw !== "object") {
            return null;
        }

        window.__clozeHydratorProblemData = raw;
        return raw;
    }

    function hydrate() {
        var problems = getProblemData();
        if (!problems) {
            return false;
        }

        var foundAll = true;
        Object.keys(problems).forEach(function (pid) {
            var problem = problems[pid];
            if (!problem || problem.type !== "cloze") {
                return;
            }

            [
                ["text", typeof problem.text === "string" ? problem.text : ""],
                ["variants_file", typeof problem.variants_file === "string" ? problem.variants_file : ""]
            ].forEach(function (entry) {
                var field = entry[0];
                var value = entry[1];
                var node = document.querySelector('[name="problem[' + pid + '][' + field + ']"]');
                if (!node) {
                    foundAll = false;
                    return;
                }
                node.value = value;
            });
        });

        return foundAll;
    }

    function attempt(count) {
        if (hydrate() || count >= 40) {
            return;
        }
        window.setTimeout(function () {
            attempt(count + 1);
        }, 100);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            attempt(0);
        });
    } else {
        attempt(0);
    }
})();
</script>
"""


def init(plugin_manager, course_factory, client, entry):
    try:
        from inginious.frontend.environment_types import register_env_type
    except Exception:
        register_env_type = getattr(plugin_manager, "register_env_type", None)

    if callable(register_env_type):
        register_env_type(ClozeFrontendEnv())

    database = getattr(plugin_manager, "get_database", lambda: None)()
    plugin_manager.add_hook(
        "submission_done",
        lambda submission, archive, newsub: _sync_cloze_user_task_cache(database, course_factory, submission),
    )
    plugin_manager.add_hook("task_menu", _inject_task_status_fix)
    plugin_manager.add_hook(
        "task_editor_tab",
        lambda course, taskid, task_data, template_helper: _restore_cloze_editor_data(
            course_factory, course, taskid, task_data, template_helper
        ),
    )
    _patch_task_editor_get_auth()
    _start_cloze_agent(client, course_factory)
    return
