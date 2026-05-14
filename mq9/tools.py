"""Tool handlers for mq9 Hermes plugin."""

from __future__ import annotations

import json
import logging
from typing import Any

from .runtime import MQ9HermesRuntime

logger = logging.getLogger(__name__)

_RUNTIME: MQ9HermesRuntime | None = None

try:  # pragma: no cover - only active inside Hermes runtime
    from tools.registry import tool_error as _tool_error
    from tools.registry import tool_result as _tool_result
except Exception:  # pragma: no cover - local fallback
    def _tool_error(message: Any, **extra: Any) -> str:
        payload = {"error": str(message)}
        payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)

    def _tool_result(data: Any = None, **kwargs: Any) -> str:
        if data is not None:
            return json.dumps(data, ensure_ascii=False)
        return json.dumps(kwargs, ensure_ascii=False)


def bind_runtime(runtime: MQ9HermesRuntime) -> None:
    global _RUNTIME
    _RUNTIME = runtime


def _require_runtime() -> MQ9HermesRuntime:
    if _RUNTIME is None:
        raise RuntimeError("mq9 runtime is not initialized")
    return _RUNTIME


def mq9_register_self(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    try:
        result = runtime.register_self(args)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("mq9_register_self failed: %s", exc)
        return _tool_error(f"mq9_register_self failed: {exc}")


def mq9_unregister_self(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    try:
        result = runtime.unregister_self(args)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("mq9_unregister_self failed: %s", exc)
        return _tool_error(f"mq9_unregister_self failed: {exc}")


def mq9_discover(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    try:
        result = runtime.discover(args)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("mq9_discover failed: %s", exc)
        return _tool_error(f"mq9_discover failed: {exc}")


def mq9_call(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    try:
        result = runtime.call(args)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("mq9_call failed: %s", exc)
        return _tool_error(f"mq9_call failed: {exc}")


def mq9_status(args: dict[str, Any], **kwargs: Any) -> str:
    del args, kwargs
    runtime = _require_runtime()
    try:
        return _tool_result(runtime.status())
    except Exception as exc:
        logger.exception("mq9_status failed: %s", exc)
        return _tool_error(f"mq9_status failed: {exc}")


def a2a_register_self(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    merged = dict(args or {})
    raw_protocols = merged.get("protocols")
    if isinstance(raw_protocols, list):
        protocols = [str(item).strip() for item in raw_protocols if str(item).strip()]
    elif raw_protocols:
        protocols = [str(raw_protocols).strip()]
    else:
        protocols = []
    if "a2a" not in protocols:
        protocols.append("a2a")
    merged["protocols"] = protocols
    try:
        result = runtime.register_self(merged)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("a2a_register_self failed: %s", exc)
        return _tool_error(f"a2a_register_self failed: {exc}")


def a2a_discover(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    merged = dict(args or {})
    merged["protocol"] = "a2a"
    merged["require_protocol"] = _as_bool_like(merged.get("require_protocol"), True)
    try:
        result = runtime.discover(merged)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("a2a_discover failed: %s", exc)
        return _tool_error(f"a2a_discover failed: {exc}")


def a2a_call(args: dict[str, Any], **kwargs: Any) -> str:
    del kwargs
    runtime = _require_runtime()
    merged = dict(args or {})
    merged["protocol"] = "a2a"
    merged["require_protocol"] = _as_bool_like(merged.get("require_protocol"), True)
    if "content_type" not in merged:
        merged["content_type"] = "application/json"
    try:
        result = runtime.call(merged)
        return _tool_result(result)
    except Exception as exc:
        logger.exception("a2a_call failed: %s", exc)
        return _tool_error(f"a2a_call failed: {exc}")


def _as_bool_like(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default
