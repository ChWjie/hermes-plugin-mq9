#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NATS_URL="${NATS_URL:-nats://127.0.0.1:46222}"
JSON_OUT="${JSON_OUT:-/private/tmp/mq9_conformance_python_p0_ci.json}"

if [[ ! -f "${ROOT_DIR}/.venv-hermes/bin/activate" ]]; then
  echo "[ci-gate] missing virtualenv at ${ROOT_DIR}/.venv-hermes" >&2
  exit 1
fi

source "${ROOT_DIR}/.venv-hermes/bin/activate"

echo "[ci-gate] running unit tests"
python -m unittest discover -s "${ROOT_DIR}/tests" -p 'test_*.py' -v

echo "[ci-gate] running conformance p0 (python)"
python "${ROOT_DIR}/conformance/run_conformance.py" \
  --sdk python \
  --suite p0 \
  --nats-url "${NATS_URL}" \
  --json-out "${JSON_OUT}"

echo "[ci-gate] done: ${JSON_OUT}"
