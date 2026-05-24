"""
美国能源信息署（EIA）Today in Energy 爬虫。
通过 RSS 源抓取: https://www.eia.gov/rss/todayinenergy.xml
"""

import time
from email.utils import parsedate_to_datetime

import feedparser
import requests

from scrapers.intl_base import IntlBaseScraper
from scrapers.intl_config import EIA_RSS_URL


class EIAScraper(IntlBaseScraper):
    """EIA Today in Energy RSS 爬虫。"""

    def __init__(self):
        super().__init__(source_name="EIA")

    def _parse_date(self, entry) -> str:
        """从 RSS entry 解析日期为 YYYY-MM-DD 格式。"""
        published = entry.get("published", "")
        if not published:
            return ""
        try:
            dt = parsedate_to_datetime(published)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    def scrape(self, year_month: str) -> list[dict]:
        """抓取 EIA RSS 并筛选指定月份的文章。"""
        print(f"[EIA] 正在抓取 RSS: {EIA_RSS_URL}")

        try:
            resp = requests.get(EIA_RSS_URL, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except requests.RequestException as e:
            print(f"[EIA] 请求失败: {e}")
            return []

        if feed.bozo and not feed.entries:
            print(f"[EIA] RSS 解析失败: {feed.bozo_exception}")
            return []

        print(f"[EIA] RSS 共 {len(feed.entries)} 条")

        # 先收集需要翻译的条目
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
            if not self.is_relevant(title_en):
                continue

            relevant_items.append({
                "title_en": title_en,
                "link": link,
                "pub_date": pub_date,
                "summary_en": summary_en[:200] if summary_en else "",
            })

        if not relevant_items:
            print(f"[EIA] {year_month} 筛选出 0 条")
            return []

        # 批量翻译
        titles_en = [item["title_en"] for item in relevant_items]
        titles_cn = self.translate_titles_batch(titles_en)

        all_records = []
        for item, title_cn in zip(relevant_items, titles_cn):
            sub_industry = self.classify_industry(item["title_en"])
            record = self.make_intl_record(
                title=title_cn,
                title_en=item["title_en"],
                pub_date=item["pub_date"],
                source="EIA",
                sub_industry=sub_industry,
                summary=item["summary_en"],
                url=item["link"],
            )
            all_records.append(record)

        print(f"[EIA] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[EIA] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[EIA] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
