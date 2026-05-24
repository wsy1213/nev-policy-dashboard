"""
InsideEVs 电动汽车新闻爬虫。
通过 RSS 获取全球电动汽车行业报道和销量数据。
"""

from email.utils import parsedate_to_datetime

import feedparser
import requests

from scrapers.intl_base import IntlBaseScraper


INSIDEEVS_RSS_URL = "https://insideevs.com/rss/news/all/"


class InsideEVsScraper(IntlBaseScraper):
    """InsideEVs RSS 爬虫。"""

    def __init__(self):
        super().__init__(source_name="InsideEVs")

    def _parse_date(self, entry) -> str:
        published = entry.get("published", "")
        if not published:
            return ""
        try:
            dt = parsedate_to_datetime(published)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    def scrape(self, year_month: str) -> list[dict]:
        print(f"[InsideEVs] 正在抓取 RSS: {INSIDEEVS_RSS_URL}")
        try:
            resp = requests.get(
                INSIDEEVS_RSS_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; NEVBot/1.0)",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                },
                timeout=20,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except requests.RequestException as e:
            print(f"[InsideEVs] 请求失败: {e}")
            return []

        if feed.bozo and not feed.entries:
            print(f"[InsideEVs] RSS 解析失败: {feed.bozo_exception}")
            return []

        print(f"[InsideEVs] RSS 共 {len(feed.entries)} 条")

        relevant_items = []
        for entry in feed.entries:
            title_en = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            pub_date = self._parse_date(entry)
            summary_en = entry.get("description", "").strip()

            if not title_en or not link:
                continue
            if pub_date and not pub_date.startswith(year_month):
                continue
            # InsideEVs 本身就是 EV 专业媒体，不需要关键词过滤
            if not self.is_relevant(title_en):
                continue

            relevant_items.append({
                "title_en": title_en,
                "link": link,
                "pub_date": pub_date,
                "summary_en": summary_en[:200] if summary_en else "",
            })

        if not relevant_items:
            print(f"[InsideEVs] {year_month} 筛选出 0 条")
            return []

        titles_en = [item["title_en"] for item in relevant_items]
        titles_cn = self.translate_titles_batch(titles_en)

        all_records = []
        for item, title_cn in zip(relevant_items, titles_cn):
            record = self.make_intl_record(
                title=title_cn,
                title_en=item["title_en"],
                pub_date=item["pub_date"],
                source="InsideEVs",
                sub_industry="新能源汽车",
                url=item["link"],
            )
            if record:
                all_records.append(record)

        print(f"[InsideEVs] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[InsideEVs] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[InsideEVs] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
