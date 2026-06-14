# 开源项目信源扩展调研

> 日期：2026-06-14
> 目标：解决电商热点雷达“真实可用信号源不足”的问题，优先寻找能接入现有 RSS/OPML/web-sources 流水线的开源项目。

## 结论

可用开源项目分三类：

1. **RSS 生成基础设施**：解决“目标网站没有 RSS”的问题，需要我们部署或接入实例。
2. **现成 OPML / Feed 清单**：解决“AI/科技/商业信源不够”的问题，可以筛选后直接并入 `feeds/ecommerce.example.opml`。
3. **微信公众号/中文内容桥接**：解决“国内运营、内容电商、公众号源少”的问题，但需要更谨慎，因为登录态、版权、稳定性风险更高。

优先级建议：

- P0：接入更多稳定 OPML / RSS 清单，先扩大 AI 情报池和电商运营池。
- P1：把 RSSHub / RSS-Bridge 作为可选基础设施，不默认依赖。
- P2：公众号桥接项目只做私有部署候选，不直接放进公开默认流水线。

## 候选项目

### 1. DIYgod/RSSHub

- 地址：https://github.com/DIYgod/RSSHub
- GitHub API 查询结果：约 44k stars。
- 作用：把很多没有 RSS 的网站、社交平台、内容平台转换成 RSS。
- 对本项目价值：
  - 可用于补国内内容源、平台动态源、社区源。
  - 适合作为“私有 RSSHub 实例 + OPML 接入”的扩展路线。
- 风险：
  - 部分 route 需要反爬、登录态、Puppeteer 或代理。
  - 不建议把公共不稳定 route 直接作为 P0 默认源。
- 推荐接入方式：
  - 先做 `RSSHUB_BASE_URL` 可选环境变量。
  - 默认不开启，只在用户自己部署 RSSHub 后接入。

### 2. RSS-Bridge/rss-bridge

- 地址：https://github.com/RSS-Bridge/rss-bridge
- GitHub API 查询结果：约 9k stars。
- 作用：给缺少 RSS 的网站生成 RSS feed。
- 对本项目价值：
  - 可以作为 RSSHub 的备选基础设施。
  - 对英文站、论坛、博客更适合；国内平台支持不一定强。
- 风险：
  - 也需要自部署或找稳定实例。
  - 仍需逐个 bridge 验证时间、标题、详情页 URL。
- 推荐接入方式：
  - 作为 P1 基础设施方案记录，不先写入默认源。

### 3. cooderl/wewe-rss

- 地址：https://github.com/cooderl/wewe-rss
- GitHub API 查询结果：约 9.5k stars。
- 作用：微信公众号订阅和 RSS 生成。
- 对本项目价值：
  - 适合补国内电商运营、投流、平台规则解读类公众号。
  - 可以大幅提升“中文真实运营信号源”的覆盖。
- 风险：
  - 需要私有化部署和账号侧能力。
  - 不适合公共仓库默认源，不应提交 Cookie、账号、私有订阅。
- 推荐接入方式：
  - 私有部署后输出 RSS，再通过 `FOLLOW_OPML_B64` 或私有 OPML 接入。
  - 公开仓库只保留示例和说明，不放真实私有公众号源。

### 4. rachelos/we-mp-rss

- 地址：https://github.com/rachelos/we-mp-rss
- GitHub API 查询结果：约 3.5k stars。
- 作用：微信公众号文章订阅、导出、RSS、Webhook、AI Agent 接入。
- 对本项目价值：
  - 和“公众号信源采集”目标更贴近。
  - 可能适合后续把公众号文章转成电商热点候选池。
- 风险：
  - 同样属于私有化/账号相关能力。
  - 需要单独评估合规、稳定性和数据格式。
- 推荐接入方式：
  - 作为 P2 研究方向，不进入默认自动流水线。

### 5. RSS-Renaissance/awesome-AI-feeds

- 地址：https://github.com/RSS-Renaissance/awesome-AI-feeds
- GitHub API 查询结果：约 90 stars。
- 实测：
  - `feedlist.opml` 可下载，但 XML 解析失败，疑似包含非法字符。
- 对本项目价值：
  - 可作为 AI 情报源候选库。
  - 不建议直接批量导入，需先清洗 OPML。
- 推荐接入方式：
  - 写一个候选导入脚本，清洗 OPML 后只挑稳定官方/媒体源。

### 6. alan-turing-institute/ai-rss-feeds

- 地址：https://github.com/alan-turing-institute/ai-rss-feeds
- 实测：
  - OPML 可解析，约 12 个 feed。
  - feed 指向该仓库生成的 raw XML，如 Anthropic、Claude、AISI、Allen AI 等。
- 对本项目价值：
  - 适合补“没有稳定官方 RSS 或官方源易变”的 AI 源。
  - 可用于 AI 情报板块，不一定进电商首页。
- 风险：
  - 不是原站官方 feed，而是 GitHub 生成 feed，需要信任该项目维护。
