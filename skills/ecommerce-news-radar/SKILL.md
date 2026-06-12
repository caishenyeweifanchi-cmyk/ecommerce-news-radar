---
name: ecommerce-news-radar
description: Read Ecommerce News Radar daily briefs and surface ecommerce operations intelligence: platform rules, content commerce playbooks, traffic creative changes, AI commerce capabilities, product trends, and high-value extended watch signals.
---

# Ecommerce News Radar

Use this skill when the user asks for ecommerce daily intelligence, platform rule changes, merchant policy updates, content commerce playbooks, traffic/creative changes, AI commerce opportunities, product trends, or cross-border signals that directly affect sellers.

## Source of Truth

Read these files from the installed repository:

- `data/daily-brief.json`: daily priority brief. Use this first.
- `data/stories-merged.json`: merged story timeline.
- `data/latest-24h.json`: current ecommerce signal stream.
- `data/source-status.json`: source health and whether official web sources are list/API/snapshot.

## Daily Brief Rules

1. Always check `data/daily-brief.json` first.
2. The product is not a generic news aggregator. Include an item only if it helps ecommerce operations, content production, traffic buying, product selection, store management, risk control, or automation efficiency.
3. Official ecommerce platform rules are P0. If an item has `primary_item.site_id == "websource"` or `importance_label == "官方更新"`, include it in the daily report unless it is only `page_snapshot`.
4. Put these before general industry news:
   - platform rules, new policies, penalties, violation governance, merchant access, settlement, fulfillment, after-sales;
   - Douyin/Taobao/Tmall/JD/Pinduoduo/Xiaohongshu/Kuaishou/WeChat/Alipay/Eleme/Meituan official updates;
   - traffic platform rule changes such as Qianchuan, Ocean Engine, Tencent Ads, Xiaohongshu Juguang, Kuaishou Magnetic Engine.
5. AI model/tool news can enter only after mapping: model capability -> transferable capability -> ecommerce use case -> operator action. Never report a bare item like "OpenAI released a model" without ecommerce use.
6. Cross-border is extended watch by default. Promote only when it directly affects seller rules, operations, product trends, traffic, logistics, payment, tariffs, or TikTok Shop/Amazon/Temu/Shopify operations.
7. If `data/daily-brief.json` is empty, fall back to `data/stories-merged.json`, then `data/latest-24h.json`, but keep the same usefulness gate.
8. Do not invent content. If a source is only `page_snapshot`, say it is page-change monitoring, not article-level extraction.

## Output Format

Produce a short Chinese daily report:

```markdown
# 电商热点日报

## 今日必看
- 平台｜标题｜影响｜建议动作｜链接

## 平台规则与风险
- 平台｜规则变化｜影响对象｜风险点｜建议动作｜链接

## 运营玩法与热点
- 玩法｜适合谁｜可以怎么用｜建议动作｜链接

## AI 电商
- AI能力/工具｜可用于什么电商场景｜建议动作｜链接

## 投流与素材
- 平台｜变化｜对素材/投放的影响｜建议动作｜链接

## 扩展观察
- 跨境/物流/支付｜是否重要｜为什么｜链接

## 信息源状态
- 官方网页源：X/Y
- 真实列表/API：X
- 页面快照：Y
- 失败源：Z
```

## Failure Rules

- If files are missing, say which file is missing.
- If an official source is marked as snapshot only, do not claim full article-level collection.
- If `source-status.json` shows failures, include them under source status.
- If you cannot answer "这对我的电商运营有什么用？", do not include the item in the main brief.
