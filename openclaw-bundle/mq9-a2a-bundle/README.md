# mq9-a2a-bundle (OpenClaw)

OpenClaw-compatible bundle that provides:

- `.mcp.json` mapping to RobustMQ broker MCP endpoint (`/mcp`)
- one guidance skill for A2A-over-mq9 operation

Default test endpoint in this repo matches `config/server-poc-isolated.toml`:

- `http://127.0.0.1:39080/mcp`

If you use a different RobustMQ config, change the port to match that broker's `http_port`.

Install:

```bash
openclaw plugins install ./openclaw-bundle/mq9-a2a-bundle
openclaw plugins enable mq9-a2a-bundle
openclaw gateway restart
```

Inspect:

```bash
openclaw plugins inspect mq9-a2a-bundle --runtime --json
```
