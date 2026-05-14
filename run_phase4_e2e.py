#!/usr/bin/env python3
"""Run Phase 4 Hermes-A <-> Hermes-B e2e tests for mq9 plugin.

Two modes:
- toolcall: Hermes-A/B use plugin tool helper script directly (no LLM key needed).
- llm: Hermes-A uses natural-language prompt via `hermes -z`, then triggers mq9 tools.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    plugin_dir = Path(__file__).resolve().parent
    venv_python = plugin_dir / ".venv-hermes" / "bin" / "python"
    venv_hermes = plugin_dir / ".venv-hermes" / "bin" / "hermes"

    parser = argparse.ArgumentParser(description="Run Hermes mq9 phase-4 e2e test")
    parser.add_argument("--mode", choices=["toolcall", "llm"], default="toolcall")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:45222")
    parser.add_argument("--broker-conf", default=str(root / "config" / "server-poc-isolated.toml"))
    parser.add_argument("--workdir", default=str(root))
    parser.add_argument("--plugin-dir", default=str(plugin_dir))
    parser.add_argument("--home-root", default="")
    parser.add_argument("--hermes-python", default=str(venv_python))
    parser.add_argument("--hermes-bin", default=str(venv_hermes))
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument(
        "--server-execute-mode",
        choices=["auto", "minimal", "oneshot"],
        default="auto",
        help=(
            "Hermes-B passive execute mode. auto=oneshot for llm mode, "
            "minimal for toolcall mode."
        ),
    )
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--startup-timeout", type=float, default=25.0)
    parser.add_argument("--call-timeout", type=float, default=90.0)
    parser.add_argument("--server-duration", type=float, default=240.0)
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def now_ts() -> int:
    return int(time.time())


def log(msg: str) -> None:
    print(f"[phase4-e2e] {msg}", flush=True)


def parse_nats_host_port(nats_url: str) -> tuple[str, int]:
    parsed = urlparse(nats_url)
    if parsed.scheme != "nats":
        raise ValueError(f"Unsupported nats url: {nats_url}")
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or 4222)
    return host, port


def wait_port_open(host: str, port: int, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.6)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            time.sleep(0.25)
        finally:
            sock.close()
    return False


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_home_config(
    nats_url: str,
    passive_execute_mode: str,
    provider: str,
    model: str,
) -> str:
    base = [
        f"model: {model}",
        "toolsets:",
        "  - hermes-cli",
        "  - mq9",
        "plugins:",
        "  enabled:",
        "    - mq9",
        "  disabled: []",
        "  entries:",
        "    mq9:",
        f"      nats_url: {nats_url}",
        "      auto_register: true",
        "      passive_serve: true",
        f"      passive_execute_mode: {passive_execute_mode}",
        "      default_discover_limit: 10",
        "      default_call_timeout_s: 30",
    ]
    if passive_execute_mode == "oneshot":
        base.extend(
            [
                "      oneshot_timeout_s: 90",
                f"      oneshot_provider: {provider}",
                f"      oneshot_model: {model}",
            ]
        )
    return "\n".join(base) + "\n"


def create_homes(
    args: argparse.Namespace,
    *,
    b_execute_mode: str,
) -> tuple[Path, Path, Path]:
    if args.home_root:
        base = Path(args.home_root).resolve()
        base.mkdir(parents=True, exist_ok=True)
    else:
        base = Path(tempfile.mkdtemp(prefix="mq9-hermes-e2e.", dir="/private/tmp"))

    plugin_src = Path(args.plugin_dir).resolve() / "mq9"
    if not plugin_src.exists():
        raise FileNotFoundError(f"mq9 plugin directory not found: {plugin_src}")

    home_a = base / "home_a"
    home_b = base / "home_b"
    for home in (home_a, home_b):
        (home / "plugins").mkdir(parents=True, exist_ok=True)
        dst = home / "plugins" / "mq9"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(plugin_src, dst)

    cfg_a = make_home_config(args.nats_url, "minimal", args.provider, args.model)
    cfg_b = make_home_config(args.nats_url, b_execute_mode, args.provider, args.model)
    write_text(home_a / "config.yaml", cfg_a)
    write_text(home_b / "config.yaml", cfg_b)

    return base, home_a, home_b


def start_broker(args: argparse.Namespace) -> subprocess.Popen[str]:
    workdir = Path(args.workdir).resolve()
    conf = Path(args.broker_conf).resolve()
    if not conf.exists():
        raise FileNotFoundError(f"Broker config not found: {conf}")

    target_bin = workdir / "target" / "debug" / "broker-server"
    if target_bin.exists():
        cmd = [str(target_bin), "--conf", str(conf)]
    else:
        cmd = ["cargo", "run", "--package", "cmd", "--bin", "broker-server", "--", "--conf", str(conf)]

    log(f"starting broker: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    host, port = parse_nats_host_port(args.nats_url)
    if not wait_port_open(host, port, timeout_s=args.startup_timeout):
        output = read_available_output(process, max_lines=200)
        raise RuntimeError(f"broker did not open {host}:{port}\n{output}")
    return process


def read_available_output(process: subprocess.Popen[str], max_lines: int = 80) -> str:
    lines: list[str] = []
    if process.stdout is None:
        return ""
    while len(lines) < max_lines:
        ready, _, _ = select.select([process.stdout], [], [], 0.01)
        if not ready:
            break
        line = process.stdout.readline()
        if not line:
            break
        lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def wait_for_server_ready(process: subprocess.Popen[str], timeout_s: float) -> str:
    if process.stdout is None:
        raise RuntimeError("server process missing stdout pipe")
    deadline = time.time() + timeout_s
    output_lines: list[str] = []
    while time.time() < deadline:
        if process.poll() is not None:
            break
        ready, _, _ = select.select([process.stdout], [], [], 0.2)
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            continue
        text = line.rstrip("\n")
        output_lines.append(text)
        if '"running": true' in text:
            return "\n".join(output_lines)
        # Some environments may delay full status dump; seeing a successful
        # register_self payload and a still-running process is enough.
        if '"ok": true' in text and process.poll() is None:
            return "\n".join(output_lines)
    extra = read_available_output(process, max_lines=200)
    if extra:
        output_lines.append(extra)
    raise RuntimeError(
        "Hermes-B server did not become ready in time.\n" + "\n".join(output_lines)
    )


def start_hermes_b(
    args: argparse.Namespace,
    home_b: Path,
    agent_b: str,
    mailbox_b: str,
    execute_mode: str,
    api_key: str,
) -> subprocess.Popen[str]:
    helper = Path(args.plugin_dir).resolve() / "hermes_plugin_toolcall.py"
    if not helper.exists():
        raise FileNotFoundError(f"helper script not found: {helper}")

    env = os.environ.copy()
    env["HOME"] = str(home_b)
    env["HERMES_HOME"] = str(home_b)
    env["HERMES_MQ9_PASSIVE_EXECUTE_MODE"] = execute_mode
    if execute_mode == "oneshot":
        env["HERMES_MQ9_ONESHOT_PROVIDER"] = args.provider
        env["HERMES_MQ9_ONESHOT_MODEL"] = args.model
        if api_key:
            env[args.api_key_env] = api_key

    cmd = [
        args.hermes_python,
        "-u",
        str(helper),
        "--home",
        str(home_b),
        "--mode",
        "server",
        "--nats-url",
        args.nats_url,
        "--agent-name",
        agent_b,
        "--mailbox",
        mailbox_b,
        "--duration",
        str(args.server_duration),
    ]
    log(f"starting Hermes-B server: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=str(Path(args.workdir).resolve()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    ready_output = wait_for_server_ready(process, timeout_s=args.startup_timeout)
    if args.verbose:
        log("Hermes-B server ready output:")
        print(ready_output, flush=True)
    return process


def extract_json_after_marker(text: str, marker: str) -> dict[str, Any]:
    idx = text.find(marker)
    if idx < 0:
        raise ValueError(f"marker not found: {marker}")
    tail = text[idx + len(marker) :]
    start = tail.find("{")
    if start < 0:
        raise ValueError(f"json start not found after marker: {marker}")
    raw = tail[start:]

    depth = 0
    in_string = False
    escaped = False
    end_index = -1
    for i, ch in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_index = i + 1
                break
    if end_index < 0:
        raise ValueError(f"json object not closed after marker: {marker}")
    return json.loads(raw[:end_index])


def run_toolcall_mode(
    args: argparse.Namespace,
    home_a: Path,
    agent_a: str,
    mailbox_a: str,
    agent_b: str,
) -> dict[str, Any]:
    helper = Path(args.plugin_dir).resolve() / "hermes_plugin_toolcall.py"
    cmd = [
        args.hermes_python,
        str(helper),
        "--home",
        str(home_a),
        "--mode",
        "client",
        "--nats-url",
        args.nats_url,
        "--agent-name",
        agent_a,
        "--mailbox",
        mailbox_a,
        "--query",
        "Python HTTP server",
        "--prefer-name",
        agent_b,
        "--task",
        "Please write a minimal Python HTTP server with one GET /health endpoint and how to run it.",
        "--timeout",
        str(args.call_timeout),
    ]
    env = os.environ.copy()
    env["HOME"] = str(home_a)
    env["HERMES_HOME"] = str(home_a)
    log(f"running toolcall client: {' '.join(cmd)}")
    run = subprocess.run(
        cmd,
        cwd=str(Path(args.workdir).resolve()),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (run.stdout or "") + ("\n" + run.stderr if run.stderr else "")
    if run.returncode != 0:
        raise RuntimeError(f"toolcall mode failed: exit={run.returncode}\n{output}")

    discover = extract_json_after_marker(output, "[hermes-plugin-client] discover:")
    call = extract_json_after_marker(output, "[hermes-plugin-client] call:")
    return {"discover": discover, "call": call, "raw_output": output}


def latest_request_error(home: Path) -> str:
    sessions = home / "sessions"
    if not sessions.exists():
        return ""
    dumps = sorted(sessions.glob("request_dump_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not dumps:
        return ""
    try:
        payload = json.loads(dumps[0].read_text(encoding="utf-8"))
    except Exception:
        return ""
    err = payload.get("error")
    if not isinstance(err, dict):
        return ""
    message = str(err.get("message") or "").strip()
    code = str(err.get("code") or "").strip()
    status_code = err.get("status_code")
    if message or code or status_code:
        return f"status={status_code}, code={code}, message={message}"
    return ""


def run_llm_mode(
    args: argparse.Namespace,
    home_a: Path,
    agent_a: str,
    mailbox_a: str,
    agent_b: str,
    api_key: str,
) -> dict[str, Any]:
    hermes_bin = Path(args.hermes_bin)
    if not hermes_bin.exists():
        which = shutil.which("hermes")
        if which:
            hermes_bin = Path(which)
        else:
            raise FileNotFoundError(f"hermes binary not found: {args.hermes_bin}")

    prompt = (
        "你是 Hermes-A。请完成这个任务：找个会写 Python 的 agent 帮我写个 HTTP server。"
        f"要求：先调用 mq9_discover，query='Python HTTP server'，prefer_name='{agent_b}'；"
        "再调用 mq9_call 把任务发给发现到的目标；"
        "最后把对方返回的代码和运行方法整理成中文答复。"
    )

    cmd = [
        str(hermes_bin),
        "-z",
        prompt,
        "--toolsets",
        "hermes-cli,mq9",
        "--provider",
        args.provider,
        "--model",
        args.model,
    ]
    env = os.environ.copy()
    env["HOME"] = str(home_a)
    env["HERMES_HOME"] = str(home_a)
    env["HERMES_MQ9_NATS_URL"] = args.nats_url
    env["HERMES_MQ9_AGENT_NAME"] = agent_a
    env["HERMES_MQ9_MAILBOX"] = mailbox_a
    if api_key:
        env[args.api_key_env] = api_key

    log(f"running Hermes-A llm call: {' '.join(cmd)}")
    run = subprocess.run(
        cmd,
        cwd=str(Path(args.workdir).resolve()),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (run.stdout or "").strip()
    stderr = (run.stderr or "").strip()
    request_error = latest_request_error(home_a)

    result = {
        "returncode": run.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "request_error": request_error,
    }
    if run.returncode != 0:
        raise RuntimeError(f"llm mode failed: {json.dumps(result, ensure_ascii=False, indent=2)}")
    if not stdout:
        raise RuntimeError(
            "llm mode returned empty output. "
            f"request_error={request_error or 'unknown'}"
        )
    return result


def stop_process(process: subprocess.Popen[str], name: str) -> None:
    if process.poll() is not None:
        return
    try:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=4)
    except Exception:
        process.terminate()
        try:
            process.wait(timeout=3)
        except Exception:
            process.kill()

    output = read_available_output(process, max_lines=120)
    if output:
        log(f"{name} tail output:\n{output}")


def resolve_api_key(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key.strip()
    return os.getenv(args.api_key_env, "").strip()


def cleanup_artifacts(base: Path) -> None:
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)


def run() -> int:
    args = parse_args()
    api_key = resolve_api_key(args)
    base: Path | None = None
    broker: subprocess.Popen[str] | None = None
    server_b: subprocess.Popen[str] | None = None

    ts = now_ts()
    agent_a = f"hermes-a-e2e-{ts}"
    agent_b = f"hermes-b-e2e-{ts}"
    mailbox_a = f"hermes.a.e2e.inbox.{ts}"
    mailbox_b = f"hermes.b.e2e.inbox.{ts}"

    try:
        if args.server_execute_mode == "auto":
            b_mode = "oneshot" if args.mode == "llm" else "minimal"
        else:
            b_mode = args.server_execute_mode
        base, home_a, home_b = create_homes(args, b_execute_mode=b_mode)
        log(f"artifacts root: {base}")
        broker = start_broker(args)
        server_b = start_hermes_b(
            args,
            home_b,
            agent_b,
            mailbox_b,
            execute_mode=b_mode,
            api_key=api_key,
        )

        if args.mode == "toolcall":
            outcome = run_toolcall_mode(args, home_a, agent_a, mailbox_a, agent_b)
            call = outcome["call"]
            top_ok = bool(call.get("ok"))
            response = call.get("response") if isinstance(call.get("response"), dict) else {}
            response_ok = bool(response.get("ok")) if isinstance(response, dict) else False
            result = response.get("result") if isinstance(response, dict) else {}
            mode = result.get("mode")
            ok = bool(top_ok and response_ok)
            summary = {
                "mode": "toolcall",
                "success": ok,
                "server_execute_mode": b_mode,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "nats_url": args.nats_url,
                "call_mode": mode,
                "correlation_id": call.get("correlation_id"),
                "target_mailbox": call.get("target_mailbox"),
                "attempted_targets": call.get("attempted_targets"),
                "answer_preview": str(result.get("answer", ""))[:240],
                "artifacts_root": str(base),
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            if not ok:
                raise RuntimeError(
                    "toolcall e2e returned non-success reply: "
                    f"top_ok={top_ok}, response_ok={response_ok}"
                )
            return 0

        if not api_key:
            raise RuntimeError(
                f"llm mode requires API key via --api-key or env {args.api_key_env}"
            )

        llm = run_llm_mode(args, home_a, agent_a, mailbox_a, agent_b, api_key=api_key)
        summary = {
            "mode": "llm",
            "success": True,
            "server_execute_mode": b_mode,
            "agent_a": agent_a,
            "agent_b": agent_b,
            "nats_url": args.nats_url,
            "response_preview": llm["stdout"][:500],
            "artifacts_root": str(base),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    finally:
        if server_b is not None:
            stop_process(server_b, "Hermes-B server")
        if broker is not None:
            stop_process(broker, "broker")
        if base is not None and not args.keep_artifacts:
            cleanup_artifacts(base)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        raise SystemExit(130)
