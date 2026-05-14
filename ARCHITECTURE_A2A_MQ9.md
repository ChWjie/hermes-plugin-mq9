# mq9 as A2A Transport/Discovery Substrate

This plugin version adopts the boundary described in RobustMQ blogs 96/99/101/102/103:

- A2A defines interaction semantics.
- mq9 provides transport + discovery infrastructure.
- The transport layer keeps upper-layer payload protocol-opaque.

## Why this is correct

The design follows the same split used in the blog series:

1. Discovery gap: A2A does not define a global registry protocol.
2. Async reliability gap: webhook/SSE/polling do not provide mailbox-grade durability.
3. Framework duplication gap: each framework rebuilding discover/call/serve logic.

mq9 already provides mailbox persistence, reliable async delivery, and registry APIs.
So the plugin keeps A2A in a thin wrapper layer while using mq9 for delivery/discovery.

## Implemented boundaries in this repo

1. Protocol-agnostic transport core:
   - `mq9/protocol_bridge.py`
   - Envelope fields include `protocol`, `content_type`, and opaque `payload`.
2. Discovery with protocol filtering:
   - `mq9_discover` supports `protocol` + `require_protocol`.
3. A2A wrappers (thin layer):
   - `a2a_register_self`
   - `a2a_discover`
   - `a2a_call`
4. Backward compatibility:
   - Existing `mq9_*` tools remain available.
5. OpenClaw near-zero migration path:
   - `openclaw-bundle/mq9-a2a-bundle/` contributes `.mcp.json` instead of reimplementing runtime logic.

## References

- https://robustmq.com/zh/Blogs/96
- https://robustmq.com/zh/Blogs/99
- https://robustmq.com/zh/Blogs/101
- https://robustmq.com/zh/Blogs/102
- https://robustmq.com/zh/Blogs/103
