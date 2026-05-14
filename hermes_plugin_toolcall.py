#!/usr/bin/env python3
"""Invoke mq9 plugin tools through Hermes plugin + registry runtime.

This script proves the plugin is loaded by Hermes plugin manager and that
its tool handlers can be called through Hermes tool dispatch path.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
import time
from pathlib import Path

from hermes_cli.plugins import discover_plugins
from tools.registry import registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hermes mq9 plugin toolcall helper")
    parser.add_argument("--home", default="~/.hermes")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:45222")
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--mailbox", required=True)

    parser.add_argument("--mode", choices=["server", "client", "status"], default="status")

    parser.add_argument("--query", default="Python HTTP server")
    parser.add_argument("--prefer-name", default="hermes-b")
    parser.add_argument("--target-mailbox", default="")
    parser.add_argument("--task", default="Please write a Python HTTP server with one GET endpoint.")
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--tool-family", choices=["mq9", "a2a"], default="mq9")

    parser.add_argument("--duration", type=float, default=0.0, help="server mode only")
    return parser.parse_args()


def _dispatch(name: str, payload: dict) -> dict:
    raw = registry.dispatch(name, payload)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def main() -> int:
    args = parse_args()
    hermes_home = Path(args.home).expanduser().resolve()

    os.environ["HERMES_HOME"] = str(hermes_home)
    if not os.environ.get("HOME"):
        os.environ["HOME"] = str(Path.home())
    os.environ["HERMES_MQ9_NATS_URL"] = args.nats_url
    os.environ["HERMES_MQ9_AGENT_NAME"] = args.agent_name
    os.environ["HERMES_MQ9_MAILBOX"] = args.mailbox

    if args.mode == "server":
        os.environ["HERMES_MQ9_AUTO_REGISTER"] = "1"
        os.environ["HERMES_MQ9_PASSIVE_SERVE"] = "1"
    else:
        os.environ["HERMES_MQ9_AUTO_REGISTER"] = "0"
        os.environ["HERMES_MQ9_PASSIVE_SERVE"] = "0"

    discover_plugins(force=True)

    register_tool = "a2a_register_self" if args.tool_family == "a2a" else "mq9_register_self"
    discover_tool = "a2a_discover" if args.tool_family == "a2a" else "mq9_discover"
    call_tool = "a2a_call" if args.tool_family == "a2a" else "mq9_call"

    if args.mode == "status":
        print(json.dumps(_dispatch("mq9_status", {}), ensure_ascii=False, indent=2))
        return 0

    if args.mode == "server":
        print("[hermes-plugin-server] register_self:")
        print(
            json.dumps(
                _dispatch(
                    register_tool,
                    {
                        "agent_name": args.agent_name,
                        "mailbox": args.mailbox,
                        "ensure_runtime": True,
                        "description": "Hermes-B plugin runtime server",
                        "tags": ["python", "http", "backend"],
                    },
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        print("[hermes-plugin-server] status:")
        print(json.dumps(_dispatch("mq9_status", {}), ensure_ascii=False, indent=2), flush=True)

        stop_event = threading.Event()

        def _on_signal(signum, _frame):
            print(f"[hermes-plugin-server] got signal={signum}, exiting", flush=True)
            stop_event.set()

        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)

        deadline = time.time() + args.duration if args.duration > 0 else None
        while not stop_event.is_set():
            if deadline is not None and time.time() >= deadline:
                break
            time.sleep(1.0)

        print("[hermes-plugin-server] unregister_self:")
        print(
            json.dumps(
                _dispatch("mq9_unregister_self", {"agent_name": args.agent_name}),
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        return 0

    print("[hermes-plugin-client] discover:")
    discover_payload = {
        "query": args.query,
        "limit": 10,
        "prefer_name": args.prefer_name,
    }
    print(json.dumps(_dispatch(discover_tool, discover_payload), ensure_ascii=False, indent=2))

    call_payload = {
        "target_mailbox": args.target_mailbox,
        "query": args.query,
        "prefer_name": args.prefer_name,
        "message": {
            "instruction": args.task,
            "lang": "python",
            "expect": "return runnable HTTP server example",
        },
        "from_agent": args.agent_name,
        "timeout_s": args.timeout,
    }
    print("[hermes-plugin-client] call:")
    print(json.dumps(_dispatch(call_tool, call_payload), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
