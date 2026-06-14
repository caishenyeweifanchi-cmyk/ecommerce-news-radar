#!/usr/bin/env python3
"""
run_pipeline.py — 采集 + 推送一键运行

执行顺序：
  1. 采集（update_news.py）
  2. 精选实时提醒（feishu_alert.py）— 新进精选的条目每条单独推
  3. 每日日报（feishu_push.py）  — 仅在 --daily 模式下运行

用法:
  D:/python.exe scripts/run_pipeline.py             # 采集 + 精选提醒
  D:/python.exe scripts/run_pipeline.py --daily     # 采集 + 精选提醒 + 日报汇总
  D:/python.exe scripts/run_pipeline.py --dry-run   # 全程不实际发送
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
PYTHON = sys.executable  # 用当前 Python，保证和调用者一致


def run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*50}")
    print(f"▶ {label}")
    print(f"{'='*50}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"✗ {label} 失败（exit code {result.returncode}），中止流程。")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="电商热点雷达一键运行流水线")
    parser.add_argument("--daily", action="store_true", help="同时发送每日日报汇总")
    parser.add_argument("--dry-run", action="store_true", help="不实际发飞书消息")
    parser.add_argument("--skip-collect", action="store_true", help="跳过采集直接推送（调试用）")
    args = parser.parse_args()

    # ── Step 1: 采集 ──────────────────────────────────────────────
    if not args.skip_collect:
        collect_cmd = [
            PYTHON, str(ROOT / "scripts" / "update_news.py"),
            "--topic", "ecommerce",
            "--output-dir", "data",
            "--window-hours", "168",
            "--archive-days", "21",
            "--rss-opml", "feeds/ecommerce.example.opml",
            "--rss-max-feeds", "0",
            "--web-sources", "feeds/ecommerce.web-sources.json",
            "--web-max-sources", "0",
            "--translate-max-new", "0",
        ]
        if not run(collect_cmd, "Step 1 / 3  采集最新内容"):
            sys.exit(1)

    # ── Step 2: 精选实时提醒 ──────────────────────────────────────
    alert_cmd = [PYTHON, str(ROOT / "scripts" / "feishu_alert.py")]
    if args.dry_run:
        alert_cmd.append("--dry-run")
    if not run(alert_cmd, "Step 2 / 3  精选实时提醒（新条目逐条推送）"):
        print("⚠ 精选提醒失败，继续执行后续步骤。")

    # ── Step 3: 每日日报（可选）──────────────────────────────────
    if args.daily:
        daily_cmd = [PYTHON, str(ROOT / "scripts" / "feishu_push.py"), "--top", "5"]
        if args.dry_run:
            daily_cmd.append("--dry-run")
        if not run(daily_cmd, "Step 3 / 3  每日日报汇总推送"):
            print("⚠ 日报推送失败。")

    print(f"\n{'='*50}")
    print("✓ 流水线完成")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
