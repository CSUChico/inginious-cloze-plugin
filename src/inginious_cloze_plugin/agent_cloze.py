# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse

try:
    import zmq.asyncio
    from inginious_cloze_plugin.cloze_agent import ClozeAgent
except ModuleNotFoundError:  # pragma: no cover - local tests without INGInious installed
    zmq = None
    ClozeAgent = None


def _load_local_fs_provider():
    candidates = [
        "inginious.common.filesystems.local.LocalFSProvider",
        "inginious.common.filesystems.localfs.LocalFSProvider",
    ]
    for dotted_path in candidates:
        module_name, class_name = dotted_path.rsplit(".", 1)
        try:
            module = __import__(module_name, fromlist=[class_name])
            return getattr(module, class_name)
        except Exception:
            continue
    raise ImportError("Could not locate INGInious LocalFSProvider implementation.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the INGInious cloze grading agent.")
    parser.add_argument("--backend", required=True, help="ZeroMQ backend address, for example tcp://127.0.0.1:2000")
    parser.add_argument("--tasks-dir", required=True, help="Root directory containing courses and tasks")
    parser.add_argument("--name", default="Cloze - Local agent", help="Friendly agent name")
    parser.add_argument("--concurrency", type=int, default=1, help="Maximum concurrent jobs")
    args = parser.parse_args(argv)

    local_fs_provider = _load_local_fs_provider()
    context = zmq.asyncio.Context()
    agent = ClozeAgent(context, args.backend, args.name, args.concurrency, local_fs_provider(args.tasks_dir))
    agent.run()


if __name__ == "__main__":  # pragma: no cover
    main()
