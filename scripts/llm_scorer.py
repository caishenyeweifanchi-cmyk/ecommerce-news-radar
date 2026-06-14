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

PROMPT_VERSION = "ecommerce-intel-v2"

SYSTEM_PROMPT = """你是一个电商运营情报分析师，标准极严。
只分析对「在抖音/小红书/淘宝/拼多多/亚马逊/TikTok Shop做电商的卖家或运营」有直接实操价值的内容。

【8-10分】直接影响运营决策，必看：
- 平台规则新规/处罚/封号/佣金/保证金变化
- 千川/聚光/巨量投流策略变化、素材审核政策
- 带货直播/短视频运营具体玩法、转化技巧
- 选品爆款、类目供需机会、竞品动态
- 能直接生成电商素材、商品图、广告视频、商品描述、客服话术、选品分析、竞品分析、运营 SOP 的 AI 能力或工具
- 跨境关税、合规、物流、收款政策变化

【5-7分】有参考价值但不紧迫：
- 平台生态变化、行业整体趋势
- 通用运营方法论（非平台特定）
- 电商相关企业融资/战略动态
- AI 模型、Agent、多模态、图像/视频生成、自动化能力变化，但只能间接迁移到电商

【1-4分】与电商运营无直接关系，不应进入精选：
- AI 公司融资、上市、收购、内部组织新闻
- AI 模型能力测评、技术突破（如果无法映射到素材、投流、选品、客服、竞品分析、自动化运营）
- Agent 开发、编程工具、代码框架
- 通用科技产品发布（学习工具、生产力工具、非电商场景）
- 企业管理、社会热点、财经宏观

判断关键：
1. 这条信息能不能帮助电商运营、内容生产、投流、选品、店铺经营或自动化提效？
2. 如果是 AI 新闻，必须先完成映射：模型能力 → 可迁移能力 → 电商使用场景 → 是否值得运营关注。
3. 如果说不出具体电商使用场景，只能给低分，不能为了“AI 热点”而高分。

只返回JSON，不要其他文字：
{
  "score": 0-10,
  "label": "platform_policy/operations_playbook/ai_commerce/traffic_creative/extended_watch/irrelevant",
  "summary_zh": "1-2句中文摘要，说清楚这条内容讲了什么（英文内容需翻译成中文）",
  "impact_zh": "score>=7时必填：对电商卖家/运营的直接影响是什么，20字以内，否则填空字符串",
  "ecommerce_use_case": "能用于什么电商场景；没有直接场景则填空字符串",
  "suggested_action": "score>=7时给一个具体建议动作，30字以内；否则填空字符串"
}"""


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
        "max_tokens": 320,
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


def item_cache_key(item: dict[str, Any]) -> str:
    """Return a stable key for in-run LLM result reuse across duplicated arrays."""
    for key in ("id", "url", "link"):
        value = str(item.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    title = str(item.get("title") or item.get("title_zh") or "").strip()
    source = str(item.get("source") or item.get("site_name") or "").strip()
    return f"title:{source}:{title}"


def has_current_llm_enrichment(item: dict[str, Any]) -> bool:
    """Skip already enriched items unless the prompt version changes."""
    return (
        item.get("llm_prompt_version") == PROMPT_VERSION
        and bool(item.get("summary_zh"))
        and bool(item.get("llm_score") is not None)
    )


def coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(10.0, score))


