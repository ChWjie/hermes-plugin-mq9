# mq9 Hermes Plugin Ecosystem Note

## Status

This integration is published as a standalone plugin repository:

- Repo: `https://github.com/ChWjie/hermes-plugin-mq9`
- Release: `v0.2.2`

In-tree PR path under `NousResearch/hermes-agent/plugins/` is intentionally not used, following Hermes maintainer guidance in `CONTRIBUTING.md`.

## What users get

- `mq9_register_self`
- `mq9_unregister_self`
- `mq9_discover`
- `mq9_call`
- `mq9_status`
- Passive inbox serve loop with lifecycle hooks

## Install path for ecosystem users

```bash
pip install git+https://github.com/NousResearch/hermes-agent.git
hermes plugins install ChWjie/hermes-plugin-mq9 --enable
```

Then configure mq9 entries in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - mq9
```

## Validation snapshot (2026-05-14)

- Unit: `7/7` pass
- Conformance (python p0): `3/3` pass
- Standalone entrypoint load: pass (`source='entrypoint'`)
- Standalone toolcall e2e: pass (discover + call + reply + unregister)

## Compatibility note

Validated upstream Hermes snapshot (commit `524490a`) has CLI list/enable focused on directory plugins. Pip entrypoint plugin remains fully loadable when `mq9` is included in `plugins.enabled`.
