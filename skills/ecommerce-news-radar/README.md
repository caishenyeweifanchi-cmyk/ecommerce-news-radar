# Ecommerce News Radar Skill

给 Agent 安装这个 Skill 后，Agent 每天读取仓库里的 `data/daily-brief.json`，优先输出官方平台新规、违规治理、商家规则、投流规则和跨境电商变化。

重点规则：

- 官方电商平台规则更新必须进入日报。
- `api_list` / `list` 是真实条目级采集。
- `page_snapshot` 是页面变化监控，不等同于已抓到页面内全部规则明细。
- 日报为空时，回退读取 `stories-merged.json` 和 `latest-24h.json`。

