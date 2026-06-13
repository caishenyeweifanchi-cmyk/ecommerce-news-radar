from __future__ import annotations

from datetime import datetime, timedelta, timezone

from scripts.update_news import (
    add_source_tier_fields,
    build_daily_brief_payload,
    build_merge_log_payload,
    build_stories_payload,
    calculate_item_importance,
    enrich_items_with_operational_depth,
    filter_records_for_local_date,
    merge_story_items,
    story_passes_brief_gate,
)


NOW = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)


def make_item(
    idx: int,
    *,
    site_id: str = "official_ai",
    title: str | None = None,
    hours_ago: int = 1,
    ai_score: float = 0.9,
) -> dict:
    item = {
        "id": f"item-{idx}",
        "site_id": site_id,
        "site_name": site_id.replace("_", " ").title(),
        "source": "Test Feed",
        "title": title or f"OpenAI ships Codex data pipeline update {idx}",
        "url": f"https://example.com/news/{idx}",
        "published_at": (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z"),
        "ai_is_related": True,
        "ai_score": ai_score,
    }
    return add_source_tier_fields(item)


def test_importance_score_favors_official_relevant_recent_items():
    official = make_item(1, site_id="official_ai", hours_ago=1, ai_score=0.95)
    discussion = make_item(2, site_id="tophub", hours_ago=20, ai_score=0.65)

    official_score = calculate_item_importance(official, NOW, 24)["score"]
    discussion_score = calculate_item_importance(discussion, NOW, 24)["score"]

    assert official_score > discussion_score


def test_daily_brief_respects_20_cap_when_enough_distinct_stories_exist():
    # Titles must be genuinely distinct: same-cluster stories are now
    # deliberately suppressed at selection time, so near-identical titles
    # may no longer fill the brief.
    subjects = [
        "quantum annealing", "protein folding", "code review bots", "speech synthesis",
        "robot grasping", "wafer yields", "vector databases", "edge inference",
        "retrieval pipelines", "agent sandboxing", "diffusion video", "tokenizer design",
        "kernel fusion", "sparse attention", "memory tiering", "eval harnesses",
        "watermark detection", "policy gradients", "scene graphs", "voice cloning",
        "data curation", "reward modeling", "chip packaging", "model routing", "cache layouts",
    ]
    items = [make_item(i, title=f"Briefing {i}: advances in {subjects[i]} reshape AI workloads") for i in range(25)]
    stories, _events = merge_story_items(items, NOW, 24, title_threshold=1.1)

    payload = build_daily_brief_payload(stories, generated_at="2026-06-02T12:00:00Z", window_hours=24)

    assert len(stories) == 25
    assert payload["total_items"] == 20
    assert len(payload["items"]) == 20


def test_daily_brief_record_supports_bole_output_contract():
    items = [
        make_item(1, title="OpenAI releases Codex agent orchestration"),
        make_item(2, site_id="aihot", title="OpenAI releases Codex agent orchestration", ai_score=0.86),
    ]
    stories, events = merge_story_items(items, NOW, 24)

    payload = build_daily_brief_payload(stories, generated_at="2026-06-02T12:00:00Z", window_hours=24)
    record = payload["items"][0]

    assert events
    assert record["title"]
    assert record["url"]
    assert record["primary_url"] == record["url"]
    assert record["source"]
    assert record["source_name"]
    assert record["source_count"] == 2
    assert record["score"] == record["importance"] == record["importance_score"]
    assert record["category"] in {"official", "multi_source", "industry", "watch"}
    assert record["reasons"]
    assert record["earliest_at"]
    assert record["latest_at"]
    assert len(record["items"]) == 2
    assert len(record["sources"]) == 2
    assert record["primary_item"]["id"] == "item-1"


def test_story_record_includes_product_depth_fields_for_operator_action():
    items = [
        make_item(
            1,
            site_id="websource",
            title="Douyin ecommerce updates seller violation rule for creators",
            ai_score=0.9,
        )
    ]
    items[0]["topic_label"] = "platform_policy"
    items[0]["impact"] = "Impacts merchant account risk and product compliance checks."
    items[0]["suggested_action"] = "Review affected products and update the compliance checklist today."
    items[0]["meta"] = {
        "web_source_priority": "P0",
        "web_source_domain": "平台规则",
        "web_source_mode": "api_list",
        "article_url_source": "douyin_articlev0",
        "published_time_source": "api",
    }
    stories, _events = merge_story_items(items, NOW, 24)
    record = stories[0]

    assert record["operational_depth"]["affected_roles"]
    assert record["operational_depth"]["action_priority"] in {"P0", "P1", "P2"}
    assert record["operational_depth"]["operator_question"] == "这条信息对电商运营有什么用？"
    assert record["primary_item"]["operational_depth"] == record["operational_depth"]


def test_latest_items_can_be_enriched_with_product_depth_fields():
    item = make_item(1, site_id="opmlrss", title="AI video workflow improves ecommerce ad creative testing")
    item["topic_label"] = "ai_commerce"
    item["topic_score"] = 0.82

    enriched = enrich_items_with_operational_depth([item])

    assert enriched[0]["operational_depth"]["operator_question"] == "这条信息对电商运营有什么用？"
    assert enriched[0]["operational_depth"]["action_priority"] == "P1"
    assert enriched[0]["operational_depth"]["quality_basis"]["channel"] == "ai_commerce"


def test_brief_gate_rejects_p0_websource_without_detail_url_and_real_time():
    story = {
        "story_id": "story_weak_websource",
        "title": "平台规则中心栏目页",
        "score": 0.95,
        "source_count": 1,
        "brief_channel": "platform_policy",
        "primary_item": {
            "site_id": "websource",
            "source": "淘宝规则中心",
            "title": "平台规则中心栏目页",
            "meta": {
                "web_source_priority": "P0",
                "web_source_domain": "平台规则",
                "web_source_mode": "list",
                "published_time_source": "unconfirmed",
            },
        },
    }

    assert story_passes_brief_gate(story) is False


def test_today_filter_keeps_only_same_shanghai_calendar_day_for_brief_inputs():
    today = make_item(1, title="Today official ecommerce rule update", hours_ago=1)
    yesterday = make_item(2, title="Yesterday official ecommerce rule update", hours_ago=30)

    filtered = filter_records_for_local_date([today, yesterday], NOW.astimezone(timezone.utc).date())

    assert [item["id"] for item in filtered] == ["item-1"]


def test_stories_and_merge_log_payload_shapes_are_explicit():
    items = [
        make_item(1, title="OpenAI releases Codex agent orchestration"),
        make_item(2, title="OpenAI releases Codex agent orchestration"),
    ]
    stories, events = merge_story_items(items, NOW, 24)

    stories_payload = build_stories_payload(stories, generated_at="2026-06-02T12:00:00Z", window_hours=24)
    merge_payload = build_merge_log_payload(events, generated_at="2026-06-02T12:00:00Z")

    assert stories_payload["total_stories"] == 1
    assert stories_payload["stories"][0]["story_id"]
    assert merge_payload["merge_strategy"] == "url_or_title_similarity_v0_6"
    assert merge_payload["total_events"] == len(events) == 1
