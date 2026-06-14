#!/usr/bin/env python3
"""
wx_fetcher.py — 微信公众号文章抓取

模拟微信内置浏览器 UA，绕过"环境异常"验证，抓取 mp.weixin.qq.com 文章。

单条用法:
  D:/python.exe scripts/wx_fetcher.py https://mp.weixin.qq.com/s/xxx

批量用法 (从 feeds/wx-accounts.json 读账号列表):
  D:/python.exe scripts/wx_fetcher.py --batch
  D:/python.exe scripts/wx_fetcher.py --batch --output data/wx-articles.json

输出 JSON 格式与 ai-radar.json items 兼容，可直接合并进采集流水线。
"""

from __future__ import annotations

import argparse
import io
import json
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

# 模拟微信内置浏览器 UA（服务器认为请求来自微信客户端）
WX_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Mobile/15E148 MicroMessenger/8.0.47(0x18002f2f) "
    "NetType/WIFI Language/zh_CN"
)

WX_HEADERS = {
    "User-Agent": WX_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://mp.weixin.qq.com/",
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch_article(url: str) -> dict:
    """抓取单篇微信文章，返回标准化 item dict。"""
    req = urllib.request.Request(url, headers=WX_HEADERS)
    try:
        resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}

    # 标题：优先 og:title
    title = "未知标题"
    m = re.search(r'property="og:title"\s+content="([^"]*)"', html)
    if m:
        title = m.group(1).strip()
    else:
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            title = m.group(1).strip()

    # 作者/公众号名
    account = ""
    m = re.search(r'var\s+nickname\s*=\s*"([^"]+)"', html)
    if m:
        account = m.group(1)

    # 发布时间
    pub_date = ""
    m = re.search(r'var\s+ct\s*=\s*"(\d+)"', html)
    if m:
        try:
            ts = int(m.group(1))
            pub_date = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except Exception:
            pass

    # 正文
    content = ""
    m = re.search(
        r'id="js_content"[^>]*>(.*?)</div>\s*(?:<script|<div\s+class="rich_media_tool)',
        html, re.DOTALL,
    )
    if m:
        raw = m.group(1)
        content = re.sub(r"<[^>]+>", " ", raw)
        content = re.sub(r"\s+", " ", content).strip()[:2000]

    if not content:
        return {"success": False, "url": url, "error": "无法提取正文（可能需登录或已删除）", "title": title}

    return {
        "success": True,
        "id": f"wx_{abs(hash(url)):x}",
        "site_id": "wechat_mp",
        "site_name": account or "微信公众号",
        "source": account or "微信公众号",
        "title": title,
        "title_zh": title,
        "url": url,
        "published_at": pub_date,
        "first_seen_at": datetime.now(timezone.utc).isoformat(),
        "content_snippet": content[:500],
        "ai_label": "",          # 由后续 AI 相关性评分填充
        "ai_is_related": None,
        "ai_score": None,
    }


def batch_fetch(accounts_path: Path, output_path: Path, delay: float = 1.5) -> list[dict]:
    """
    从 feeds/wx-accounts.json 批量抓取。
    格式: [{"name": "公众号名", "recent_urls": ["https://mp.weixin.qq.com/s/xxx", ...]}]
    """
    if not accounts_path.exists():
        print(f"错误：找不到账号列表 {accounts_path}", file=sys.stderr)
        return []

    accounts = json.loads(accounts_path.read_text(encoding="utf-8"))
    results = []
    total = sum(len(a.get("recent_urls", [])) for a in accounts)
    done = 0

    for account in accounts:
        name = account.get("name", "未知")
        urls = account.get("recent_urls", [])
        for url in urls:
            done += 1
            print(f"[{done}/{total}] {name} — {url[:60]}...")
            item = fetch_article(url)
            if item.get("success"):
                item["source"] = name
                item["site_name"] = name
                results.append(item)
                print(f"  ✓ {item['title'][:50]}")
            else:
                print(f"  ✗ {item.get('error', '未知错误')}")
            if done < total:
                time.sleep(delay)

    if output_path:
        output_path.write_text(
            json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                        "items": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n共抓取 {len(results)}/{total} 条，写入 {output_path}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="微信公众号文章抓取")
    parser.add_argument("url", nargs="?", help="单篇文章 URL")
    parser.add_argument("--batch", action="store_true", help="批量模式（读 feeds/wx-accounts.json）")
    parser.add_argument("--accounts", default="feeds/wx-accounts.json", help="账号列表文件")
    parser.add_argument("--output", default="data/wx-articles.json", help="输出文件")
    parser.add_argument("--delay", type=float, default=1.5, help="请求间隔秒数（默认1.5）")
    args = parser.parse_args()

    if args.batch:
        batch_fetch(
            ROOT / args.accounts,
            ROOT / args.output,
            delay=args.delay,
        )
    elif args.url:
        result = fetch_article(args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
