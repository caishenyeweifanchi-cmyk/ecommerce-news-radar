# Claude Code Notes

Before changing this project, read:

- `docs/WORK_LOG.md`
- `skills/ai-news-radar/SKILL.md`
- `docs/SOURCE_COVERAGE.md`
- `README.md`

After every task, append a short entry to `docs/WORK_LOG.md` explaining:

- what you changed
- which files you touched
- what you verified
- what remains risky or unfinished
- the commit id, if you committed

Codex and Claude Code both use this file as the shared handoff log. If a change is not written there, the next agent should treat it as unknown.

Agents may also use `docs/WORK_LOG.md` for asynchronous discussion:

- If you finish a task and have a question, suggestion, risk, or implementation idea for the next agent, write a short `给下一个 Agent 的话` section at the end of your own work-log entry.
- If the previous agent left a question, answer it in your new entry under `回复上一个 Agent` before describing your own work.
- Keep the exchange technical and actionable. Do not put secrets, API keys, cookies, private OPML, or generated data snapshots into the discussion.

## 核心原则：项目必须完全自动运行

**任何功能必须在没有 Claude Code 或 Codex 介入的情况下持续运转。**

- 采集、评分、分类、推送全部由 GitHub Actions 定时触发（每30分钟）
- Claude Code / Codex 只负责改代码和配置，不负责触发日常运行
- 新增信源必须写入 `feeds/ecommerce.example.opml` 或 `feeds/ecommerce.web-sources.json`，GitHub Actions 会自动读取
- 飞书推送脚本如需自动执行，必须集成进 GitHub Actions workflow，不能只靠本机手动运行
- 如果某个能力还需要人工触发，必须在 WORK_LOG.md 里标记为"未产品化"，不能说已完成

Do not commit private OPML files, API keys, cookies, browser exports, or `.env`
values. Keep the public repo usable without secrets.

The product direction is a two-layer AI news tool:

- Default layer: curated AI-focused view for ordinary AI enthusiasts.
- Advanced layer: custom OPML/source configuration and source health details for maintainers.

When adding sources, prefer official RSS/Atom feeds or OPML first. Add custom
fetchers only for stable, public, high-signal sources.