def score_item(item: dict[str, Any], env: dict[str, str]) -> dict[str, Any] | None:
    """用主力 API 打分，失败自动切换备用 API。返回 {score, reason, label} 或 None。"""
    title = item.get("title") or item.get("title_zh") or ""
    snippet = (
        item.get("content_snippet")
        or item.get("summary")
        or item.get("summary_zh")
        or item.get("description")
        or ""
    )
    text = f"标题：{title}"
    if snippet:
        text += f"\n摘要：{snippet[:300]}"
    source = item.get("source") or item.get("site_name") or ""
    if source:
        text += f"\n来源：{source}"

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
    preserve_ai_membership: bool = False,
    result_cache: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """对关键词分数在 [low, high] 模糊区间的条目调用 LLM 二次判断。"""
    scored = 0
    skipped = 0
    result_cache = result_cache if result_cache is not None else {}
    for item in items:
        kw_score = item.get("ai_score") or 0.0
        needs_enrichment = not has_current_llm_enrichment(item)
        in_fuzzy_zone = low <= kw_score <= high
        high_value_without_summary = kw_score > high and needs_enrichment
        if kw_score < low or not (in_fuzzy_zone or high_value_without_summary):
            skipped += 1
            continue

        cache_key = item_cache_key(item)
        result = result_cache.get(cache_key)
        if result is None:
            result = score_item(item, env)
            if result is not None:
                result_cache[cache_key] = result
        if result is None:
            continue

        llm_score = coerce_score(result.get("score", 0))
        label = str(result.get("label") or "irrelevant").strip() or "irrelevant"
        reason = result.get("reason", "")

        item["llm_score"] = round(llm_score / 10, 2)
        item["llm_label"] = label
        item["llm_prompt_version"] = PROMPT_VERSION
        item["ecommerce_relevance_score"] = round(llm_score / 10, 2)
        item["ecommerce_label"] = label

        summary_zh = str(result.get("summary_zh") or "").strip()
        impact_zh = str(result.get("impact_zh") or "").strip()
        ecommerce_use_case = str(result.get("ecommerce_use_case") or "").strip()
        suggested_action = str(result.get("suggested_action") or "").strip()
        if summary_zh:
            item["summary_zh"] = summary_zh
        if impact_zh:
            item["impact_zh"] = impact_zh
        if ecommerce_use_case:
            item["ecommerce_use_case"] = ecommerce_use_case
            item["business_value"] = ecommerce_use_case
        if suggested_action:
            item["suggested_action"] = suggested_action

        if llm_score >= 7:
            item["ai_commerce_eligible"] = True
            if not preserve_ai_membership:
                item["ai_is_related"] = True
                item["ai_label"] = label
            if impact_zh:
                item["impact"] = impact_zh
        else:
            item["ai_commerce_eligible"] = False
            if not preserve_ai_membership:
                item["ai_is_related"] = False
                item["ai_label"] = "irrelevant"

        scored += 1
        if verbose:
            print(f"  [{llm_score:2}/10] {label:20} {item.get('title','')[:50]}")

        time.sleep(delay)

    if verbose:
        print(f"LLM 二次打分完成：{scored}/{len(items)} 条，跳过 {skipped} 条")
    return items


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LLM 电商打分（MiniMax + Mimo 备用）")
    parser.add_argument("--test", action="store_true", help="内置样本测试")
    parser.add_argument("--file", help="对指定 JSON 文件批量打分")
    parser.add_argument(
        "--preserve-ai-membership",
        action="store_true",
        help="只补充电商价值字段，不把低电商价值条目从 AI 情报池移除",
    )
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
        preserve_ai_membership = (
            args.preserve_ai_membership
            or path.name == "ai-radar.json"
            or str(data.get("topic") or "").lower() == "ai"
        )
        result_cache: dict[str, dict[str, Any]] = {}
        # Score all item arrays in the file (items, items_ai, items_all, etc.)
        # so summary_zh/impact_zh propagate to whichever array the frontend reads.
        scored_any = False
        for key in ("items_ai", "items", "items_all", "items_all_raw"):
            arr = data.get(key)
            if not isinstance(arr, list) or not arr:
                continue
            print(f"对 {key}({len(arr)} 条) 进行 LLM 二次打分...")
            batch_score(
                arr,
                env,
                verbose=True,
                preserve_ai_membership=preserve_ai_membership,
                result_cache=result_cache,
            )
            data[key] = arr
            scored_any = True
        if not scored_any:
            print("文件中未找到可打分的条目列表")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写回 {path}")


if __name__ == "__main__":
    main()
