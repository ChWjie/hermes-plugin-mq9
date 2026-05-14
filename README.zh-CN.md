# mq9-hermes-openclaw-plugin（中文说明）

[English README](README.md)

## 插件作用（先看这个）

这个插件的定位是：把 **Hermes / OpenClaw 上层的 Agent 协作语义**，稳定地落到 **RobustMQ 的 mq9 通信基础设施** 上。

- 上层保持 A2A 风格（发现、调用、回复）。
- 底层由 mq9 提供注册、发现、消息投递、收件箱回复等能力。
- 同一套插件实现可在 Hermes 先落地，再低成本迁移到 OpenClaw。

## 这是什么，不是什么

- 这是 Hermes/OpenClaw 侧的插件与适配层（Python）。
- 不是 mq9 内核本体。mq9 内核在 RobustMQ 官方仓库（Rust）里。

RobustMQ 官方仓库与文档：

- [robustmq/robustmq](https://github.com/robustmq/robustmq)
- mq9 博客文档：[96](https://robustmq.com/zh/Blogs/96)、[99](https://robustmq.com/zh/Blogs/99)、[101](https://robustmq.com/zh/Blogs/101)、[102](https://robustmq.com/zh/Blogs/102)、[103](https://robustmq.com/zh/Blogs/103)

## 核心能力

- mq9 原生工具：
  - `mq9_register_self`
  - `mq9_unregister_self`
  - `mq9_discover`
  - `mq9_call`
  - `mq9_status`
- A2A 语义桥接工具：
  - `a2a_register_self`
  - `a2a_discover`
  - `a2a_call`
- 会话钩子里自动启用被动收件服务（`on_session_start`/`on_session_finalize`）。

## 安装（Hermes）

1. 安装 Hermes：

```bash
pip install git+https://github.com/NousResearch/hermes-agent.git
```

2. 安装插件（二选一）：

方式 A（Hermes 插件命令）：

```bash
hermes plugins install ChWjie/mq9-hermes-openclaw-plugin --enable
```

方式 B（pip entrypoint）：

```bash
pip install git+https://github.com/ChWjie/mq9-hermes-openclaw-plugin.git
```

3. 配置 `~/.hermes/config.yaml`：

```yaml
plugins:
  enabled: [mq9]
  entries:
    mq9:
      nats_url: "nats://127.0.0.1:45222"
      agent_name: "hermes-a"
      mailbox: "hermes.a.inbox"
      mailbox_ttl: 86400
      auto_register: true
      passive_serve: true
      passive_execute_mode: minimal
      oneshot_timeout_s: 90
      oneshot_provider: deepseek
      oneshot_model: deepseek-chat
      default_discover_limit: 10
      default_call_timeout_s: 25
      default_protocol: a2a
      discovery_require_protocol: false
```

## 快速验证（本地）

1. 在 RobustMQ 仓库启动 broker：

```bash
cargo run --package cmd --bin broker-server -- --conf config/server-poc-isolated.toml
```

2. 启动被动服务端（Hermes-B）：

```bash
RUN_ID=$(date +%s)
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode server \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-b-standalone-$RUN_ID \
  --mailbox hermes.b.standalone.inbox.$RUN_ID \
  --duration 120
```

3. 在另一个终端发起调用（Hermes-A）：

```bash
python hermes_plugin_toolcall.py \
  --home ~/.hermes \
  --mode client \
  --nats-url nats://127.0.0.1:45222 \
  --agent-name hermes-a-standalone-$RUN_ID \
  --mailbox hermes.a.standalone.inbox.$RUN_ID \
  --query "hermes-b-standalone-$RUN_ID" \
  --prefer-name "hermes-b-standalone-$RUN_ID"
```

预期结果：

- discover 能找到目标 agent card。
- call 返回 `ok: true` 与 `mq9_call_reply`。

## OpenClaw 迁移

仓库已包含 OpenClaw 适配包：

- `openclaw-bundle/mq9-a2a-bundle/`

可直接安装并启用：

```bash
openclaw plugins install ./openclaw-bundle/mq9-a2a-bundle
openclaw plugins enable mq9-a2a-bundle
openclaw gateway restart
openclaw plugins inspect mq9-a2a-bundle --runtime --json
```

## 更多

- 端到端示例文档：`examples/hermes-openclaw-fullchain/README.md`
- 架构说明：`ARCHITECTURE_A2A_MQ9.md`
