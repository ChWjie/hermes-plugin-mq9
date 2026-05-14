from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mq9.mq9_client import Mq9Client


class _CreateMailboxClient(Mq9Client):
    def __init__(self) -> None:
        super().__init__("nats://127.0.0.1:4222")
        self.last_request: dict[str, Any] = {}

    async def _request(  # type: ignore[override]
        self,
        subject: str,
        payload: dict[str, Any] | str,
        *,
        headers: dict[str, str] | None = None,
        retries: int = 1,
    ) -> dict[str, Any]:
        self.last_request = {
            "subject": subject,
            "payload": payload,
            "headers": headers,
            "retries": retries,
        }
        return {
            "error": "",
            "mail_address": "demo.box",
            "created": False,
            "already_exists": True,
        }


class _RetryClient(Mq9Client):
    def __init__(self) -> None:
        super().__init__("nats://127.0.0.1:4222")
        self.calls = 0

    async def _raw_nats_request(  # type: ignore[override]
        self,
        subject: str,
        payload: bytes,
        *,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        del subject, payload, headers
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("timeout")
        return b'{"error":"","ok":true}'


class Mq9ClientUnitTests(unittest.TestCase):
    def test_create_mailbox_defaults_to_idempotent(self) -> None:
        client = _CreateMailboxClient()
        mailbox = asyncio.run(client.create_mailbox(name="demo.box", ttl=600))
        self.assertEqual(mailbox.mail_address, "demo.box")
        self.assertEqual(mailbox.created, False)
        self.assertEqual(mailbox.already_exists, True)
        self.assertEqual(client.last_request["subject"], "$mq9.AI.MAILBOX.CREATE")
        self.assertEqual(client.last_request["retries"], 3)
        payload = client.last_request["payload"]
        self.assertEqual(payload["name"], "demo.box")
        self.assertEqual(payload["idempotent"], True)

    def test_request_retries_after_timeout(self) -> None:
        client = _RetryClient()
        result = asyncio.run(
            client._request(  # pylint: disable=protected-access
                "$mq9.AI.MSG.FETCH.demo.box",
                {"group_name": "g"},
                retries=2,
            )
        )
        self.assertEqual(client.calls, 2)
        self.assertEqual(result.get("ok"), True)

    def test_unregister_agent_rejects_empty_name(self) -> None:
        client = _CreateMailboxClient()
        with self.assertRaises(ValueError):
            asyncio.run(client.unregister_agent(name="  "))


if __name__ == "__main__":
    unittest.main()
