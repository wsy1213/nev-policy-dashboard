"""
国际能源署（IEA）新闻爬虫。
使用 requests + BeautifulSoup 抓取: https://www.iea.org/news
IEA 无可靠 RSS，走 HTML 解析 + 分页。
"""

import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.intl_base import IntlBaseScraper
from scrapers.intl_config import IEA_NEWS_URL


class IEAScraper(IntlBaseScraper):
    """IEA News HTML 爬虫。"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # 月份名称 → 数字映射
    MONTH_MAP = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }

    def __init__(self):
        super().__init__(source_name="IEA")

    def _parse_date(self, date_text: str) -> str:
        """解析 IEA 日期文本（如 '02 April 2026'）为 YYYY-MM-DD。"""
        if not date_text:
            return ""
        # 匹配 "DD Month YYYY" 或 "D Month YYYY"
        m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_text.strip())
        if not m:
            return ""
        day = m.group(1).zfill(2)
        month_name = m.group(2).lower()
        year = m.group(3)
        month = self.MONTH_MAP.get(month_name, "")
        if not month:
            return ""
        return f"{year}-{month}-{day}"

    def _parse_list_page(self, page: int) -> list[dict]:
        """解析 IEA 新闻列表页。"""
        url = f"{IEA_NEWS_URL}?page={page}" if page > 1 else IEA_NEWS_URL
        print(f"[IEA] 正在抓取第 {page} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[IEA] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        # IEA 列表: a.m-news-detailed-listing__link 包含完整文章条目
        for a in soup.select("a.m-news-detailed-listing__link"):
            href = a.get("href", "").strip()
            if not href:
                continue

            # 构建完整 URL
            if href.startswith("/"):
                full_url = f"https://www.iea.org{href}"
            else:
                full_url = href

            # 标题在 h5.m-news-detailed-listing__title
            title_el = a.select_one("h5.m-news-detailed-listing__title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 10:
                continue

            # 日期在 .m-news-detailed-listing__authors
            date_el = a.select_one(".m-news-detailed-listing__authors")
            date_text = date_el.get_text(strip=True) if date_el else ""
            pub_date = self._parse_date(date_text)

            items.append({
                "title": title,
                "pub_date": pub_date,
                "url": full_url,
            })

        print(f"[IEA] 第 {page} 页找到 {len(items)} 条新闻")
        return items

    def scrape(self, year_month: str, max_pages: int = 2) -> list[dict]:
        """抓取 IEA 新闻并筛选指定月份。"""
        # 先收集所有相关条目
        relevant_items = []

        for page in range(1, max_pages + 1):
            items = self._parse_list_page(page)
            if not items:
                break

            for item in items:
                title_en = item["title"]
                pub_date = item["pub_date"]
                link = item["url"]

                if pub_date and not pub_date.startswith(year_month):
                    continue
                if not self.is_relevant(title_en):
                    continue

                relevant_items.append({
                    "title_en": title_en,
                    "pub_date": pub_date,
                    "url": link,
                })

            self.random_delay()

        if not relevant_items:
            print(f"[IEA] {year_month} 筛选出 0 条")
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
                source="IEA",
                sub_industry=sub_industry,
                summary="",
                url=item["url"],
            )
            if record:
                all_records.append(record)

            self.random_delay()

        print(f"[IEA] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[IEA] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=3)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[IEA] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=1)
