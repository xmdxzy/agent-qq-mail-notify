#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 任务完成 QQ 邮箱通知脚本（Python，跨平台）。

当 Codex / WorkBuddy 等智能体完成任务后调用本脚本，
通过 QQ 邮箱 SMTP（smtp.qq.com）向用户指定的收件箱发送一封完成通知邮件。

配置优先级（从高到低）：
  1. 环境变量 XUCE_NOTIFY_*（WorkBuddy/序策优先）
  2. 环境变量 CODEX_NOTIFY_*（兼容 Codex 旧方案）
  3. 配置文件 task-done-notify.local.json（默认：脚本同目录）

用法示例：
  # 真正发信
  python3 task-done-notify.py --source WorkBuddy --summary "生成周报" \
      --message "周报已生成：report.md"

  # 仅校验配置就绪（不真正发信）
  python3 task-done-notify.py --dry-run --source WorkBuddy --summary "测试"

依赖：仅标准库（smtplib / ssl / email），无需 pip install。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from ssl import create_default_context


def first_value(*values):
    for v in values:
        if v is not None and str(v).strip() != "":
            return v
    return None


def load_config(path: Path):
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = f.read().strip()
            return json.loads(raw) if raw else {}
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 读取配置文件失败，已忽略：{exc}", file=sys.stderr)
        return {}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agent 任务完成 QQ 邮箱通知")
    p.add_argument("--message", help="邮件正文；省略时根据来源/摘要自动生成")
    p.add_argument("--subject", help="邮件主题；省略时自动拼成 [Source] 任务完成：Summary")
    p.add_argument("--source", default="WorkBuddy", help="任务来源标识，如 Codex / WorkBuddy")
    p.add_argument("--summary", help="任务摘要（短标题）")
    p.add_argument("--config", help="配置文件路径（默认：脚本同目录 task-done-notify.local.json）")
    p.add_argument("--dry-run", action="store_true", help="只校验配置并输出邮件元信息，不真正发信")
    return p


def main() -> int:
    args = build_parser().parse_args()

    script_dir = Path(__file__).resolve().parent
    config_path = Path(args.config) if args.config else (script_dir / "task-done-notify.local.json")
    config = load_config(config_path)

    # WorkBuddy/序策优先 XUCE_NOTIFY_*，并兼容 Codex 既有 CODEX_NOTIFY_*。
    smtp_server = first_value(os.environ.get("XUCE_NOTIFY_SMTP_SERVER"),
                              os.environ.get("CODEX_NOTIFY_SMTP_SERVER"), config.get("smtpServer"))
    smtp_port = first_value(os.environ.get("XUCE_NOTIFY_SMTP_PORT"),
                            os.environ.get("CODEX_NOTIFY_SMTP_PORT"), config.get("smtpPort"))
    smtp_user = first_value(os.environ.get("XUCE_NOTIFY_SMTP_USER"),
                            os.environ.get("CODEX_NOTIFY_SMTP_USER"), config.get("smtpUser"))
    smtp_password = first_value(os.environ.get("XUCE_NOTIFY_SMTP_PASSWORD"),
                                os.environ.get("CODEX_NOTIFY_SMTP_PASSWORD"), config.get("smtpPassword"))
    from_addr = first_value(os.environ.get("XUCE_NOTIFY_FROM"),
                            os.environ.get("CODEX_NOTIFY_FROM"), config.get("from"))
    to_addr = first_value(os.environ.get("XUCE_NOTIFY_TO"),
                          os.environ.get("CODEX_NOTIFY_TO"), config.get("to"), "1181861399@qq.com")
    ssl_raw = first_value(os.environ.get("XUCE_NOTIFY_SMTP_SSL"),
                          os.environ.get("CODEX_NOTIFY_SMTP_SSL"), config.get("enableSsl"))

    clean_source = (args.source or "WorkBuddy").replace("\r", " ").replace("\n", " ").strip()
    clean_summary = (args.summary or "").replace("\r", " ").replace("\n", " ").strip()

    default_subject = f"[{clean_source}] 任务完成：{clean_summary}" if clean_summary else f"[{clean_source}] 任务完成"
    resolved_subject = first_value(
        args.subject,
        os.environ.get("XUCE_NOTIFY_SUBJECT"),
        os.environ.get("CODEX_NOTIFY_SUBJECT"),
        default_subject if clean_summary else None,
        config.get("subject"),
        default_subject,
    )
    resolved_subject = resolved_subject[:150]

    enable_ssl = True
    if smtp_port is None:
        smtp_port = 587
    else:
        smtp_port = int(smtp_port)
    if ssl_raw is not None and str(ssl_raw).strip() != "":
        enable_ssl = str(ssl_raw).strip().lower() in ("1", "true", "yes", "on")

    if not from_addr:
        from_addr = smtp_user

    if args.message:
        resolved_message = args.message
    else:
        summary_line = clean_summary or "（未提供）"
        resolved_message = "\n".join([
            f"任务来源：{clean_source}",
            f"任务摘要：{summary_line}",
            f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ])

    missing = [n for n, v in (("smtpServer", smtp_server), ("smtpUser", smtp_user),
                              ("smtpPassword", smtp_password), ("from", from_addr),
                              ("to", to_addr)) if not v]
    if missing:
        print("Email notification is not configured. Missing: " + ", ".join(missing) +
              ". Copy config/task-done-notify.example.json to task-done-notify.local.json "
              "and set SMTP values, or use XUCE_NOTIFY_SMTP_* environment variables.",
              file=sys.stderr)
        return 2

    meta = {
        "smtpServer": smtp_server,
        "smtpPort": smtp_port,
        "enableSsl": enable_ssl,
        "from": from_addr,
        "to": to_addr,
        "subject": resolved_subject,
        "source": clean_source,
        "hasPassword": bool(smtp_password),
        "message": resolved_message,
    }

    if args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = resolved_subject
    msg.set_content(resolved_message)

    with SMTP(smtp_server, smtp_port) as server:
        if enable_ssl:
            server.starttls(context=create_default_context())
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    print(f"Task completion email sent to {to_addr}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
