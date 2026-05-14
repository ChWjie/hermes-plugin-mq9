from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mq9 import tools  # noqa: E402


class _FakeRuntime:
    def __init__(self) -> None:
        self.last_register_args: dict | None = None
        self.last_discover_args: dict | None = None
        self.last_call_args: dict | None = None

    def register_self(self, args: dict) -> dict:
        self.last_register_args = dict(args)
        return {"ok": True}

    def discover(self, args: dict) -> dict:
        self.last_discover_args = dict(args)
        return {"ok": True, "agents": []}

    def call(self, args: dict) -> dict:
        self.last_call_args = dict(args)
        return {"ok": True}

    def status(self) -> dict:
        return {"ok": True}


class ToolWrapperUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = _FakeRuntime()
        tools.bind_runtime(self.runtime)

    def test_a2a_register_self_enforces_protocol(self) -> None:
        raw = tools.a2a_register_self({"agent_name": "demo"})
        self.assertTrue(json.loads(raw)["ok"])
        assert self.runtime.last_register_args is not None
        self.assertIn("a2a", self.runtime.last_register_args["protocols"])

    def test_a2a_discover_sets_protocol_filter(self) -> None:
        raw = tools.a2a_discover({"query": "python"})
        self.assertTrue(json.loads(raw)["ok"])
        assert self.runtime.last_discover_args is not None
        self.assertEqual(self.runtime.last_discover_args["protocol"], "a2a")
        self.assertEqual(self.runtime.last_discover_args["require_protocol"], True)

    def test_a2a_call_sets_protocol_defaults(self) -> None:
        raw = tools.a2a_call({"message": {"instruction": "demo"}})
        self.assertTrue(json.loads(raw)["ok"])
        assert self.runtime.last_call_args is not None
        self.assertEqual(self.runtime.last_call_args["protocol"], "a2a")
        self.assertEqual(self.runtime.last_call_args["require_protocol"], True)
        self.assertEqual(self.runtime.last_call_args["content_type"], "application/json")


if __name__ == "__main__":
    unittest.main()
