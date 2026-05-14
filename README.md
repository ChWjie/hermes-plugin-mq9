# mq9 Hermes Plugin (Phase 3 Minimal)

This folder contains a minimal Hermes plugin that bridges Hermes to mq9.

Current scope:
- `mq9_register_self`: register current Hermes agent card into mq9 registry
- `mq9_unregister_self`: unregister current Hermes agent from mq9 registry
- `mq9_discover`: discover remote agents by query
- `mq9_call`: send a call envelope and wait for callback reply
- `mq9_status`: inspect runtime/mailbox/registration status
- Passive inbox serve loop:
  - `passive_execute_mode=minimal` (default): structured placeholder reply
  - `passive_execute_mode=oneshot`: execute inbound task with `hermes -z` and reply with real answer

## Directory

```text
example/hermes-plugin-mq9/
├── hermes_plugin_toolcall.py
├── demo_runtime_server.py
├── demo_runtime_caller.py
├── run_phase4_e2e.py
└── mq9/
    ├── __init__.py
    ├── mq9_client.py
    ├── plugin.yaml
    ├── runtime.py
    ├── schemas.py
    └── tools.py
```

## Install into Hermes

```bash
mkdir -p ~/.hermes/plugins
cp -R example/hermes-plugin-mq9/mq9 ~/.hermes/plugins/mq9
```

Enable plugin:

```bash
hermes plugins enable mq9
```

Or edit `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - mq9
```

## Configure mq9 runtime

Recommended (new style):

```yaml
plugins:
  entries:
    mq9:
      nats_url: "nats://127.0.0.1:45222"
      agent_name: "hermes-b"
      mailbox: "hermes.b.inbox"
      mailbox_ttl: 86400
      auto_register: true
      passive_serve: true
      passive_execute_mode: minimal   # or oneshot
      oneshot_timeout_s: 90
      oneshot_provider: deepseek
      oneshot_model: deepseek-chat
      default_discover_limit: 10
      default_call_timeout_s: 25
```

Compatibility fallback (also supported):

```yaml
mq9:
  nats_url: "nats://127.0.0.1:45222"
  agent_name: "hermes-b"
  mailbox: "hermes.b.inbox"
```

Env override (highest priority):
- `HERMES_MQ9_NATS_URL`
- `HERMES_MQ9_AGENT_NAME`
- `HERMES_MQ9_MAILBOX`
- `HERMES_MQ9_AUTO_REGISTER`
- `HERMES_MQ9_PASSIVE_SERVE`
- `HERMES_MQ9_PASSIVE_EXECUTE_MODE` (`minimal` / `oneshot`)
- `HERMES_MQ9_ONESHOT_PROVIDER`
- `HERMES_MQ9_ONESHOT_MODEL`
- `HERMES_MQ9_ONESHOT_TIMEOUT`

## Validate quickly

1. Start RobustMQ broker (isolated port suggested):

```bash
cargo run --package cmd --bin broker-server -- --conf config/server-poc-isolated.toml
```

2. Start Hermes with plugin enabled and run:

- `mq9_register_self`
- `mq9_status`
- `mq9_discover` with a known query
- `mq9_call` to a mailbox
- `mq9_unregister_self` to clean registry record

## One-Command Phase-4 E2E

Use `run_phase4_e2e.py` to validate Hermes-A/Hermes-B end-to-end flow.

- `toolcall` mode: no LLM key required, validates mq9 discover/call plumbing.
- `llm` mode: Hermes-A uses natural-language prompt and actually calls `mq9_discover` + `mq9_call`.
- Server execute mode defaults:
  - `toolcall` -> `minimal`
  - `llm` -> `oneshot`

Toolcall mode:

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python example/hermes-plugin-mq9/run_phase4_e2e.py --mode toolcall
```

LLM mode:

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python example/hermes-plugin-mq9/run_phase4_e2e.py \
  --mode llm \
  --api-key "$DEEPSEEK_API_KEY"
```

Optional flags:
- `--provider deepseek --model deepseek-chat`
- `--server-execute-mode auto|minimal|oneshot`
- `--keep-artifacts` keeps temporary logs under `/private/tmp/mq9-hermes-e2e.*`

## Quality Gates

Run unit tests:

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python -m unittest discover -s example/hermes-plugin-mq9/tests -p 'test_*.py' -v
```

Run conformance p0:

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python example/hermes-plugin-mq9/conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --nats-url nats://127.0.0.1:46222 \
  --json-out /private/tmp/mq9_conformance_python_p0_20260514.json
```

## Hermes Download + E2E Test

If `hermes` is not installed, use a local virtualenv:

```bash
python3.12 -m venv example/hermes-plugin-mq9/.venv-hermes
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
pip install -e /private/tmp/hermes-agent
```

Install plugin into Hermes home:

```bash
mkdir -p ~/.hermes/plugins
cp -R example/hermes-plugin-mq9/mq9 ~/.hermes/plugins/mq9
hermes plugins enable mq9
```

Run broker:

```bash
cargo run --package cmd --bin broker-server -- --conf config/server-poc-isolated.toml
```

In another terminal, run Hermes-B (server side):

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python example/hermes-plugin-mq9/hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode server \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-b \
  --mailbox hermes.b.inbox.$(date +%s) \
  --duration 120
```

Run Hermes-A (caller side):

```bash
source example/hermes-plugin-mq9/.venv-hermes/bin/activate
python example/hermes-plugin-mq9/hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode client \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-a \
  --mailbox hermes.a.inbox.$(date +%s) \
  --query "hermes-b" \
  --prefer-name hermes-b
```

Expected caller result:
- `mq9_discover` returns the `hermes-b` card
- `mq9_call` returns `ok: true` with `mq9_call_reply`

## Notes

- `minimal` mode is safest for offline or model-less environments.
- `oneshot` mode requires a valid inference key (for example `DEEPSEEK_API_KEY`) and a reachable model endpoint.
- Runtime now uses idempotent mailbox creation to keep mailbox names stable across restarts.
- Runtime performs best-effort unregister on `on_session_finalize` and process exit to reduce stale discover records.
