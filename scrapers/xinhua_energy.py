"""
新华网新能源报道爬虫。
使用新华网搜索接口，按关键词搜索新能源相关新闻。
"""

import re
import requests

from scrapers.media_base import MediaBaseScraper


class XinhuaScraper(MediaBaseScraper):
    """新华网新能源报道爬虫（搜索 API）。"""

    SEARCH_URL = "https://search.news.cn/getNews"
    SEARCH_KEYWORDS = ["新能源", "光伏发电", "储能", "风电", "新能源汽车", "充电桩"]

    def __init__(self):
        super().__init__(source_name="新华网")

    def _search(self, keyword: str, page: int = 0, size: int = 20) -> list[dict]:
        """调用新华网搜索 API。"""
        params = {
            "keyword": keyword,
            "curPage": page,
            "sortField": 0,  # 按相关度排序
            "searchFields": 1,  # 标题+正文
            "lang": "cn",
        }
        try:
            resp = requests.get(
                self.SEARCH_URL, params=params,
                headers={**self.HEADERS, "Accept": "application/json", "Referer": "https://search.news.cn/"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"[新华网] 搜索失败 ({keyword}): {e}")
            return []

        content = data.get("content", {})
        results = content.get("results", [])
        if not isinstance(results, list):
            return []
        return results

    def scrape(self, year_month: str):
        all_items = []
        seen_urls = set()

        for keyword in self.SEARCH_KEYWORDS:
            print(f"[新华网] 搜索关键词: {keyword}")
            results = self._search(keyword, page=0, size=30)

            for item in results:
                title = (item.get("title") or "").strip()
                # 清理 HTML
                if "<" in title:
                    from bs4 import BeautifulSoup
                    title = BeautifulSoup(title, "html.parser").get_text(strip=True)
                if not title:
                    continue

                url = item.get("url", "").strip()
                if not url:
                    continue
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_date = ""
                pub_time = item.get("pubtime", "")
                if pub_time:
                    m = re.match(r"(\d{4}-\d{2}-\d{2})", pub_time)
                    if m:
                        pub_date = m.group(1)

                # 月份过滤
                if pub_date and not pub_date.startswith(year_month):
                    continue

                # 新能源相关性二次过滤
                if not self._is_relevant(title):
                    continue

                summary = (item.get("des") or "").strip()
                if summary and "<" in summary:
                    from bs4 import BeautifulSoup
                    summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
                if summary and len(summary) > 200:
                    summary = summary[:200]

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="新华网",
                    sub_industry=self._classify_industry(title),
                    url=url,
                )
                if record:
                    all_items.append(record)

            self.random_delay()

        print(f"[新华网] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[新华网] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[新华网] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
