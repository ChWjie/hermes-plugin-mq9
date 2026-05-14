from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mq9.mq9_client import Mailbox, Mq9Error
from mq9.runtime import MQ9HermesRuntime, _strip_mq9_uri


class _MailboxClient:
    def __init__(self, nats_url: str) -> None:
        self.nats_url = nats_url
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "_MailboxClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def create_mailbox(
        self,
        *,
        ttl: int,
        name: str | None = None,
        desc: str | None = None,
        idempotent: bool = True,
        public: bool | None = None,
    ) -> Mailbox:
        self.calls.append(
            {
                "ttl": ttl,
                "name": name,
                "desc": desc,
                "idempotent": idempotent,
                "public": public,
            }
        )
        return Mailbox(mail_address=str(name or "generated"))


class _UnregisterClient:
    def __init__(self, nats_url: str) -> None:
        self.nats_url = nats_url
        self.unregistered: list[str] = []

    async def __aenter__(self) -> "_UnregisterClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def unregister_agent(self, *, name: str) -> None:
        self.unregistered.append(name)
        if name.endswith(".missing"):
            raise Mq9Error("agent not found")


class RuntimeUnitTests(unittest.TestCase):
    def test_strip_mq9_uri(self) -> None:
        self.assertEqual(_strip_mq9_uri("mq9://broker/a.b"), "a.b")
        self.assertEqual(_strip_mq9_uri("mq9s://broker/a.b"), "a.b")
        self.assertEqual(_strip_mq9_uri("a.b"), "a.b")

    def test_ensure_mailbox_uses_idempotent_create(self) -> None:
        runtime = MQ9HermesRuntime()
        client = _MailboxClient("nats://127.0.0.1:4222")
        mailbox = asyncio.run(runtime._ensure_mailbox(client, "mq9://broker/demo.box", 120))
        self.assertEqual(mailbox, "demo.box")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["name"], "demo.box")
        self.assertEqual(client.calls[0]["idempotent"], True)

    def test_unregister_cleanup_clears_runtime_state(self) -> None:
        runtime = MQ9HermesRuntime()
        runtime._registered_names = {"agent-a"}  # pylint: disable=protected-access
        runtime._registered_card = {"name": "agent-a"}  # pylint: disable=protected-access

        with patch("mq9.runtime.Mq9Client", _UnregisterClient):
            runtime._unregister_registered_agents_best_effort()  # pylint: disable=protected-access

        self.assertEqual(runtime._registered_names, set())  # pylint: disable=protected-access
        self.assertIsNone(runtime._registered_card)  # pylint: disable=protected-access

    def test_unregister_self_treats_not_found_as_removed(self) -> None:
        runtime = MQ9HermesRuntime()
        runtime._registered_names = {  # pylint: disable=protected-access
            "agent-a",
            "agent-b.missing",
        }
        runtime._registered_card = {"name": "agent-a"}  # pylint: disable=protected-access

        with patch("mq9.runtime.Mq9Client", _UnregisterClient):
            result = runtime.unregister_self({})

        self.assertTrue(result["ok"])
        self.assertEqual(sorted(result["removed"]), ["agent-a", "agent-b.missing"])
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
