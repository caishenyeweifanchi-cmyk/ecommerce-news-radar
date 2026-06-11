import json
from pathlib import Path


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
