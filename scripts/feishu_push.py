#!/usr/bin/env python3
"""
feishu_push.py — 电商热点雷达飞书日报推送

用法:
  D:/python.exe scripts/feishu_push.py
  D:/python.exe scripts/feishu_push.py --chat-id oc_xxx  # 指定群
  D:/python.exe scripts/feishu_push.py --dry-run         # 仅打印不发送
  D:/python.exe scripts/feishu_push.py --top 8           # 推送条数(默认5)

配置 (项目根目录 .env 或环境变量):
  FEISHU_APP_ID=cli_xxx
  FEISHU_APP_SECRET=xxx
  FEISHU_CHAT_ID=oc_xxx
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

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


def load_items(top: int) -> list[dict]:
    """优先 daily-brief.json，不足则从 ai-radar.json 取最新条目。"""
    brief_path = DATA_DIR / "daily-brief.json"
    if brief_path.exists():
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        items = brief.get("items", [])
        if len(items) >= 3:
            return items[:top]

    radar_path = DATA_DIR / "ai-radar.json"
    if not radar_path.exists():
        return []
    radar = json.loads(radar_path.read_text(encoding="utf-8"))
    items = radar.get("items", [])
    items.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    items = [i for i in items if i.get("ai_label") != "not_ai"]
    return items[:top]


def build_card(items: list[dict], date_str: str) -> str:
    elements = []
    for idx, item in enumerate(items, 1):
        title = item.get("title_zh") or item.get("title") or "(无标题)"
        url = item.get("url") or item.get("primary_url") or ""
        label = label_text(item.get("ai_label") or "")
        impact = (
            item.get("impact")
            or item.get("suggested_action")
            or item.get("ai_relevance_reason")
            or ""
        )
        title_md = f"[{title}]({url})" if url else title
        impact_line = f"\n📌 {impact[:120]}" if impact and impact != "matched_ai_signal" else ""
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{idx}.** `{label}` **{title_md}**{impact_line}",
            },
        })
        if idx < len(items):
            elements.append({"tag": "hr"})

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"共 {len(items)} 条 · ecommerce-news-radar 自动生成"}],
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📡 电商热点雷达 · {date_str} 情报日报"},
            "template": "blue",
        },
        "elements": elements,
    }
    return json.dumps(card, ensure_ascii=False)


def build_text(items: list[dict], date_str: str) -> str:
    """纯文本备用格式。"""
    lines = [f"📡 电商热点雷达 · {date_str} 情报日报\n"]
    for idx, item in enumerate(items, 1):
        title = item.get("title_zh") or item.get("title") or "(无标题)"
        url = item.get("url") or item.get("primary_url") or ""
        label = label_text(item.get("ai_label") or "")
        lines.append(f"{idx}. [{label}] {title}")
        if url:
            lines.append(f"   {url}")
        lines.append("")
    lines.append(f"共 {len(items)} 条  |  ecommerce-news-radar 自动生成")
    return "\n".join(lines)


def send_message(client: lark.Client, chat_id: str, content: str, msg_type: str) -> str:
    """发送消息，返回 message_id。"""
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type(msg_type)
            .content(content)
            .build()
        )
        .build()
    )
    resp = client.im.v1.message.create(req)
    if not resp.success():
        raise RuntimeError(
            f"飞书推送失败 code={resp.code} msg={resp.msg} "
            f"log_id={resp.get_log_id()}"
        )
    return resp.data.message_id


def main() -> None:
    parser = argparse.ArgumentParser(description="飞书日报推送")
    parser.add_argument("--chat-id", help="飞书 chat_id (覆盖 .env)")
    parser.add_argument("--top", type=int, default=5, help="推送条数 (默认5)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不发送")
    args = parser.parse_args()

    env = load_env()
    chat_id = args.chat_id or env.get("FEISHU_CHAT_ID", "")
    app_id = env.get("FEISHU_APP_ID", "")
    app_secret = env.get("FEISHU_APP_SECRET", "")

    items = load_items(args.top)
    if not items:
        print("无可推送内容（ai-radar.json 和 daily-brief.json 均无有效条目）。")
        sys.exit(0)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.dry_run:
        print(build_text(items, date_str))
        return

    if not chat_id:
        print("错误：未指定 chat_id。在 .env 设置 FEISHU_CHAT_ID 或用 --chat-id。")
        sys.exit(1)
    if not app_id or not app_secret:
        print("错误：.env 缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET。")
        sys.exit(1)

    client = (
        lark.Client.builder()
        .app_id(app_id)
        .app_secret(app_secret)
        .log_level(lark.LogLevel.ERROR)
        .build()
    )

    print(f"推送 {len(items)} 条情报到 {chat_id} ...")
    card_content = build_card(items, date_str)
    try:
        msg_id = send_message(client, chat_id, card_content, "interactive")
    except RuntimeError:
        # 卡片失败则降级为文本
        text_content = json.dumps({"text": build_text(items, date_str)}, ensure_ascii=False)
        msg_id = send_message(client, chat_id, text_content, "text")
    print(f"✓ 推送成功  message_id={msg_id}")


if __name__ == "__main__":
    main()
