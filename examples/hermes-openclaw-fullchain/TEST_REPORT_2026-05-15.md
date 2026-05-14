# 全链路测试报告（2026-05-15）

测试目录：`examples/hermes-openclaw-fullchain/`

## 测试目标

1. 验证 Hermes 插件在 mq9 基础设施上可用。
2. 验证 A2A 语义包装（`a2a_*`）在真实 discover/call/reply 场景可跑通。
3. 验证 OpenClaw bundle 能安装、启用并挂载 mq9 MCP server。

## 执行命令

```bash
cd /Users/clittletree/Documents/Playground/hermes-plugin-mq9
ROBUSTMQ_REPO=/Users/clittletree/Documents/Playground/08_RobustMQ_work \
HERMES_PYTHON=/private/tmp/hermes-mq9-standalone-venv/bin/python \
HERMES_BIN=/private/tmp/hermes-mq9-standalone-venv/bin/hermes \
OPENCLAW_BIN=/Users/clittletree/.npm/_npx/87115a8ab6c363bd/node_modules/.bin/openclaw \
examples/hermes-openclaw-fullchain/scripts/verify.sh
```

## 结果

1. Hermes 单元测试：`14/14` 通过。
2. Hermes mq9 e2e：成功。
3. OpenClaw bundle 安装与启用：成功。
4. OpenClaw runtime inspect：成功，诊断为空。

关键证据：

- Hermes e2e 日志：`artifacts/hermes-e2e.log`
  - `"success": true`
  - `"tool-family a2a"` 路径下 discover/call 完成
  - 目标邮箱：`hermes.b.e2e.inbox.1778790644`
- OpenClaw inspect：`artifacts/openclaw-inspect.json`
  - `"enabled": true`
  - `"status": "loaded"`
  - `"mcpServers": [{"name": "mq9", "hasStdioTransport": true}]`
  - `"diagnostics": []`

## 结论

1. 插件可用：Hermes 侧 discover/call/reply 全链路已跑通。
2. mq9 发挥作用：A2A 语义通过 mq9 mailbox 与 discover 基础设施完成跨 agent 通信。
3. OpenClaw 可迁移：bundle 形态可直接安装并挂载 mq9 MCP server，无需重写 mq9 传输层。

## 当前边界

1. 本次 OpenClaw 验证聚焦插件安装与 runtime 挂载，不包含带模型推理的完整对话回合。
2. 若要继续做 OpenClaw 真实业务回合，需要额外配置可用模型与 channel/session 路径。

