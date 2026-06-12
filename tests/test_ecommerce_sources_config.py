import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.ecommerce_relevance import score_ecommerce_relevance
from scripts.update_news import (
    build_daily_brief_payload,
    build_web_source_snapshot_item,
    event_time,
    extract_datetime_from_text,
    extract_web_source_candidates,
    suppress_superseded_web_snapshots,
)


ROOT = Path(__file__).resolve().parents[1]


def test_mandatory_cn_platform_sources_are_p0_required():
    payload = json.loads((ROOT / "feeds" / "ecommerce.web-sources.json").read_text(encoding="utf-8"))
    sources = payload["sources"]

    assert len(sources) >= 150

    required_ids = {
        "taobao_rule_center",
        "tmall_rule_channel",
        "alimama_rule_center",
        "1688_rule_center",
        "jd_rule_center",
        "pinduoduo_rule_center",
        "douyin_ecommerce_rule_center",
        "qianchuan_rule_center",
        "xiaohongshu_ecommerce_official_info",
        "kuaishou_ecommerce_rule_center",
        "tencent_ads_help",
        "eleme_rule_center",
        "meituan_life_rule_center",
        "alipay_open_rules",
    }
    present_ids = {source["id"] for source in sources}
    assert required_ids <= present_ids
    by_id = {source["id"]: source for source in sources}
    assert all(by_id[source_id]["priority"] == "P0" for source_id in required_ids)
    assert all(by_id[source_id]["required"] is True for source_id in required_ids)


def test_direct_rss_opml_contains_batch_sources():
    opml = (ROOT / "feeds" / "ecommerce.example.opml").read_text(encoding="utf-8")

    assert "Batch 1 direct RSS feeds" in opml
    assert "https://changelog.shopify.com/feed" in opml
    assert "https://www.reddit.com/r/ecommerce/.rss" in opml
    assert "https://stripe.com/docs/changelog.rss" in opml


def test_web_source_adapter_extracts_rule_links():
    html = """
    <html><body>
      <a href="/notice/1">普通首页</a>
      <a href="/rule/abc">淘宝商家违规治理规则更新公告</a>
      <a href="https://example.com/policy/pay">支付结算政策变更通知</a>
      <a href="https://other.example.com/rule">站外链接不采</a>
    </body></html>
    """
    source = {
        "id": "example_rule_center",
        "name": "示例规则中心",
        "platform": "示例平台",
        "domain": "平台规则",
        "type": "规则中心",
        "url": "https://example.com/rules",
        "priority": "P0",
    }

    items = extract_web_source_candidates(html, source, datetime(2026, 6, 11, tzinfo=timezone.utc))

    titles = {item.title for item in items}
    assert "淘宝商家违规治理规则更新公告" in titles
    assert "支付结算政策变更通知" in titles
    assert all(item.site_id == "websource" for item in items)
    assert all(item.url.startswith("https://example.com/") for item in items)
    assert all(item.published_at is None for item in items)
    assert all(item.meta["published_time_source"] == "unconfirmed" for item in items)


def test_web_source_adapter_uses_real_list_time_when_available():
    html = """
    <html><body>
      <a href="/rule/abc">【二手3C数码】行业管理规范 2026-06-11 00:00:05</a>
    </body></html>
    """
    source = {
        "id": "douyin_rule_center",
        "name": "抖音电商规则中心",
        "platform": "抖音电商",
        "domain": "平台规则",
        "type": "规则中心",
        "url": "https://school.jinritemai.com/doudian/web/rules",
        "priority": "P0",
    }

    items = extract_web_source_candidates(html, source, datetime(2026, 6, 12, tzinfo=timezone.utc))

    assert items[0].published_at == datetime(2026, 6, 10, 16, 0, 5, tzinfo=timezone.utc)
    assert items[0].meta["published_time_source"] == "list_text"


def test_web_source_snapshot_tracks_js_shell_pages():
    html = """
    <html>
      <head><title>规则中心</title><script>window.__APP__ = {}</script></head>
      <body><div id="root">商家规则、平台治理、违规处罚公告请在页面加载后查看。</div></body>
    </html>
    """
    source = {
        "id": "js_rule_center",
        "name": "JS规则中心",
        "platform": "示例平台",
        "domain": "平台规则",
        "type": "规则中心",
        "url": "https://example.com/rules",
        "priority": "P0",
    }

    item = build_web_source_snapshot_item(html, source, datetime(2026, 6, 12, tzinfo=timezone.utc))

    assert item is not None
    assert item.title == "页面监控：JS规则中心 · 规则中心"
    assert item.url == "https://example.com/rules"
    assert item.published_at is None
    assert item.meta["web_source_mode"] == "page_snapshot"
    assert item.meta["web_source_snapshot_hash"]
    assert item.meta["published_time_source"] == "snapshot"


def test_event_time_for_websource_never_falls_back_to_seen_time():
    assert event_time(
        {
            "site_id": "websource",
            "published_at": None,
            "first_seen_at": "2026-06-12T01:12:00Z",
        }
    ) is None


def test_extract_datetime_from_text_supports_full_chinese_rule_time():
    parsed = extract_datetime_from_text("巨量星图达人管理规则 2026-05-12 15:02:46", datetime(2026, 6, 12, tzinfo=timezone.utc))

    assert parsed == datetime(2026, 5, 12, 7, 2, 46, tzinfo=timezone.utc)


def test_official_web_source_rule_scores_above_generic_threshold():
    result = score_ecommerce_relevance(
        {
            "site_id": "websource",
            "site_name": "重点网页源",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "url": "https://school.jinritemai.com/doudian/web/rules/aJksF3Y7x1Bc?tabKey=rules",
        }
    )

    assert result["is_ecommerce_related"] is True
    assert result["score"] >= 0.8
    assert result["label"] == "platform_policy"


def test_daily_brief_keeps_official_p0_rule_single_source():
    story = {
        "story_id": "story_rule",
        "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
        "score": 0.62,
        "source_count": 1,
        "primary_item": {
            "site_id": "websource",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "meta": {
                "web_source_priority": "P0",
                "web_source_domain": "平台规则",
                "web_source_mode": "api_list",
            },
        },
    }

    brief = build_daily_brief_payload([story], generated_at="2026-06-12T00:00:00Z", window_hours=24)

    assert brief["total_items"] == 1
    assert brief["items"][0]["story_id"] == "story_rule"


def test_daily_brief_excludes_page_snapshot_as_rule_update():
    story = {
        "story_id": "story_snapshot",
        "title": "页面监控：淘宝规则中心 · 淘宝规则",
        "score": 0.9,
        "source_count": 1,
        "primary_item": {
            "site_id": "websource",
            "source": "淘宝规则中心",
            "title": "页面监控：淘宝规则中心 · 淘宝规则",
            "meta": {
                "web_source_priority": "P0",
                "web_source_domain": "平台规则",
                "web_source_mode": "page_snapshot",
            },
        },
    }

    brief = build_daily_brief_payload([story], generated_at="2026-06-12T00:00:00Z", window_hours=24)

    assert brief["total_items"] == 0


def test_real_web_source_list_suppresses_old_snapshot():
    items = [
        {
            "id": "snapshot",
            "site_id": "websource",
            "source": "抖音电商规则中心",
            "title": "页面监控：抖音电商规则中心",
            "meta": {"web_source_mode": "page_snapshot"},
        },
        {
            "id": "rule",
            "site_id": "websource",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "meta": {"web_source_mode": "api_list"},
        },
    ]

    filtered = suppress_superseded_web_snapshots(items)

    assert [item["id"] for item in filtered] == ["rule"]
