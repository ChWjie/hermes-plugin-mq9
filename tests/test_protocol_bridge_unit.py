from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mq9.protocol_bridge import (  # noqa: E402
    agent_supports_protocol,
    build_call_envelope,
    extract_agent_protocols,
    normalize_protocols,
    parse_call_envelope,
)


class ProtocolBridgeUnitTests(unittest.TestCase):
    def test_normalize_protocols_dedupes_and_keeps_default(self) -> None:
        self.assertEqual(
            normalize_protocols(["A2A", "custom", "a2a"], default_protocol="a2a"),
            ["a2a", "custom"],
        )

    def test_extract_agent_protocols(self) -> None:
        agent = {
            "name": "demo",
            "metadata": {"protocols": ["a2a", "x-custom"]},
        }
        self.assertEqual(extract_agent_protocols(agent), ["a2a", "x-custom"])

    def test_agent_supports_protocol(self) -> None:
        undeclared = {"name": "node-1"}
        self.assertTrue(agent_supports_protocol(undeclared, "a2a", require_declared=False))
        self.assertFalse(agent_supports_protocol(undeclared, "a2a", require_declared=True))

    def test_call_envelope_roundtrip(self) -> None:
        envelope = build_call_envelope(
            from_agent="agent-a",
            correlation_id="cid-1",
            reply_to="agent.a.callback",
            payload={"task": "demo"},
            protocol="a2a",
            content_type="application/json",
            context={"trace_id": "t-001"},
        )
        parsed = parse_call_envelope(envelope)
        assert parsed is not None
        self.assertEqual(parsed["protocol"], "a2a")
        self.assertEqual(parsed["callback_mailbox"], "agent.a.callback")
        self.assertEqual(parsed["correlation_id"], "cid-1")
        self.assertEqual(parsed["payload"], {"task": "demo"})
        self.assertEqual(parsed["content_type"], "application/json")
        self.assertEqual(parsed["context"], {"trace_id": "t-001"})


if __name__ == "__main__":
    unittest.main()
