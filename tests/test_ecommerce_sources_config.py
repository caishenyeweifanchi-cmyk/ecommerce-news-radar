import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.ecommerce_relevance import score_ecommerce_relevance
from scripts.update_news import (
    build_daily_brief_payload,
    build_web_source_snapshot_item,
    canonical_douyin_article_url,
    canonicalize_archive_item_ids,
    clear_future_record_publish_time,
    event_time,
    extract_datetime_from_text,
    extract_web_source_candidates,
    fetch_douyin_rule_center_items,
    fetch_kuaishou_rule_center_items,
    fetch_xiaohongshu_official_info_items,
    suppress_superseded_web_snapshots,
)
from scripts.ecommerce_relevance import score_ecommerce_relevance


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

    assert "P0/P1 ecommerce operations feeds" in opml
    assert "https://www.ebrun.com/rss/news_b2c.xml" in opml
    assert "https://changelog.shopify.com/feed" in opml
    assert "https://www.ecommercebytes.com/feed/" in opml
    assert "https://www.junglescout.com/blog/feed/" in opml
    assert "https://www.reddit.com/r/ecommerce/.rss" not in opml


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


def test_extract_datetime_from_text_ignores_future_event_registration_time():
    parsed = extract_datetime_from_text(
        "报名中 2026 Ozon全球产业带招商系列峰会-泉州站 2026-07-16 13:30 泉州市",
        datetime(2026, 6, 12, 6, 0, tzinfo=timezone.utc),
    )

    assert parsed is None


def test_clear_future_record_publish_time_removes_event_time_from_timeline():
    record = {
        "site_id": "opmlrss",
        "published_at": "2026-07-16T05:30:00Z",
        "first_seen_at": "2026-06-12T06:00:00Z",
        "meta": {},
    }

    clear_future_record_publish_time(record, datetime(2026, 6, 12, 6, 0, tzinfo=timezone.utc))

    assert record["published_at"] is None
    assert record["meta"]["rejected_published_at"] == "2026-07-16T05:30:00Z"
    assert record["meta"]["published_time_source"] == "future_time_rejected"
    assert event_time(record) is None


def test_official_web_source_rule_scores_above_generic_threshold():
    result = score_ecommerce_relevance(
        {
            "site_id": "websource",
            "site_name": "重点网页源",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "url": "https://school.jinritemai.com/doudian/web/articlev0/aJksF3Y7x1Bc",
        }
    )

    assert result["is_ecommerce_related"] is True
    assert result["score"] >= 0.8
    assert result["label"] == "platform_policy"


def test_douyin_rule_api_items_link_to_article_detail_page():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "rule_infos": [
                        {
                            "knowledge_id": "aJksF3Y7x1Bc",
                            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
                            "update_time": "1781185233",
                            "status_code": 201,
                        }
                    ]
                }
            }

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    items = fetch_douyin_rule_center_items(
        Session(),
        {"id": "douyin_ecommerce_rule_center", "name": "抖音电商规则中心"},
        datetime(2026, 6, 12, tzinfo=timezone.utc),
    )

    assert items[0].url == "https://school.jinritemai.com/doudian/web/articlev0/aJksF3Y7x1Bc"
    assert items[0].meta["article_url_source"] == "douyin_articlev0"


def test_xiaohongshu_official_api_items_use_notice_links_and_times():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "red_official_information_notice": {
                        "notice_config_list": [
                            {
                                "title": "规则公告",
                                "information_detail_list": [
                                    {
                                        "title": "小红书电商商家规则更新通知",
                                        "time": "2026-06-11",
                                        "link": "https://ec.xiaohongshu.com/rule/detail/abc",
                                    }
                                ],
                            }
                        ]
                    }
                }
            }

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    items = fetch_xiaohongshu_official_info_items(
        Session(),
        {"id": "xiaohongshu_ecommerce_official_info", "name": "小红书电商官方资讯"},
        datetime(2026, 6, 12, tzinfo=timezone.utc),
    )

    assert items[0].url == "https://ec.xiaohongshu.com/rule/detail/abc"
    assert items[0].published_at == datetime(2026, 6, 11, 0, 0, tzinfo=timezone.utc)
    assert items[0].meta["web_source_mode"] == "api_list"
    assert items[0].meta["published_time_source"] == "api"


def test_kuaishou_rule_api_items_link_to_rule_detail_page():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "result": 1,
                "data": {
                    "list": [
                        {
                            "title": "快手电商品牌标识管理规则修订公告",
                            "resourceId": "4NJAdFIRMe",
                            "publishTime": 1781179116954,
                        }
                    ]
                },
            }

    class Session:
        def post(self, *args, **kwargs):
            return Response()

    items = fetch_kuaishou_rule_center_items(
        Session(),
        {"id": "kuaishou_ecommerce_rule_center", "name": "快手电商规则中心"},
        datetime(2026, 6, 12, tzinfo=timezone.utc),
    )

    assert items[0].url == "https://edu.kwaixiaodian.com/rule/web/detail?id=4NJAdFIRMe"
    assert items[0].published_at == datetime(2026, 6, 11, 11, 58, 36, 954000, tzinfo=timezone.utc)
    assert items[0].meta["article_url_source"] == "kuaishou_rule_resource_api"


