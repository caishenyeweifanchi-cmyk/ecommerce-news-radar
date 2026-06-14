# 电商热点雷达协作工作记录

> 本文件是 Codex、Claude Code 和其他开发 Agent 的共同工作记录。执行任何项目任务前必须先阅读本文件，执行完成后必须追加记录。

## 协作规则

1. 执行前先读本文件，确认最近谁改了什么、哪些文件不能碰、哪些问题还没验证。
2. 执行时只改本次任务必须改的文件，不覆盖其他 Agent 或自动任务产生的变更。
3. 执行后必须在本文件追加一条记录，写清楚做了什么、改了哪些文件、验证了什么、还有什么风险。
4. 如果只做了文档、方案、提示词，也必须记录。
5. 如果发现未提交的 `data/*.json`、`data/feishu-pushed.json` 等自动采集结果，默认不要提交，除非任务明确要求提交数据快照。
6. 如果某个能力还需要 Claude Code、Codex 或人工手动触发，必须标记为“未产品化”，不能说已经完成自动化。
7. 推送前确认没有提交 `.env`、私有 OPML、Cookie、密钥、浏览器导出文件。

## 记录格式

```markdown
### YYYY-MM-DD HH:mm +08:00 - Agent 名称 - 任务标题

- 目标：
- 改动：
- 验证：
- 影响：
- 未完成/风险：
- 提交：
```

## 工作记录

### 2026-06-14 15:01 +08:00 - Codex - 建立协作工作记录制度

- 目标：让 Codex 和 Claude Code 在同一项目内共享工作状态，执行前先读记录，执行后追加记录。
- 改动：
  - 新增 `docs/WORK_LOG.md`，作为共同工作记录。
  - 更新 `AGENTS.md`，加入所有 Agent 必须遵守的工作记录规则。
  - 更新 `CLAUDE.md`，明确 Claude Code 进入项目前必须读取工作记录。
- 验证：
  - 已做文档差异检查。
  - 本次只涉及文档和协作规则，不运行采集脚本。
- 影响：
  - 不影响 GitHub Actions。
  - 不影响数据采集。
  - 不影响飞书推送。
- 未完成/风险：
  - 当前工作区存在自动采集产生的 `data/*.json` 和 `data/feishu-pushed.json` 变更，本次不提交。
- 提交：待提交。

### 2026-06-14 - Claude Code - 飞书推送集成 + 当前热点模块 + 导航/UI 迭代

- 目标：完成 GitHub 推送、真实采集验证新 RSS 源、飞书日报推送集成、当前热点模块。
- 改动：
  - `scripts/feishu_push.py`：飞书日报推送，使用 lark-oapi SDK，优先推 daily-brief.json 全量，兜底 ai-radar.json Top10
  - `scripts/feishu_alert.py`：精选实时提醒，每条新进精选单独推卡片，去重记录存 `data/feishu-pushed.json`
  - `scripts/run_pipeline.py`：一键流水线，采集→精选提醒→日报（--daily）
  - `env.example`：飞书凭证配置模板（chat_id 已填，app_secret 不写入）
  - `requirements.txt`：新增 lark-oapi>=1.3.0
  - `feeds/ecommerce.example.opml`：新增 Anthropic、LangChain、量子位、机器之心、AIGC开放社区
  - `index.html`：新增 `#hotTopicsWrap` 热点区块，nav 加"当前热点"
  - `assets/app.js`：新增 computeHotTopics() + renderHotTopics()，三信号融合（多源同报×3 + 实体聚合 + 时间衰减12h），20个实体词典
  - `assets/styles.css`：新增热点卡片样式
- 验证：
  - 采集跑通，ai-radar.json 478条；6个RSS失败（已知）
  - 飞书卡片消息推送成功（群 oc_7f372a21eb3f16564ee9e924711e9079）
  - 热点预览：Anthropic/Claude #1(17条·6源)、OpenAI/GPT #2(17条·9源) 正确显示
- 影响：
  - 飞书推送依赖本机 `.env`（FEISHU_APP_SECRET），不入库
  - `data/feishu-pushed.json` 是推送去重状态文件，不要手动覆盖
- 未完成/风险：
  - 导航仍有冗余（平台规则/运营玩法等与 filter-tabs 重复），本 session 继续精简
  - 公众号信源采集尚未实现，待集成
  - daily-brief.json 经常为空，需增加信源后改善
  - 多源同报热点（source_count≥2）暂未触发，信源不足
