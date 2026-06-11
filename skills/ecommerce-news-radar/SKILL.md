---
name: ecommerce-news-radar
description: Read Ecommerce News Radar daily briefs and surface official ecommerce platform rule updates, policy changes, traffic marketing changes, and cross-border ecommerce signals.
---

# Ecommerce News Radar

Use this skill when the user asks for ecommerce daily news, platform rule changes, merchant policy updates, traffic marketing changes, or cross-border ecommerce signals.

## Source of Truth

Read these files from the installed repository:

- `data/daily-brief.json`: daily priority brief. Use this first.
- `data/stories-merged.json`: merged story timeline.
- `data/latest-24h.json`: current ecommerce signal stream.
- `data/source-status.json`: source health and whether official web sources are list/API/snapshot.

## Daily Brief Rules

1. Always check `data/daily-brief.json` first.
2. Official ecommerce platform rules are P0. If an item has `primary_item.site_id == "websource"` or `importance_label == "官方更新"`, include it in the daily report.
3. Put these before general industry news:
   - platform rules, new policies, penalties, violation governance, merchant access, settlement, fulfillment, after-sales;
   - Douyin/Taobao/Tmall/JD/Pinduoduo/Xiaohongshu/Kuaishou/WeChat/Alipay/Eleme/Meituan official updates;
   - traffic platform rule changes such as Qianchuan, Ocean Engine, Tencent Ads, Xiaohongshu Juguang, Kuaishou Magnetic Engine.
4. If `data/daily-brief.json` is empty, fall back to `data/stories-merged.json`, then `data/latest-24h.json`.
5. Do not invent content. If a source is only `page_snapshot`, say it is page-change monitoring, not article-level extraction.

## Output Format

Produce a short Chinese daily report:

```markdown
# 电商规则与热点日报

## 必看官方新规
- 平台｜标题｜为什么重要｜链接

## 投流与内容电商变化
- 平台｜标题｜影响｜链接

## 跨境与平台经营动态
- 来源｜标题｜影响｜链接

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
