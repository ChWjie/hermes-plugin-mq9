"""Protocol-agnostic helpers for mq9 transport envelopes.

mq9 is the transport/discovery substrate. Higher-level protocols (A2A or
custom application envelopes) are carried opaquely through mq9 payload fields.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PROTOCOL = "a2a"


def normalize_protocol(value: Any, fallback: str = DEFAULT_PROTOCOL) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in "._-")
    return cleaned or fallback


def normalize_protocols(values: Any, default_protocol: str = DEFAULT_PROTOCOL) -> list[str]:
    raw_items: list[Any]
    if isinstance(values, list):
        raw_items = values
    elif values in (None, ""):
        raw_items = [default_protocol]
    else:
        raw_items = [values]

    ordered: list[str] = []
    for raw in raw_items:
        name = normalize_protocol(raw, fallback=default_protocol)
        if name not in ordered:
            ordered.append(name)

    if default_protocol not in ordered:
        ordered.insert(0, default_protocol)
    return ordered


def extract_agent_protocols(agent: dict[str, Any]) -> list[str]:
    protocols: list[str] = []

    top_level = agent.get("protocols")
    if isinstance(top_level, list):
        for item in top_level:
            name = normalize_protocol(item, fallback="")
            if name and name not in protocols:
                protocols.append(name)

    metadata = agent.get("metadata")
    if isinstance(metadata, dict):
        meta_protocols = metadata.get("protocols")
        if isinstance(meta_protocols, list):
            for item in meta_protocols:
                name = normalize_protocol(item, fallback="")
                if name and name not in protocols:
                    protocols.append(name)

        raw_single = metadata.get("protocol")
        if raw_single:
            name = normalize_protocol(raw_single, fallback="")
            if name and name not in protocols:
                protocols.append(name)

    if "a2a" in str(agent).lower() and "a2a" not in protocols:
        # Best-effort heuristic for cards that include A2A hints but do not
        # expose explicit metadata.protocols.
        protocols.append("a2a")

    return protocols


def agent_supports_protocol(
    agent: dict[str, Any],
    protocol: str | None,
    *,
    require_declared: bool,
) -> bool:
    if not protocol:
        return True
    normalized = normalize_protocol(protocol, fallback="")
    if not normalized:
        return True

    declared = extract_agent_protocols(agent)
    if not declared:
        return not require_declared
    return normalized in declared


def build_transport_metadata(
    mailbox: str,
    *,
    protocols: list[str],
    extra_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "mq9": {
            "mailbox": mailbox,
            "transport": "nats",
        },
        "protocols": normalize_protocols(protocols),
    }
    if isinstance(extra_metadata, dict):
        for key, value in extra_metadata.items():
            metadata[key] = value
    return metadata


def build_call_envelope(
    *,
    from_agent: str,
    correlation_id: str,
    reply_to: str,
    payload: Any,
    protocol: str,
    content_type: str | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "type": "mq9_call",
        "from": from_agent,
        "reply_to": reply_to,
        "correlation_id": correlation_id,
        "protocol": normalize_protocol(protocol),
        "payload": payload,
    }
    if content_type:
        envelope["content_type"] = str(content_type).strip()
    if isinstance(context, dict) and context:
        envelope["context"] = context
    return envelope


def parse_call_envelope(body: Any) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    if body.get("type") != "mq9_call":
        return None

    callback_mailbox = body.get("reply_to")
    correlation_id = body.get("correlation_id")
    if not callback_mailbox or not correlation_id:
        return None

    return {
        "protocol": normalize_protocol(body.get("protocol")),
        "content_type": str(body.get("content_type") or "").strip() or None,
        "payload": body.get("payload"),
        "context": body.get("context") if isinstance(body.get("context"), dict) else None,
        "callback_mailbox": str(callback_mailbox),
        "correlation_id": str(correlation_id),
    }


def build_call_reply(
    *,
    from_agent: str,
    correlation_id: str,
    protocol: str,
    content_type: str | None,
    ok: bool,
    result: dict[str, Any],
) -> dict[str, Any]:
    reply: dict[str, Any] = {
        "type": "mq9_call_reply",
        "ok": ok,
        "from": from_agent,
        "correlation_id": correlation_id,
        "protocol": normalize_protocol(protocol),
        "result": result,
    }
    if content_type:
        reply["content_type"] = str(content_type).strip()
    return reply
