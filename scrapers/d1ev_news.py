"""
电车通（D1EV）新能源汽车垂直媒体爬虫。
抓取 d1ev.com 的新能源汽车资讯和数据报道。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper


D1EV_BASE_URL = "https://www.d1ev.com"
D1EV_NEWS_URL = "https://www.d1ev.com/news"


# 排除低价值内容
D1EV_EXCLUDE = [
    "评测", "试驾", "实拍", "官图", "谍照", "优惠", "降价",
    "亮相", "官宣", "预售", "发布会", "赞助",
    "Seeds", "Pre-A", "天使轮",
    "座椅", "内饰", "外观", "配置",
]

# 重要性关键词
D1EV_IMPORTANCE = [
    "产业", "行业", "市场", "政策", "关税",
    "装机", "排行", "市占率", "渗透率",
    "固态电池", "钠电", "氢能", "IPO",
    "供应链", "芯片",
    "趋势", "变革", "转型", "出海",
    "院士", "部长", "发改委", "工信部", "百人会",
    "出口", "产能", "白皮书",
]

# 每月最多保留条数
D1EV_MAX_ITEMS = 8


class D1evScraper(IndustryBaseScraper):
    """电车通（D1EV）行业新闻爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.d1ev.com/",
    }

    def __init__(self):
        super().__init__(source_name="电车通")

    def _parse_list_page(self, url: str) -> list[dict]:
        print(f"[电车通] 正在抓取: {url}")
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[电车通] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        seen = set()

        for wrap in soup.select(".article--wraped"):
            # 标题在 .article_p > a
            title_a = wrap.select_one(".article_p a[href]")
            if not title_a:
                continue

            title = title_a.get_text(strip=True)
            href = title_a.get("href", "")
            if not title or len(title) < 6:
                continue
            if href.startswith("/"):
                href = D1EV_BASE_URL + href
            if href in seen:
                continue
            seen.add(href)

            pub_date = ""
            time_el = wrap.select_one(".article--time")
            if time_el:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", time_el.get_text(strip=True))
                if m:
                    pub_date = m.group(1)

            items.append({"title": title, "url": href, "pub_date": pub_date})

        print(f"[电车通] 找到 {len(items)} 条文章")
        return items

    def scrape(self, year_month: str, max_pages: int = 3):
        all_items = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            url = f"{D1EV_NEWS_URL}/list-{page}" if page > 1 else D1EV_NEWS_URL
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

                # 排除低价值内容
                if any(ex in title for ex in D1EV_EXCLUDE):
                    continue

                # 重要性过滤
                if not any(kw in title for kw in D1EV_IMPORTANCE):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="电车通",
                    sub_industry="新能源汽车",
                    url=item_url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        # 限制每月数量，只保留最新的
        if len(all_items) > D1EV_MAX_ITEMS:
            all_items = all_items[:D1EV_MAX_ITEMS]

        print(f"[电车通] {year_month} 筛选出 {len(all_items)} 条报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[电车通] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[电车通] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
