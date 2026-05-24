"""
第一财经新能源报道爬虫。
抓取 yicai.com 新闻列表页的新能源相关新闻。
直接解析 HTML 列表页。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.media_base import MediaBaseScraper
from scrapers.media_config import YICAI_BASE_URL


class YicaiScraper(MediaBaseScraper):
    """第一财经新能源报道爬虫。"""

    # 抓取多个频道页面
    PAGE_URLS = [
        f"{YICAI_BASE_URL}/news/",
        f"{YICAI_BASE_URL}/esg/",
    ]

    def __init__(self):
        super().__init__(source_name="第一财经")

    def _parse_page(self, url: str) -> list[dict]:
        """解析列表页 HTML，提取文章链接。"""
        print(f"[第一财经] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[第一财经] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for a_tag in soup.select("a[href*='/news/']"):
            href = a_tag.get("href", "").strip()
            title = a_tag.get_text(strip=True)
            # 清理 HTML 残留、过短标题
            if "<" in title:
                title = BeautifulSoup(title, "html.parser").get_text(strip=True)
            if not title or len(title) < 8:
                continue
            # 排除纯数字 ID 链接文本
            if re.match(r"^\d+$", title):
                continue

            if href.startswith("/"):
                href = YICAI_BASE_URL + href

            items.append({"title": title, "url": href})

        return items

    def _fetch_article_date(self, url: str) -> str:
        """从文章详情页获取发布日期。"""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "utf-8"
        except requests.RequestException:
            return ""

        # 从 meta 或页面中提取日期
        m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', resp.text)
        if m:
            return m.group(1)
        m = re.search(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}', resp.text)
        if m:
            return m.group(1)
        return ""

    def scrape(self, year_month: str):
        all_items = []
        seen_urls = set()

        for page_url in self.PAGE_URLS:
            page_items = self._parse_page(page_url)

            for item in page_items:
                title = item["title"]
                url = item["url"]

                if not self._is_relevant(title):
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # 获取文章日期（从详情页）
                pub_date = self._fetch_article_date(url)
                if pub_date and not pub_date.startswith(year_month):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="第一财经",
                    sub_industry=self._classify_industry(title),
                    summary="",
                    url=url,
                )
                if record:
                    all_items.append(record)
                self.random_delay()

            self.random_delay()

        print(f"[第一财经] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[第一财经] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[第一财经] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
