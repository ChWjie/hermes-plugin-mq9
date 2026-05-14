#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAB="$ROOT/examples/hermes-openclaw-fullchain"
ROBUSTMQ_REPO="${ROBUSTMQ_REPO:-$ROOT/../08_RobustMQ_work}"
HERMES_BIN="${HERMES_BIN:-/private/tmp/hermes-mq9-standalone-venv/bin/hermes}"
HERMES_PYTHON="${HERMES_PYTHON:-/private/tmp/hermes-mq9-standalone-venv/bin/python}"
OPENCLAW_BIN="${OPENCLAW_BIN:-$(command -v openclaw || true)}"
OPENCLAW_FALLBACK="/Users/clittletree/.npm/_npx/87115a8ab6c363bd/node_modules/.bin/openclaw"
if [ -z "$OPENCLAW_BIN" ] && [ -x "$OPENCLAW_FALLBACK" ]; then
  OPENCLAW_BIN="$OPENCLAW_FALLBACK"
fi
OPENCLAW_PROFILE="${OPENCLAW_PROFILE:-mq9-lab}"
NATS_URL="${NATS_URL:-nats://127.0.0.1:45222}"
BROKER_CONF="${BROKER_CONF:-$ROBUSTMQ_REPO/config/server-poc-isolated.toml}"
ARTIFACTS="$LAB/artifacts"
mkdir -p "$ARTIFACTS"

echo "[1/4] Hermes unit tests"
"$HERMES_PYTHON" -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v

echo "[2/4] Hermes mq9 e2e"
"$HERMES_PYTHON" "$ROOT/run_phase4_e2e.py" \
  --mode toolcall \
  --tool-family a2a \
  --plugin-source directory \
  --home-root "$ARTIFACTS/hermes-e2e" \
  --workdir "$ROBUSTMQ_REPO" \
  --nats-url "$NATS_URL" \
  --broker-conf "$BROKER_CONF" \
  --hermes-python "$HERMES_PYTHON" \
  --hermes-bin "$HERMES_BIN" | tee "$ARTIFACTS/hermes-e2e.log"

if [ -n "$OPENCLAW_BIN" ] && [ -x "$OPENCLAW_BIN" ]; then
  echo "[3/4] OpenClaw plugin install"
  HOME="$ARTIFACTS/openclaw-home" "$OPENCLAW_BIN" --profile "$OPENCLAW_PROFILE" plugins install "$ROOT/openclaw-bundle/mq9-a2a-bundle" | tee "$ARTIFACTS/openclaw-install.log"
  HOME="$ARTIFACTS/openclaw-home" "$OPENCLAW_BIN" --profile "$OPENCLAW_PROFILE" plugins enable mq9-a2a-bundle | tee "$ARTIFACTS/openclaw-enable.log"

  echo "[4/4] OpenClaw plugin inspect"
  HOME="$ARTIFACTS/openclaw-home" "$OPENCLAW_BIN" --profile "$OPENCLAW_PROFILE" plugins inspect mq9-a2a-bundle --runtime --json | tee "$ARTIFACTS/openclaw-inspect.json"
else
  echo "[3/4] Skipped OpenClaw: openclaw binary not found"
fi
