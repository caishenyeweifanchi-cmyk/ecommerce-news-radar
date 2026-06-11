import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.update_news import build_web_source_snapshot_item, extract_web_source_candidates


ROOT = Path(__file__).resolve().parents[1]


def test_mandatory_cn_platform_sources_are_p0_required():
    payload = json.loads((ROOT / "feeds" / "ecommerce.web-sources.json").read_text(encoding="utf-8"))
    sources = payload["sources"]

    assert len(sources) >= 30
    assert all(source["priority"] == "P0" for source in sources)
    assert all(source["required"] is True for source in sources)

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
    assert item.meta["web_source_mode"] == "page_snapshot"
    assert item.meta["web_source_snapshot_hash"]
