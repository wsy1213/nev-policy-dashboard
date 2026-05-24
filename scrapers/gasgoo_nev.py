"""
盖世汽车（gasgoo.com）新能源频道爬虫。
供应链、零部件、产业链上下游报道，视角偏 B 端。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper

GASGOO_BASE_URL = "https://auto.gasgoo.com"
GASGOO_NEV_URL = "https://auto.gasgoo.com/nev/C-501"

# 排除低价值内容
EXCLUDE_PATTERNS = [
    "快讯", "官图", "谍照", "实拍", "试驾", "评测",
    "优惠", "降价", "补贴后售价", "E周看点",
    "亮相", "官宣", "下线", "门店",
    "预售", "发布会", "战略合作", "合作伙伴",
    "Seeds", "Pre-A", "天使轮",
    "座椅", "基因", "内饰", "外观",
]

# 重要性关键词 — 标题须包含至少一个才保留
IMPORTANCE_KEYWORDS = [
    # 宏观行业趋势
    "产业", "行业", "市场", "政策", "关税",
    "装机", "排行", "市占率", "渗透率",
    # 供应链/技术突破
    "固态电池", "钠电", "氢能", "IPO",
    "供应链", "芯片",
    # 宏观数据（全国/全球级别）
    "趋势", "变革", "转型", "出海",
    # 权威声音
    "院士", "部长", "发改委", "工信部", "百人会",
]

# 每月每个来源最多保留条数
MAX_ITEMS_PER_MONTH = 8


class GasgooScraper(IndustryBaseScraper):
    """盖世汽车新能源频道爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://auto.gasgoo.com/",
    }

    def __init__(self):
        super().__init__(source_name="盖世汽车")

    def _should_exclude(self, title: str) -> bool:
        for pat in EXCLUDE_PATTERNS:
            if pat in title:
                return True
        return False

    def _is_important(self, title: str) -> bool:
        for kw in IMPORTANCE_KEYWORDS:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, page: int) -> list[dict]:
        url = f"{GASGOO_NEV_URL}/{page}" if page > 1 else GASGOO_NEV_URL
        print(f"[盖世汽车] 正在抓取第 {page} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[盖世汽车] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for cl in soup.select(".contentList"):
            h2_a = cl.select_one("h2 a")
            if not h2_a:
                continue

            title = h2_a.get_text(strip=True)
            href = h2_a.get("href", "")
            if not title or len(title) < 8:
                continue
            if not href.startswith("http"):
                href = GASGOO_BASE_URL + href

            pub_date = ""
            for span in cl.select("span"):
                t = span.get_text(strip=True)
                m = re.match(r"(\d{4}-\d{2}-\d{2})", t)
                if m:
                    pub_date = m.group(1)
                    break

            items.append({"title": title, "url": href, "pub_date": pub_date})

        print(f"[盖世汽车] 第 {page} 页共找到 {len(items)} 条")
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

                title = item["title"]
                if self._should_exclude(title):
                    continue
                if not self._is_important(title):
                    continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="盖世汽车",
                    sub_industry="新能源汽车",
                    url=item["url"],
                )
                if record:
                    all_items.append(record)

            if stop:
                break
            self.random_delay()

        # 限制每月数量，只保留最新的
        if len(all_items) > MAX_ITEMS_PER_MONTH:
            all_items = all_items[:MAX_ITEMS_PER_MONTH]

        print(f"[盖世汽车] {year_month} 筛选出 {len(all_items)} 条")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[盖世汽车] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[盖世汽车] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
