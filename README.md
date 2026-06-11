# 电商热点雷达

这是一个自动更新的电商信息收集与热点雷达，基于开源项目 `LearnPrompt/ai-news-radar` 改造而来。

它的目标不是做 AI 新闻，而是持续追踪：

- 电商平台规则
- 内容电商趋势
- 跨境电商动态
- 品牌与投流营销
- 供应链、物流、支付、合规信息
- 公开 RSS / OPML / 公告页 / 媒体站信息源

当前仓库地址：

https://github.com/caishenyeweifanchi-cmyk/ecommerce-news-radar

## 当前状态

- 已改成电商主题页面
- 已新增电商相关性评分规则
- 已新增电商 RSS 信息源清单
- 已配置 GitHub Actions 自动更新
- 默认每 30 分钟检查一次信息源
- 页面读取 `data/*.json`，不需要后端服务器

## 本地预览

在项目目录运行：

```powershell
D:\python.exe -m http.server 8097 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:8097/
```

## 手动刷新数据

运行：

```powershell
D:\python.exe scripts/update_news.py --topic ecommerce --output-dir data --window-hours 24 --archive-days 21 --rss-opml feeds/ecommerce.example.opml --rss-max-feeds 0 --translate-max-new 0
```

如果想临时扩大观察窗口，比如看近 7 天：

```powershell
D:\python.exe scripts/update_news.py --topic ecommerce --output-dir data --window-hours 168 --archive-days 21 --rss-opml feeds/ecommerce.example.opml --rss-max-feeds 0 --translate-max-new 0
```

## 怎么添加信息源

优先添加标准 RSS / Atom 源。

编辑：

```text
feeds/ecommerce.example.opml
```

增加一段：

```xml
<outline
  text="信息源名称"
  title="信息源名称"
  type="rss"
  xmlUrl="RSS地址"
  htmlUrl="网站首页地址"
/>
```

适合直接添加的源：

- 电商媒体 RSS
- 平台公告 RSS
- 跨境电商媒体 RSS
- 自己整理后的 OPML / RSS

不适合直接加 OPML、需要写专门适配器的源：

- 抖音电商规则中心
- 小红书商业 / 蒲公英公告
- 淘宝天猫商家公告
- 京东商家公告
- 快手电商规则
- TikTok Shop 官方公告
- 灰豚、蝉妈妈等登录态或会员后台
- 微信公众号

## 自动更新原理

GitHub Actions 配置在：

```text
.github/workflows/update-news.yml
```

定时规则：

```yaml
schedule:
  - cron: "*/30 * * * *"
```

意思是 GitHub 每 30 分钟自动运行一次采集脚本。

自动流程：

1. GitHub Actions 拉取仓库
2. 安装 Python 依赖
3. 读取 `feeds/ecommerce.example.opml`
4. 执行 `scripts/update_news.py --topic ecommerce`
5. 生成 `data/*.json`
6. 自动提交更新后的数据
7. GitHub Pages 页面读取这些 JSON

所以它不是浏览器一直开着实时抓，而是云端定时检查信息源。

## 输出数据

核心输出文件：

- `data/latest-24h.json`：当前窗口内电商强相关信息
- `data/latest-24h-all.json`：当前窗口内全量候选信息
- `data/source-status.json`：信息源健康状态
- `data/daily-brief.json`：精选故事线
- `data/stories-merged.json`：合并后的事件节点
- `data/merge-log.json`：合并记录
- `data/archive.json`：归档数据

## 当前限制

当前版本是公开信息源雷达，不是登录态采集器。

它适合：

- 公开媒体
- 公开公告
- RSS / OPML
- 平台规则公开页
- 跨境电商资讯

它不适合直接替代：

- 小红书登录态采集
- 抖音后台采集
- 灰豚 / 蝉妈妈会员数据
- 商品加购、销量、直播间实时数据
- 微信公众号稳定自动抓取

这些需要浏览器插件、云手机或专门采集适配器。

## 验证

已运行：

```powershell
D:\python.exe -m pytest -q
```

结果：

```text
85 passed
```

## 来源与许可

本项目基于：

https://github.com/LearnPrompt/ai-news-radar

原项目许可证为 MIT，本仓库继续使用 MIT License。
