"""
欧洲汽车制造商协会（ACEA）电动汽车数据爬虫。
抓取 acea.auto 的欧洲电动汽车注册量月度报告。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.intl_base import IntlBaseScraper


ACEA_BASE_URL = "https://www.acea.auto"
ACEA_EV_URL = "https://www.acea.auto/nav/?content=news"

ACEA_KEYWORDS = [
    "electric", "ev", "battery", "plug-in", "registration",
    "sales", "market", "zero-emission", "charging",
]


class ACEAScraper(IntlBaseScraper):
    """ACEA 欧洲电动汽车数据爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self):
        super().__init__(source_name="ACEA")

    def _is_ev_relevant(self, title: str) -> bool:
        lower = title.lower()
        for kw in ACEA_KEYWORDS:
            if kw in lower:
                return True
        return False

    def _parse_list(self) -> list[dict]:
        """抓取 ACEA 新闻/数据发布页面。"""
        print(f"[ACEA] 正在抓取: {ACEA_EV_URL}")
        try:
            resp = requests.get(ACEA_EV_URL, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[ACEA] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []

        for article in soup.select("article, .post, .news-item, .card"):
            a_tag = article.select_one("a[href]")
            if not a_tag:
                continue
            href = a_tag.get("href", "").strip()
            title = a_tag.get_text(strip=True)

            if not title or len(title) < 10:
                h_tag = article.select_one("h2, h3, h4")
                if h_tag:
                    title = h_tag.get_text(strip=True)

            if not title or len(title) < 10:
                continue
            if href.startswith("/"):
                href = ACEA_BASE_URL + href

            pub_date = ""
            time_el = article.select_one("time[datetime]")
            if time_el:
                dt = time_el.get("datetime", "")
                m = re.match(r"(\d{4}-\d{2}-\d{2})", dt)
                if m:
                    pub_date = m.group(1)
            if not pub_date:
                date_el = article.select_one(".date, .meta, span")
                if date_el:
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_el.get_text())
                    if m:
                        pub_date = m.group(1)

            items.append({"title": title, "url": href, "pub_date": pub_date})

        # 去重
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)

        print(f"[ACEA] 找到 {len(unique)} 条文章")
        return unique

    def scrape(self, year_month: str) -> list[dict]:
        items = self._parse_list()

        relevant_items = []
        for item in items:
            title_en = item["title"]
            pub_date = item["pub_date"]
            if pub_date and not pub_date.startswith(year_month):
                continue
            if not self._is_ev_relevant(title_en):
                continue
            relevant_items.append(item)

        if not relevant_items:
            print(f"[ACEA] {year_month} 筛选出 0 条")
            return []

        titles_en = [item["title"] for item in relevant_items]
        titles_cn = self.translate_titles_batch(titles_en)

        all_records = []
        for item, title_cn in zip(relevant_items, titles_cn):
            record = self.make_intl_record(
                title=title_cn,
                title_en=item["title"],
                pub_date=item["pub_date"],
                source="ACEA",
                sub_industry="新能源汽车",
                summary="",
                url=item["url"],
            )
            if record:
                all_records.append(record)

        print(f"[ACEA] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[ACEA] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[ACEA] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