- 提交：82e65fe、4118c6b、272ec65 等

### 2026-06-14 - Claude Code - 新增9个中文媒体 RSS 源 + 确立自动化原则

- 目标：增加电商/科技中文媒体信源，写入项目核心原则。
- 改动：
  - `feeds/ecommerce.example.opml`：新增36氪、钛媒体、雷锋网、爱范儿、人人都是产品经理、运营派、白鲸出海、InfoQ中文、少数派
  - `CLAUDE.md`：新增"核心原则：项目必须完全自动运行"，明确 Claude Code/Codex 只改代码不触发日常运行
- 验证：本地采集跑通，36氪186条、钛媒体49条、爱范儿/雷锋/InfoQ/运营派各20条、少数派16条，白鲸出海待验证
- 影响：GitHub Actions 使用 ecommerce.example.opml（无私有 OPML secret 时），新源下次 CI 自动生效
- 未完成/风险：
  - **【未产品化】飞书推送**：feishu_push.py / feishu_alert.py 尚未集成进 GitHub Actions，目前只能本机手动运行
  - 白鲸出海 RSS 本地未采集到内容，可能需代理
- 提交：5f81af4、daf4a2a

### 2026-06-14 16:13 +08:00 - Codex - 源池治理第一轮：补充稳定电商 RSS

- 目标：缓解真实可用电商信息源不足的问题，先补充一批能自动采集、可解析、有条目的高质量 RSS 源。
- 改动：
  - `feeds/ecommerce.example.opml`：新增 13 个已验证 RSS 源，覆盖广告投流、独立站、私域营销、跨境 marketplace、零售动态、物流履约、支付和电商 SEO。
  - 新增源包括 AdExchanger、ChannelX、Drip Blog、Ecommerce Germany News、HubSpot Sales Ecommerce、InternetRetailing、Marketing Dive、Omnisend Blog、PYMNTS Retail、Search Engine Journal Ecommerce、ShipBob Blog、Social Media Today、Stripe Blog。
- 验证：
  - 使用 `D:/python.exe` 解析 OPML，结果：XML 合法，feed_count=68，重复 URL=0。
  - 使用 `requests + feedparser` 验证 13 个新增 RSS，结果：全部 HTTP 200 且能解析到条目。
  - 运行 `D:/python.exe scripts/update_news.py --output-dir data --window-hours 24 --rss-opml feeds/ecommerce.example.opml --rss-max-feeds 0 --web-sources feeds/ecommerce.web-sources.json --web-max-sources 0 --topic ecommerce`，采集跑通；严格当天门槛下 `daily-brief.json` 仍为 0 条，说明日报不能靠低质量内容补量。
  - `Retail Gazette` 在单独验证时可用，但完整流水线触发 429 限流，已撤掉，不进入默认 OPML。
- 影响：
  - 下次 GitHub Actions 会自动采集新增 RSS。
  - 不影响飞书推送代码。
  - 不修改 `data/*.json` 的提交策略，本次采集产生的数据变更不提交。
- 未完成/风险：
  - 新增源主要补足海外电商、投流、营销和履约信息；国内平台官方规则仍需要靠 P1 代理源和后续专项治理。
  - 日报仍缺当天高优先级内容，下一步需要继续补国内内容电商、平台规则代理、公众号真实 URL 和高价值论坛/社区源。
- 提交：d939c11

### 2026-06-14 - Claude Code - 飞书推送集成进 GitHub Actions

- 目标：飞书推送完全自动化，不依赖本机手动触发。
- 改动：
  - `.github/workflows/update-news.yml`：采集后新增两步：
    1. 精选实时提醒（每次 CI 跑都执行，有去重）
    2. 每日日报（UTC 01:00-01:29 触发，对应北京时间 09:00）
  - 两步均通过 `FEISHU_APP_ID` 环境变量判断是否启用，secrets 未配置时自动跳过
- 验证：workflow 语法已人工检查，脚本本身已验证可用
- 影响：需要在 GitHub 仓库 Settings → Secrets 配置3个 secret（见下）
- 未完成/风险：
  - **必须手动配置 GitHub Secrets** 才能生效，否则两步会被跳过（不报错）
  - `data/feishu-pushed.json` 去重状态由 CI commit 回仓库，首次运行后生效
- 提交：待提交
