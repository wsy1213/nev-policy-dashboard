"""
乘联会（CPCA）车市解读爬虫。
抓取 cpcaauto.com 的市场分析、销量排名等数据类文章。
使用 requests + BeautifulSoup，无需 Playwright。
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.industry_base import IndustryBaseScraper
from scrapers.industry_config import CPCA_BASE_URL, CPCA_DATA_KEYWORDS


class CPCAScraper(IndustryBaseScraper):
    """乘联会车市解读爬虫。"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.cpcaauto.com/",
    }

    # 只保留这些类型的核心分析报告（排除周报和快讯）
    CORE_KEYWORDS = [
        "月度分析", "月份全国", "深度分析", "市场分析",
        "月度排名", "厂商销量",
        "皮卡市场", "新能源", "乘用车", "车市", "渗透率",
        "零售", "出口", "产销", "走势", "销量",
    ]

    def __init__(self):
        super().__init__(source_name="乘联会")

    def _get_list_url(self, page: int) -> str:
        return f"{CPCA_BASE_URL}/news.php?types=csjd&page={page}"

    def _is_core_article(self, title: str) -> bool:
        """判断是否为核心月度分析文章（排除周报、快讯等高频内容）。"""
        for kw in self.CORE_KEYWORDS:
            if kw in title:
                return True
        return False

    def _extract_data_month(self, title: str) -> str:
        """从标题提取数据月份。如 '2026年2月份全国' → '2026-02'。"""
        m = re.search(r"(\d{4})年(\d{1,2})月", title)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}"
        return ""

    def _parse_list_page(self, page: int) -> list[dict]:
        """解析列表页。"""
        url = self._get_list_url(page)
        print(f"[乘联会] 正在抓取第 {page} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[乘联会] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        seen = set()

        for li in soup.select("li.q"):
            a_tag = li.select_one("a[href*='newslist.php']")
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)

            if not title or len(title) < 5:
                continue
            if "types=csjd" not in href and "types=bgzl" not in href:
                continue

            full_url = urljoin(CPCA_BASE_URL + "/", href)
            if full_url in seen:
                continue
            seen.add(full_url)

            # 从 <span> 提取日期
            pub_date = ""
            span = li.select_one("span")
            if span:
                date_text = span.get_text(strip=True)
                m = re.match(r"\d{4}-\d{2}-\d{2}", date_text)
                if m:
                    pub_date = m.group(0)

            items.append({"title": title, "url": full_url, "pub_date": pub_date})

        print(f"[乘联会] 第 {page} 页共找到 {len(items)} 条链接")
        return items

    def scrape(self, year_month: str, max_pages: int = 3):
        """
        抓取指定月份的数据类文章。
        优先用列表页上的发布日期筛选月份，回退到标题中的数据月份。

        Args:
            year_month: 目标月份 "YYYY-MM"（按发布月份筛选）
            max_pages: 最多翻几页
        """
        all_items = []

        for page in range(1, max_pages + 1):
            items = self._parse_list_page(page)
            if not items:
                break

            for item in items:
                title = item["title"]
                pub_date = item.get("pub_date", "")

                # 只要核心月度报告
                if not self._is_core_article(title):
                    continue

                # 用发布日期过滤月份
                if pub_date:
                    if not pub_date.startswith(year_month):
                        continue
                else:
                    # 无日期时用标题中的数据月份推断
                    data_ym = self._extract_data_month(title)
                    if data_ym and data_ym != year_month:
                        continue

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="乘联会",
                    sub_industry="新能源汽车",
                    summary="",
                    url=item["url"],
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        print(f"[乘联会] {year_month} 筛选出 {len(all_items)} 条核心分析文章")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[乘联会] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=5)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[乘联会] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[乘联会] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2, fetch_detail=True)
