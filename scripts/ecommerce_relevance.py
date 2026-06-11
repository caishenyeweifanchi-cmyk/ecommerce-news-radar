#!/usr/bin/env python3
"""Explainable ecommerce relevance scoring for news records."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

ECOMMERCE_KEYWORDS = [
    "ecommerce",
    "e-commerce",
    "retail",
    "marketplace",
    "shopify",
    "amazon",
    "tiktok shop",
    "temu",
    "shopee",
    "lazada",
    "aliexpress",
    "cross-border",
    "电商",
    "内容电商",
    "直播电商",
    "兴趣电商",
    "货架电商",
    "跨境电商",
    "零售",
    "平台",
    "商家",
    "卖家",
    "店铺",
    "选品",
    "爆品",
    "爆款",
    "带货",
    "直播带货",
    "达人带货",
    "短视频带货",
    "私域",
    "复购",
    "转化率",
    "客单价",
    "gmv",
    "roi",
    "roas",
    "投流",
    "千川",
    "巨量千川",
    "广告投放",
    "信息流广告",
    "素材",
    "种草",
    "小红书",
    "抖音电商",
    "快手电商",
    "淘宝",
    "天猫",
    "京东",
    "拼多多",
    "亚马逊",
    "速卖通",
    "阿里国际站",
    "独立站",
    "供应链",
    "物流",
    "仓储",
    "fba",
    "合规",
    "侵权",
    "关税",
    "支付",
]

PLATFORM_POLICY_KEYWORDS = [
    "规则",
    "政策",
    "公告",
    "治理",
    "处罚",
    "封禁",
    "保证金",
    "佣金",
    "费率",
    "类目",
    "入驻",
    "招商",
    "商家规则",
    "seller policy",
    "policy update",
]

MARKETING_KEYWORDS = [
    "营销",
    "增长",
    "品牌",
    "案例",
    "campaign",
    "kol",
    "koc",
    "influencer",
    "creator",
    "affiliate",
    "联盟营销",
    "达人",
    "蒲公英",
    "星图",
]

CROSS_BORDER_KEYWORDS = [
    "跨境",
    "出海",
    "海外",
    "关税",
    "海关",
    "物流",
    "fba",
    "tiktok shop",
    "amazon",
    "temu",
    "shopee",
    "lazada",
    "aliexpress",
    "shopify",
    "独立站",
]

NOISE_KEYWORDS = [
    "优惠券",
    "券后",
    "低价秒杀",
    "今日特价",
    "下单立减",
    "买一送一",
    "返利",
    "白菜价",
    "招聘",
    "求职",
    "租房",
    "彩票",
    "体育",
    "娱乐八卦",
]

ECOMMERCE_RELEVANCE_THRESHOLD = 0.65

SOURCE_PRIORS = {
    "opmlrss": 0.18,
    "xapi": 0.12,
    "agentmail": 0.12,
}

TRUSTED_SOURCE_HINTS = [
    "亿邦",
    "ebrun",
    "电商报",
    "电商派",
    "派代",
    "amz123",
    "雨果",
    "跨境",
    "seller",
    "merchant",
    "商家",
    "卖家",
    "tiktok shop",
    "amazon",
    "shopify",
]

LABEL_KEYWORDS = [
    ("cross_border", CROSS_BORDER_KEYWORDS),
    ("platform_policy", PLATFORM_POLICY_KEYWORDS),
    ("traffic_marketing", MARKETING_KEYWORDS + ["投流", "千川", "广告", "素材"]),
    ("content_commerce", ["内容电商", "直播电商", "种草", "小红书", "抖音", "快手", "带货", "达人"]),
    ("product_trend", ["选品", "爆品", "爆款", "新品", "趋势", "品类", "类目"]),
    ("supply_chain", ["供应链", "工厂", "仓储", "物流", "履约", "fba"]),
    ("retail_platform", ["淘宝", "天猫", "京东", "拼多多", "temu", "amazon", "shopify", "shopee", "lazada"]),
    ("industry_business", ["融资", "收购", "上市", "财报", "增长", "gmv", "营收"]),
]


def contains_any_keyword(haystack: str, keywords: list[str]) -> bool:
    h = haystack.lower()
    return any(k.lower() in h for k in keywords)


def matched_keywords(haystack: str, keywords: list[str]) -> list[str]:
    h = haystack.lower()
    return sorted({k for k in keywords if k.lower() in h})


def _label_for_text(text: str) -> str:
    for label, keywords in LABEL_KEYWORDS:
        if contains_any_keyword(text, keywords):
            return label
    return "ecommerce_general"


def _result(
    *,
    is_related: bool,
    score: float,
    label: str,
    reason: str,
    signals: list[str] | None = None,
    noise: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "is_ecommerce_related": bool(is_related),
        "score": round(max(0.0, min(1.0, score)), 2),
        "label": label,
        "reason": reason,
        "signals": signals or [],
        "noise": noise or [],
    }


def score_ecommerce_relevance(record: dict[str, Any]) -> dict[str, Any]:
    site_id = str(record.get("site_id") or "")
    title = str(record.get("title") or "")
    source = str(record.get("source") or "")
    site_name = str(record.get("site_name") or "")
    url = str(record.get("url") or "")
    try:
        url_host = (urlparse(url).netloc or "").lower()
    except Exception:
        url_host = ""
    text = f"{title} {source} {site_name} {url_host}".lower()

    ecommerce_signals = matched_keywords(text, ECOMMERCE_KEYWORDS)
    policy_signals = matched_keywords(text, PLATFORM_POLICY_KEYWORDS)
    marketing_signals = matched_keywords(text, MARKETING_KEYWORDS)
    cross_border_signals = matched_keywords(text, CROSS_BORDER_KEYWORDS)
    trusted_signals = matched_keywords(text, TRUSTED_SOURCE_HINTS)
    noise = matched_keywords(text, NOISE_KEYWORDS)
    source_prior = SOURCE_PRIORS.get(site_id, 0.0)

    if not (ecommerce_signals or policy_signals or marketing_signals or cross_border_signals or trusted_signals):
        return _result(
            is_related=False,
            score=source_prior,
            label="not_ecommerce",
            reason="missing_ecommerce_signal",
            signals=[],
            noise=noise,
        )

    score = source_prior
    score += min(0.5, 0.09 * len(ecommerce_signals))
    score += min(0.18, 0.06 * len(policy_signals))
    score += min(0.16, 0.05 * len(marketing_signals))
    score += min(0.18, 0.05 * len(cross_border_signals))
    score += min(0.22, 0.08 * len(trusted_signals))

    has_ecommerce_context = bool(ecommerce_signals or trusted_signals)
    strong_cross_border = bool(set(cross_border_signals) & {"tiktok shop", "amazon", "temu", "shopee", "lazada", "aliexpress", "shopify", "跨境", "跨境电商", "独立站"})
    if (cross_border_signals and (has_ecommerce_context or strong_cross_border)) or (policy_signals and has_ecommerce_context) or (marketing_signals and ecommerce_signals):
        score = max(score, ECOMMERCE_RELEVANCE_THRESHOLD)
    if noise and len(noise) > len(ecommerce_signals):
        score -= min(0.24, 0.06 * len(noise))

    is_related = score >= ECOMMERCE_RELEVANCE_THRESHOLD
    return _result(
        is_related=is_related,
        score=score,
        label=_label_for_text(text) if is_related else "weak_ecommerce_signal",
        reason="matched_ecommerce_signal" if is_related else "below_ecommerce_threshold",
        signals=ecommerce_signals + policy_signals + marketing_signals + cross_border_signals + trusted_signals,
        noise=noise,
    )


def is_ecommerce_related_record(record: dict[str, Any]) -> bool:
    return bool(score_ecommerce_relevance(record)["is_ecommerce_related"])


def add_ecommerce_relevance_fields(record: dict[str, Any]) -> dict[str, Any]:
    relevance = score_ecommerce_relevance(record)
    out = dict(record)
    out["ai_is_related"] = relevance["is_ecommerce_related"]
    out["ai_score"] = relevance["score"]
    out["ai_label"] = relevance["label"]
    out["ai_relevance_reason"] = relevance["reason"]
    out["ai_signals"] = relevance["signals"]
    out["ai_noise"] = relevance["noise"]
    out["topic"] = "ecommerce"
    out["topic_is_related"] = relevance["is_ecommerce_related"]
    out["topic_score"] = relevance["score"]
    out["topic_label"] = relevance["label"]
    return out
