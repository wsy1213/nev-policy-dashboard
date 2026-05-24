"""
北极星储能网数据栏目爬虫。
抓取 chuneng.bjx.com.cn/sj/ 的数据类新闻。
覆盖：储能、充电基础设施、新能源汽车、光伏、风电、氢能等子行业。
使用 requests + BeautifulSoup，列表页为静态 HTML。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper
from scrapers.industry_config import (
    BJX_TITLE_INDUSTRY_MAP,
    BJX_TITLE_EXCLUDE,
)


class BJXDataScraper(IndustryBaseScraper):
    """北极星储能网爬虫（数据栏目 + 新能源汽车栏目）。"""

    # 多个栏目
    SECTIONS = [
        {"name": "数据", "base": "https://chuneng.bjx.com.cn/sj/", "tpl": "https://chuneng.bjx.com.cn/sj/{page}/"},
        {"name": "新能源汽车", "base": "https://chuneng.bjx.com.cn/xnyqc/", "tpl": "https://chuneng.bjx.com.cn/xnyqc/{page}/"},
    ]

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    def __init__(self):
        super().__init__(source_name="北极星储能网")

    def _get_list_url(self, section: dict, page: int) -> str:
        if page == 1:
            return section["base"]
        return section["tpl"].format(page=page)

    def _classify_industry(self, title: str) -> str:
        """根据标题关键词判断子行业。"""
        for keyword, industry in BJX_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return ""

    def _should_exclude(self, title: str) -> bool:
        """排除非数据类新闻（企业广告、招投标等）。"""
        for kw in BJX_TITLE_EXCLUDE:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, section: dict, page: int) -> list[dict]:
        """
        解析列表页。
        HTML 结构：<li><a href="..." title="...">标题</a><span>2026-03-26</span></li>
        """
        url = self._get_list_url(section, page)
        print(f"[北极星储能网] 正在抓取 {section['name']} 第 {page} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[北极星储能网] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        # 找所有包含 news.bjx.com.cn/html/ 链接的 <li>
        for li in soup.find_all("li"):
            a_tag = li.find("a", href=lambda h: h and "news.bjx.com.cn/html/" in h)
            if not a_tag:
                continue

            title = a_tag.get("title", "") or a_tag.get_text(strip=True)
            href = a_tag["href"]

            # 从 <span> 获取日期
            span = li.find("span")
            pub_date = span.get_text(strip=True) if span else ""

            # 验证日期格式
            if pub_date and not re.match(r"\d{4}-\d{2}-\d{2}", pub_date):
                pub_date = ""

            if title and href:
                items.append({
                    "title": title,
                    "url": href,
                    "pub_date": pub_date,
                })

        print(f"[北极星储能网] 第 {page} 页共找到 {len(items)} 条链接")
        return items

    def scrape(self, year_month: str, max_pages: int = 5):
        """
        抓取指定月份的新闻。

        Args:
            year_month: 目标月份，如 "2026-03"
            max_pages: 最多翻几页列表页
        """
        target_ym = year_month
        all_items = []
        seen_urls = set()

        for section in self.SECTIONS:
            stop = False
            for page in range(1, max_pages + 1):
                items = self._parse_list_page(section, page)
                if not items:
                    break

                for item in items:
                    pub_date = item["pub_date"]
                    item_ym = pub_date[:7] if pub_date else ""

                    if item_ym and item_ym < target_ym:
                        stop = True
                        break

                    if item_ym != target_ym:
                        continue

                    if item["url"] in seen_urls:
                        continue
                    seen_urls.add(item["url"])

                    title = item["title"]

                    if self._should_exclude(title):
                        continue

                    # 新能源汽车栏目的文章默认归类
                    sub_industry = self._classify_industry(title)
                    if not sub_industry:
                        if section["name"] == "新能源汽车":
                            sub_industry = "新能源汽车"
                        elif any(kw in title for kw in ["出口", "产量", "产销", "同比", "增长", "下降", "装机", "并网"]):
                            sub_industry = "综合/其他"
                        else:
                            continue

                    record = self.make_record(
                        title=title,
                        pub_date=pub_date,
                        source="北极星储能网",
                        sub_industry=sub_industry,
                        summary="",
                        url=item["url"],
                    )
                    if record:
                        all_items.append(record)

                if stop:
                    break
                self.random_delay()

        print(f"[北极星储能网] {year_month} 筛选出 {len(all_items)} 条数据类新闻")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        """入口方法。"""
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[北极星储能网] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=10)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[北极星储能网] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=3)
