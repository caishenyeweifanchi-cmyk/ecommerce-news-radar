#!/usr/bin/env python3
"""
xhs_fetcher.py — 小红书电商学习中心官方规则采集

调用小红书电商学院内部 JSON API，无需登录，无需 headless 浏览器。
采集：新规通知(NEW_RULE)、公示中(PUBLIC)、意见征集(OPINION)。

用法:
  D:/python.exe scripts/xhs_fetcher.py
  D:/python.exe scripts/xhs_fetcher.py --output data/xhs-rules.json
  D:/python.exe scripts/xhs_fetcher.py --test
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent

API_BASE = "https://school.xiaohongshu.com"
DETAIL_BASE = "https://school.xiaohongshu.com/rule/detail/{article_id}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://school.xiaohongshu.com/rule",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# columnType → (中文名, ai_label)
COLUMN_TYPES = {
    "NEW_RULE": ("新规通知", "platform_policy"),
    "PUBLIC":   ("公示公告", "platform_policy"),
    "OPINION":  ("意见征集", "platform_policy"),
}

CTX = ssl.create_default_context()


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(API_BASE + path, data=data, headers=HEADERS, method="POST")
    resp = urllib.request.urlopen(req, context=CTX, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


def parse_date(date_str: str) -> str:
    """把 '2026年06月14日' 转成 ISO 8601 字符串（CST+8）。"""
    if not date_str:
        return datetime.now(tz=timezone(timedelta(hours=8))).isoformat()
    try:
        dt = datetime.strptime(date_str, "%Y年%m月%d日")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        return dt.isoformat()
    except Exception:
        return datetime.now(tz=timezone(timedelta(hours=8))).isoformat()


def article_to_item(article: dict, col_name: str, label: str) -> dict:
    article_id = article.get("articleId", "")
    title = article.get("title", "").strip()
    create_time = article.get("createTime", "")
    publish_start = article.get("publishStartTime", "")

    date_str = publish_start or create_time
    published = parse_date(date_str)

    return {
        "id": f"xhs_rule_{article_id}",
        "title": title,
        "title_zh": title,
        "url": DETAIL_BASE.format(article_id=article_id),
        "published": published,
        "source": f"小红书电商·{col_name}",
        "site_name": "小红书电商学习中心",
        "site_id": "xhs_school",
        "content_snippet": "",
        "summary_zh": None,
        "ai_label": label,
        "ai_is_related": True,
        "ai_score": 0.85,
        "llm_label": label,
        "llm_score": 0.85,
        "source_type": "official_api",
    }


def fetch_column(col_type: str, col_name: str, label: str, page_size: int = 20) -> list[dict]:
    try:
        r = post(
            "/api/edith/governance/inform/rule/query_article_list_by_column",
            {"pageNo": 1, "pageSize": page_size, "columnType": col_type},
        )
        articles = r.get("data", {}).get("dataList", [])
        return [article_to_item(a, col_name, label) for a in articles]
    except Exception as e:
        print(f"  [{col_type}] 采集失败: {e}")
        return []


def fetch_all(window_hours: int = 168) -> list[dict]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
    all_items: list[dict] = []
    seen_ids: set[str] = set()

    for col_type, (col_name, label) in COLUMN_TYPES.items():
        print(f"  采集小红书 {col_name}({col_type})...")
        items = fetch_column(col_type, col_name, label, page_size=20)

        filtered = []
        for item in items:
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            try:
                pub_dt = datetime.fromisoformat(item["published"])
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt.astimezone(timezone.utc) < cutoff:
                    continue
            except Exception:
                pass
            filtered.append(item)

        print(f"    → {len(filtered)} 条（{window_hours//24}天内）")
        all_items.extend(filtered)
        time.sleep(0.5)

    all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return all_items


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="小红书电商官方规则采集")
    parser.add_argument("--output", default="data/xhs-rules.json")
    parser.add_argument("--window-hours", type=int, default=168)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    print("小红书电商规则采集开始...")

    if args.test:
        r = post("/api/edith/governance/inform/rule/query_article_list_by_column",
                 {"pageNo": 1, "pageSize": 5, "columnType": "NEW_RULE"})
        lst = r.get("data", {}).get("dataList", [])
        print(f"NEW_RULE API 返回 {len(lst)} 条:")
        for a in lst:
            print(f"  [{a.get('articleId')}] {a.get('title')} ({a.get('createTime')})")
        return

    items = fetch_all(window_hours=args.window_hours)

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": "小红书电商学习中心",
            "total": len(items),
            "items": items,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已写入 {out_path}（{len(items)} 条）")


if __name__ == "__main__":
    main()
