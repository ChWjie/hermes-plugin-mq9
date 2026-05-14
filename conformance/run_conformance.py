#!/usr/bin/env python3
"""mq9 SDK conformance runner for Hermes plugin foundation (B2).

Current status:
- python: implemented (using example/hermes-plugin-mq9/mq9/mq9_client.py)
- go: reserved in matrix, not implemented yet
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

THIS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = THIS_DIR.parent
DEFAULT_CONTRACT = THIS_DIR / "contracts" / "hermes_foundation_v1.json"
DEFAULT_MATRIX = THIS_DIR / "matrix.json"

if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from mq9.mq9_client import FetchedMessage, Mq9Client, Mq9Error  # noqa: E402


@dataclass
class CaseResult:
    id: str
    title: str
    status: str
    duration_ms: int
    error: str | None
    details: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_mailbox(agent: dict[str, Any]) -> str | None:
    raw = agent.get("mailbox")
    if isinstance(raw, str):
        if raw.startswith("mq9://broker/"):
            return raw.removeprefix("mq9://broker/")
        return raw

    metadata = agent.get("metadata")
    if isinstance(metadata, dict):
        mq9_info = metadata.get("mq9")
        if isinstance(mq9_info, dict):
            for key in ("mailbox", "mail_address"):
                value = mq9_info.get(key)
                if isinstance(value, str) and value:
                    return value
    return None


class PythonMq9Adapter:
    def __init__(self, nats_url: str) -> None:
        self._client = Mq9Client(nats_url=nats_url, request_timeout=5.0)

    async def __aenter__(self) -> "PythonMq9Adapter":
        await self._client.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._client.close()

    async def create_mailbox(self, *, name: str, ttl: int, desc: str | None = None) -> str:
        mb = await self._client.create_mailbox(name=name, ttl=ttl, desc=desc)
        return mb.mail_address

    async def send_message(
        self,
        mailbox: str,
        payload: dict[str, Any] | str,
        *,
        priority: str = "normal",
    ) -> int:
        return await self._client.send_message(mailbox, payload, priority=priority)

    async def fetch_messages(
        self,
        mailbox: str,
        *,
        group_name: str,
        deliver: str,
        max_messages: int,
        max_wait_ms: int,
    ) -> list[FetchedMessage]:
        return await self._client.fetch_messages(
            mailbox,
            group_name=group_name,
            deliver=deliver,
            max_messages=max_messages,
            max_wait_ms=max_wait_ms,
        )

    async def ack_message(self, mailbox: str, group_name: str, msg_id: int) -> None:
        await self._client.ack_message(mailbox, group_name, msg_id)

    async def register_agent(self, *, name: str, payload: str) -> None:
        await self._client.register_agent(name=name, payload=payload)

    async def discover_agents(self, *, query: str, limit: int) -> list[dict[str, Any]]:
        return await self._client.discover_agents(query=query, limit=limit)

    async def unregister_agent(self, *, name: str) -> None:
        await self._client.unregister_agent(name=name)


async def _wait_for_messages(
    adapter: PythonMq9Adapter,
    *,
    mailbox: str,
    group_name: str,
    deliver: str,
    timeout_s: float,
    max_messages: int = 20,
) -> list[FetchedMessage]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        messages = await adapter.fetch_messages(
            mailbox,
            group_name=group_name,
            deliver=deliver,
            max_messages=max_messages,
            max_wait_ms=700,
        )
        if messages:
            return messages
        await asyncio.sleep(0.2)
    return []


async def case_mailbox_create_send_fetch_ack(
    adapter: PythonMq9Adapter,
    run_id: str,
) -> dict[str, Any]:
    mailbox = await adapter.create_mailbox(
        name=f"cf.p0.mail.{run_id}",
        ttl=3600,
        desc="conformance mailbox",
    )
    payload = {
        "kind": "conformance",
        "run_id": run_id,
        "step": "send_fetch_ack",
    }
    await adapter.send_message(mailbox, payload, priority="normal")

    group = f"cf-g.{run_id}"
    messages = await _wait_for_messages(
        adapter,
        mailbox=mailbox,
        group_name=group,
        deliver="earliest",
        timeout_s=8.0,
        max_messages=10,
    )
    if not messages:
        raise AssertionError("no message fetched for create/send/fetch/ack case")

    message = messages[0]
    body = message.parse_json()
    if not isinstance(body, dict):
        raise AssertionError(f"expected json payload, got: {body!r}")
    if body.get("run_id") != run_id:
        raise AssertionError(f"payload run_id mismatch: {body}")

    await adapter.ack_message(mailbox, group, message.msg_id)

    # Ensure no replay after ack on same group.
    for _ in range(3):
        replay = await adapter.fetch_messages(
            mailbox,
            group_name=group,
            deliver="latest",
            max_messages=10,
            max_wait_ms=300,
        )
        if not replay:
            break
        await asyncio.sleep(0.2)
    else:
        raise AssertionError("messages still replayed after ack")

    return {
        "mailbox": mailbox,
        "group": group,
        "msg_id": message.msg_id,
    }


async def case_message_priority_header(
    adapter: PythonMq9Adapter,
    run_id: str,
) -> dict[str, Any]:
    mailbox = await adapter.create_mailbox(
        name=f"cf.p0.priority.{run_id}",
        ttl=3600,
        desc="priority case mailbox",
    )
    await adapter.send_message(
        mailbox,
        {"kind": "priority", "run_id": run_id, "priority": "urgent"},
        priority="urgent",
    )

    group = f"cf-pri.{run_id}"
    messages = await _wait_for_messages(
        adapter,
        mailbox=mailbox,
        group_name=group,
        deliver="earliest",
        timeout_s=8.0,
        max_messages=10,
    )
    if not messages:
        raise AssertionError("no message fetched for priority case")

    first = messages[0]
    if first.priority != "urgent":
        raise AssertionError(f"expected urgent priority, got {first.priority!r}")

    await adapter.ack_message(mailbox, group, first.msg_id)
    return {
        "mailbox": mailbox,
        "group": group,
        "msg_id": first.msg_id,
        "priority": first.priority,
    }


async def case_agent_register_discover(
    adapter: PythonMq9Adapter,
    run_id: str,
) -> dict[str, Any]:
    agent_name = f"cf-agent-{run_id}"
    mailbox = await adapter.create_mailbox(
        name=f"cf.p0.agent.{run_id}",
        ttl=3600,
        desc="agent discover mailbox",
    )
    card = {
        "name": agent_name,
        "mailbox": f"mq9://broker/{mailbox}",
        "description": "conformance agent",
        "skills": [
            {
                "id": "python-http",
                "name": "Python HTTP",
                "tags": ["python", "http", "conformance"],
                "examples": ["write a python http server"]
            }
        ],
    }

    await adapter.register_agent(name=agent_name, payload=json.dumps(card, ensure_ascii=False))

    discovered: list[dict[str, Any]] = []
    for _ in range(12):
        discovered = await adapter.discover_agents(query=agent_name, limit=20)
        if any(item.get("name") == agent_name for item in discovered):
            break
        await asyncio.sleep(0.25)

    match = None
    for item in discovered:
        if item.get("name") == agent_name:
            discovered_mailbox = _extract_mailbox(item)
            if discovered_mailbox == mailbox:
                match = item
                break

    # cleanup best effort
    try:
        await adapter.unregister_agent(name=agent_name)
    except Mq9Error:
        pass

    if match is None:
        raise AssertionError(
            f"discover mismatch for {agent_name}: expected mailbox={mailbox}, got={discovered}"
        )

    return {
        "agent_name": agent_name,
        "mailbox": mailbox,
        "discover_count": len(discovered),
    }


CASE_IMPL: dict[str, Callable[[PythonMq9Adapter, str], Coroutine[Any, Any, dict[str, Any]]]] = {
    "mailbox.create_send_fetch_ack": case_mailbox_create_send_fetch_ack,
    "message.priority_header": case_message_priority_header,
    "agent.register_discover": case_agent_register_discover,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mq9 B2 conformance suite")
    parser.add_argument("--sdk", default="python", choices=["python", "go"])
    parser.add_argument("--suite", default="p0")
    parser.add_argument("--nats-url", default="nats://127.0.0.1:4222")
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--cases", default="")
    parser.add_argument("--json-out", default="")
    return parser.parse_args()


async def _run_python_suite(
    *,
    case_ids: list[str],
    case_defs: dict[str, dict[str, Any]],
    nats_url: str,
) -> list[CaseResult]:
    results: list[CaseResult] = []

    async with PythonMq9Adapter(nats_url=nats_url) as adapter:
        for case_id in case_ids:
            case_def = case_defs[case_id]
            title = str(case_def.get("title", case_id))
            started = time.perf_counter()
            run_id = uuid.uuid4().hex[:12]
            try:
                details = await CASE_IMPL[case_id](adapter, run_id)
                status = "passed"
                error = None
            except Exception as exc:  # noqa: BLE001
                details = {}
                status = "failed"
                error = str(exc)
            duration_ms = int((time.perf_counter() - started) * 1000)
            results.append(
                CaseResult(
                    id=case_id,
                    title=title,
                    status=status,
                    duration_ms=duration_ms,
                    error=error,
                    details=details,
                )
            )

    return results


def _select_cases(
    *,
    contract: dict[str, Any],
    matrix: dict[str, Any],
    suite: str,
    case_filter: str,
) -> tuple[list[str], dict[str, dict[str, Any]], list[str]]:
    suites = matrix.get("suites", {})
    if suite not in suites:
        raise ValueError(f"suite not found: {suite}")

    contract_cases = contract.get("cases", [])
    case_defs: dict[str, dict[str, Any]] = {}
    for item in contract_cases:
        if not isinstance(item, dict):
            continue
        case_id = item.get("id")
        if isinstance(case_id, str):
            case_defs[case_id] = item

    planned = suites[suite].get("cases", [])
    case_ids = [case_id for case_id in planned if case_id in case_defs and case_id in CASE_IMPL]

    if case_filter:
        allow = {segment.strip() for segment in case_filter.split(",") if segment.strip()}
        case_ids = [case_id for case_id in case_ids if case_id in allow]

    sdk_allow = suites[suite].get("sdks", [])
    return case_ids, case_defs, sdk_allow


async def _amain() -> int:
    args = _parse_args()
    contract = _load_json(Path(args.contract))
    matrix = _load_json(Path(args.matrix))

    started_at = int(time.time())
    case_ids, case_defs, sdk_allow = _select_cases(
        contract=contract,
        matrix=matrix,
        suite=args.suite,
        case_filter=args.cases,
    )

    summary: dict[str, Any] = {
        "contract_version": contract.get("contract_version"),
        "matrix_version": matrix.get("matrix_version"),
        "sdk": args.sdk,
        "suite": args.suite,
        "nats_url": args.nats_url,
        "started_at": started_at,
        "ended_at": None,
        "total": len(case_ids),
        "passed": 0,
        "failed": 0,
        "results": [],
    }

    if args.sdk not in sdk_allow:
        summary["failed"] = len(case_ids)
        summary["results"] = [
            {
                "id": "suite.sdk_guard",
                "title": "SDK allowed in suite",
                "status": "failed",
                "duration_ms": 0,
                "error": f"sdk '{args.sdk}' is not enabled in suite '{args.suite}'",
                "details": {"allowed_sdks": sdk_allow},
            }
        ]
        summary["ended_at"] = int(time.time())
        _emit_summary(summary, args.json_out)
        return 1

    if args.sdk == "go":
        summary["failed"] = len(case_ids)
        summary["results"] = [
            {
                "id": "runner.go.not_implemented",
                "title": "Go runner placeholder",
                "status": "failed",
                "duration_ms": 0,
                "error": "go runner is reserved in matrix but not implemented yet",
                "details": {
                    "next_step": "implement Go adapter with same case IDs",
                },
            }
        ]
        summary["ended_at"] = int(time.time())
        _emit_summary(summary, args.json_out)
        return 2

    results = await _run_python_suite(
        case_ids=case_ids,
        case_defs=case_defs,
        nats_url=args.nats_url,
    )

    summary["results"] = [asdict(item) for item in results]
    summary["passed"] = sum(1 for item in results if item.status == "passed")
    summary["failed"] = sum(1 for item in results if item.status != "passed")
    summary["ended_at"] = int(time.time())

    _emit_summary(summary, args.json_out)
    return 0 if summary["failed"] == 0 else 1


def _emit_summary(summary: dict[str, Any], json_out: str) -> None:
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(text)
    if json_out:
        out_path = Path(json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_amain()))