def test_douyin_rule_urls_are_canonicalized_to_article_detail_page():
    old_url = "https://school.jinritemai.com/doudian/web/rules/aJksF3Y7x1Bc?tabKey=rules"

    assert (
        canonical_douyin_article_url(old_url)
        == "https://school.jinritemai.com/doudian/web/articlev0/aJksF3Y7x1Bc"
    )


def test_archive_canonicalization_merges_old_douyin_rule_route():
    old = {
        "old": {
            "id": "old",
            "site_id": "websource",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "url": "https://school.jinritemai.com/doudian/web/rules/aJksF3Y7x1Bc?tabKey=rules",
            "published_at": "2026-06-11T13:40:33Z",
            "last_seen_at": "2026-06-12T01:00:00Z",
        },
        "new": {
            "id": "new",
            "site_id": "websource",
            "source": "抖音电商规则中心",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "url": "https://school.jinritemai.com/doudian/web/articlev0/aJksF3Y7x1Bc",
            "published_at": "2026-06-11T13:40:33Z",
            "last_seen_at": "2026-06-12T02:00:00Z",
        },
    }

    merged = canonicalize_archive_item_ids(old)

    assert len(merged) == 1
    assert next(iter(merged.values()))["url"] == "https://school.jinritemai.com/doudian/web/articlev0/aJksF3Y7x1Bc"


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


def test_daily_brief_prioritizes_official_p0_rules_over_generic_high_score_items():
    official = {
        "story_id": "official_rule",
        "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
        "score": 0.62,
        "source_count": 1,
        "source": "抖音电商规则中心",
        "primary_item": {
            "site_id": "websource",
            "title": "关于修订《创作者【违规营销活动或玩法】处置细则》的意见征集通知",
            "source": "抖音电商规则中心",
            "meta": {
                "web_source_priority": "P0",
                "web_source_domain": "平台规则",
                "web_source_mode": "api_list",
            },
        },
    }
    generic = [
        {
            "story_id": f"generic_{idx}",
            "title": f"跨境电商运营热点 {idx}",
            "score": 0.95,
            "source_count": 2,
            "source": f"行业媒体 {idx}",
            "primary_item": {"site_id": "opmlrss", "title": f"跨境电商运营热点 {idx}"},
        }
        for idx in range(25)
    ]

    brief = build_daily_brief_payload(generic + [official], generated_at="2026-06-12T00:00:00Z", window_hours=24)

    assert brief["total_items"] == 20
    assert brief["items"][0]["story_id"] == "official_rule"


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


def test_ecommerce_relevance_blocks_auto_recall_noise():
    result = score_ecommerce_relevance(
        {
            "site_id": "opmlrss",
            "source": "市场监管总局公告",
            "title": "四川南骏汽车集团有限公司扩大召回部分新祥康EDH纯电动自卸汽车",
            "url": "https://example.com/recall",
        }
    )

    assert result["is_ecommerce_related"] is False
    assert result["label"] == "excluded_noise"


def test_ai_model_news_requires_ecommerce_use_case():
    result = score_ecommerce_relevance(
        {
            "site_id": "opmlrss",
            "source": "AI News",
            "title": "OpenAI 发布新模型，推理能力提升",
            "url": "https://example.com/model",
        }
    )

    assert result["is_ecommerce_related"] is False
    assert result["label"] == "ai_without_commerce_scenario"


def test_ai_capability_maps_to_commerce_channel_when_useful():
    result = score_ecommerce_relevance(
        {
            "site_id": "opmlrss",
            "source": "AI 素材工具",
            "title": "OpenAI 新模型视频生成速度提升，可用于批量生成商品图、广告素材和短视频脚本",
            "url": "https://example.com/ai-commerce",
        }
    )

    assert result["is_ecommerce_related"] is True
    assert result["label"] == "ai_commerce"
    assert "商品图" in result["usefulness"] or "短视频" in result["usefulness"]


def test_cross_border_activity_without_seller_value_is_extended_only():
    result = score_ecommerce_relevance(
        {
            "site_id": "opmlrss",
            "source": "雨果跨境",
            "title": "2026 Ozon全球产业带招商系列峰会-泉州站 报名中",
            "url": "https://example.com/activity",
        }
    )

    assert result["is_ecommerce_related"] is False
    assert result["reason"] in {"cross_border_weak_signal", "missing_scene_or_value_gate", "below_ecommerce_threshold"}
