#!/usr/bin/env python3
"""
llm_scorer.py — LLM 二次打分（MiniMax 主力 + Mimo 备用）

对关键词评分处于中间地带的条目调用 LLM 进行语义判断，
提升电商运营相关内容的识别准确率。MiniMax 失败时自动切换 Mimo。

用法:
  D:/python.exe scripts/llm_scorer.py --test
  D:/python.exe scripts/llm_scorer.py --file data/ai-radar.json
"""

from __future__ import annotations

import io
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

# ── API 配置 ──────────────────────────────────────────────────────────────
PROVIDERS = [
    {
        "name": "MiniMax",
        "url": "https://api.minimax.chat/v1/chat/completions",
        "model": "MiniMax-Text-01",
        "key_env": "MINIMAX_API_KEY",
        "key_dotenv": "MINIMAX_API_KEY",
    },
    {
        "name": "Mimo",
        "url": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "model": "mimo-v2.5-pro",
        "key_env": "MIMO_API_KEY",
        "key_dotenv": "MIMO_API_KEY",
    },
]

SYSTEM_PROMPT = """你是一个电商运营情报过滤器。
判断这条内容是否对「在抖音/小红书/淘宝/拼多多/亚马逊/TikTok Shop做电商的卖家或运营」有直接参考价值。

有价值的内容包括：
- 平台规则变化（新规、处罚、入驻、佣金、保证金）
- 投流/广告策略（千川、聚光、巨量、素材方向）
- 带货玩法（直播、短视频、种草、达人合作）
- 选品趋势（爆款、类目机会、竞品动态）
- AI工具提效（能直接用于电商素材、客服、选品、脚本的AI能力）
- 跨境政策（关税、合规、物流、收款）
- 运营技巧（转化、复购、私域、店铺经营）

无价值的内容：纯技术开发、通用科技新闻、学术研究、娱乐、与电商无关的社会话题。

只返回JSON，不要其他文字：
{"score": 0-10, "reason": "一句话说明判断依据", "label": "platform_policy/operations_playbook/ai_commerce/traffic_creative/extended_watch/irrelevant"}"""


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k in
                 {p["key_env"] for p in PROVIDERS}})
    return env


def _get_provider_key(provider: dict, env: dict[str, str]) -> str:
    return env.get(provider["key_env"], "") or env.get(provider["key_dotenv"], "")


def _call_api(provider: dict, api_key: str, messages: list[dict]) -> dict | None:
    payload = json.dumps({
        "model": provider["model"],
        "messages": messages,
        "max_tokens": 120,
        "temperature": 0.1,
    }).encode()
    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        provider["url"],
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, context=ctx, timeout=20)
    return json.loads(resp.read())


def score_item(item: dict[str, Any], env: dict[str, str]) -> dict[str, Any] | None:
    """用主力 API 打分，失败自动切换备用 API。返回 {score, reason, label} 或 None。"""
    title = item.get("title") or item.get("title_zh") or ""
    snippet = item.get("content_snippet") or ""
    text = f"标题：{title}"
    if snippet:
        text += f"\n摘要：{snippet[:300]}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    for provider in PROVIDERS:
        api_key = _get_provider_key(provider, env)
        if not api_key:
            continue
        for attempt in range(2):
            try:
                data = _call_api(provider, api_key, messages)
                reply = data["choices"][0]["message"]["content"].strip()
                if reply.startswith("```"):
                    reply = reply.split("```")[1]
                    if reply.startswith("json"):
                        reply = reply[4:]
                result = json.loads(reply.strip())
                return result
            except Exception:
                if attempt == 0:
                    time.sleep(1)
        print(f"  ⚠ {provider['name']} 失败，切换备用...")

    return None


def batch_score(
    items: list[dict[str, Any]],
    env: dict[str, str],
    *,
    low: float = 0.35,
    high: float = 0.70,
    delay: float = 0.25,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """对关键词分数在 [low, high] 模糊区间的条目调用 LLM 二次判断。"""
    scored = 0
    for item in items:
        kw_score = item.get("ai_score") or 0.0
        if kw_score < low or kw_score > high:
            continue

        result = score_item(item, env)
        if result is None:
            continue

        llm_score = result.get("score", 0)
        label = result.get("label", "irrelevant")
        reason = result.get("reason", "")

        item["llm_score"] = round(llm_score / 10, 2)
        item["llm_label"] = label
        item["llm_reason"] = reason

        if llm_score >= 6:
            item["ai_is_related"] = True
            item["ai_label"] = label
        else:
            item["ai_is_related"] = False
            item["ai_label"] = "irrelevant"

        scored += 1
        if verbose:
            print(f"  [{llm_score:2}/10] {label:20} {item.get('title','')[:50]}")

        time.sleep(delay)

    if verbose:
        print(f"LLM 二次打分完成：{scored}/{len(items)} 条")
    return items


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LLM 电商打分（MiniMax + Mimo 备用）")
    parser.add_argument("--test", action="store_true", help="内置样本测试")
    parser.add_argument("--file", help="对指定 JSON 文件批量打分")
    args = parser.parse_args()

    env = _load_env()

    available = [p["name"] for p in PROVIDERS if _get_provider_key(p, env)]
    if not available:
        print("错误：未找到任何 API Key（MINIMAX_API_KEY 或 MIMO_API_KEY）")
        sys.exit(1)
    print(f"可用 API：{', '.join(available)}")

    if args.test:
        samples = [
            {"title": "抖音电商2026达人带货新规：佣金结算缩短至7天", "ai_score": 0.5},
            {"title": "千川投流避坑：这5种素材正在被系统降权", "ai_score": 0.5},
            {"title": "拼多多保证金新规：违规扣款上限调至2000元", "ai_score": 0.5},
            {"title": "OpenAI发布GPT-5，推理能力大幅提升", "ai_score": 0.5},
            {"title": "微信多图合并展示功能上线", "ai_score": 0.5},
            {"title": "小红书种草笔记爆款公式：3个结构提升转化率40%", "ai_score": 0.5},
            {"title": "我为什么说AI时代不适合上班", "ai_score": 0.5},
            {"title": "百亿补贴的真相", "ai_score": 0.5},
        ]
        print(f"\n测试 {len(samples)} 条样本...\n")
        batch_score(samples, env, verbose=True)

    elif args.file:
        path = Path(args.file)
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        print(f"对 {len(items)} 条内容进行 LLM 二次打分...")
        batch_score(items, env, verbose=True)
        data["items"] = items
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写回 {path}")


if __name__ == "__main__":
    main()
