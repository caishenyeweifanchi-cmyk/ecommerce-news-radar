import unittest

from scripts.ecommerce_relevance import (
    add_ecommerce_relevance_fields,
    is_ecommerce_related_record,
    score_ecommerce_relevance,
)


class EcommerceRelevanceScoringTests(unittest.TestCase):
    def test_scores_platform_policy_as_high_value(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "抖音电商规则中心",
            "title": "抖音电商发布商家保证金与类目治理新规",
            "url": "https://example.com/douyin-policy",
        }
        result = score_ecommerce_relevance(rec)
        self.assertTrue(result["is_ecommerce_related"])
        self.assertGreaterEqual(result["score"], 0.65)
        self.assertEqual(result["label"], "platform_policy")
        self.assertIn("抖音电商", result["signals"])

    def test_scores_cross_border_marketplace_news(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "AMZ123",
            "title": "TikTok Shop调整东南亚跨境卖家物流履约政策",
            "url": "https://example.com/tiktok-shop-cross-border",
        }
        result = score_ecommerce_relevance(rec)
        self.assertTrue(result["is_ecommerce_related"])
        self.assertEqual(result["label"], "extended_watch")
        self.assertIn("tiktok shop", result["signals"])

    def test_rejects_non_ecommerce_margin_policy(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "ReadHub",
            "title": "上期所调整黄金、白银期货相关合约涨跌停板幅度和交易保证金比例",
            "url": "https://example.com/futures-margin",
        }
        result = score_ecommerce_relevance(rec)
        self.assertFalse(result["is_ecommerce_related"])
        self.assertLess(result["score"], 0.65)

    def test_rejects_overseas_news_without_ecommerce_context(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "AIbase",
            "title": "某 AI 公司在海外市场推出自动化编程服务",
            "url": "https://example.com/overseas-ai",
        }
        result = score_ecommerce_relevance(rec)
        self.assertFalse(result["is_ecommerce_related"])
        self.assertLess(result["score"], 0.65)

    def test_rejects_generic_official_ai_news_without_commerce_use_case(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "OpenAI News",
            "title": "OpenAI releases a new reasoning model with improved benchmark scores",
            "url": "https://openai.com/news/example-model",
        }
        result = score_ecommerce_relevance(rec)
        self.assertFalse(result["is_ecommerce_related"])
        self.assertEqual(result["label"], "ai_without_commerce_scenario")

    def test_accepts_ai_capability_when_mapped_to_commerce_use_case(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "Google DeepMind Blog",
            "title": "New image generation model improves product image and ad creative testing",
            "url": "https://deepmind.google/blog/example-image-model",
        }
        result = score_ecommerce_relevance(rec)
        self.assertTrue(result["is_ecommerce_related"])
        self.assertEqual(result["label"], "ai_commerce")
        self.assertIn("product image", result["signals"])

    def test_adds_compatible_topic_fields(self):
        rec = {
            "site_id": "opmlrss",
            "site_name": "OPML RSS",
            "source": "小红书商业动态",
            "title": "小红书种草营销案例带动美妆品牌复购增长",
            "url": "https://example.com/xhs-case",
        }
        out = add_ecommerce_relevance_fields(rec)
        self.assertTrue(out["ai_is_related"])
        self.assertTrue(out["topic_is_related"])
        self.assertEqual(out["topic"], "ecommerce")
        self.assertTrue(is_ecommerce_related_record(rec))


if __name__ == "__main__":
    unittest.main()
