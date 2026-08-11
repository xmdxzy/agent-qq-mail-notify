---
name: agent-qq-mail-notify
description: 当任意 AI 智能体（如 Codex / WorkBuddy / Claude）完成任务后，通过 QQ 邮箱 SMTP 向用户发送完成通知。当用户说「完成后通知我」「任务完成发QQ邮件」「开启邮件通知」「检查通知配置」等触发词，或已配置持久化通知时使用。仅在用户明确要求邮件通知时才发信，不主动打扰。本技能不依赖任何特定智能体平台，可独立运行。
---

# Agent 任务完成 QQ 邮箱通知

完成任务后，按用户意图用 QQ 邮箱发送一封完成通知邮件。配套脚本：`scripts/task-done-notify.ps1`（PowerShell）与 `scripts/task-done-notify.py`（Python，跨平台）。本技能与具体智能体平台解耦，任何能调用脚本的智能体均可使用。

## 触发词

| 意图 | 触发词示例 |
|------|------------|
| 单次通知 | 「完成后通知我」「做完发QQ邮件提醒我」「notify me when done」 |
| 持久通知 | 「以后任务完成都发QQ邮件通知我」「开启任务完成邮件通知」「always notify me by QQ email」 |
| 配置自检 | 「通知配置好了吗」「检查通知配置」「测试一下邮件通知」 |
| 关闭通知 | 「不用通知了」「关闭邮件通知」「disable email notifications」 |

匹配规则：含「完成/做完 + 通知/邮件/QQ邮箱」或 `notify/email me when (done/finished/complete)` 即视为命中。

## 执行逻辑

1. **解析触发词** → 设置 `notify_intent`：`once` / `persistent` / `check` / `off`。
2. **持久化**：`persistent` → 在记忆/配置写入 `notify.persistent=true`；`off` → 清除。
3. **执行任务**（完成、失败、部分完成都算结束）。
4. **判定发信**：`intent == once` 或 `notify.persistent == true` → 发；否则不发。
5. **发信流程**：
   - 解析配置：环境变量 `QQ_NOTIFY_*` ＞ `task-done-notify.local.json`。
   - 构造载荷：`Source` 取本智能体名（任意，如 Agent / Codex / WorkBuddy），`Summary` 为任务短标题，`Message` 为结果摘要 + 时间戳。
   - 未知配置时先 `--dry-run` 探测；就绪则正式发送。
   - 成功 → 最终回复附「已发 QQ 邮件通知」；失败 → 仅提示，不阻塞结果。

## 调用（按运行环境任选其一）

PowerShell（Windows）：
```powershell
powershell -NoProfile -File ./scripts/task-done-notify.ps1 -Source "Agent" -Summary "<任务短标题>" -Message "<结果摘要>"
```

Python（macOS / Linux / 跨平台）：
```bash
python3 ./scripts/task-done-notify.py --source Agent --summary "<任务短标题>" --message "<结果摘要>"
```

自检（不发信）：追加 `-DryRun` / `--dry-run`。

## 安全边界（必须遵守）

- **永不阻塞任务结果**：通知是旁路副作用，无论成败都先把结果返回用户。
- **配置缺失不报错**：未配置时提示用户复制 `config/task-done-notify.example.json` 或设置 `QQ_NOTIFY_SMTP_*`，不要抛错中断。
- **正文不含敏感信息**：`Message` 只放摘要/来源/时间/产物路径，禁止包含密码、token、密钥。
- **摘要清洗**：`Summary`/`Source` 去除换行，主题截断到 150 字符，防 SMTP 注入。
- 凭据存储在 `*.local.json` 或环境变量 `QQ_NOTIFY_*`，仅在用户本机，不上仓库、不进日志。
