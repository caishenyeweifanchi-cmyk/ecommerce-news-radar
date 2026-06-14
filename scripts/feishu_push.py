#!/usr/bin/env python3
"""
feishu_push.py — 电商热点雷达飞书日报推送

将 ai-radar.json / daily-brief.json 的热点内容推送到飞书群。

用法:
  D:/python.exe scripts/feishu_push.py
  D:/python.exe scripts/feishu_push.py --chat-id oc_xxx    # 指定群
  D:/python.exe scripts/feishu_push.py --dry-run           # 仅打印不发送
  D:/python.exe scripts/feishu_push.py --top 8             # 推送条数(默认5)

配置:
  在项目根目录 .env 中设置:
    FEISHU_APP_ID=cli_xxx
    FEISHU_APP_SECRET=xxx
    FEISHU_CHAT_ID=oc_xxx   (也可用 --chat-id 覆盖)
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# ── Label display map ──────────────────────────────────────────────
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
    "not_ai": "其他",
}

def label_text(label: str) -> str:
    return LABEL_MAP.get(label, label or "情报")


# ── Env / config ──────────────────────────────────────────────────
def load_env() -> dict:
    env_path = ROOT / ".env"
    env: dict = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    # override with process env
    for key in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_CHAT_ID"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


# ── Feishu HTTP helpers ────────────────────────────────────────────
def feishu_post(path: str, body: dict, token: str) -> dict:
    url = f"https://open.feishu.cn/open-apis{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_tenant_token(app_id: str, app_secret: str) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = {"app_id": app_id, "app_secret": app_secret}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {result}")
    return result["tenant_access_token"]


# ── Data loading ───────────────────────────────────────────────────
def load_items(top: int) -> list[dict]:
    """优先用 daily-brief.json，无内容则从 ai-radar.json 取最新 top 条。"""
    brief_path = DATA_DIR / "daily-brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8")) if brief_path.exists() else {}
    brief_items = brief.get("items", [])
    if len(brief_items) >= 3:
        return brief_items[:top]

    radar_path = DATA_DIR / "ai-radar.json"
    if not radar_path.exists():
        return []
    radar = json.loads(radar_path.read_text(encoding="utf-8"))
    items = radar.get("items", [])
    # sort by published_at descending, then ai_score
    items.sort(
        key=lambda x: (x.get("published_at") or "", x.get("ai_score") or 0),
        reverse=True,
    )
    # exclude not_ai
    items = [i for i in items if i.get("ai_label") != "not_ai"]
    return items[:top]


# ── Message formatting ─────────────────────────────────────────────
def format_card(items: list[dict], date_str: str) -> dict:
    """Build a Feishu interactive card message."""
    elements: list[dict] = []

    for idx, item in enumerate(items, 1):
        title = item.get("title_zh") or item.get("title") or "(无标题)"
        url = item.get("url") or item.get("primary_url") or ""
        label = label_text(item.get("ai_label") or "")
        impact = item.get("impact") or item.get("ai_relevance_reason") or ""
        action = item.get("suggested_action") or ""

        # Title line with link
        title_element = {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{idx}. [{title}]({url})**" if url else f"**{idx}. {title}**",
            },
        }
        elements.append(title_element)

        # Tag + impact
        sub_lines = [f"🏷 `{label}`"]
        if impact:
            sub_lines.append(f"📌 {impact[:100]}")
        if action:
            sub_lines.append(f"💡 {action[:80]}")

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "  \n".join(sub_lines),
            },
        })

        if idx < len(items):
            elements.append({"tag": "hr"})

    card = {
        "schema": "2.0",
        "body": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"## 📡 电商热点雷达 · {date_str} 情报日报",
                },
                {"tag": "hr"},
                *elements,
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"共 {len(items)} 条 · 由 ecommerce-news-radar 自动生成",
                    },
                },
            ]
        },
    }
    return card


def format_text(items: list[dict], date_str: str) -> str:
    """Fallback: plain text message."""
    lines = [f"📡 电商热点雷达 · {date_str} 情报日报\n"]
    for idx, item in enumerate(items, 1):
        title = item.get("title_zh") or item.get("title") or "(无标题)"
        url = item.get("url") or item.get("primary_url") or ""
        label = label_text(item.get("ai_label") or "")
        impact = item.get("impact") or item.get("ai_relevance_reason") or ""
        lines.append(f"{idx}. [{label}] {title}")
        if url:
            lines.append(f"   {url}")
        if impact:
            lines.append(f"   📌 {impact[:100]}")
        lines.append("")
    lines.append(f"共 {len(items)} 条 · ecommerce-news-radar")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="飞书日报推送")
    parser.add_argument("--chat-id", help="飞书 chat_id (覆盖 .env 中的 FEISHU_CHAT_ID)")
    parser.add_argument("--top", type=int, default=5, help="推送条数 (默认5)")
    parser.add_argument("--dry-run", action="store_true", help="仅打印消息体，不发送")
    parser.add_argument("--text", action="store_true", help="使用纯文本格式(而非卡片)")
    args = parser.parse_args()

    env = load_env()
    chat_id = args.chat_id or env.get("FEISHU_CHAT_ID", "")
    app_id = env.get("FEISHU_APP_ID", "")
    app_secret = env.get("FEISHU_APP_SECRET", "")

    if not chat_id and not args.dry_run:
        print("错误：未指定 chat_id。请在 .env 中设置 FEISHU_CHAT_ID 或用 --chat-id 参数。")
        sys.exit(1)

    items = load_items(args.top)
    if not items:
        print("无可推送内容（ai-radar.json 和 daily-brief.json 均为空）。")
        sys.exit(0)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.text or args.dry_run:
        msg_text = format_text(items, date_str)
        print(msg_text)
        if args.dry_run:
            return

    # Build card message
    card = format_card(items, date_str)
    card_json = json.dumps(card, ensure_ascii=False)
    content_json = json.dumps({"type": "template", "data": card}, ensure_ascii=False)

    # Try card first, fall back to text
    if args.text:
        msg_type = "text"
        content = json.dumps({"text": format_text(items, date_str)}, ensure_ascii=False)
    else:
        msg_type = "interactive"
        content = card_json

    if args.dry_run:
        print("[dry-run] card JSON:\n", card_json[:2000])
        return

    if not app_id or not app_secret:
        print("错误：.env 中缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET。")
        sys.exit(1)

    print(f"获取 tenant_access_token...")
    token = get_tenant_token(app_id, app_secret)

    print(f"推送 {len(items)} 条情报到 {chat_id}...")
    result = feishu_post(
        "/im/v1/messages",
        {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": content,
        },
        token,
    )

    if result.get("code") == 0:
        msg_id = result.get("data", {}).get("message_id", "")
        print(f"✓ 推送成功！message_id={msg_id}")
    else:
        # try text fallback
        print(f"卡片推送失败 (code={result.get('code')})，尝试文本格式...")
        text_content = json.dumps({"text": format_text(items, date_str)}, ensure_ascii=False)
        result2 = feishu_post(
            "/im/v1/messages",
            {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": text_content,
            },
            token,
        )
        if result2.get("code") == 0:
            print(f"✓ 文本推送成功！")
        else:
            print(f"✗ 推送失败: {result2}")
            sys.exit(1)


if __name__ == "__main__":
    main()
