# [Plugin] mq9 transport plugin for Hermes

## Summary

This PR introduces a production-usable Hermes plugin `mq9` for cross-agent discovery and RPC-style task calls over RobustMQ mq9.

Implemented tools:

- `mq9_register_self`
- `mq9_unregister_self`
- `mq9_discover`
- `mq9_call`
- `mq9_status`

Implemented hooks:

- `on_session_start`
- `on_session_reset`
- `on_session_finalize`

## Key Improvements in This Version

1. Lifecycle-safe registration cleanup

- Runtime now tracks registered agent names.
- Best-effort unregister on `on_session_finalize`.
- Best-effort unregister on process exit (`atexit`) to reduce stale discover records.
- Added explicit manual cleanup tool: `mq9_unregister_self`.

2. Stable mailbox semantics

- Mailbox creation uses `idempotent=true` by default.
- Avoids mailbox name churn across restart/re-registration.

3. Reliability hardening

- Bounded retries for transient request failures in Python SDK.
- Improved call attempt diagnostics (timeout and protocol-level errors).
- Toolcall E2E defaults to `minimal` passive mode (no model key required).

4. Quality gates and evidence

- Unit tests for client/runtime.
- Contract-driven conformance suite (B2 foundation).
- Hermes-A/Hermes-B end-to-end flow validation.

## Validation

Executed on 2026-05-14:

1. Unit tests

```bash
python -m unittest discover -s example/hermes-plugin-mq9/tests -p 'test_*.py' -v
```

Result: `7 passed`

2. Conformance (Python p0)

```bash
python example/hermes-plugin-mq9/conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --nats-url nats://127.0.0.1:46222 \
  --json-out /private/tmp/mq9_conformance_python_p0_20260514.json
```

Result: `3/3 passed`

3. E2E toolcall mode

```bash
python example/hermes-plugin-mq9/run_phase4_e2e.py \
  --mode toolcall \
  --nats-url nats://127.0.0.1:46222 \
  --broker-conf /private/tmp/server-mq9-hermes-plugin.toml
```

Result: success = `true`

4. E2E llm mode

```bash
python example/hermes-plugin-mq9/run_phase4_e2e.py \
  --mode llm \
  --nats-url nats://127.0.0.1:46222 \
  --broker-conf /private/tmp/server-mq9-hermes-plugin.toml \
  --provider deepseek \
  --model deepseek-chat
```

Result: success = `true`

## Installation

```bash
mkdir -p ~/.hermes/plugins
cp -R example/hermes-plugin-mq9/mq9 ~/.hermes/plugins/mq9
hermes plugins enable mq9
```

## Notes

- `minimal` mode is safe default and model-key free.
- `oneshot` mode is supported but requires provider/model/API key.
- Go conformance runner is reserved in matrix but not implemented in this PR.
