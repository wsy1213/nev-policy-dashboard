"""
国家能源局新闻发布爬虫。
抓取 nea.gov.cn/xwfb/ 的数据类新闻（装机、发电量、充电设施等统计数据）。
直接调用 CMS JSON API，无需解析 HTML。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper
from scrapers.industry_config import (
    NEA_BASE_URL,
    NEA_TITLE_INDUSTRY_MAP,
    NEA_DATA_KEYWORDS,
    NEA_TITLE_EXCLUDE,
)


class NEAScraper(IndustryBaseScraper):
    """国家能源局新闻发布爬虫（通过 JSON API）。"""

    # CMS 数据源 JSON 接口（从页面 data 属性中提取的 datasource ID）
    JSON_API_URL = "https://www.nea.gov.cn/xwfb/ds_4f3484af7ea244e7ab18d094856c82a6.json"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, */*",
    }

    def __init__(self):
        super().__init__(source_name="国家能源局")

    def _classify_industry(self, title: str) -> str:
        """根据标题关键词判断子行业。"""
        for keyword, industry in NEA_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return ""

    def _is_data_news(self, title: str) -> bool:
        """判断是否为数据/统计类新闻。"""
        for exclude in NEA_TITLE_EXCLUDE:
            if exclude in title:
                return False
        for keyword in NEA_DATA_KEYWORDS:
            if keyword in title:
                return True
        return False

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        """清理标题中可能嵌套的 HTML 标签（老数据的 showTitle 偶尔有 <a> 标签）。"""
        if "<" in raw_title:
            from bs4 import BeautifulSoup as BS
            return BS(raw_title, "html.parser").get_text(strip=True)
        return raw_title.strip()

    def _resolve_url(self, publish_url: str) -> str:
        """将相对 URL 转为绝对 URL。
        publishUrl 格式示例：../20260327/xxx/c.html
        """
        if publish_url.startswith("http"):
            return publish_url
        # ../20260327/xxx/c.html → https://www.nea.gov.cn/20260327/xxx/c.html
        cleaned = publish_url.lstrip("./")
        return f"{NEA_BASE_URL}/{cleaned}"

    def _fetch_all_items(self) -> list[dict]:
        """一次性获取全部新闻发布数据（JSON API 返回所有条目）。"""
        print(f"[国家能源局] 正在请求 JSON API ...")
        try:
            resp = requests.get(self.JSON_API_URL, headers=self.HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[国家能源局] API 请求失败: {e}")
            return []

        items = data.get("datasource", [])
        print(f"[国家能源局] API 返回 {len(items)} 条新闻")
        return items

    def _fetch_article_summary(self, url: str) -> str:
        """抓取文章详情页的前几段作为摘要。"""
        try:
            resp = requests.get(url, headers={**self.HEADERS, "Accept": "text/html"}, timeout=15)
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")
        content_div = soup.select_one(".TRS_Editor, .article_con, #zoom, .content")
        if not content_div:
            return ""

        paragraphs = content_div.find_all("p")
        texts = []
        for p in paragraphs[:3]:
            text = p.get_text(strip=True)
            if text and len(text) > 10:
                texts.append(text)
        return " ".join(texts)[:300] if texts else ""

    def scrape(self, year_month: str, fetch_summary: bool = False):
        """
        抓取指定月份的数据类新闻。

        Args:
            year_month: 目标月份，如 "2026-03"
            fetch_summary: 是否进入详情页抓取摘要（较慢）
        """
        target_ym = year_month
        all_raw = self._fetch_all_items()
        if not all_raw:
            return []

        all_items = []
        for raw in all_raw:
            # 提取发布时间 "2026-03-27 18:59:39" → "2026-03-27"
            publish_time = raw.get("publishTime", "")
            pub_date = publish_time[:10] if publish_time else ""
            item_ym = pub_date[:7]

            # 只保留目标月份
            if item_ym != target_ym:
                continue

            # 清理标题
            title = self._clean_title(raw.get("showTitle", "") or raw.get("title", ""))
            if not title:
                continue

            # 过滤：只要数据类新闻
            if not self._is_data_news(title):
                continue

            # 分类子行业
            sub_industry = self._classify_industry(title)
            if not sub_industry:
                continue

            # 解析 URL
            publish_url = raw.get("publishUrl", "")
            full_url = self._resolve_url(publish_url) if publish_url else ""

            record = self.make_record(
                title=title,
                pub_date=pub_date,
                source="国家能源局",
                sub_industry=sub_industry,
                url=full_url,
            )
            if record:
                all_items.append(record)

        print(f"[国家能源局] {year_month} 筛选出 {len(all_items)} 条数据类新闻")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        """入口方法。"""
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[国家能源局] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, fetch_summary=True)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[国家能源局] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, fetch_summary=False)
