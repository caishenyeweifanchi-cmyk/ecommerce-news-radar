# Ecommerce News Radar

An ecommerce-focused news radar adapted from `LearnPrompt/ai-news-radar`.

This fork tracks ecommerce sources instead of AI news:

- marketplace policy updates
- content commerce trends
- cross-border ecommerce
- retail and brand growth
- performance marketing and ad signals
- supply chain, logistics, payment, and compliance updates
- public RSS / OPML / media / announcement sources

Repository:

https://github.com/caishenyeweifanchi-cmyk/ecommerce-news-radar

## Status

- Ecommerce topic profile enabled
- Ecommerce scoring rules added
- Ecommerce OPML source list added
- GitHub Actions configured for scheduled updates
- Default schedule: every 30 minutes
- Static web UI reads generated `data/*.json`

## Local preview

```powershell
D:\python.exe -m http.server 8097 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8097/
```

## Manual data refresh

```powershell
D:\python.exe scripts/update_news.py --topic ecommerce --output-dir data --window-hours 24 --archive-days 21 --rss-opml feeds/ecommerce.example.opml --rss-max-feeds 0 --translate-max-new 0
```

For a 7-day observation window:

```powershell
D:\python.exe scripts/update_news.py --topic ecommerce --output-dir data --window-hours 168 --archive-days 21 --rss-opml feeds/ecommerce.example.opml --rss-max-feeds 0 --translate-max-new 0
```

## Add sources

Prefer standard RSS / Atom sources.

Edit:

```text
feeds/ecommerce.example.opml
```

Add:

```xml
<outline
  text="Source name"
  title="Source name"
  type="rss"
  xmlUrl="RSS URL"
  htmlUrl="Website URL"
/>
```

Sources that usually need custom adapters:

- Douyin ecommerce rule pages
- Xiaohongshu business / Pugongying announcements
- Taobao / Tmall merchant announcements
- JD merchant announcements
- Kuaishou ecommerce rules
- TikTok Shop official announcements
- login-gated analytics platforms
- WeChat public accounts

## How scheduled updates work

GitHub Actions config:

```text
.github/workflows/update-news.yml
```

Schedule:

```yaml
schedule:
  - cron: "*/30 * * * *"
```

The workflow:

1. checks out the repository
2. installs Python dependencies
3. loads `feeds/ecommerce.example.opml`
4. runs `scripts/update_news.py --topic ecommerce`
5. writes `data/*.json`
6. commits the updated data
7. GitHub Pages serves the static UI

## Output files

- `data/latest-24h.json`
- `data/latest-24h-all.json`
- `data/source-status.json`
- `data/daily-brief.json`
- `data/stories-merged.json`
- `data/merge-log.json`
- `data/archive.json`

## Limits

This is a public-source radar, not a login-state scraper.

It does not replace browser plugins, cloud-phone collectors, or private platform crawlers for Xiaohongshu, Douyin, analytics dashboards, live rooms, product sales, or add-to-cart data.

## Validation

```powershell
D:\python.exe -m pytest -q
```

Current result:

```text
85 passed
```

## License

Based on:

https://github.com/LearnPrompt/ai-news-radar

MIT License.
