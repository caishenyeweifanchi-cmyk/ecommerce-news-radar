#!/usr/bin/env python3
"""
llm_scorer.py — MiniMax LLM 二次打分

对关键词评分处于中间地带的条目调用 MiniMax API 进行语义判断，
提升电商运营相关内容的识别准确率。

用法（主要由 update_news.py 调用，也可单独测试）:
  D:/python.exe scripts/llm_scorer.py --test
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

MINIMAX_API_URL = "https://api.minimax.chat/v1/chat/completions"
MINIMAX_MODEL = "MiniMax-Text-01"

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


def _get_api_key() -> str:
    key = os.environ.get("MINIMAX_API_KEY", "")
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MINIMAX_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def score_item(item: dict[str, Any], api_key: str, retry: int = 2) -> dict[str, Any] | None:
    """调用 MiniMax 对单条内容打分，返回 {score, reason, label} 或 None（失败）。"""
    title = item.get("title") or item.get("title_zh") or ""
    snippet = item.get("content_snippet") or ""
    text = f"标题：{title}"
    if snippet:
        text += f"\n摘要：{snippet[:300]}"

    payload = json.dumps({
        "model": MINIMAX_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "max_tokens": 120,
        "temperature": 0.1,
    }).encode()

    ctx = ssl.create_default_context()
    for attempt in range(retry + 1):
        try:
            req = urllib.request.Request(
                MINIMAX_API_URL,
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp = urllib.request.urlopen(req, context=ctx, timeout=20)
            data = json.loads(resp.read())
            reply = data["choices"][0]["message"]["content"].strip()
            # 兼容模型有时在 JSON 外包一层 ```json ... ```
            if reply.startswith("```"):
                reply = reply.split("```")[1]
                if reply.startswith("json"):
                    reply = reply[4:]
            return json.loads(reply.strip())
        except Exception:
            if attempt < retry:
                time.sleep(1 + attempt)
    return None


def batch_score(
    items: list[dict[str, Any]],
    api_key: str,
    *,
    keyword_score_field: str = "ai_score",
    low: float = 0.35,
    high: float = 0.70,
    delay: float = 0.25,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """
    对关键词分数在 [low, high] 模糊区间的条目调用 LLM 二次判断。
    明确低分（<low）直接标 irrelevant，明确高分（>high）保持原判。
    返回更新后的 items 列表。
    """
    scored = 0
    for item in items:
        kw_score = item.get(keyword_score_field) or 0.0
        if kw_score < low:
            # 关键词已明确低分，直接跳过（保持 irrelevant）
            continue
        if kw_score > high:
            # 关键词已明确高分，信任关键词结果
            continue

        result = score_item(item, api_key)
        if result is None:
            continue

        llm_score = result.get("score", 0)
        label = result.get("label", "irrelevant")
        reason = result.get("reason", "")

        # LLM 分 0-10 → 归一化到 0-1
        item["llm_score"] = round(llm_score / 10, 2)
        item["llm_label"] = label
        item["llm_reason"] = reason

        # 用 LLM 结论覆盖关键词打分
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
        print(f"LLM 二次打分完成：{scored} 条")
    return items


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="MiniMax LLM 电商打分测试")
    parser.add_argument("--test", action="store_true", help="用内置样本测试")
    parser.add_argument("--file", help="对指定 JSON 文件（ai-radar.json 格式）批量打分")
    args = parser.parse_args()

    api_key = _get_api_key()
    if not api_key:
        print("错误：未找到 MINIMAX_API_KEY（.env 或环境变量）")
        sys.exit(1)

    if args.test:
        samples = [
            {"title": "抖音电商2026达人带货新规：佣金结算缩短至7天"},
            {"title": "千川投流避坑：这5种素材正在被系统降权"},
            {"title": "拼多多保证金新规：违规扣款上限调至2000元"},
            {"title": "OpenAI发布GPT-5，推理能力大幅提升"},
            {"title": "微信多图合并展示功能上线"},
            {"title": "我为什么说AI时代不适合上班"},
            {"title": "小红书种草笔记爆款公式：3个结构提升转化率40%"},
            {"title": "百亿补贴的真相"},
        ]
        # 给所有样本设中间分触发 LLM
        for s in samples:
            s["ai_score"] = 0.5
        print(f"测试 {len(samples)} 条样本...\n")
        batch_score(samples, api_key, verbose=True)

    elif args.file:
        path = Path(args.file)
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        print(f"对 {len(items)} 条内容进行 LLM 二次打分...")
        batch_score(items, api_key, verbose=True)
        data["items"] = items
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写回 {path}")


if __name__ == "__main__":
    main()
