# Hermes + OpenClaw + mq9 全链路实操

这个目录是给最终用户的“照着做就能跑”的联调手册。

目标：

1. 用 RobustMQ 提供 mq9 底层基础设施（Rust 内核）。
2. 在 Hermes 里通过 `hermes-plugin-mq9` 实现 A2A 语义的发现和调用。
3. 在 OpenClaw 里通过 bundle + MCP 接入同一套 mq9 能力。

## 先理解边界

- RobustMQ 仓库（Rust）负责 broker、mq9 协议、持久化、优先级、TTL、MCP `/mcp` 入口。
- 本仓库（Python）是 Hermes 插件适配层，提供 `a2a_*`/`mq9_*` 工具和被动收件服务。
- OpenClaw 侧不重写 mq9 协议，只通过 `.mcp.json` 连同一个 RobustMQ MCP 端点。

参考：

- RobustMQ 主仓库: https://github.com/robustmq/robustmq
- 博客 96: https://robustmq.com/zh/Blogs/96
- 博客 99: https://robustmq.com/zh/Blogs/99
- 博客 101: https://robustmq.com/zh/Blogs/101
- 博客 102: https://robustmq.com/zh/Blogs/102
- 博客 103: https://robustmq.com/zh/Blogs/103

## 目录内容

- `hermes/config-a.yaml`: Hermes-A 模板配置。
- `hermes/config-b.yaml`: Hermes-B 模板配置。
- `openclaw/.mcp.json`: OpenClaw MCP 连接模板（默认 `http://127.0.0.1:39080/mcp`）。
- `scripts/verify.sh`: 一键验证脚本（Hermes 单测 + Hermes e2e + OpenClaw 插件 inspect）。
- `TEST_REPORT_2026-05-15.md`: 本目录的实际执行结果记录。

## 前置条件

1. Python 3.10+。
2. Cargo（用于启动 RobustMQ broker）。
3. Hermes 可执行文件。
4. OpenClaw 可执行文件（可选，用于第三段验证）。

## 用户实操命令

### 1) 准备仓库

```bash
git clone https://github.com/robustmq/robustmq.git 08_RobustMQ_work
git clone https://github.com/ChWjie/hermes-plugin-mq9.git hermes-plugin-mq9
```

### 2) 启动 RobustMQ（mq9 + MCP）

`server-poc-isolated.toml` 默认端口：

- NATS: `45222`
- HTTP/MCP: `39080`（MCP path 是 `/mcp`）

```bash
cd 08_RobustMQ_work
cargo run --package cmd --bin broker-server -- --conf config/server-poc-isolated.toml
```

### 3) 安装 Hermes 插件

> 在 Hermes 所在的 Python 环境里执行下面命令。

```bash
cd hermes-plugin-mq9
python -m pip install -e .
python - <<'PY'
import importlib.metadata as md
print([e.name for e in md.entry_points().select(group='hermes_agent.plugins')])
PY
```

### 4) 跑 Hermes A2A over mq9

另开终端 A（Hermes-B，作为被调方）：

```bash
cd hermes-plugin-mq9
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode server \
  --tool-family a2a \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-b-demo-001 \
  --mailbox hermes.b.inbox.demo-001 \
  --duration 120
```

终端 B（Hermes-A，作为调用方）：

```bash
cd hermes-plugin-mq9
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode client \
  --tool-family a2a \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-a-demo-001 \
  --mailbox hermes.a.inbox.demo-001 \
  --query "hermes-b-demo-001" \
  --prefer-name "hermes-b-demo-001"
```

期望输出：

- discover 返回目标 agent。
- call 返回 `ok: true`。
- 回包包含 `mq9_call_reply`。

### 5) 接入 OpenClaw bundle

```bash
cd hermes-plugin-mq9
openclaw plugins install ./openclaw-bundle/mq9-a2a-bundle
openclaw plugins enable mq9-a2a-bundle
openclaw gateway restart
openclaw plugins inspect mq9-a2a-bundle --runtime --json
```

如果你使用的是本目录模板，把 `openclaw/.mcp.json` 的 URL 和 broker 端口保持一致。

### 6) 一键验证

```bash
cd hermes-plugin-mq9
examples/hermes-openclaw-fullchain/scripts/verify.sh
```

可选环境变量：

- `ROBUSTMQ_REPO`: RobustMQ 仓库目录。
- `HERMES_BIN`: hermes 可执行文件。
- `HERMES_PYTHON`: python 可执行文件（需装好 hermes）。
- `OPENCLAW_BIN`: openclaw 可执行文件。
- `NATS_URL`: mq9 NATS 地址。
- `BROKER_CONF`: broker 配置文件路径。

## 如何判断 mq9 真的发挥了作用

1. Hermes-B 先启动再等待，Hermes-A 后发起调用，仍可收发成功。
2. 调用路径中出现 discover + mailbox call + callback reply，不是本地直接函数调用。
3. OpenClaw inspect 能看到 bundle 的 MCP server 已挂载，表示能调用同一条 mq9 基础设施。
