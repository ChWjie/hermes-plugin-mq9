# hermes-plugin-mq9

`mq9` transport plugin for Hermes. This standalone package adds cross-agent communication over RobustMQ mq9:

- `mq9_register_self`
- `mq9_unregister_self`
- `mq9_discover`
- `mq9_call`
- `mq9_status`

It also runs a passive inbox server in background hooks (`on_session_start`/`on_session_finalize`) so Hermes agents can receive and reply to mq9 calls.

## Why standalone

Per Hermes `CONTRIBUTING.md`, new plugin integrations should be published as standalone plugin repos/packages instead of submitting new in-tree plugins under `plugins/`.

This repository is that standalone package.

## Scope

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
hermes plugins install ChWjie/hermes-plugin-mq9 --enable
```

Method B (pip entrypoint plugin):

```bash
pip install git+https://github.com/ChWjie/hermes-plugin-mq9.git
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
