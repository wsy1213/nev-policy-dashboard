"""
动力电池产业创新联盟（CPBCS）数据爬虫。
抓取动力电池装车量、产量、出口等月度统计数据。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper


CPBCS_BASE_URL = "http://www.iccsz.com"

CPBCS_DATA_KEYWORDS = [
    "动力电池", "装车量", "电池产量", "电池产销",
    "月度数据", "月度", "统计", "运行情况",
    "锂电池", "出货量", "出口",
]


class CPBCSScraper(IndustryBaseScraper):
    """动力电池联盟数据爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self):
        super().__init__(source_name="动力电池联盟")

    def _is_relevant(self, title: str) -> bool:
        for kw in CPBCS_DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, url: str) -> list[dict]:
        print(f"[动力电池联盟] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[动力电池联盟] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for a_tag in soup.select("a[href]"):
            title = a_tag.get("title", "").strip() or a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 8:
                continue
            if not self._is_relevant(title):
                continue
            if href.startswith("/"):
                href = CPBCS_BASE_URL + href

            pub_date = ""
            parent = a_tag.parent
            if parent:
                text = parent.get_text()
                m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                if m:
                    pub_date = m.group(1)

            items.append({"title": title, "url": href, "pub_date": pub_date})

        # 去重
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        print(f"[动力电池联盟] 找到 {len(unique)} 条相关文章")
        return unique

    def scrape(self, year_month: str):
        items = self._parse_list_page(CPBCS_BASE_URL)
        all_records = []

        for item in items:
            title, pub_date, url = item["title"], item["pub_date"], item["url"]
            if pub_date and not pub_date.startswith(year_month):
                continue
            record = self.make_record(
                title=title,
                pub_date=pub_date,
                source="动力电池联盟",
                sub_industry="新能源汽车",
                summary="",
                url=url,
            )
            if record:
                all_records.append(record)

        print(f"[动力电池联盟] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[动力电池联盟] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[动力电池联盟] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
