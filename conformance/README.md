# mq9 SDK Conformance (B2 Foundation)

This directory provides the first B2 conformance framework for Hermes plugin foundation.

Scope now:
- Contract + matrix are defined.
- Python runner is implemented and executable.
- Go is reserved in matrix (placeholder, not implemented yet).

## Files

```text
conformance/
├── contracts/
│   └── hermes_foundation_v1.json
├── matrix.json
├── run_ci_gate.sh
└── run_conformance.py
```

## Contract Cases

`hermes_foundation_v1.json` currently defines 3 must-pass cases for Hermes plugin base path:

1. `mailbox.create_send_fetch_ack`
2. `message.priority_header`
3. `agent.register_discover`

These map to plugin-critical operations:
- register/discover
- send/fetch/ack

## Run

Start a broker first (NATS on `4222`):

```bash
cargo run --package cmd --bin broker-server -- --conf config/server.toml
```

Then run conformance:

```bash
python example/hermes-plugin-mq9/conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --nats-url nats://127.0.0.1:4222
```

Save JSON report:

```bash
python example/hermes-plugin-mq9/conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --json-out /private/tmp/mq9_conformance_python_p0.json
```

Run selected cases:

```bash
python example/hermes-plugin-mq9/conformance/run_conformance.py \
  --sdk python \
  --suite p0 \
  --cases mailbox.create_send_fetch_ack,agent.register_discover
```

## Exit Codes

- `0`: all selected cases passed
- `1`: one or more cases failed
- `2`: sdk runner not implemented (for now: `go`)

## Local CI Gate

Run unit tests + conformance together:

```bash
example/hermes-plugin-mq9/conformance/run_ci_gate.sh
```

Env overrides:
- `NATS_URL` (default `nats://127.0.0.1:46222`)
- `JSON_OUT` (default `/private/tmp/mq9_conformance_python_p0_ci.json`)

## Next (B2 rollout)

1. Implement Go adapter with same case IDs.
2. Add matrix job for Python + Go in CI.
3. Expand contract with error-semantics parity checks.
