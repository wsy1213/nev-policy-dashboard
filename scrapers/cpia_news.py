"""
中国光伏行业协会 (CPIA) 市场动态爬虫。
抓取 chinapv.org.cn 的市场动态和政策法规栏目。
使用 requests + BeautifulSoup，静态 HTML。
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.industry_base import IndustryBaseScraper
from scrapers.industry_config import CPIA_BASE_URL


class CPIAScraper(IndustryBaseScraper):
    """中国光伏行业协会爬虫。"""

    # 列表页 URL 模板
    SECTIONS = {
        "市场动态": "https://www.chinapv.org.cn/StaticPage/association_list29_{page}.html",
        "政策法规": "https://www.chinapv.org.cn/StaticPage/association_list28_{page}.html",
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    # 数据/统计类关键词
    DATA_KEYWORDS = [
        "数据", "统计", "装机", "发电量", "产量", "产能",
        "出货", "出口", "产销", "同比", "增长",
        "并网", "运行", "建设情况",
        "月报", "季报", "年报",
        "GW", "MW", "TWh",
    ]

    def __init__(self):
        super().__init__(source_name="中国光伏行业协会")

    def _is_data_article(self, title: str) -> bool:
        """判断是否为数据类文章。"""
        for kw in self.DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    def _parse_list_page(self, section_name: str, page: int) -> list[dict]:
        """解析列表页。"""
        url_template = self.SECTIONS[section_name]
        url = url_template.format(page=page)
        print(f"[光伏协会] 正在抓取 {section_name} 第 {page} 页")

        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[光伏协会] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        # 链接格式：association_content_{id}.html，日期在同级文本中
        for a_tag in soup.find_all("a", href=lambda h: h and "association_content" in str(h)):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")

            if not title or len(title) < 5:
                continue
            # 跳过 "查看更多" 链接
            if "查看更多" in title:
                continue

            # 构建完整 URL
            full_url = urljoin(CPIA_BASE_URL + "/", href)

            # 找日期：在父元素的文本中寻找
            pub_date = ""
            parent = a_tag.parent
            if parent:
                for s in parent.stripped_strings:
                    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
                    if m:
                        pub_date = m.group(0)
                        break
                    # 也可能是 YYYY/MM/DD 格式
                    m2 = re.search(r"(\d{4})/(\d{2})/(\d{2})", s)
                    if m2:
                        pub_date = f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
                        break

            items.append({
                "title": title,
                "url": full_url,
                "pub_date": pub_date,
            })

        # 去重（每条新闻有标题链接+图片链接，可能出现两次）
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        print(f"[光伏协会] {section_name} 第 {page} 页找到 {len(unique)} 条")
        return unique

    def scrape(self, year_month: str, max_pages: int = 3):
        """
        抓取指定月份的光伏行业市场动态。

        Args:
            year_month: 目标月份 "YYYY-MM"
            max_pages: 每个栏目最多翻几页
        """
        target_ym = year_month
        all_items = []

        for section_name in self.SECTIONS:
            for page in range(1, max_pages + 1):
                items = self._parse_list_page(section_name, page)
                if not items:
                    break

                found_older = False
                for item in items:
                    pub_date = item["pub_date"]
                    item_ym = pub_date[:7] if pub_date else ""

                    if item_ym and item_ym < target_ym:
                        found_older = True
                        break

                    if item_ym != target_ym:
                        continue

                    title = item["title"]

                    # 市场动态栏目的文章基本都和光伏相关，不需严格过滤
                    # 但政策法规栏目需要过滤出数据类
                    if section_name == "政策法规" and not self._is_data_article(title):
                        continue

                    record = self.make_record(
                        title=title,
                        pub_date=pub_date,
                        source="中国光伏行业协会",
                        sub_industry="光伏",
                        summary="",
                        url=item["url"],
                    )
                    all_items.append(record)

                if found_older:
                    break
                self.random_delay()

        print(f"[光伏协会] {year_month} 筛选出 {len(all_items)} 条")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        """入口方法。"""
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[光伏协会] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=5)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[光伏协会] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=2)
