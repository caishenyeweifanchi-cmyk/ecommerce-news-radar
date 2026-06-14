#!/usr/bin/env python3
"""把抖音/小红书官方规则条目合并进 latest-24h.json。"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
news_path = ROOT / "data" / "latest-24h.json"

if not news_path.exists():
    print("Skip: latest-24h.json missing")
    sys.exit(0)

news = json.loads(news_path.read_text(encoding="utf-8"))
news.setdefault("items", [])
news.setdefault("items_ai", [])

existing_ids = {i.get("id") for i in news["items"]}
total_added = 0

for fname in ["data/douyin-rules.json", "data/xhs-rules.json"]:
    src = ROOT / fname
    if not src.exists():
        print(f"Skip {fname}: not found")
        continue
    d = json.loads(src.read_text(encoding="utf-8"))
    new_items = d.get("items", [])
    to_add = [i for i in new_items if i.get("id") not in existing_ids]
    if not to_add:
        print(f"{fname}: 无新条目")
        continue
    for i in to_add:
        existing_ids.add(i["id"])
    news["items"] = to_add + news["items"]
    ai_ids = {i.get("id") for i in news["items_ai"]}
    news["items_ai"] = [i for i in to_add if i.get("id") not in ai_ids] + news["items_ai"]
    print(f"{fname}: 合并 {len(to_add)} 条")
    total_added += len(to_add)

news_path.write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"合并完成，共新增 {total_added} 条")
