"""
国际可再生能源署（IRENA）新闻爬虫。
使用 requests + BeautifulSoup 抓取 HTML 页面。
RSS 源返回403，改用 HTML 解析。
"""

import re
import time

import requests
from bs4 import BeautifulSoup

from scrapers.intl_base import IntlBaseScraper


# IRENA 新闻页面
IRENA_NEWS_URL = "https://www.irena.org/News"

# 月份名称映射
MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


class IRENAScraper(IntlBaseScraper):
    """IRENA News HTML 爬虫。"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        super().__init__(source_name="IRENA")

    def _parse_date(self, date_text: str) -> str:
        """解析日期文本（如 '1 April 2026'）为 YYYY-MM-DD。"""
        if not date_text:
            return ""
        m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_text.strip())
        if not m:
            return ""
        day = m.group(1).zfill(2)
        month_name = m.group(2).lower()
        year = m.group(3)
        month = MONTH_MAP.get(month_name, "")
        if not month:
            return ""
        return f"{year}-{month}-{day}"

    def _parse_date_from_url(self, url: str) -> str:
        """从 URL 路径提取日期（如 /2026/Apr/ → 2026-04）。"""
        m = re.search(r"/(\d{4})/(\w{3})/", url)
        if not m:
            return ""
        year = m.group(1)
        month_abbr = m.group(2).lower()
        month = MONTH_MAP.get(month_abbr, "")
        if not month:
            return ""
        return f"{year}-{month}"

    def scrape(self, year_month: str) -> list[dict]:
        """抓取 IRENA 新闻页面。"""
        print(f"[IRENA] 正在抓取: {IRENA_NEWS_URL}")

        try:
            resp = requests.get(IRENA_NEWS_URL, headers=self.HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[IRENA] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找所有 /News/ 链接
        relevant_items = []
        seen_urls = set()

        for a in soup.select("a[href*='/News/']"):
            href = a.get("href", "").strip()
            if not href or href == "/News" or href == "/News/":
                continue

            # 构建完整 URL
            if href.startswith("/"):
                full_url = f"https://www.irena.org{href}"
            else:
                full_url = href

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = a.get_text(strip=True)
            if not title or len(title) < 15:
                continue

            # 跳过导航链接
            if title.lower() in ("news", "view all", "more news", "read more"):
                continue

            # 从 URL 提取月份
            url_month = self._parse_date_from_url(full_url)

            # 按月份过滤
            if url_month and not url_month.startswith(year_month[:7]):
                continue

            # 看紧邻文本中是否有日期
            parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            pub_date = ""
            date_m = re.search(
                r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
                parent_text, re.IGNORECASE
            )
            if date_m:
                pub_date = self._parse_date(date_m.group(0))

            if not pub_date and url_month:
                pub_date = f"{url_month}-01"

            if pub_date and not pub_date.startswith(year_month):
                continue

            # IRENA 全是可再生能源内容——宽松过滤
            if not self.is_relevant(title + " renewable energy capacity"):
                continue

            relevant_items.append({
                "title_en": title,
                "pub_date": pub_date,
                "url": full_url,
            })

        print(f"[IRENA] 找到 {len(relevant_items)} 条相关新闻")

        if not relevant_items:
            print(f"[IRENA] {year_month} 筛选出 0 条")
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
                source="IRENA",
                sub_industry=sub_industry,
                summary="",
                url=item["url"],
            )
            all_records.append(record)

        print(f"[IRENA] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[IRENA] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[IRENA] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
