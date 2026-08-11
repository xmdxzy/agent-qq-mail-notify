# agent-qq-mail-notify

> 当 **任意 AI 智能体**（如 Codex / WorkBuddy / Claude 等）完成任务后，通过 **QQ 邮箱 SMTP** 自动向你的收件箱发送一封完成通知邮件。

一个轻量、跨平台、零外部依赖的通知方案。智能体在任务收尾时调用一段脚本即可发信，配置通过环境变量或本地 JSON 文件提供，触发词与执行逻辑见 [`docs/TRIGGERS.md`](docs/TRIGGERS.md)。**本方案不依赖任何特定智能体平台，可独立运行。**

---

## 特性

- ✅ **QQ 邮箱原生 SMTP**（`smtp.qq.com`，STARTTLS，端口 587）
- ✅ **跨平台**：PowerShell（`task-done-notify.ps1`，Windows PowerShell 5.1 或 PowerShell 7）与 Python 3 标准库（`task-done-notify.py`）双实现，macOS / Linux / Windows 通用
- ✅ **零依赖**：Python 版仅用标准库，无需 `pip install`
- ✅ **清晰的触发词**：单次 / 持久 / 自检 / 关闭，见 [`docs/TRIGGERS.md`](docs/TRIGGERS.md)
- ✅ **安全**：凭据不外泄、正文不含密钥、主题注入防护、通知失败不阻塞任务结果
- ✅ **来源可区分**：自动主题前缀 `[Source] 任务完成：Summary`，`Source` 由调用方任意指定

---

## 目录结构

```
agent-qq-mail-notify/
├── scripts/
│   ├── task-done-notify.ps1   # PowerShell 版（Windows PowerShell / PowerShell 7）
│   └── task-done-notify.py    # Python 3 跨平台版（仅标准库）
├── config/
│   └── task-done-notify.example.json  # 配置模板
├── docs/
│   └── TRIGGERS.md            # 触发词与执行逻辑规范
├── skill/
│   └── SKILL.md               # 供智能体加载的 Skill（与平台解耦）
├── README.md
├── LICENSE
└── .gitignore
```

---

## 快速开始

### 1. 配置 QQ 邮箱

1. 登录 QQ 邮箱网页版 → **设置 → 账户 → 开启 IMAP/SMTP 服务**。
2. 按提示获取 **授权码**（不是 QQ 密码），记为 `<AUTH_CODE>`。
3. 发件地址即你的 QQ 邮箱（在配置中以 `your-sender@qq.com` 占位）。

### 2. 写入配置（二选一）

**方式 A：本地 JSON（推荐，仅本机）**

复制模板并按需修改：

```bash
cp config/task-done-notify.example.json scripts/task-done-notify.local.json
```

```json
{
  "smtpServer": "smtp.qq.com",
  "smtpPort": 587,
  "enableSsl": true,
  "smtpUser": "your-sender@qq.com",
  "smtpPassword": "<AUTH_CODE>",
  "from": "Agent Notifier <your-sender@qq.com>",
  "to": "your-receiver@qq.com",
  "subject": "Agent task complete"
}
```

**方式 B：环境变量（CI / 多机更方便）**

```bash
export QQ_NOTIFY_SMTP_SERVER=smtp.qq.com
export QQ_NOTIFY_SMTP_PORT=587
export QQ_NOTIFY_SMTP_USER=your-sender@qq.com
export QQ_NOTIFY_SMTP_PASSWORD=<AUTH_CODE>
export QQ_NOTIFY_FROM="Agent Notifier <your-sender@qq.com>"
export QQ_NOTIFY_TO=your-receiver@qq.com
```

> 优先级：环境变量 `QQ_NOTIFY_*` ＞ `*.local.json`。

### 3. 验证配置（不发信）

```bash
# PowerShell
powershell -NoProfile -File ./scripts/task-done-notify.ps1 -DryRun -Source "Agent" -Summary "测试"

# Python
python3 ./scripts/task-done-notify.py --dry-run --source Agent --summary "测试"
```

输出 JSON 含 `From / To / Subject / Source / HasPassword` 即配置就绪。

### 4. 真正发信

```bash
# PowerShell
powershell -NoProfile -File ./scripts/task-done-notify.ps1 -Source "Agent" -Summary "生成周报" -Message "周报已生成：report.md"

# Python
python3 ./scripts/task-done-notify.py --source Agent --summary "生成周报" --message "周报已生成：report.md"
```

---

## 在智能体中集成

将 `skill/SKILL.md` 作为 Skill 放入对应智能体的 skills 目录（例如 `~/.workbuddy/skills/agent-qq-mail-notify/` 或 Codex 的技能目录），智能体即可在识别到触发词时自动调用。触发词与执行逻辑见 [`docs/TRIGGERS.md`](docs/TRIGGERS.md)。

调用时通过 `--source`（或 `-Source`）传入当前智能体名称，即可在邮件主题中区分来源。

### 触发词速查

| 意图 | 触发词 |
|------|--------|
| 单次通知 | 「完成后通知我」「做完发QQ邮件提醒我」「notify me when done」 |
| 持久通知 | 「以后任务完成都发QQ邮件通知我」「开启任务完成邮件通知」 |
| 配置自检 | 「通知配置好了吗」「检查通知配置」 |
| 关闭通知 | 「不用通知了」「关闭邮件通知」 |

---

## 安全说明

- **凭据仅本机**：`*.local.json` 与 `QQ_NOTIFY_SMTP_PASSWORD` 含授权码，已在 `.gitignore` 忽略，**切勿提交进仓库**。
- **正文不泄露密钥**：通知邮件只含任务摘要、来源、完成时间、产物路径。
- **注入防护**：主题与来源去除换行、截断到 150 字符。
- **旁路副作用**：通知失败只提示，不影响任务结果返回。

---

## License

[MIT](LICENSE)
