#!/usr/bin/env python3
"""
source_audit.py — 输出可读的信源质量报告

用法：
  D:/python.exe scripts/source_audit.py
  D:/python.exe scripts/source_audit.py --json          # 输出 JSON
  D:/python.exe scripts/source_audit.py --failed-only   # 只看失败源
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Force UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
WEB_SOURCES_PATH = ROOT / "feeds" / "ecommerce.web-sources.json"
OPML_PATH = ROOT / "feeds" / "ecommerce.example.opml"
STATUS_PATH = ROOT / "data" / "source-status.json"


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 无法加载 {path}: {e}", file=sys.stderr)
        return None


def audit_web_sources(data: dict, status: dict | None) -> dict:
    sources = data.get("sources", [])
    web_status = (status or {}).get("web_sources", {})
    failed_ids = set((web_status.get("failed_sources") or []))
    zero_ids = set((web_status.get("zero_item_sources") or []))

    result = {
        "total": len(sources),
        "enabled": [],
        "headless_blocked": [],
        "candidate_only": [],
        "disabled": [],
        "failed": [],
        "zero_result": [],
    }

    for s in sources:
        sid = s.get("id", "")
        name = s.get("name", sid)
        platform = s.get("platform", "")
        priority = s.get("priority", "")
        url = s.get("url", "")
        enabled = s.get("enabled", True)
        is_candidate = s.get("candidate_only") or s.get("ingestion_method") == "candidate_only"
        needs_headless = s.get("needs_headless", False)

        entry = {
            "id": sid,
            "name": name,
            "platform": platform,
            "priority": priority,
            "url": url,
        }

        if is_candidate:
            result["candidate_only"].append(entry)
        elif enabled is False:
            entry["reason"] = s.get("disabled_reason", "")
            result["disabled"].append(entry)
        elif needs_headless:
            result["headless_blocked"].append(entry)
        else:
            result["enabled"].append(entry)
            if sid in failed_ids:
                result["failed"].append(entry)
            elif sid in zero_ids:
                result["zero_result"].append(entry)

    return result


def audit_rss(status: dict | None) -> dict:
    rss = (status or {}).get("rss_opml", {})
    return {
        "total": rss.get("effective_feed_total", 0),
        "ok": rss.get("ok_feeds", 0),
        "failed": rss.get("failed_feeds") or [],
        "zero": rss.get("zero_item_feeds") or [],
        "skipped": rss.get("skipped_feeds") or [],
    }


def print_report(web: dict, rss: dict, status: dict | None) -> None:
    sep = "─" * 60

    print(sep)
    print("  电商热点雷达 · 信源质量审计报告")
    print(sep)

    # === RSS ===
    print(f"\n【RSS / OPML】")
    print(f"  总计: {rss['total']} 条  |  正常: {rss['ok']}  |  失败: {len(rss['failed'])}  |  零结果: {len(rss['zero'])}")
    if rss["failed"]:
        print(f"  失败 ({len(rss['failed'])}):")
        for url in rss["failed"]:
            print(f"    ✗  {url}")
    if rss["zero"]:
        print(f"  零结果 ({len(rss['zero'])}):")
        for url in rss["zero"]:
            print(f"    ○  {url}")

    # === Web Sources Summary ===
    print(f"\n【网页源汇总】")
    print(f"  总计:      {web['total']}")
    print(f"  启用抓取:  {len(web['enabled'])}")
    print(f"  Headless封锁: {len(web['headless_blocked'])}  (JS渲染，跳过，不计入失败)")
    print(f"  待验证候选:   {len(web['candidate_only'])}  (未验证，不进首页)")
    print(f"  已禁用:       {len(web['disabled'])}")
    print(f"  失败:      {len(web['failed'])}")
    print(f"  零结果:    {len(web['zero_result'])}")

    # === Headless Blocked (P0) ===
    headless_p0 = [s for s in web["headless_blocked"] if s.get("priority") == "P0"]
    headless_p1 = [s for s in web["headless_blocked"] if s.get("priority") == "P1"]
    if headless_p0:
        print(f"\n【Headless封锁 P0 — 官方平台规则中心（需浏览器才能抓取）】")
        for s in headless_p0[:20]:
            print(f"  ⊘  {s['name']} ({s['platform']})  {s['url'][:60]}")
        if len(headless_p0) > 20:
            print(f"  ... 另有 {len(headless_p0) - 20} 个")

    # === Failed Web Sources ===
    if web["failed"]:
        print(f"\n【失败网页源 — 需修复或禁用】")
        for s in web["failed"]:
            print(f"  ✗  [{s.get('priority','')}] {s['name']}  {s['url'][:60]}")

    # === Zero Result Web Sources ===
    if web["zero_result"]:
        print(f"\n【零结果网页源 — 抓取成功但无内容】")
        for s in web["zero_result"]:
            print(f"  ○  [{s.get('priority','')}] {s['name']}  {s['url'][:60]}")

    # === Disabled ===
    disabled_with_reason = [s for s in web["disabled"] if s.get("reason")]
    if disabled_with_reason:
        print(f"\n【近期禁用源（有明确原因）】")
        for s in disabled_with_reason[:10]:
            print(f"  —  {s['name']}  ({s['reason']})")

    # === Last run stats ===
    if status:
        gen = status.get("generated_at", "")
        items_raw = status.get("fetched_raw_items") or status.get("items_in_24h", 0)
        print(f"\n【最近一次采集】")
        print(f"  生成时间:   {gen}")
        print(f"  原始条目:   {items_raw}")
        headless_blocked = status.get("headless_blocked_source_count")
        real_failed = status.get("real_failed_source_count")
        if headless_blocked is not None:
            print(f"  Headless封锁: {headless_blocked}")
        if real_failed is not None:
            print(f"  真实失败源:   {real_failed}")

    print(f"\n{sep}")
    print("  审计完成。修复建议：")
    print("  1. 失败 RSS → 更换 URL 或标注 candidate_only")
    print("  2. 失败网页源 → 在 web-sources.json 设 enabled: false")
    print("  3. Headless P0 → 优先用 RSS 行业媒体代理覆盖规则变化")
    print("  4. 零结果源 → 检查 URL 是否为栏目页（列表页）而非详情页")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="信源质量审计")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--failed-only", action="store_true", help="只显示失败源")
    args = parser.parse_args()

    web_data = load_json(WEB_SOURCES_PATH)
    status = load_json(STATUS_PATH)

    if not web_data:
        print("错误：无法加载 feeds/ecommerce.web-sources.json", file=sys.stderr)
        sys.exit(1)

    web = audit_web_sources(web_data, status)
    rss = audit_rss(status)

    if args.json:
        print(json.dumps({"web": web, "rss": rss}, ensure_ascii=False, indent=2))
        return

    if args.failed_only:
        print("失败 RSS:", rss["failed"])
        print("失败网页源:", [s["id"] for s in web["failed"]])
        return

    print_report(web, rss, status)


if __name__ == "__main__":
    main()
