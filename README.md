# mq9-hermes-openclaw-plugin

[中文说明（README.zh-CN）](README.zh-CN.md)

## What This Plugin Does

This plugin is a transport and discovery bridge for multi-agent systems:

- It keeps **A2A-style agent interaction semantics** (`discover`, `call`) at the tool layer.
- It uses **RobustMQ mq9 as the transport substrate** under the hood.
- It exposes one plugin package that can be used by **Hermes now** and migrated to **OpenClaw with near-zero cost**.

`mq9` transport plugin for Hermes. This standalone package adds cross-agent communication over RobustMQ mq9 with a protocol-agnostic core:

- `mq9_register_self`
- `mq9_unregister_self`
- `mq9_discover`
- `mq9_call`
- `mq9_status`
- `a2a_register_self`
- `a2a_discover`
- `a2a_call`

It also runs a passive inbox server in background hooks (`on_session_start`/`on_session_finalize`) so Hermes agents can receive and reply to mq9 calls.

## RobustMQ source of truth

mq9 core does not live here. The Rust implementation stays in the official RobustMQ repository:

- [robustmq/robustmq](https://github.com/robustmq/robustmq)
- mq9 docs: [96](https://robustmq.com/zh/Blogs/96), [99](https://robustmq.com/zh/Blogs/99), [101](https://robustmq.com/zh/Blogs/101), [102](https://robustmq.com/zh/Blogs/102), [103](https://robustmq.com/zh/Blogs/103)

RobustMQ is the broker/runtime layer. This repository is the Hermes-facing adapter on top of it.

## Why standalone

Per Hermes `CONTRIBUTING.md`, new plugin integrations should be published as standalone plugin repos/packages instead of submitting new in-tree plugins under `plugins/`.

This repository is that standalone package.

## Scope

- Generic transport/discovery substrate: mq9 carries opaque protocol payloads.
- A2A-first adapter tools: `a2a_discover`/`a2a_call` wrappers on mq9 substrate.
- Phase 1 (client): register/discover/call
- Phase 2 minimal (passive serve): receive + reply (`minimal` mode default)
- Optional `oneshot` mode: execute delegated task with `hermes -z` before replying

## Install

1. Install Hermes (official repo):

```bash
pip install git+https://github.com/NousResearch/hermes-agent.git
```

2. Choose one plugin install method:

Method A (Hermes ecosystem command, directory plugin):

```bash
hermes plugins install ChWjie/mq9-hermes-openclaw-plugin --enable
```

Method B (pip entrypoint plugin):

```bash
pip install git+https://github.com/ChWjie/mq9-hermes-openclaw-plugin.git
```

3. Configure mq9 runtime in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled: [mq9]
  entries:
    mq9:
      nats_url: "nats://127.0.0.1:45222"
      agent_name: "hermes-a"
      mailbox: "hermes.a.inbox"
      mailbox_ttl: 86400
      auto_register: true
      passive_serve: true
      passive_execute_mode: minimal   # minimal | oneshot
      oneshot_timeout_s: 90
      oneshot_provider: deepseek
      oneshot_model: deepseek-chat
      default_discover_limit: 10
      default_call_timeout_s: 25
      default_protocol: a2a
      discovery_require_protocol: false
```

Env vars (higher priority):

- `HERMES_MQ9_NATS_URL`
- `HERMES_MQ9_AGENT_NAME`
- `HERMES_MQ9_MAILBOX`
- `HERMES_MQ9_AUTO_REGISTER`
- `HERMES_MQ9_PASSIVE_SERVE`
- `HERMES_MQ9_PASSIVE_EXECUTE_MODE`
- `HERMES_MQ9_ONESHOT_PROVIDER`
- `HERMES_MQ9_ONESHOT_MODEL`
- `HERMES_MQ9_ONESHOT_TIMEOUT`
- `HERMES_MQ9_DEFAULT_PROTOCOL`
- `HERMES_MQ9_DISCOVERY_REQUIRE_PROTOCOL`

Note:
- On the upstream snapshot validated on **2026-05-14** (Hermes commit `524490a`), `hermes plugins list/enable` focuses on directory plugins.
- If you use Method B (pip), keep `mq9` in `plugins.enabled` as shown above.

## Quick check (entrypoint installed)

```bash
python - <<'PY'
import importlib.metadata as md
entries = md.entry_points().select(group='hermes_agent.plugins')
print([e.name for e in entries])
PY
```

Expected output includes `mq9`.

## A2A usage in Hermes

Use the A2A wrappers when you want Hermes prompts and tool plans to stay aligned with A2A semantics while mq9 handles transport/discovery.

- `a2a_register_self`: register this Hermes instance as A2A-capable.
- `a2a_discover`: discover A2A-capable agents.
- `a2a_call`: send A2A payload over mq9 and wait for reply.

Example tool args:

```json
{
  "query": "Python HTTP server agent",
  "prefer_name": "hermes-b",
  "limit": 5
}
```

```json
{
  "query": "Python HTTP server agent",
  "prefer_name": "hermes-b",
  "message": {
    "task_id": "a2a-task-001",
    "instruction": "Write a minimal Python HTTP server with /health",
    "expect": "runnable code + run command"
  },
  "timeout_s": 45
}
```

## OpenClaw near-zero migration

This repo includes an OpenClaw-compatible bundle at:

- `openclaw-bundle/mq9-a2a-bundle/`

The bundle contributes `.mcp.json` so OpenClaw can consume RobustMQ broker MCP tools directly (`mq9_create_mailbox`, `mq9_send_message`, `mq9_discover_agents`, etc.) without rewriting mq9 transport logic in TypeScript.

Match the endpoint to your RobustMQ broker config:

- `config/server.toml` -> `http://127.0.0.1:8080/mcp`
- `config/server-poc-isolated.toml` -> `http://127.0.0.1:39080/mcp`

Install locally:

```bash
openclaw plugins install ./openclaw-bundle/mq9-a2a-bundle
openclaw plugins enable mq9-a2a-bundle
openclaw gateway restart
openclaw plugins inspect mq9-a2a-bundle --runtime --json
```

Set broker MCP endpoint in bundle config:

```json
{
  "mcpServers": {
    "mq9": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:39080/mcp"]
    }
  }
}
```

## Local E2E (standalone entrypoint mode)

1. Start RobustMQ broker (from your RobustMQ repo):

```bash
cargo run --package cmd --bin broker-server -- --conf config/server-poc-isolated.toml
```

2. Pick one run id and run `Hermes-B` passive server:

```bash
RUN_ID=$(date +%s)
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode server \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-b-standalone-$RUN_ID \
  --mailbox hermes.b.standalone.inbox.$RUN_ID \
  --duration 120
```

3. In another terminal, use the same `RUN_ID` for `Hermes-A` caller:

```bash
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode client \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-a-standalone-$RUN_ID \
  --mailbox hermes.a.standalone.inbox.$RUN_ID \
  --query "hermes-b-standalone-$RUN_ID" \
  --prefer-name "hermes-b-standalone-$RUN_ID"
```

Expected:

- discover returns target agent card
- call returns `ok: true` and `mq9_call_reply`

## Automated Phase-4 E2E

`run_phase4_e2e.py` now supports two plugin source modes:

- `--plugin-source directory`: copy local `mq9/` into isolated home (legacy dev mode)
- `--plugin-source entrypoint`: verify installed pip entrypoint plugin (standalone publish mode)

Toolcall (no model key):

```bash
python run_phase4_e2e.py \
  --mode toolcall \
  --plugin-source entrypoint \
  --nats-url nats://127.0.0.1:45222
```

LLM mode (requires key):

```bash
python run_phase4_e2e.py \
  --mode llm \
  --plugin-source entrypoint \
  --provider deepseek \
  --model deepseek-chat \
  --api-key "$DEEPSEEK_API_KEY" \
  --nats-url nats://127.0.0.1:45222
```

## Tests

Unit tests:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Conformance (Python p0):

```bash
python conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --nats-url nats://127.0.0.1:46222 \
  --json-out /private/tmp/mq9_conformance_python_p0_latest.json
```

## Rust core location

This repository is only Hermes plugin adapter code (Python).

RobustMQ mq9 core stays in RobustMQ repo (Rust), mainly under:

- `src/mq9-core/`
- `src/nats-broker/src/mq9/`

## User flow

For a Chinese, end-to-end setup guide with Hermes + OpenClaw configs and test commands, see:

- [examples/hermes-openclaw-fullchain/README.md](examples/hermes-openclaw-fullchain/README.md)
