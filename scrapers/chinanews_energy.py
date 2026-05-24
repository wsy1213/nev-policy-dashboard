"""
中国新闻网财经频道爬虫。
抓取 chinanews.com.cn/cj/ 的新能源相关报道。
简单 HTML 列表解析，结构稳定。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.media_base import MediaBaseScraper
from scrapers.media_config import CHINANEWS_BASE_URL


class ChinanewsScraper(MediaBaseScraper):
    """中国新闻网财经频道爬虫。"""

    # 滚动新闻页面，每页约 100+ 条
    LIST_URL_TPL = "https://www.chinanews.com.cn/scroll-news/cj/news{}.html"

    def __init__(self):
        super().__init__(source_name="中国新闻网")

    def _parse_list_page(self, page: int) -> list[dict]:
        """解析滚动新闻列表页。"""
        url = self.LIST_URL_TPL.format(page) if page > 1 else self.LIST_URL_TPL.format("")
        # 也可以直接用 /cj/gd.shtml 但那只有一页
        if page == 1:
            url = "https://www.chinanews.com.cn/cj/gd.shtml"

        print(f"[中国新闻网] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[中国新闻网] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        # 结构: <div class="content_list"> <ul> <li>
        # 或直接匹配带链接的 li
        for li in soup.select("li"):
            a_tag = li.select_one("a[href*='/cj/']")
            if not a_tag:
                continue

            href = a_tag.get("href", "").strip()
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # URL 处理
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = CHINANEWS_BASE_URL + href

            # 从 href 提取日期：/cj/2026/04-02/10597561.shtml
            pub_date = ""
            m = re.search(r"/(\d{4})/(\d{2})-(\d{2})/", href)
            if m:
                pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            if not pub_date:
                # 从 li 内 span 提取日期
                span = li.select_one("span")
                if span:
                    date_text = span.get_text(strip=True)
                    dm = re.match(r"(\d{1,2})-(\d{1,2})\s", date_text)
                    if dm:
                        pub_date = f"2026-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"

            items.append({"title": title, "url": href, "pub_date": pub_date})

        print(f"[中国新闻网] 找到 {len(items)} 条链接")
        return items

    def scrape(self, year_month: str, max_pages: int = 2):
        all_items = []

        for page in range(1, max_pages + 1):
            items = self._parse_list_page(page)
            if not items:
                break

            for item in items:
                title = item["title"]
                pub_date = item.get("pub_date", "")

                # 月份过滤
                if pub_date and not pub_date.startswith(year_month):
                    continue

                # 新能源相关性过滤
                if not self._is_relevant(title):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="中国新闻网",
                    sub_industry=self._classify_industry(title),
                    summary="",
                    url=item["url"],
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        print(f"[中国新闻网] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[中国新闻网] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=3)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[中国新闻网] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
