#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键安装 agent-qq-mail-notify 技能到目标智能体的 skills 目录。

纯标准库、跨平台（Windows / macOS / Linux）。安装 = 把项目里的 skill/、scripts/、
config/ 三个目录**整体复制**到目标智能体约定的 skills 目录下（目录名固定为
agent-qq-mail-notify），技能因此是**自包含**的：SKILL.md 引用的通知脚本
（scripts/）与配置模板（config/）都随技能一起安装，智能体加载后即可直接调用。
智能体下次启动会话时会自动扫描加载。

用法：
  python3 scripts/install-skill.py                       # 交互式选择目标
  python3 scripts/install-skill.py --target workbuddy    # 装到 WorkBuddy 全局
  python3 scripts/install-skill.py --target codex        # 装到 Codex CLI 全局
  python3 scripts/install-skill.py --target claude       # 装到 Claude Code 全局
  python3 scripts/install-skill.py --target <目录>       # 装到自定义 skills 目录
  python3 scripts/install-skill.py --check               # 检查已安装位置

说明：
  - workbuddy 全局目录：~/.workbuddy/skills/
  - codex 全局目录：     ~/.codex/skills/
  - claude 全局目录：    ~/.claude/skills/
  - 需要"仅当前项目生效"时，可把 --target 指向项目内 .codex/skills（或
    .workbuddy/skills / .claude/skills），脚本同样支持。
"""

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "agent-qq-mail-notify"

# 需要复制进技能目录的源目录（自包含：说明 + 脚本 + 配置模板）
SRC_DIRS = ["skill", "scripts", "config"]

GLOBAL_TARGETS = {
    "workbuddy": Path.home() / ".workbuddy" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}

PROJECT_TARGETS = {
    "workbuddy": Path(".workbuddy") / "skills",
    "codex": Path(".codex") / "skills",
    "claude": Path(".claude") / "skills",
}


def copy_skill(dest_dir: Path) -> Path:
    dest = dest_dir / SKILL_NAME
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for src_name in SRC_DIRS:
        src = REPO_ROOT / src_name
        if not src.exists():
            sys.exit(f"[ERR] 未找到源目录：{src}")
        for item in sorted(src.iterdir()):
            if item.name == "install-skill.py":  # 安装器本身不进技能目录
                continue
            target = dest / src_name / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
            n += 1
    print(f"[OK] 已安装 {n} 项 -> {dest}")
    print(f"[OK] 技能为自包含：skill/ + scripts/ + config/ 已就位。")
    return dest


def interactive_select():
    print("选择要安装到的智能体：")
    options = [
        ("workbuddy", GLOBAL_TARGETS["workbuddy"], "WorkBuddy 全局（~/.workbuddy/skills）"),
        ("codex", GLOBAL_TARGETS["codex"], "Codex CLI 全局（~/.codex/skills）"),
        ("claude", GLOBAL_TARGETS["claude"], "Claude Code 全局（~/.claude/skills）"),
        ("project", Path(".codex") / "skills", "当前项目 .codex/skills（仅本项目）"),
        ("custom", None, "自定义目录"),
    ]
    for i, (_, _, label) in enumerate(options, 1):
        print(f"  [{i}] {label}")
    while True:
        s = input("输入序号（1-5，回车默认 1）：").strip() or "1"
        try:
            idx = int(s) - 1
            if 0 <= idx < len(options):
                break
        except ValueError:
            pass
        print("  无效输入，请重试。")
    key, d, _ = options[idx]
    if key == "custom":
        while True:
            s = input("输入自定义 skills 目录（绝对路径）：").strip()
            if s:
                return Path(s).expanduser()
            print("  路径不能为空。")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(
        description="一键安装 agent-qq-mail-notify 技能到智能体 skills 目录（纯标准库，跨平台）")
    ap.add_argument("--target",
                    help="workbuddy / codex / claude / <自定义目录>；缺省为交互式选择")
    ap.add_argument("--check", action="store_true",
                    help="仅检查已安装位置，不安装")
    args = ap.parse_args()

    if args.check:
        checked = {}
        for name, root in GLOBAL_TARGETS.items():
            checked[f"{name}(全局)"] = root / SKILL_NAME
        for name, root in PROJECT_TARGETS.items():
            checked[f"{name}(项目)"] = root / SKILL_NAME
        found = [d for d in checked.values() if d.exists()]
        if found:
            print("已检测到安装位置：")
            for label, d in checked.items():
                if d.exists():
                    print(f"  - {label}: {d}")
        else:
            print("未检测到已安装的 skill。")
            print(f"运行 python3 {Path(__file__).name} 开始安装。")
        return 0

    dest_dir = None
    if args.target:
        t = args.target.strip()
        if t in GLOBAL_TARGETS:
            dest_dir = GLOBAL_TARGETS[t]
        elif t in PROJECT_TARGETS:
            dest_dir = PROJECT_TARGETS[t]
        else:
            dest_dir = Path(t).expanduser()
    else:
        dest_dir = interactive_select()

    if dest_dir is None:
        sys.exit("[ERR] 未指定目标目录。")

    copy_skill(dest_dir)
    print()
    print("[NEXT] 1) 新开一个会话，让智能体重新扫描 skills。")
    print("[NEXT] 2) 对智能体说「检查通知配置」，若它回显配置 JSON 说明 skill 已生效。")
    print(f"[NEXT] 3) 本地快速自检：python3 {REPO_ROOT / 'scripts' / 'task-done-notify.py'} --dry-run --source Agent --summary 安装自检")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