- 推荐接入方式：
  - 先挑 3-5 个与现有源不重复的 AI 官方/研究源进入 AI 情报池。

### 7. xiangyugongzuoliu/awesome-rss-feeds

- 地址：https://github.com/xiangyugongzuoliu/awesome-rss-feeds
- GitHub API 查询结果：约 43 stars。
- 实测：
  - `feeds/en-ai-research.opml` 可解析，约 80 个 feed。
- 对本项目价值：
  - 可作为大规模 AI 候选源池。
  - 适合补 AI 情报板块，而不是直接进今日必看。
- 风险：
  - 含 X bridge、研究博客、泛 AI 内容，噪音较多。
  - 需要按“模型能力能否迁移电商场景”二次打分。
- 推荐接入方式：
  - 不直接全量导入；先筛官方、模型、工具、自动化相关源。

### 8. tuan3w/awesome-tech-rss

- 地址：https://github.com/tuan3w/awesome-tech-rss
- GitHub API 查询结果：约 688 stars。
- 实测：
  - `feeds.opml` 可解析，约 143 个 feed。
- 对本项目价值：
  - 能补一部分产品、创业、技术商业源。
  - 对电商直接价值中等。
- 风险：
  - 泛科技/创业内容多，容易污染首页。
- 推荐接入方式：
  - 只作为“AI 情报/扩展候选”，不直接进电商首页。

### 9. plenaryapp/awesome-rss-feeds

- 地址：https://github.com/plenaryapp/awesome-rss-feeds
- GitHub API 查询结果：约 2.4k stars。
- 作用：推荐 RSS 和本地新闻 OPML 清单。
- 对本项目价值：
  - 可以从商业、科技、零售新闻里补宽源。
- 风险：
  - 过宽，绝大多数不适合电商运营日报。
- 推荐接入方式：
  - 仅用于离线挖源，不作为默认导入源。

### 10. vishalshar/awesome_ML_AI_RSS_feed

- 地址：https://github.com/vishalshar/awesome_ML_AI_RSS_feed
- GitHub API 查询结果：约 289 stars。
- 作用：机器学习、AI、强化学习 RSS 清单。
- 对本项目价值：
  - 可以扩 AI 情报池，但偏研究。
- 风险：
  - 研究论文/学术源多，电商转化价值低。
- 推荐接入方式：
  - 只挑模型、工具、自动化、图像/视频生成相关源。

## 推荐落地方案

### 第一步：新增“外部源清单导入脚本”

新增脚本建议：

```text
scripts/import_external_feeds.py
```

功能：

- 读取外部 OPML 或 GitHub raw URL。
- 提取 `title/xmlUrl/htmlUrl`。
- 去重当前 `feeds/ecommerce.example.opml` 已有 URL。
- 按规则打标签：
  - `ai_official`
  - `ai_tools`
  - `ecommerce_operations`
  - `marketing_ads`
  - `cross_border`
  - `candidate_only`
- 输出候选文件，不直接写默认 OPML：

```text
feeds/external-feed-candidates.json
```

### 第二步：先接 20-40 个高质量源，不全量导入

优先从这些项目筛：

- `alan-turing-institute/ai-rss-feeds`
- `xiangyugongzuoliu/awesome-rss-feeds`
- `tuan3w/awesome-tech-rss`
- `RSS-Renaissance/awesome-AI-feeds`

筛选标准：

- 官方模型/工具/平台源优先。
- AI 图像、视频、Agent、自动化、营销工具优先。
- 泛研究、泛科技、个人博客、X bridge 默认不进首页。

### 第三步：把 RSSHub/wewe-rss 作为“私有增强层”

不建议现在就把 RSSHub 或公众号桥接写死进默认 workflow。

更稳的做法：

- 在 README 或 docs 里增加“私有信源增强方案”。
- 支持用户自己部署 RSSHub / wewe-rss 后，把 OPML 放进 `FOLLOW_OPML_B64`。
- 默认公开仓库仍保持可运行，不依赖 Cookie、登录态或私有服务。

## 当前不建议做的事

- 不要把所有 awesome feed 全量导入。
- 不要把 RSSHub 公共实例 route 当 P0 生产源。
- 不要把微信公众号账号/Cookie/私有订阅写进仓库。
- 不要让跨境/泛科技/AI 研究源再次霸屏电商首页。

## 下一步可执行任务

1. 写 `scripts/import_external_feeds.py`。
2. 导入并清洗 `alan-turing-institute/ai-rss-feeds` 和 `xiangyugongzuoliu/en-ai-research.opml`。
3. 输出 `feeds/external-feed-candidates.json`。
4. 人工/LLM 选出第一批 30 个候选：
   - 15 个 AI 情报源
   - 10 个 AI 电商可迁移源
   - 5 个电商运营/营销源
5. 验证 30 个 feed 的 HTTP 状态、更新时间、条目数量。
6. 只把验证通过且低噪音的源写入 `feeds/ecommerce.example.opml`。
