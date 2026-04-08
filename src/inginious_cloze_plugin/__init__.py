# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio

from .cloze_problem_backend import ClozeProblem  # noqa: F401
from .cloze_agent import ClozeAgent  # noqa: F401
from .cloze_env import ClozeFrontendEnv  # noqa: F401
from .cloze_problem_frontend import DisplayableClozeProblem  # noqa: F401

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


def init(plugin_manager, course_factory, client, entry):
    try:
        from inginious.frontend.environment_types import register_env_type
    except Exception:
        register_env_type = getattr(plugin_manager, "register_env_type", None)

    if callable(register_env_type):
        register_env_type(ClozeFrontendEnv())

    _start_cloze_agent(client, course_factory)
    return
