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
│   ├── task-done-notify.py    # Python 3 跨平台版（仅标准库）
│   └── install-skill.py       # 一键把 skill 装进智能体（WorkBuddy/Codex/Claude/自定义）
├── config/
│   └── task-done-notify.example.json  # 配置模板
├── docs/
│   └── TRIGGERS.md            # 触发词与执行逻辑规范
├── skill/
│   └── SKILL.md               # 供智能体加载的 Skill（与平台解耦）
├── tests/
│   └── test_mock_smtp.py      # 端到端功能测试（纯标准库 mock SMTP，无需真实凭据/联网）
├── .github/
│   └── workflows/
│       └── test.yml           # 提交 / PR 时自动跑测试（fork 也能用）
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

## 在智能体中集成（让 AI 自动发通知）

把 `skill/` 装进你的智能体后，AI 就会在识别到触发词（如「完成后通知我」「检查通知配置」）时自动调用脚本发邮件。**装一次，到处可用。**

### 方式 A：一键安装（推荐）

clone 项目后运行安装脚本（纯标准库，Windows / macOS / Linux 通用）：

```bash
git clone https://github.com/xmdxzy/agent-qq-mail-notify
cd agent-qq-mail-notify

# 交互式选择目标智能体
python3 scripts/install-skill.py

# 或直接指定目标：workbuddy / codex / claude / 自定义目录
python3 scripts/install-skill.py --target workbuddy
python3 scripts/install-skill.py --target codex
python3 scripts/install-skill.py --target claude
python3 scripts/install-skill.py --target ~/my-agent/skills
```

脚本会把 `skill/`、`scripts/`、`config/` 一起复制到目标位置（目录名固定为 `agent-qq-mail-notify`，技能**自包含**：SKILL.md 引用的通知脚本与配置模板都随之就位），并提示验证方法。

### 方式 B：手动放置

把 `skill/`、`scripts/`、`config/` 三个目录复制到对应智能体的 skills 目录下（保持 `agent-qq-mail-notify/<子目录>/` 结构，让技能自包含）：

| 智能体 | skills 目录（替换 `<用户目录>`） |
|--------|----------------------------------|
| WorkBuddy（全局） | `<用户目录>/.workbuddy/skills/agent-qq-mail-notify/` |
| WorkBuddy（项目） | `<项目>/.workbuddy/skills/agent-qq-mail-notify/` |
| Codex CLI（全局） | `<用户目录>/.codex/skills/agent-qq-mail-notify/` |
| Codex CLI（项目） | `<项目>/.codex/skills/agent-qq-mail-notify/` |
| Claude Code（全局） | `<用户目录>/.claude/skills/agent-qq-mail-notify/` |

> 目录内必须含 `SKILL.md`（含 `name` / `description` 元信息），智能体靠它识别加载。

### 装好后如何确认生效

1. **新开一个会话**（让智能体重新扫描 skills 目录）。
2. 对智能体说：「**检查通知配置**」或「**测试一下邮件通知**」。
3. 如果它调用脚本做 `--dry-run` 自检并回显配置 JSON → **skill 已生效**；
   如果答非所问 → 检查目录路径与文件名是否为 `SKILL.md`。
4. 本地快速自检（不经智能体，直接验证脚本本身可用）：

```bash
python3 scripts/task-done-notify.py --dry-run --source Agent --summary 安装自检
```

> 未配置 SMTP 前，「检查通知配置」只会提示缺失项（退出码 2），**不会发信**，属正常行为。

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

## 测试 / Testing（部署后如何验证可用）

本仓库附带的测试能在**不暴露任何真实 QQ 凭据、不联网**的前提下，验证脚本能完整走通「连接 → 登录 → 发送」。这是其他用户 clone/fork 之后确认项目可用的关键手段。

### 原理

用一个**纯标准库**起的本地 mock SMTP 服务（端口 `8137`），让通知脚本把信"发"到本地而不是真实 QQ 服务器。测试覆盖三条路径：

1. **DryRun（配置就绪校验）**：缺配置时输出缺失项并优雅退出（退出码 `2`）；配置就绪时输出 JSON 元信息（退出码 `0`）。
2. **真实发送走通**：脚本完整执行 `connect → login → send`，mock 服务端能正确收到邮件（校验主题前缀、正文、收件人）。
3. **缺配置优雅退出**：未提供任何 SMTP 配置时退出码 `2`，不崩溃。

> 通过这条路径，任何用户只要换上**自己的** SMTP 配置（环境变量或本地 JSON），即可在真实环境发信——测试本身不依赖你的邮箱。

### 本地运行

```bash
# 需要 Python 3（仅标准库，无需 pip install）
python3 tests/test_mock_smtp.py
# 期望输出：ALL TESTS PASSED ✅
```

### 持续集成（CI）

`.github/workflows/test.yml` 会在每次 `push` 与 `pull_request` 时，在 `ubuntu-latest` 上自动运行上述测试。

- **原仓库**：提交即自动验证。
- **Fork 仓库**：在 GitHub 网页点一下 `Actions` → 启用 workflows，之后自己的提交也会自动跑测试。

这样，无论是你自己还是其他贡献者，都能一眼看到"部署后项目是否仍正常工作"。

### 真机自检（可选）

不放心的话，发一封真实邮件验证：

```bash
# 仅校验配置（不发信）
python3 ./scripts/task-done-notify.py --dry-run --source Agent --summary "测试"

# 真正发一封到你的收件箱
python3 ./scripts/task-done-notify.py --source Agent --summary "部署自检" --message "项目已部署可用"
```

---

## License

[MIT](LICENSE)
