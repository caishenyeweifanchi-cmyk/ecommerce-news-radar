#!/usr/bin/env python3
"""Explainable ecommerce operations relevance scoring for news records."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

ECOMMERCE_RELEVANCE_THRESHOLD = 0.62

CORE_SCENE_KEYWORDS = [
    "电商",
    "商家",
    "卖家",
    "店铺",
    "商品",
    "带货",
    "直播",
    "直播带货",
    "短视频",
    "短视频带货",
    "种草",
    "选品",
    "爆款",
    "爆品",
    "投流",
    "素材",
    "转化",
    "gmv",
    "roi",
    "roas",
    "客服",
    "私域",
    "复购",
    "达人",
    "平台规则",
    "规则中心",
    "商家规则",
    "千川",
    "聚光",
    "蒲公英",
    "星图",
    "小红书",
    "抖音电商",
    "快手电商",
    "淘宝",
    "天猫",
    "京东",
    "拼多多",
    "微信小店",
    "tiktok shop",
    "amazon seller",
    "seller central",
    "shopify",
    "temu",
    "shopee",
    "lazada",
    "跨境",
    "物流",
    "履约",
    "收款",
    "关税",
]

VALUE_KEYWORDS = {
    "platform_policy": [
        "规则",
        "政策",
        "公告",
        "公示",
        "治理",
        "处罚",
        "违规",
        "保证金",
        "佣金",
        "费率",
        "类目",
        "入驻",
        "招商",
        "履约",
        "售后",
        "准入",
        "结算",
    ],
    "operations_playbook": [
        "玩法",
        "案例",
        "拆解",
        "运营",
        "店播",
        "达人",
        "种草",
        "私域",
        "复购",
        "活动",
        "直播间",
        "内容电商",
        "短视频带货",
    ],
    "ai_commerce": [
        "aigc",
        "openai",
        "claude",
        "gemini",
        "deepseek",
        "gpt",
        "openai",
        "anthropic",
        "deepmind",
        "hugging face",
        "github ai",
        "nvidia",
        "agent",
        "智能体",
        "多模态",
        "图像生成",
        "视频生成",
        "image generation",
        "video generation",
        "product image",
        "product photo",
        "ad creative",
        "advertising creative",
        "customer support",
        "shopping assistant",
        "browser automation",
        "商品图",
        "广告素材",
        "脚本",
        "客服",
        "自动化",
        "竞品分析",
    ],
    "traffic_creative": [
        "投流",
        "千川",
        "巨量",
        "广告",
        "信息流",
        "素材",
        "转化",
        "roi",
        "roas",
        "达人合作",
        "蒲公英",
        "星图",
        "聚光",
        "腾讯广告",
    ],
    "product_trend": [
        "选品",
        "爆款",
        "爆品",
        "新品",
        "趋势",
        "品类",
        "类目",
        "需求",
        "热销",
    ],
    "platform_opportunity": [
        "平台",
        "扶持",
        "补贴",
        "招商",
        "入驻",
        "流量",
        "活动",
        "工具",
        "服务市场",
    ],
    "extended_watch": [
        "跨境",
        "出海",
        "海外",
        "物流",
        "仓储",
        "fba",
        "支付",
        "关税",
        "收款",
        "独立站",
        "amazon",
        "tiktok shop",
        "temu",
        "shopify",
        "shopee",
        "lazada",
    ],
}

AI_COMMERCE_SCENE_KEYWORDS = [
    "商品图",
    "详情页",
    "模特图",
    "封面图",
    "广告素材",
    "短视频",
    "视频生成",
    "直播切片",
    "脚本",
    "文案",
    "客服",
    "评论分析",
    "买家秀",
    "素材拆解",
    "店铺诊断",
    "爆款拆解",
    "投流复盘",
    "运营 sop",
    "批量生成",
    "竞品采集",
    "价格监控",
    "飞书表",
    "自动化运营",
    "图像生成",
    "多模态",
    "智能体",
    "工作流",
    "低代码",
    "no-code",
    "no code",
    "automation",
    "workflow",
    "agent",
    "multimodal",
    "vision model",
    "image generation",
    "video generation",
    "text to image",
    "text to video",
    "ad creative",
    "advertising creative",
    "product image",
    "product photo",
    "product video",
    "product description",
    "customer support",
    "customer service",
    "shopping assistant",
    "retail",
    "commerce",
    "merchant",
    "seller workflow",
    "ecommerce",
    "e-commerce",
    "电商",
    "商家",
    "店铺",
    "带货",
    "投流",
    "选品",
]

CROSS_BORDER_STRONG_KEYWORDS = [
    "平台规则",
    "seller policy",
    "卖家",
    "商家",
    "运营",
    "选品",
    "投流",
    "物流",
    "收款",
    "关税",
    "tiktok shop",
    "amazon",
    "temu",
    "shopify",
    "shopee",
    "lazada",
]

OFFICIAL_SOURCE_HINTS = [
    "抖音电商规则中心",
    "抖音电商学习中心",
    "巨量千川",
    "巨量引擎",
    "小红书电商",
    "小红书蒲公英",
    "小红书聚光",
    "快手电商规则中心",
    "快手电商学习中心",
    "淘宝规则",
    "天猫规则",
    "阿里妈妈",
    "京东商家规则",
    "拼多多规则",
    "微信小店",
    "腾讯广告",
]

TRUSTED_MEDIA_HINTS = [
    "电商报",
    "亿邦",
    "ebrun",
    "派代",
    "见实",
    "运营研究社",
    "品牌星球",
    "新榜",
    "飞瓜",
    "蝉妈妈",
    "灰豚",
    "morketing",
]

NOISE_KEYWORDS = [
    "汽车召回",
    "召回部分",
    "车辆召回",
    "医药",
    "药品",
    "it之家",
    "上线通知",
    "好友上线",
    "战略合作协议",
    "战略合作",
    "market update",
    "monthly update",
    "custom liquid",
    "融资",
    "估值",
    "资本市场",
    "股票",
    "指数",
    "财报电话会",
    "普通政策",
    "国务院",
    "部委通知",
    "体育",
    "娱乐八卦",
    "招聘",
    "求职",
    "租房",
    "彩票",
    "首页",
    "栏目页",
    "法律声明",
    "隐私政策",
    "用户协议",
]

SOURCE_PRIORS = {
    "websource": 0.38,
    "opmlrss": 0.12,
    "xapi": 0.05,
    "agentmail": 0.05,
}

LABEL_TO_CHANNEL = {
    "platform_policy": "platform_policy",
    "operations_playbook": "operations_playbook",
    "ai_commerce": "ai_commerce",
    "traffic_creative": "traffic_creative",
    "product_trend": "operations_playbook",
    "platform_opportunity": "operations_playbook",
    "extended_watch": "extended_watch",
}


def contains_any_keyword(haystack: str, keywords: list[str]) -> bool:
    h = haystack.lower()
    return any(k.lower() in h for k in keywords)


def matched_keywords(haystack: str, keywords: list[str]) -> list[str]:
    h = haystack.lower()
    return sorted({k for k in keywords if k.lower() in h})


def has_standalone_ai(text: str) -> bool:
    return bool(re.search(r"(^|[^a-z0-9])ai([^a-z0-9]|$)", text.lower()))


def _result(
    *,
    is_related: bool,
    score: float,
    label: str,
    reason: str,
    signals: list[str] | None = None,
    noise: list[str] | None = None,
    usefulness: str = "",
) -> dict[str, Any]:
    return {
        "is_ecommerce_related": bool(is_related),
        "score": round(max(0.0, min(1.0, score)), 2),
        "label": label,
        "reason": reason,
        "signals": signals or [],
        "noise": noise or [],
        "usefulness": usefulness,
    }


def _dominant_value_bucket(value_hits: dict[str, list[str]]) -> str:
    ordered = [
        "platform_policy",
        "traffic_creative",
        "ai_commerce",
        "operations_playbook",
        "product_trend",
        "platform_opportunity",
        "extended_watch",
    ]
    return max(ordered, key=lambda key: (len(value_hits.get(key, [])), -ordered.index(key)))


def _ai_commerce_usefulness(text: str) -> str:
    if contains_any_keyword(
        text,
        [
            "图像",
            "图片",
            "商品图",
            "详情页",
            "模特图",
            "封面",
            "视觉",
            "image",
            "product image",
            "product photo",
            "ad creative",
            "advertising creative",
        ],
    ):
        return "可用于商品图、详情页、封面图和广告素材批量生产。"
    if contains_any_keyword(text, ["视频", "短视频", "直播", "切片", "video", "product video"]):
        return "可用于短视频带货、产品展示、直播切片和信息流视频素材。"
    if contains_any_keyword(text, ["多模态", "视觉理解", "评论", "买家秀", "页面分析", "multimodal"]):
        return "可用于竞品页面、评论、买家秀和素材拆解分析。"
    if contains_any_keyword(text, ["长上下文", "推理", "分析", "诊断", "复盘", "reasoning", "analysis"]):
        return "可用于店铺诊断、爆款拆解、投流复盘和运营 SOP 分析。"
    if contains_any_keyword(text, ["降价", "成本", "速度", "批量", "便宜", "faster", "cheaper", "cost"]):
        return "可用于批量生成文案、素材、脚本和客服回复，降低内容生产成本。"
    if contains_any_keyword(text, ["agent", "浏览器", "自动化", "采集", "监控", "browser", "automation"]):
        return "可用于竞品采集、价格监控、飞书表整理和自动化运营。"
    if contains_any_keyword(text, ["customer support", "customer service", "shopping assistant"]):
        return "可用于售前客服、导购问答、客服回复和店铺服务提效。"
    return ""


def _has_direct_ai_commerce_transfer(text: str) -> bool:
    direct_terms = [
        "商品图",
        "详情页",
        "模特图",
        "封面图",
        "广告素材",
        "短视频",
        "直播切片",
        "脚本",
        "文案",
        "客服",
        "评论分析",
        "买家秀",
        "素材拆解",
        "店铺诊断",
        "爆款拆解",
        "投流复盘",
        "运营 sop",
        "批量生成",
        "竞品采集",
        "价格监控",
        "飞书表",
        "自动化运营",
        "图像生成",
        "视频生成",
        "多模态",
        "agent",
        "智能体",
        "工作流",
        "低代码",
        "no-code",
        "no code",
        "automation",
        "workflow",
        "multimodal",
        "vision model",
        "image generation",
        "video generation",
        "text to image",
        "text to video",
        "ad creative",
        "advertising creative",
        "product image",
        "product photo",
        "product video",
        "product description",
        "customer support",
        "customer service",
        "shopping assistant",
        "seller workflow",
        "browser automation",
        "retail ai",
        "ecommerce ai",
        "commerce ai",
    ]
    return contains_any_keyword(text, direct_terms)


def score_ecommerce_relevance(record: dict[str, Any]) -> dict[str, Any]:
    site_id = str(record.get("site_id") or "")
    title = str(record.get("title") or "")
    source = str(record.get("source") or "")
    site_name = str(record.get("site_name") or "")
    url = str(record.get("url") or "")
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    try:
        url_host = (urlparse(url).netloc or "").lower()
    except Exception:
        url_host = ""
    text = f"{title} {source} {site_name} {url_host} {meta.get('web_source_domain') or ''}".lower()

    noise = matched_keywords(text, NOISE_KEYWORDS)
    official_hits = matched_keywords(text, OFFICIAL_SOURCE_HINTS)
    media_hits = matched_keywords(text, TRUSTED_MEDIA_HINTS)
    scene_hits = matched_keywords(text, CORE_SCENE_KEYWORDS)
    value_hits = {bucket: matched_keywords(text, keywords) for bucket, keywords in VALUE_KEYWORDS.items()}
    value_signals = [signal for signals in value_hits.values() for signal in signals]
    label = _dominant_value_bucket(value_hits)
    channel = LABEL_TO_CHANNEL.get(label, label)
    source_prior = SOURCE_PRIORS.get(site_id, 0.0)
    is_snapshot = meta.get("web_source_mode") == "page_snapshot" or title.startswith("页面监控：")
    is_ai_candidate = bool(value_hits["ai_commerce"] or has_standalone_ai(text))
    ai_usefulness = _ai_commerce_usefulness(text)

    if noise and not official_hits:
        return _result(
            is_related=False,
            score=max(0.0, source_prior - 0.05),
            label="excluded_noise",
            reason="blocked_noise_keyword",
            signals=scene_hits + value_signals + official_hits + media_hits,
            noise=noise,
        )

    has_scene = bool(scene_hits or official_hits)
    has_business_value = bool(value_signals or official_hits or media_hits)

    if is_ai_candidate and not has_scene:
        if ai_usefulness and _has_direct_ai_commerce_transfer(text):
            has_scene = True
            has_business_value = True
            channel = "ai_commerce"
        else:
            return _result(
                is_related=False,
                score=source_prior,
                label="ai_without_commerce_scenario",
                reason="ai_news_missing_ecommerce_use_case",
                signals=value_hits["ai_commerce"],
                noise=noise,
            )

    if channel == "extended_watch" and not (official_hits or matched_keywords(text, CROSS_BORDER_STRONG_KEYWORDS)):
        return _result(
            is_related=False,
            score=0.34,
            label="extended_watch",
            reason="cross_border_weak_signal",
            signals=scene_hits + value_signals + media_hits,
            noise=noise,
        )

    if not has_scene or not has_business_value:
        return _result(
            is_related=False,
            score=source_prior,
            label="missing_ecommerce_business_value",
            reason="missing_scene_or_value_gate",
            signals=scene_hits + value_signals + official_hits + media_hits,
            noise=noise,
        )

    score = source_prior
    score += min(0.36, 0.12 * len(scene_hits))
    score += min(0.3, 0.1 * len(value_signals))
    score += min(0.24, 0.12 * len(official_hits))
    score += min(0.16, 0.08 * len(media_hits))
    if is_ai_candidate and ai_usefulness:
        score += 0.16
        channel = "ai_commerce"
        if _has_direct_ai_commerce_transfer(text):
            score = max(score, 0.68)
    if is_snapshot:
        score = min(score - 0.18, 0.58)
    if channel == "extended_watch":
        score -= 0.12

    is_related = score >= ECOMMERCE_RELEVANCE_THRESHOLD
    usefulness = ai_usefulness or _business_usefulness(channel)
    return _result(
        is_related=is_related,
        score=score,
        label=channel if is_related else "below_ecommerce_threshold",
        reason="matched_ecommerce_operations_value" if is_related else "below_ecommerce_threshold",
        signals=scene_hits + value_signals + official_hits + media_hits,
        noise=noise,
        usefulness=usefulness,
    )


def _business_usefulness(label: str) -> str:
    return {
        "platform_policy": "用于判断平台规则、账号风险、处罚治理和商家经营动作。",
        "operations_playbook": "用于内容电商运营、店播/达人/种草玩法和活动机会判断。",
        "traffic_creative": "用于判断投流规则、素材生产、达人合作和广告转化变化。",
        "ai_commerce": "用于判断 AI 能力能否迁移到电商素材、脚本、客服、选品或自动化。",
        "extended_watch": "作为跨境、物流、支付和海外平台经营变化的观察信号。",
    }.get(label, "用于判断是否存在电商运营机会。")


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
    out["business_value"] = relevance["usefulness"]
    out["topic"] = "ecommerce"
    out["topic_is_related"] = relevance["is_ecommerce_related"]
    out["topic_score"] = relevance["score"]
    out["topic_label"] = relevance["label"]
    return out
