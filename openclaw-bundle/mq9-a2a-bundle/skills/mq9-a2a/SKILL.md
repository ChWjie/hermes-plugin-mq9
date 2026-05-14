---
name: mq9-a2a
description: Route cross-agent collaboration through A2A semantics on top of mq9 MCP transport.
---

Use this skill when a task needs remote-agent discovery/call patterns.

Preferred tool flow:

1. `mq9_discover_agents` to find candidate agents by capability text.
2. `mq9_create_mailbox` to create callback or state mailbox when needed.
3. `mq9_send_message` to dispatch structured payload to target mailbox.
4. `mq9_fetch_messages` and `mq9_ack_message` to consume replies reliably.
5. `mq9_query_mailbox` to inspect status snapshots without consuming offsets.

Guidance:

- Keep payload protocol-opaque. The transport layer should not parse A2A schema details.
- Include task identifiers (`task_id`, `correlation_id`) in payload for reply matching.
- Prefer mailbox names that encode owner and purpose, such as `agent.backend.inbox`.
