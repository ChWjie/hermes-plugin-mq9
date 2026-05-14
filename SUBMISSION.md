# mq9 Hermes Plugin Submission Notes

Last updated: 2026-05-14

## Deliverable

- Plugin path: `example/hermes-plugin-mq9/mq9`
- Plugin name/version: `mq9` / `0.2.0`
- Type: Hermes standalone plugin
- Tools:
  - `mq9_register_self`
  - `mq9_unregister_self`
  - `mq9_discover`
  - `mq9_call`
  - `mq9_status`
- Hooks:
  - `on_session_start`
  - `on_session_reset`
  - `on_session_finalize`

## Production-readiness changes

1. Stable mailbox semantics
   - Mailbox create uses `idempotent=true` by default.
   - Runtime avoids timestamp-suffixed fallback mailbox churn.
2. Lifecycle cleanup
   - Added runtime tracked registration set.
   - Best-effort unregister on `on_session_finalize`.
   - Best-effort unregister on process exit (`atexit`) to reduce stale discover records.
3. Operational control
   - Added `mq9_unregister_self` tool for manual cleanup.
4. Reliability
   - Python mq9 client has bounded retry for transient request failures.
   - Runtime call attempt diagnostics now include timeout and mq9 protocol errors.
5. Testability
   - Added unit tests for client/runtime behavior.

## Validation evidence

Validated on 2026-05-14 with local RobustMQ broker and Hermes plugin harness.

1. Unit tests:
   - Command:
     - `python -m unittest discover -s example/hermes-plugin-mq9/tests -p 'test_*.py' -v`
   - Result:
     - `7` tests passed.
2. Conformance (B2, Python p0):
   - Command:
     - `python example/hermes-plugin-mq9/conformance/run_conformance.py --sdk python --suite p0 --nats-url nats://127.0.0.1:46222 --json-out /private/tmp/mq9_conformance_python_p0_20260514.json`
   - Result:
     - `3/3` passed.
3. Phase-4 style E2E (Hermes-A/B, toolcall):
   - Command:
     - `python example/hermes-plugin-mq9/run_phase4_e2e.py --mode toolcall --nats-url nats://127.0.0.1:46222 --broker-conf /private/tmp/server-mq9-hermes-plugin.toml --keep-artifacts`
   - Result:
     - success = `true`
     - discover + call completed over mq9
     - passive server replied in `minimal` mode
4. Phase-4 style E2E (Hermes-A/B, llm):
   - Command:
     - `python example/hermes-plugin-mq9/run_phase4_e2e.py --mode llm --nats-url nats://127.0.0.1:46222 --broker-conf /private/tmp/server-mq9-hermes-plugin.toml --provider deepseek --model deepseek-chat`
   - Result:
     - success = `true`
     - Hermes-A used natural-language prompt to trigger `mq9_discover` and `mq9_call`
     - Hermes-B executed in `oneshot` mode and returned runnable HTTP server answer

## Compatibility

- RobustMQ server: local workspace build from `08_RobustMQ_work`
- Hermes agent runtime: local checkout under `/private/tmp/hermes-agent`
- Python runtime: plugin `.venv-hermes` (Python 3.12)

## Safety model

- `minimal` mode (default for toolcall E2E) does not run delegated task code; it only returns structured placeholder response.
- `oneshot` mode is opt-in and requires explicit provider/model + API key.
- `oneshot` subprocess is launched with:
  - `--ignore-user-config`
  - `--ignore-rules`
  - plugin self-registration disabled in subprocess env

## Known limitations

1. Go conformance runner in `conformance/run_conformance.py` is still placeholder.
2. `oneshot` mode depends on external model availability and credentials.
3. This package currently targets Hermes plugin drop-in path (`~/.hermes/plugins/mq9`) rather than pip-distributed plugin packaging.

## Submit checklist (Hermes ecosystem)

1. Copy `mq9/` plugin directory into target Hermes plugin repository path.
2. Include `README.md`, `conformance/`, and this `SUBMISSION.md`.
3. In PR description include:
   - install steps
   - config sample
   - validation commands + pass outputs
   - known limitations above
4. Keep `minimal` mode as default for first ecosystem release; mark `oneshot` as experimental.
