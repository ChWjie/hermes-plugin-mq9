#!/usr/bin/env python3
"""Run mq9 plugin runtime as caller process.

This simulates one Hermes instance (Hermes-A) calling Hermes-B through mq9.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from mq9.runtime import MQ9HermesRuntime


DEFAULT_MESSAGE = "Please write a Python HTTP server with one GET endpoint."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="mq9 plugin runtime caller demo")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:45222")
    parser.add_argument("--from-agent", default="hermes-a")
    parser.add_argument("--mailbox", default="hermes.a.inbox")
    parser.add_argument("--target-mailbox", default="")
    parser.add_argument("--query", default="Python HTTP server")
    parser.add_argument("--prefer-name", default="hermes-b")
    parser.add_argument("--task", default=DEFAULT_MESSAGE)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument(
        "--register-self",
        action="store_true",
        help="register caller identity into mq9 before discover/call",
    )
    return parser.parse_args()


def apply_env(args: argparse.Namespace) -> None:
    os.environ["HERMES_MQ9_NATS_URL"] = args.nats_url
    os.environ["HERMES_MQ9_AGENT_NAME"] = args.from_agent
    os.environ["HERMES_MQ9_MAILBOX"] = args.mailbox
    os.environ["HERMES_MQ9_AUTO_REGISTER"] = "0"
    os.environ["HERMES_MQ9_PASSIVE_SERVE"] = "0"


def main() -> int:
    args = parse_args()
    apply_env(args)
    runtime = MQ9HermesRuntime()

    if args.register_self:
        reg = runtime.register_self(
            {
                "agent_name": args.from_agent,
                "mailbox": args.mailbox,
                "ensure_runtime": False,
                "description": "Hermes caller runtime demo",
            }
        )
        print("[demo-caller] register_self:")
        print(json.dumps(reg, ensure_ascii=False, indent=2), flush=True)

    discover = runtime.discover(
        {
            "query": args.query,
            "limit": 10,
            "prefer_name": args.prefer_name,
        }
    )
    print("[demo-caller] discover:")
    print(json.dumps(discover, ensure_ascii=False, indent=2), flush=True)

    message: dict[str, Any] = {
        "instruction": args.task,
        "lang": "python",
        "expect": "return runnable HTTP server example",
    }

    call = runtime.call(
        {
            "target_mailbox": args.target_mailbox,
            "query": args.query,
            "prefer_name": args.prefer_name,
            "message": message,
            "from_agent": args.from_agent,
            "timeout_s": args.timeout,
        }
    )
    print("[demo-caller] call:")
    print(json.dumps(call, ensure_ascii=False, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
