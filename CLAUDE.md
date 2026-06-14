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

Do not commit private OPML files, API keys, cookies, browser exports, or `.env`
values. Keep the public repo usable without secrets.

The product direction is a two-layer AI news tool:

- Default layer: curated AI-focused view for ordinary AI enthusiasts.
- Advanced layer: custom OPML/source configuration and source health details for maintainers.

When adding sources, prefer official RSS/Atom feeds or OPML first. Add custom
fetchers only for stable, public, high-signal sources.
