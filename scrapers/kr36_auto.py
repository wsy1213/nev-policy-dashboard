"""
36氪汽车频道爬虫。
抓取 36kr.com 汽车领域的新能源汽车报道。
"""

import re
import requests

from scrapers.industry_base import IndustryBaseScraper
from scrapers.media_config import MEDIA_INCLUDE_KEYWORDS, MEDIA_TITLE_INDUSTRY_MAP


KR36_API_URL = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"
KR36_SEARCH_URL = "https://gateway.36kr.com/api/mis/nav/search/home"

KR36_SEARCH_KEYWORDS = ["新能源汽车", "电动汽车", "充电桩", "比亚迪", "特斯拉"]


class Kr36Scraper(IndustryBaseScraper):
    """36氪汽车频道行业新闻爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://www.36kr.com/",
        "Origin": "https://www.36kr.com",
    }

    def __init__(self):
        super().__init__(source_name="36氪")

    def _is_relevant(self, title: str) -> bool:
        if not title:
            return False
        for kw in MEDIA_INCLUDE_KEYWORDS:
            if kw in title:
                return True
        return False

    def _classify_industry(self, title: str) -> str:
        for keyword, industry in MEDIA_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return "综合/其他"

    def _search(self, keyword: str, page: int = 1) -> list[dict]:
        """通过 36氪搜索 API 获取文章。"""
        payload = {
            "partner_id": "wap",
            "param": {
                "siteId": 1,
                "platformId": 2,
                "keyword": keyword,
                "pageSize": 20,
                "pageEvent": page,
                "pageCallback": "a",
            },
        }
        try:
            resp = requests.post(
                KR36_SEARCH_URL, json=payload, headers=self.HEADERS, timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("itemList", [])
            return items if isinstance(items, list) else []
        except (requests.RequestException, ValueError) as e:
            print(f"[36氪] 搜索失败 ({keyword}): {e}")
            return []

    def scrape(self, year_month: str):
        all_items = []
        seen_urls = set()

        for keyword in KR36_SEARCH_KEYWORDS:
            print(f"[36氪] 搜索: {keyword}")
            results = self._search(keyword)

            for item in results:
                widget_data = item.get("templateMaterial", {}).get("widgetData", {})
                if not widget_data:
                    widget_data = item

                title = (widget_data.get("templateTitle") or
                         widget_data.get("title") or
                         item.get("templateTitle", "")).strip()
                if not title:
                    continue

                item_id = widget_data.get("itemId") or widget_data.get("id", "")
                url = f"https://www.36kr.com/p/{item_id}" if item_id else ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_date = ""
                pub_time = widget_data.get("publishTime") or widget_data.get("publicTime", "")
                if pub_time:
                    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(pub_time))
                    if m:
                        pub_date = m.group(1)
                    elif isinstance(pub_time, (int, float)) and pub_time > 1e12:
                        from datetime import datetime
                        try:
                            pub_date = datetime.fromtimestamp(pub_time / 1000).strftime("%Y-%m-%d")
                        except (ValueError, OSError):
                            pass

                if pub_date and not pub_date.startswith(year_month):
                    continue

                if not self._is_relevant(title):
                    continue

                summary = (widget_data.get("summary") or "").strip()
                if summary and len(summary) > 200:
                    summary = summary[:200]

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="36氪",
                    sub_industry=self._classify_industry(title),
                    url=url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        print(f"[36氪] {year_month} 筛选出 {len(all_items)} 条新能源汽车报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[36氪] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[36氪] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, )
