"""
中国电动汽车百人会（chinaev100.com）爬虫。
政策解读最权威的智库，重大政策风向基本在这里首发。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper

CHINAEV100_BASE_URL = "https://www.chinaev100.com"
CHINAEV100_LIST_URL = "https://www.chinaev100.com/news/list"


class ChinaEV100Scraper(IndustryBaseScraper):
    """百人会爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.chinaev100.com/",
    }

    def __init__(self):
        super().__init__(source_name="百人会")

    def _parse_list_page(self, page: int) -> list[dict]:
        url = f"{CHINAEV100_LIST_URL}?page={page}"
        print(f"[百人会] 正在抓取第 {page} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[百人会] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for li in soup.select(".newfocusx_list li"):
            a_tag = li.select_one(".tit a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 6:
                continue
            if not href.startswith("http"):
                href = CHINAEV100_BASE_URL + href

            pub_date = ""
            time_el = li.select_one(".timefrist")
            if time_el:
                raw = time_el.get_text(strip=True)
                # 格式: 2026/04/03
                m = re.match(r"(\d{4})/(\d{2})/(\d{2})", raw)
                if m:
                    pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            items.append({"title": title, "url": href, "pub_date": pub_date})

        print(f"[百人会] 第 {page} 页共找到 {len(items)} 条")
        return items

    def scrape(self, year_month: str, max_pages: int = 3):
        all_items = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            items = self._parse_list_page(page)
            if not items:
                break

            stop = False
            for item in items:
                pub_date = item["pub_date"]
                item_ym = pub_date[:7] if pub_date else ""

                if item_ym and item_ym < year_month:
                    stop = True
                    break

                if item_ym != year_month:
                    continue

                if item["url"] in seen_urls:
                    continue
                seen_urls.add(item["url"])

                record = self.make_record(
                    title=item["title"],
                    pub_date=pub_date,
                    source="百人会",
                    sub_industry="新能源汽车",
                    url=item["url"],
                )
                if record:
                    all_items.append(record)

            if stop:
                break
            self.random_delay()

        print(f"[百人会] {year_month} 筛选出 {len(all_items)} 条")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[百人会] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[百人会] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
