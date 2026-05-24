"""
国家统计局（NBS）最新发布栏目爬虫。
抓取 stats.gov.cn/sj/zxfb/ 的统计数据发布新闻。
使用 requests + BeautifulSoup，无需 Playwright。
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.industry_base import IndustryBaseScraper

# 标题关键词 → 子行业映射
NBS_TITLE_INDUSTRY_MAP = {
    "光伏": "光伏",
    "太阳能": "光伏",
    "风电": "风电",
    "风力": "风电",
    "储能": "储能",
    "充电": "充电基础设施",
    "氢能": "氢能",
    "新能源汽车": "新能源汽车",
    "电动汽车": "新能源汽车",
    "汽车": "新能源汽车",
}

# 只抓包含这些关键词的文章（和新能源/工业相关的数据）
NBS_DATA_KEYWORDS = [
    "能源", "电力", "发电", "用电", "工业增加值",
    "工业生产", "汽车", "新能源", "光伏", "风电",
    "储能", "充电", "装机", "产量", "产销",
]

# 排除的标题关键词
NBS_TITLE_EXCLUDE = [
    "房地产", "住宅", "商品房", "采购经理",
    "流通领域", "居民消费价格", "工业生产者",
    "固定资产投资", "社会消费品", "服务业",
    "统计公报",
]

BASE_URL = "https://www.stats.gov.cn/sj/zxfb/"


class NBSScraper(IndustryBaseScraper):
    """国家统计局最新发布爬虫。"""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self):
        super().__init__(source_name="国家统计局")

    def _classify_industry(self, title: str) -> str:
        """根据标题关键词判断子行业。"""
        for keyword, industry in NBS_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return "综合/其他"

    def _is_relevant(self, title: str) -> bool:
        """判断标题是否和新能源/工业数据相关。"""
        # 先排除不相关的
        for kw in NBS_TITLE_EXCLUDE:
            if kw in title:
                return False
        # 再看是否包含数据关键词
        for kw in NBS_DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, page: int) -> list[dict]:
        """解析统计局列表页。"""
        if page == 0:
            url = BASE_URL
        else:
            url = f"{BASE_URL}index_{page}.html"

        print(f"[国家统计局] 正在抓取第 {page + 1} 页: {url}")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[国家统计局] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for li in soup.select("li"):
            a = li.select_one("a.fl.pc_1600")
            if not a:
                continue

            title = (a.get("title") or a.get_text(strip=True)).strip()
            href = a.get("href", "")

            if not title or len(title) < 5:
                continue

            # 从 href 提取日期: ./202603/t20260316_1962780.html
            pub_date = ""
            m = re.search(r"t(\d{4})(\d{2})(\d{2})", href)
            if m:
                pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            full_url = urljoin(url, href)

            items.append({
                "title": title,
                "pub_date": pub_date,
                "url": full_url,
            })

        print(f"[国家统计局] 第 {page + 1} 页共找到 {len(items)} 条")
        return items

    def scrape(self, year_month: str, max_pages: int = 2):
        """抓取指定月份的数据发布新闻。"""
        all_items = []

        for page in range(max_pages):
            items = self._parse_list_page(page)
            if not items:
                break

            found_in_page = False
            for item in items:
                title = item["title"]
                pub_date = item["pub_date"]

                # 按发布日期过滤月份
                if pub_date and not pub_date.startswith(year_month):
                    continue

                # 只要与新能源/工业相关的数据新闻
                if not self._is_relevant(title):
                    continue

                found_in_page = True
                sub_industry = self._classify_industry(title)

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="国家统计局",
                    sub_industry=sub_industry,
                    summary="",
                    url=item["url"],
                )
                all_items.append(record)

            self.random_delay()

            # 如果当页所有文章都早于目标月份，停止翻页
            if items:
                last_date = items[-1].get("pub_date", "")
                if last_date and last_date < year_month:
                    break

        print(f"[国家统计局(NBS)] {year_month} 筛选出 {len(all_items)} 条数据新闻")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[国家统计局] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=3)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[国家统计局] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=1)
