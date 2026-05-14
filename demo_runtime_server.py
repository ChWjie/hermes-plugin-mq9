#!/usr/bin/env python3
"""Run mq9 plugin runtime as a passive server process.

This simulates one Hermes instance (Hermes-B) without requiring the `hermes`
binary in local environment.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import threading
import time

from mq9.runtime import MQ9HermesRuntime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="mq9 plugin runtime server demo")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:45222")
    parser.add_argument("--agent-name", default="hermes-b")
    parser.add_argument("--mailbox", default="hermes.b.inbox")
    parser.add_argument("--mailbox-ttl", type=int, default=24 * 3600)
    parser.add_argument("--duration", type=float, default=0.0, help="optional auto-stop seconds")
    return parser.parse_args()


def apply_env(args: argparse.Namespace) -> None:
    os.environ["HERMES_MQ9_NATS_URL"] = args.nats_url
    os.environ["HERMES_MQ9_AGENT_NAME"] = args.agent_name
    os.environ["HERMES_MQ9_MAILBOX"] = args.mailbox
    os.environ["HERMES_MQ9_MAILBOX_TTL"] = str(args.mailbox_ttl)
    os.environ["HERMES_MQ9_AUTO_REGISTER"] = "1"
    os.environ["HERMES_MQ9_PASSIVE_SERVE"] = "1"


def main() -> int:
    args = parse_args()
    apply_env(args)

    runtime = MQ9HermesRuntime()
    status = runtime.start_background(reason="demo-runtime-server")
    print("[demo-server] started:")
    print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)

    stop_event = threading.Event()

    def _handle_signal(signum: int, _frame) -> None:
        print(f"[demo-server] got signal={signum}, stopping...", flush=True)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    deadline = time.time() + args.duration if args.duration > 0 else None

    try:
        while not stop_event.is_set():
            if deadline is not None and time.time() >= deadline:
                break
            time.sleep(1.0)
    finally:
        final_status = runtime.stop_background(reason="demo-runtime-server-exit")
        print("[demo-server] stopped:")
        print(json.dumps(final_status, ensure_ascii=False, indent=2), flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
