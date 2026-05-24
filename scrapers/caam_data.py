"""
中国汽车工业协会（CAAM）数据爬虫。
抓取 caam.org.cn 的新能源汽车产销数据和行业统计分析。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper


CAAM_BASE_URL = "https://www.caam.org.cn"
# 数据发布列表页
CAAM_DATA_URL = "https://www.caam.org.cn/chn/4/cate_30/list_1.html"

# 标题关键词过滤：只保留数据类文章
CAAM_DATA_KEYWORDS = [
    "产销", "销量", "新能源汽车", "汽车工业", "经济运行",
    "乘用车", "商用车", "出口", "数据", "统计",
    "月度", "月份", "季度", "前",
]


class CAAMScraper(IndustryBaseScraper):
    """中汽协数据爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.caam.org.cn/",
    }

    def __init__(self):
        super().__init__(source_name="中汽协")

    def _is_relevant(self, title: str) -> bool:
        for kw in CAAM_DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, page: int = 1) -> list[dict]:
        url = CAAM_DATA_URL.replace("list_1", f"list_{page}")
        print(f"[中汽协] 正在抓取第 {page} 页: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[中汽协] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for li in soup.select("li"):
            a_tag = li.select_one("a[href]")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 5:
                continue
            if href.startswith("/"):
                href = CAAM_BASE_URL + href

            pub_date = ""
            span = li.select_one("span")
            if span:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", span.get_text(strip=True))
                if m:
                    pub_date = m.group(1)

            items.append({"title": title, "url": href, "pub_date": pub_date})

        print(f"[中汽协] 第 {page} 页找到 {len(items)} 条")
        return items

    def scrape(self, year_month: str, max_pages: int = 3):
        all_records = []
        for page in range(1, max_pages + 1):
            items = self._parse_list_page(page)
            if not items:
                break
            for item in items:
                title, pub_date, url = item["title"], item["pub_date"], item["url"]
                if pub_date and not pub_date.startswith(year_month):
                    continue
                if not self._is_relevant(title):
                    continue
                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="中汽协",
                    sub_industry="新能源汽车",
                    summary="",
                    url=url,
                )
                if record:
                    all_records.append(record)
            self.random_delay()

        print(f"[中汽协] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[中汽协] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[中汽协] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
