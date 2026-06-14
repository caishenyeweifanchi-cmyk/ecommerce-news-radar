#!/usr/bin/env python3
"""
feishu_alert.py — 精选条目实时推送

每次采集后调用，检查 latest-24h.json 里有哪些条目是新进入精选的，
每条单独推一张卡片到飞书。已推过的记录在 data/feishu-pushed.json，不重复推。

用法:
  D:/python.exe scripts/feishu_alert.py
  D:/python.exe scripts/feishu_alert.py --dry-run
"""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
PUSHED_STATE = DATA_DIR / "feishu-pushed.json"

LABEL_MAP = {
    "platform_policy": "平台规则",
    "operations_playbook": "运营玩法",
    "ai_commerce": "AI电商",
    "traffic_creative": "投流素材",
    "extended_watch": "扩展观察",
    "ai_general": "AI动态",
    "model_release": "模型发布",
    "agent_workflow": "Agent工作流",
    "ai_product_update": "AI产品更新",
    "industry_business": "行业商业",
}

LABEL_COLOR = {
    "platform_policy": "red",
    "operations_playbook": "green",
    "ai_commerce": "blue",
    "traffic_creative": "orange",
    "model_release": "purple",
    "ai_product_update": "purple",
}


def label_text(label: str) -> str:
    return LABEL_MAP.get(label, label or "情报")


def load_env() -> dict:
    env_path = ROOT / ".env"
    env: dict = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def load_pushed() -> set[str]:
    if PUSHED_STATE.exists():
        data = json.loads(PUSHED_STATE.read_text(encoding="utf-8"))
        return set(data.get("ids", []))
    return set()


def save_pushed(ids: set[str]) -> None:
    PUSHED_STATE.write_text(
        json.dumps({"ids": sorted(ids), "updated_at": datetime.now(timezone.utc).isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_picks() -> list[dict]:
    """从 latest-24h.json 取精选条目。"""
    path = DATA_DIR / "latest-24h.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("items", [])


def build_alert_card(item: dict) -> str:
    title = item.get("title_zh") or item.get("title") or "(无标题)"
    url = item.get("url") or item.get("primary_url") or ""
    label = item.get("ai_label") or ""
    label_name = label_text(label)
    color = LABEL_COLOR.get(label, "blue")

    impact = item.get("impact") or item.get("ai_relevance_reason") or ""
    if impact == "matched_ai_signal":
        impact = ""
    action = item.get("suggested_action") or ""
    source = item.get("source") or item.get("site_name") or ""

    body_lines = []
    if impact:
        body_lines.append(f"📌 **影响** {impact[:150]}")
    if action:
        body_lines.append(f"💡 **建议** {action[:120]}")
    if source:
        body_lines.append(f"📰 来源：{source}")
    body_md = "\n".join(body_lines) if body_lines else "点击标题查看原文"

    elements = [
        {
            "tag": "div",
            "text": {"tag": "lark_md", "content": body_md},
        },
    ]

    if url:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看原文 →"},
                "type": "default",
                "url": url,
            }],
        })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"[{label_name}] {title}"},
            "template": color,
        },
        "elements": elements,
    }
    return json.dumps(card, ensure_ascii=False)


def send_card(client: lark.Client, chat_id: str, card_content: str) -> str:
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("interactive")
            .content(card_content)
            .build()
        )
        .build()
    )
    resp = client.im.v1.message.create(req)
    if not resp.success():
        raise RuntimeError(f"推送失败 code={resp.code} msg={resp.msg}")
    return resp.data.message_id


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="精选实时推送")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不发送")
    args = parser.parse_args()

    env = load_env()
    chat_id = env.get("FEISHU_CHAT_ID", "")
    app_id = env.get("FEISHU_APP_ID", "")
    app_secret = env.get("FEISHU_APP_SECRET", "")

    picks = load_picks()
    if not picks:
        print("精选列表为空，跳过。")
        return

    pushed = load_pushed()
    new_items = [i for i in picks if i.get("id") and i["id"] not in pushed]

    if not new_items:
        print(f"精选共 {len(picks)} 条，全部已推过，跳过。")
        return

    print(f"新进精选 {len(new_items)} 条，开始推送...")

    if args.dry_run:
        for item in new_items:
            title = item.get("title_zh") or item.get("title") or ""
            label = label_text(item.get("ai_label") or "")
            print(f"  [dry-run] [{label}] {title[:60]}")
        return

    if not chat_id or not app_id or not app_secret:
        print("错误：.env 缺少 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID")
        sys.exit(1)

    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.ERROR)
        .build()
    )

    newly_pushed: set[str] = set()
    for item in new_items:
        title = item.get("title_zh") or item.get("title") or ""
        label = label_text(item.get("ai_label") or "")
        try:
            card = build_alert_card(item)
            msg_id = send_card(client, chat_id, card)
            pushed.add(item["id"])
            newly_pushed.add(item["id"])
            print(f"  ✓ [{label}] {title[:50]}  msg={msg_id}")
        except Exception as e:
            print(f"  ✗ [{label}] {title[:50]}  错误: {e}")

    save_pushed(pushed)
    print(f"完成，本次推送 {len(newly_pushed)} 条，累计记录 {len(pushed)} 条。")


if __name__ == "__main__":
    main()
