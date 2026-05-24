"""
汽车之家新能源频道爬虫。
抓取 autohome.com.cn 新能源汽车行业资讯。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.media_base import MediaBaseScraper


AUTOHOME_BASE_URL = "https://www.autohome.com.cn"
# 新能源频道资讯列表
AUTOHOME_NEV_URL = "https://www.autohome.com.cn/news/list-0-0-0-1-0-0-0-2-0-0.html"


class AutohomeScraper(MediaBaseScraper):
    """汽车之家新能源频道爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.autohome.com.cn/",
    }

    def __init__(self):
        super().__init__(source_name="汽车之家")

    def _parse_list_page(self, url: str) -> list[dict]:
        print(f"[汽车之家] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "gb2312"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[汽车之家] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for li in soup.select("ul#newsList li, ul.article-list li, div.news-list li"):
            a_tag = li.select_one("a[href]")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 8:
                continue

            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = AUTOHOME_BASE_URL + href

            pub_date = ""
            span = li.select_one("span.time, span.date, em")
            if span:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", span.get_text(strip=True))
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

        print(f"[汽车之家] 找到 {len(unique)} 条文章")
        return unique

    def scrape(self, year_month: str, max_pages: int = 3):
        all_items = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            url = AUTOHOME_NEV_URL.replace("list-0-0-0-1", f"list-0-0-0-{page}")
            items = self._parse_list_page(url)
            if not items:
                break

            for item in items:
                title, pub_date, item_url = item["title"], item["pub_date"], item["url"]
                if item_url in seen_urls:
                    continue
                seen_urls.add(item_url)

                if pub_date and not pub_date.startswith(year_month):
                    continue
                if not self._is_relevant(title):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="汽车之家",
                    sub_industry=self._classify_industry(title),
                    summary="",
                    url=item_url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        print(f"[汽车之家] {year_month} 筛选出 {len(all_items)} 条报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[汽车之家] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[汽车之家] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
