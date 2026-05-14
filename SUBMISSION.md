# mq9 Hermes Plugin Submission Notes

Last updated: 2026-05-14

## Package

- Repository: `https://github.com/ChWjie/hermes-plugin-mq9`
- Release: `v0.2.1`
- Python package: `hermes-plugin-mq9`
- Entry point group: `hermes_agent.plugins`
- Entry point name: `mq9`

Repository now also supports Hermes ecosystem directory install (`hermes plugins install owner/repo`) by shipping root-level `plugin.yaml` + `__init__.py` shim.

## Why standalone

Hermes maintainers requested standalone plugin delivery (not new in-tree plugin under `plugins/`).

## Provided tools and hooks

Tools:

- `mq9_register_self`
- `mq9_unregister_self`
- `mq9_discover`
- `mq9_call`
- `mq9_status`

Hooks:

- `on_session_start`
- `on_session_reset`
- `on_session_finalize`

## Production hardening already included

1. Mailbox idempotent create
2. Runtime tracked registration set + best-effort unregister cleanup
3. Explicit `mq9_unregister_self` operational tool
4. Bounded retries for request path
5. Candidate-level diagnostic details for call attempts
6. Unit test coverage for critical client/runtime paths

## Validation evidence

Validated on 2026-05-14.

1. Unit tests (`tests/`)

- Command:
  - `python -m unittest discover -s tests -p 'test_*.py' -v`
- Result:
  - `7/7` passed

2. Conformance (Python p0)

- Command:
  - `python conformance/run_conformance.py --sdk python --suite p0 --nats-url nats://127.0.0.1:46222 --json-out /private/tmp/mq9_conformance_python_p0_20260514_round2.json`
- Result:
  - `3/3` passed

3. Standalone entrypoint load check (clean venv)

- Setup:
  - `pip install git+https://github.com/NousResearch/hermes-agent.git`
  - `pip install git+https://github.com/ChWjie/hermes-plugin-mq9.git`
- Runtime check:
  - `PluginManager().discover_and_load()` sees `mq9` with `source='entrypoint'`

4. Standalone e2e (toolcall/minimal)

- Topology:
  - RobustMQ broker on `nats://127.0.0.1:45222`
  - Hermes-B server with unique agent/mailbox name
  - Hermes-A client discover + call
- Result:
  - discover `ok: true`, `count: 1`
  - call `ok: true`
  - got `mq9_call_reply` from Hermes-B in `minimal` mode
  - unregister cleanup `ok: true`

5. Hermes ecosystem install path compatibility

- Command:
  - `hermes plugins install ChWjie/hermes-plugin-mq9 --enable`
- Expected:
  - cloned repo under `~/.hermes/plugins/`
  - plugin manifest name `mq9`
  - Hermes can load it as directory plugin

## Compatibility note

In the upstream snapshot validated on 2026-05-14 (Hermes commit `524490a`):

- `hermes plugins list/enable` scans directory plugins only
- pip entrypoint plugins are still loadable at runtime via `plugins.enabled`

Therefore installation docs enable `mq9` through `~/.hermes/config.yaml`.

## Known limitations

1. Go conformance runner is placeholder in `conformance/run_conformance.py`.
2. `oneshot` mode depends on external model endpoint and key.
3. For very broad discover queries, stale historical agents can appear; use unique agent names or `prefer_name` for deterministic routing.

## Submission checklist for ecosystem post

1. Keep standalone repo + release as source of truth.
2. Provide install commands (Hermes + plugin) and config snippet.
3. Provide one deterministic E2E command set with unique agent names.
4. Keep default passive mode as `minimal`; document `oneshot` as opt-in.
