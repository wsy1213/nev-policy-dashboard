"""
界面新闻双碳/ESG频道爬虫。
抓取 jiemian.com 双碳和 ESG 频道的新能源相关报道。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.media_base import MediaBaseScraper
from scrapers.media_config import (
    JIEMIAN_BASE_URL,
    JIEMIAN_CARBON_URL,
    JIEMIAN_ESG_URL,
)


class JiemianScraper(MediaBaseScraper):
    """界面新闻双碳/ESG频道爬虫。"""

    def __init__(self):
        super().__init__(source_name="界面新闻")

    def _parse_list_page(self, url: str) -> list[dict]:
        """解析列表页。"""
        print(f"[界面新闻] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[界面新闻] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for a_tag in soup.select("a[href*='/article/']"):
            href = a_tag.get("href", "").strip()
            title = a_tag.get_text(strip=True)

            if not title or len(title) < 8:
                continue
            # 去重：同一页可能有缩略图和标题两个 <a> 指向同一文章
            if href.startswith("/"):
                href = JIEMIAN_BASE_URL + href

            items.append({"title": title, "url": href})

        # 去重
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        print(f"[界面新闻] 找到 {len(unique)} 条链接")
        return unique

    def _try_api(self, node_id: int, page: int = 1) -> list[dict]:
        """尝试使用界面新闻 API 获取文章列表。"""
        api_url = f"https://api.jiemian.com/article/listV3.json"
        params = {
            "listId": node_id,
            "page": page,
            "pageSize": 30,
        }
        try:
            resp = requests.get(
                api_url, params=params,
                headers={**self.HEADERS, "Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("list", [])
        except (requests.RequestException, ValueError):
            return []

    def scrape(self, year_month: str):
        all_items = []
        seen_urls = set()

        # 抓取双碳频道和ESG频道
        for channel_url in [JIEMIAN_CARBON_URL, JIEMIAN_ESG_URL]:
            items = self._parse_list_page(channel_url)

            for item in items:
                title = item["title"]
                url = item["url"]

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # 新能源相关性过滤
                if not self._is_relevant(title):
                    continue

                # 从 URL 没法直接提取日期，需要后续补充
                # article ID 大致递增，但不含日期
                record = self.make_record(
                    title=title,
                    pub_date="",  # 列表页无日期，后面通过详情页补充
                    source="界面新闻",
                    sub_industry=self._classify_industry(title),
                    summary="",
                    url=url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        # 对没有日期的文章尝试获取日期
        for record in all_items:
            if not record["pub_date"]:
                pub_date = self._fetch_article_date(record["url"])
                if pub_date:
                    record["pub_date"] = pub_date

        # 按月份过滤
        if year_month:
            all_items = [
                r for r in all_items
                if not r["pub_date"] or r["pub_date"].startswith(year_month)
            ]

        print(f"[界面新闻] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def _fetch_article_date(self, url: str) -> str:
        """从文章详情页获取发布日期。"""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # 查找日期元素
        time_tag = soup.select_one("time, .article-info time, span.date, .top3-article-time")
        if time_tag:
            date_text = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
            # 先试绝对日期
            m = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
            if m:
                return m.group(1)
            # 相对时间转日期
            from datetime import datetime, timedelta
            now = datetime.now()
            if "小时前" in date_text or "分钟前" in date_text or "刚刚" in date_text:
                return now.strftime("%Y-%m-%d")
            m2 = re.match(r"(\d+)天前", date_text)
            if m2:
                return (now - timedelta(days=int(m2.group(1)))).strftime("%Y-%m-%d")
            # MM/DD or MM-DD format
            m3 = re.match(r"(\d{1,2})[/\-](\d{1,2})", date_text)
            if m3:
                return f"{now.year}-{int(m3.group(1)):02d}-{int(m3.group(2)):02d}"

        # meta 标签
        for meta in soup.select("meta[property='article:published_time'], meta[name='publishdate']"):
            content = meta.get("content", "")
            m = re.search(r"(\d{4}-\d{2}-\d{2})", content)
            if m:
                return m.group(1)

        # 正文中的日期
        text = soup.get_text()
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text[:500])
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        return ""

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[界面新闻] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[界面新闻] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
