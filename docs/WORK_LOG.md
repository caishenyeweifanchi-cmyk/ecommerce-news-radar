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
8. **Agent 间异步对话**：做完任务后如果有想法、疑问或建议想传达给另一个 Agent，直接写在本次记录末尾的 `【给下一个 Agent 的话】` 块里。另一个 Agent 读完后在自己的记录开头的 `【回复上一个 Agent】` 块里回应。用户不需要转述，Agent 自己读日志就能接收。

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

### 2026-06-14 17:52 +08:00 - Codex - 检查 MiniMax/Mimo 接入并修复 GitHub Actions 条件判断

- 目标：确认 MiniMax/Mimo LLM 二次打分是否安全接入自动流水线，并修复 GitHub Actions 中 secrets/env 判断不稳的问题。
- 改动：
  - `.github/workflows/update-news.yml`：移除直接在 `if:` 中判断 `secrets` 或 step-level `env` 的写法，改为进入步骤后在 shell 内检查 `MINIMAX_API_KEY`、`MIMO_API_KEY`、飞书 secrets 是否配置；未配置时正常跳过，不让 workflow 失败。
- 验证：
  - 运行 `D:/python.exe -m py_compile scripts/llm_scorer.py scripts/update_news.py scripts/feishu_alert.py scripts/feishu_push.py`，通过。
  - 扫描已跟踪代码、workflow、Markdown、feeds 文件中的 MiniMax/OpenAI 常见明文密钥模式，未发现明文 Key。
  - 确认 `.env` 为 ignored 文件，没有进入 Git 跟踪。
- 影响：
  - MiniMax/Mimo 二次打分会在 GitHub Actions 中由项目自动执行；未配置 secret 时自动跳过。
  - 飞书精选提醒和每日日报同样改为 shell 内检查 secrets，避免 `if:` 上下文拿不到 step env 导致误跳过。
  - 不提交 `data/*.json`。
- 未完成/风险：
  - 用户截图中暴露了完整 MiniMax API Key，应尽快在 MiniMax 后台作废并重新生成，再更新本机 `.env` 和 GitHub Actions secrets。
  - 当前 `scripts/llm_scorer.py`、`scripts/feishu_alert.py`、`assets/app.js`、`assets/styles.css` 仍有未提交改动，疑似 Claude 正在开发；本次不提交这些文件。
- 提交：6b74a1c

---

## 2026-06-14 LLM摘要+影响力展示功能上线

**任务**：给每条精选加中文摘要、加"对你意味着"、飞书卡片同步更新（用户要求三项）

**变更文件**：
- `scripts/llm_scorer.py` — 扩展 SYSTEM_PROMPT 输出 summary_zh + impact_zh；`batch_score` 同时写入所有 item 数组（items_ai、items、items_all 等）
- `.github/workflows/update-news.yml` — 在 ai-radar.json 打分后也对 latest-24h.json 执行打分
- `assets/app.js` — 卡片渲染加 `.card-summary` 段落；impact 前缀"对你意味着："
- `assets/styles.css` — 新增 `.card-summary` 样式（3行截断、muted色）
- `scripts/feishu_alert.py` — 卡片 body 优先用 summary_zh，展示"对你意味着"和来源
- `index.html` — 缓存版本号升至 ecommerce-console-0614-llmsummary

**根因发现**：scorer 原来只写 `data["items"]`，但前端读 `data["items_ai"]`，导致 summary_zh 永远进不了卡片。已修复为遍历所有数组。

**验证**：
- renderItemNode() 手动调用确认 `.card-summary` 正确渲染
- 数据管道逻辑核对通过（items_ai ai_score=0.68 在打分区间内）
- 已清理测试条目（"抖音电商2026"手动注入项已移除）

**commit**：4aecb01

**剩余风险**：
- 首次 GitHub Actions 运行后才能看到真实 summary_zh 展示效果（需等下一个整点触发）
- LLM 每次都对同一 item 重新打分（无去重缓存），稍微耗费 API token，但量小可接受

---

## 2026-06-14 协作规则更新：Agent 间异步对话机制

**变更**：在协作规则第 8 条加入 Agent 间对话约定——做完任务可在记录末尾写「给下一个 Agent 的话」，对方读日志后在自己的记录开头写「回复上一个 Agent」，实现异步沟通，不依赖用户转述。

**commit**：见下一条

---

【给下一个 Agent 的话】（Claude Code → Codex）

你好，我是 Claude Code。最近做了 LLM 摘要功能（commit 4aecb01），有几个问题想问你：

1. `llm_scorer.py` 现在每次都对同一条 item 重新打分，没有缓存已打分的 id。量小时没问题，但如果 archive 条目多起来会浪费 token。你有没有想法加一个「已打分 id 集合」跳过重复打分？

2. `feishu_alert.py` 里有一个 `feishu-pushed.json` 记录已推送条目，防止重复推。但 `llm_scorer.py` 没有类似机制。建议加 `data/llm-scored.json` 记录已处理的 item id，你觉得值得做吗？

3. 目前 MiniMax 是主力、Mimo 是备用，但没有监控哪个 API 在实际生产中成功率更高。如果你以后有机会看 Actions 日志，能不能顺手记录一下两个 API 的成功/失败情况？

