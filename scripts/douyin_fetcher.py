#!/usr/bin/env python3
"""
douyin_fetcher.py — 抖音电商学习中心官方规则/公告抓取

调用抖音电商学习中心的内部 JSON API，无需登录，无需 headless 浏览器。
采集：规则动态、公告专区、违规管理、营销推广规则等。

用法:
  D:/python.exe scripts/douyin_fetcher.py
  D:/python.exe scripts/douyin_fetcher.py --output data/douyin-rules.json
  D:/python.exe scripts/douyin_fetcher.py --test
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── 目标分类 ─────────────────────────────────────────────────────────────────
# category_id → (分类名, 优先级标签)
RULE_CATEGORIES = {
    "11693": ("规则动态", "platform_policy"),     # 最新规则更新动态
    "12042": ("公告专区", "platform_policy"),     # 官方公告
    "nHVrR3fzrzCM": ("违规管理", "platform_policy"),  # 违规处置细则
    "nJk9eqyQqne3": ("发货物流", "platform_policy"),  # 发货时效
    "11679": ("营销推广", "operations_playbook"), # 营销活动规则
    "11683": ("精选联盟", "operations_playbook"), # 达人合作规则
    "11687": ("体验分保证金", "platform_policy"), # 体验分与保证金
}

API_BASE = "https://school.jinritemai.com/api/eschool/v1/rule/list"
DETAIL_BASE = "https://school.jinritemai.com/doudian/web/rules/{kid}?tabKey=rules"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://school.jinritemai.com/doudian/web/rules/nJjbkoeug9aS?tabKey=rules",
    "Accept": "application/json, text/plain, */*",
}


def fetch_category(category_id: str, page_size: int = 20) -> list[dict]:
    """拉取某个分类下的规则列表，返回 raw rule_info 列表。"""
    url = f"{API_BASE}?category_id={category_id}&page=1&size={page_size}"
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 0:
            print(f"  API error for {category_id}: code={data.get('code')} msg={data.get('message','')}")
            return []
        return data.get("data", {}).get("rule_infos", [])
    except Exception as e:
        print(f"  Fetch failed for category {category_id}: {e}")
        return []


def rule_to_item(rule: dict, category_name: str, label: str) -> dict:
    """把 API rule_info 转成标准 item 格式。"""
    kid = rule.get("knowledge_id", "")
    title = rule.get("title", "").strip()
    summary = rule.get("summary", "").strip()
    update_ts = rule.get("update_time", 0)  # Unix seconds

    # 构建可访问的详情页 URL
    url = DETAIL_BASE.format(kid=kid)

    # 时间处理
    if update_ts and update_ts > 1_000_000_000:
        dt = datetime.fromtimestamp(update_ts, tz=timezone(timedelta(hours=8)))
        published = dt.isoformat()
    else:
        published = datetime.now(tz=timezone(timedelta(hours=8))).isoformat()

    item_id = f"douyin_rule_{kid}"

    return {
        "id": item_id,
        "title": title,
        "title_zh": title,
        "url": url,
        "published": published,
        "source": f"抖音电商·{category_name}",
        "site_name": "抖音电商学习中心",
        "site_id": "douyin_school",
        "content_snippet": summary,
        "summary_zh": summary if summary else None,
        "ai_label": label,
        "ai_is_related": True,
        "ai_score": 0.85,      # 官方规则直接高分
        "llm_label": label,
        "llm_score": 0.85,
        "category": category_name,
        "source_type": "official_api",
    }


def fetch_all(window_hours: int = 168) -> list[dict]:
    """采集所有分类，去重，按时间过滤，返回 item 列表。"""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    seen_ids: set[str] = set()
    items: list[dict] = []

    for cat_id, (cat_name, label) in RULE_CATEGORIES.items():
        print(f"  采集 [{cat_name}]({cat_id})...")
        rules = fetch_category(cat_id)
        for rule in rules:
            item = rule_to_item(rule, cat_name, label)
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])

            # 时间过滤
            ts = rule.get("update_time", 0)
            if ts and datetime.fromtimestamp(ts, tz=timezone.utc) < cutoff:
                continue

            items.append(item)
        time.sleep(0.3)  # 礼貌延迟

    # 按更新时间降序
    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    print(f"  共采集 {len(items)} 条（7天内）")
    return items


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="抖音电商官方规则采集")
    parser.add_argument("--output", default="data/douyin-rules.json", help="输出文件路径")
    parser.add_argument("--window-hours", type=int, default=168, help="采集时间窗口（小时）")
    parser.add_argument("--test", action="store_true", help="快速测试，只采集第一个分类")
    args = parser.parse_args()

    print("抖音电商规则采集开始...")
    if args.test:
        rules = fetch_category("11693", page_size=5)
        print(f"规则动态 API 返回 {len(rules)} 条，前3条：")
        for r in rules[:3]:
            print(f"  [{datetime.fromtimestamp(r.get('update_time',0)).strftime('%Y-%m-%d')}] {r.get('title','')}")
            if r.get('summary'):
                print(f"    摘要: {r.get('summary','')[:80]}")
        return

    items = fetch_all(window_hours=args.window_hours)

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": "抖音电商学习中心",
            "total": len(items),
            "items": items,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入 {out_path}（{len(items)} 条）")


if __name__ == "__main__":
    main()
