"""
中国能源报爬虫。
抓取 cnenergy.org 的新能源相关报道。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.media_base import MediaBaseScraper
from scrapers.media_config import CNENERGY_BASE_URL


class CnenergyScraper(MediaBaseScraper):
    """中国能源报爬虫。"""

    # 已知栏目页面
    CHANNEL_URLS = [
        "https://www.cnenergy.org/hb/",    # 行业报道
        "https://www.cnenergy.org/dj/",     # 独家
        "https://www.cnenergy.org/yw/",     # 要闻
    ]

    def __init__(self):
        super().__init__(source_name="中国能源报")

    def _parse_channel(self, url: str) -> list[dict]:
        """解析频道列表页。"""
        print(f"[中国能源报] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[中国能源报] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        # 遍历所有链接
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "").strip()
            title = a_tag.get_text(strip=True)

            if not title or len(title) < 8:
                continue

            # 只保留文章链接
            if not (
                "/hb/" in href or "/dj/" in href or "/yw/" in href
                or "/xny/" in href or "/gf/" in href or "/fd/" in href
                or ".html" in href or ".shtml" in href
            ):
                continue

            # URL 处理
            if href.startswith("/"):
                href = CNENERGY_BASE_URL + href
            elif not href.startswith("http"):
                continue

            items.append({"title": title, "url": href})

        # 去重
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        print(f"[中国能源报] 找到 {len(unique)} 条链接")
        return unique

    def _fetch_article_date(self, url: str) -> str:
        """从文章详情页获取发布日期。"""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # 常见日期选择器
        for selector in ["span.date", "time", ".article-date", ".pub-date", ".info span"]:
            el = soup.select_one(selector)
            if el:
                text = el.get("datetime", "") or el.get_text(strip=True)
                m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
                if m:
                    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # meta 标签
        for meta in soup.select("meta[property='article:published_time'], meta[name='publishdate']"):
            content = meta.get("content", "")
            m = re.search(r"(\d{4}-\d{2}-\d{2})", content)
            if m:
                return m.group(1)

        # 正文前500字符
        text = soup.get_text()[:500]
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        return ""

    def scrape(self, year_month: str):
        all_items = []
        seen_urls = set()

        for channel_url in self.CHANNEL_URLS:
            items = self._parse_channel(channel_url)

            for item in items:
                title = item["title"]
                url = item["url"]

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # 新能源相关性过滤
                if not self._is_relevant(title):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date="",
                    source="中国能源报",
                    sub_industry=self._classify_industry(title),
                    summary="",
                    url=url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        # 获取发布日期
        for record in all_items:
            if not record["pub_date"]:
                pub_date = self._fetch_article_date(record["url"])
                if pub_date:
                    record["pub_date"] = pub_date
                self.random_delay()

        # 按月份过滤
        if year_month:
            all_items = [
                r for r in all_items
                if not r["pub_date"] or r["pub_date"].startswith(year_month)
            ]

        print(f"[中国能源报] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[中国能源报] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[中国能源报] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
