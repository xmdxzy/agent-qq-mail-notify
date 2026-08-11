#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端功能测试：用**纯标准库**起一个本地 mock SMTP 服务，
验证通知脚本能完整走通「连接 → 登录 → 发送」流程。

特点：
  - 不需要真实 QQ 凭据，也不需要联网；
  - 证明脚本在「其他用户」机器上能正常发信（只要换上他们自己的 SMTP 配置）；
  - 同时覆盖 DryRun（配置就绪校验）与「缺配置优雅退出」两条路径。

运行：python3 tests/test_mock_smtp.py
"""

import base64
import email
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from email.header import decode_header, make_header
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "task-done-notify.py"

RECEIVED = {}  # 服务端捕获到的邮件原文


def start_mock_smtp(port: int):
    """极简 SMTP 服务（仅响应测试所需的命令，不做真实投递）。"""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        conn.sendall(b"220 mock ESMTP\r\n")
        auth_phase = 0  # 0=无 1=已发 AUTH 期待用户名 2=期待密码
        data_mode = False
        buf = []
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", "replace")
                for line in text.split("\r\n"):
                    if not line:
                        continue
                    if data_mode:
                        buf.append(line)
                        if line == ".":
                            RECEIVED["raw"] = "\r\n".join(buf)
                            conn.sendall(b"250 OK queued\r\n")
                            data_mode = False
                            buf = []
                        continue
                    cmd = line.split(" ", 1)[0].upper()
                    if cmd in ("EHLO", "HELO"):
                        conn.sendall(b"250-mock\r\n250 AUTH LOGIN\r\n")
                    elif cmd == "AUTH":
                        conn.sendall(b"334 VXNlcm5hbWU6\r\n")  # base64("Username:")
                        auth_phase = 1
                    elif cmd == "MAIL":
                        conn.sendall(b"250 OK\r\n")
                    elif cmd == "RCPT":
                        conn.sendall(b"250 OK\r\n")
                    elif cmd == "DATA":
                        conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                        data_mode = True
                    elif cmd == "QUIT":
                        conn.sendall(b"221 Bye\r\n")
                        return
                    else:
                        # AUTH 之后的用户名/密码 base64 行
                        if auth_phase == 1:
                            conn.sendall(b"334 UGFzc3dvcmQ6\r\n")  # base64("Password:")
                            auth_phase = 2
                        elif auth_phase == 2:
                            conn.sendall(b"235 Authentication successful\r\n")
                            auth_phase = 0
                        else:
                            conn.sendall(b"250 OK\r\n")
        finally:
            conn.close()
            srv.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return t


def run_script(args, env=None):
    p = subprocess.run(
        [sys.executable, str(SCRIPT)] + args,
        capture_output=True, text=True,
        env=env or os.environ,
    )
    return p


def main() -> int:
    port = 8137
    start_mock_smtp(port)
    time.sleep(0.3)

    # 临时配置：指向本地 mock 服务，关闭 SSL，避免联网
    cfg = {
        "smtpServer": "127.0.0.1",
        "smtpPort": port,
        "enableSsl": False,
        "smtpUser": "test@test.com",
        "smtpPassword": "test",
        "from": "Agent Notifier <test@test.com>",
        "to": "recv@test.com",
        "subject": "Agent task complete",
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cfg, f)
        cfg_path = f.name

    failures = []

    # 1) DryRun：配置就绪，输出 JSON 且退出码 0
    p = run_script(["--dry-run", "--config", cfg_path, "--source", "Agent", "--summary", "测试"])
    if p.returncode != 0:
        failures.append(f"[DryRun] 退出码应为0，实际 {p.returncode}; stderr={p.stderr}")
    else:
        try:
            meta = json.loads(p.stdout)
            assert meta["to"] == "recv@test.com", meta
        except Exception as e:
            failures.append(f"[DryRun] JSON 校验失败: {e}; stdout={p.stdout}")

    # 2) 真正发送：走通连接→登录→发送，mock 服务端应收到邮件
    RECEIVED.clear()
    p = run_script(["--config", cfg_path, "--source", "Agent", "--summary", "测试", "--message", "hello-world"])
    if p.returncode != 0:
        failures.append(f"[Send] 退出码应为0，实际 {p.returncode}; stderr={p.stderr}")
    else:
        raw = RECEIVED.get("raw", "")
        # raw 末尾带 SMTP 终止符 "."，先去掉再交给 email 解析
        parsed = email.message_from_string(raw.replace("\r\n.\r\n", "\r\n"))
        # 中文主题会被 EmailMessage 做 RFC 2047 编码（=?utf-8?b?...?=），需解码后断言
        subject = str(make_header(decode_header(parsed["Subject"])))
        body = parsed.get_payload()
        checks = {
            "主题含 [Agent] 任务完成：测试": "[Agent] 任务完成：测试" in subject,
            "正文含 hello-world": "hello-world" in (body or ""),
            "收件人 recv@test.com": "recv@test.com" in raw,
        }
        for label, ok in checks.items():
            if not ok:
                failures.append(f"[Send] {label}; subject={subject!r}; body={body!r}; raw={raw!r}")

    # 3) 缺配置：应优雅退出（退出码 2），而不是崩溃
    env_no_cfg = dict(os.environ)
    for k in list(env_no_cfg):
        if k.startswith("QQ_NOTIFY_"):
            del env_no_cfg[k]
    p = run_script(["--dry-run", "--summary", "x"], env=env_no_cfg)
    if p.returncode != 2:
        failures.append(f"[Missing] 缺配置应退出码2，实际 {p.returncode}; stdout={p.stdout}; stderr={p.stderr}")

    os.unlink(cfg_path)

    if failures:
        print("FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("ALL TESTS PASSED ✅  (DryRun / 真实发送走通本地 mock SMTP / 缺配置优雅退出)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
