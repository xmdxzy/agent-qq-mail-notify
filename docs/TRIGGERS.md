# 触发词与执行逻辑（Trigger Words & Execution Logic）

本文件定义 **Agent 任务完成 QQ 邮箱通知** 的触发词与执行逻辑，供 Codex / WorkBuddy 等智能体在实现通知能力时遵循。配套脚本见 `scripts/`。

---

## 一、触发词（Trigger Words）

触发词是用户在对智能体说话时使用的自然语言短语。智能体应在**解析用户输入**阶段匹配这些模式，并设置对应的 `notify_intent`。

### 1. 单次任务通知（opt-in，仅本次）

用户希望**当前这个任务**完成后收到 QQ 邮件提醒。

| 语言 | 示例触发词 |
|------|------------|
| 中文 | `完成后通知我` · `做完发QQ邮件提醒我` · `任务完成后发邮件到我的QQ邮箱` · `做完给我发个邮件` · `完成后用QQ邮箱告诉我` |
| 英文 | `notify me when done` · `send me a QQ email when finished` · `email me when the task completes` |

**匹配建议**：含「完成/做完 + 通知/邮件/QQ邮箱」或「notify/email me when (done/finished/complete)」即命中。

### 2. 持久通知（persistent，所有任务）

用户希望**今后所有任务**完成都发 QQ 邮件。

| 语言 | 示例触发词 |
|------|------------|
| 中文 | `以后任务完成都发QQ邮件通知我` · `开启任务完成邮件通知` · `打开邮件提醒` |
| 英文 | `always notify me by QQ email` · `enable email notifications` · `turn on task completion emails` |

**执行效果**：在智能体记忆/配置中写入 `notify.persistent = true`（见第四节边界）。

### 3. 配置查询 / 自检

| 语言 | 示例触发词 |
|------|------------|
| 中文 | `通知配置好了吗` · `检查通知配置` · `测试一下邮件通知` |
| 英文 | `is notification configured` · `check notify config` · `test email notify` |

**执行效果**：以 `--dry-run`（或 `-DryRun`）调用脚本，把返回的 JSON（From/To/Subject/Source/HasPassword）回显给用户，不发信。

### 4. 关闭通知

| 语言 | 示例触发词 |
|------|------------|
| 中文 | `不用通知了` · `关闭邮件通知` · `取消QQ邮箱提醒` |
| 英文 | `stop notifying me` · `disable email notifications` · `turn off task emails` |

**执行效果**：清除 `notify.persistent`，本轮及之后不再自动发信。

---

## 二、执行逻辑（Execution Logic）

```
用户输入
  │
  ▼
[1] 解析触发词 → 设置 notify_intent（none / once / persistent / check / off）
  │
  ▼
[2] 若是 persistent → 写入记忆/配置；若是 off → 清除；若是 check → 跳到 [5] DryRun
  │
  ▼
[3] 执行任务（正常完成 / 失败 / 部分完成都算"结束"）
  │
  ▼
[4] 判定是否发信：
       notify_intent == once         → 发
       notify.persistent == true      → 发
       其它                            → 不发
  │
  ▼
[5] 发信流程：
       a. 解析配置：环境变量 XUCE_NOTIFY_*  >  CODEX_NOTIFY_*  >  *.local.json
       b. 构造载荷：Source=智能体名，Summary=任务短标题，Message=结果摘要+时间戳
       c. 未知配置时先 --dry-run 探测；配置就绪则正式发送
       d. 校验返回：成功 → 在最终回复中附一句"已发 QQ 邮件通知"；失败 → 仅提示，不阻塞结果
```

### 关键规则

1. **永不阻塞任务结果**：通知是「旁路副作用」。无论通知成功或失败，都必须先把任务结果返回给用户。
2. **配置缺失不报错**：若未配置 SMTP，智能体应提示用户如何配置（复制 `config/task-done-notify.example.json` 或设置 `XUCE_NOTIFY_SMTP_*`），而不是抛错中断。
3. **主题前缀区分来源**：自动主题格式 `[Source] 任务完成：Summary`，`Source` 取 `Codex` / `WorkBuddy`，便于多智能体共存时区分。
4. **正文不含敏感信息**：`Message` 只放任务摘要、来源、完成时间、产物路径，**不得包含 SMTP 密码、token、密钥**。
5. **摘要做安全清洗**：`Summary` / `Source` 去除换行符，主题长度截断到 150 字符，防止 SMTP 注入。

---

## 三、调用方式（智能体侧示例）

PowerShell 环境（Windows）：

```powershell
powershell -NoProfile -File ./scripts/task-done-notify.ps1 -Source "WorkBuddy" -Summary "生成周报" -Message "周报已生成：report.md"
```

Python 环境（macOS / Linux / 跨平台）：

```bash
python3 ./scripts/task-done-notify.py --source WorkBuddy --summary "生成周报" --message "周报已生成：report.md"
```

自检配置（不发信）：追加 `--dry-run` / `-DryRun`。

---

## 四、持久化存储位置建议

| 智能体 | 持久标志建议位置 |
|--------|------------------|
| WorkBuddy | `~/.workbuddy/MEMORY.md` 或会话级 `.workbuddy/memory/` 日志中记录 `notify.persistent=true` |
| Codex | `~/.codex/` 下配置或环境变量 `XUCE_NOTIFY_PERSISTENT=1` |
| 通用 | 任何智能体可读写的本地标记文件，如 `~/.agent-qq-mail-notify/persistent.flag` |

> 持久化仅影响「是否自动发信」，**不改变** SMTP 凭据的存储位置（凭据始终来自环境变量或 `*.local.json`）。
