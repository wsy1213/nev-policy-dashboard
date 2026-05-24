"""
中国充电联盟（EVCIPA）数据爬虫。
抓取充电基础设施月度运行数据。
"""

import re
import requests
from bs4 import BeautifulSoup

from scrapers.industry_base import IndustryBaseScraper


EVCIPA_BASE_URL = "https://www.evcipa.org.cn"
# 数据发布/行业资讯页面
EVCIPA_NEWS_URL = "https://www.evcipa.org.cn/#/newsList"

EVCIPA_DATA_KEYWORDS = [
    "充电基础设施", "充电桩", "充换电", "充电量",
    "运行情况", "月度", "数据", "统计", "保有量",
    "公共充电", "超充", "换电站",
]


class EVCIPAScraper(IndustryBaseScraper):
    """中国充电联盟数据爬虫。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/html,*/*;q=0.8",
        "Referer": "https://www.evcipa.org.cn/",
    }

    def __init__(self):
        super().__init__(source_name="充电联盟")

    def _is_relevant(self, title: str) -> bool:
        for kw in EVCIPA_DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    def _try_api(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """尝试通过 API 获取数据。"""
        api_urls = [
            f"{EVCIPA_BASE_URL}/api/news/list",
            f"{EVCIPA_BASE_URL}/api/article/list",
        ]
        for api_url in api_urls:
            try:
                resp = requests.get(
                    api_url,
                    params={"page": page, "pageSize": page_size, "type": "data"},
                    headers=self.HEADERS,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", {}).get("list", [])
                    if items:
                        return items
            except (requests.RequestException, ValueError):
                continue
        return []

    def _parse_html(self) -> list[dict]:
        """回退到 HTML 解析。"""
        try:
            resp = requests.get(
                EVCIPA_BASE_URL, headers=self.HEADERS, timeout=15,
            )
            resp.encoding = "utf-8"
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[充电联盟] 请求失败: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for a_tag in soup.select("a[href]"):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            if not title or len(title) < 8:
                continue
            if not self._is_relevant(title):
                continue
            if href.startswith("/"):
                href = EVCIPA_BASE_URL + href
            items.append({"title": title, "url": href, "pub_date": ""})
        return items

    def scrape(self, year_month: str):
        print(f"[充电联盟] 开始抓取 {year_month}")

        # 优先尝试 API
        api_items = self._try_api()
        items = []
        if api_items:
            for item in api_items:
                title = item.get("title", "").strip()
                pub_date = ""
                create_time = item.get("createTime") or item.get("publishTime", "")
                if create_time:
                    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(create_time))
                    if m:
                        pub_date = m.group(1)
                url = item.get("url", "") or f"{EVCIPA_BASE_URL}/#/newsDetail?id={item.get('id', '')}"
                items.append({"title": title, "url": url, "pub_date": pub_date})
        else:
            items = self._parse_html()

        all_records = []
        for item in items:
            title, pub_date, url = item["title"], item["pub_date"], item["url"]
            if pub_date and not pub_date.startswith(year_month):
                continue
            if not self._is_relevant(title):
                continue
            record = self.make_record(
                title=title,
                pub_date=pub_date,
                source="充电联盟",
                sub_industry="新能源汽车",
                summary="",
                url=url,
            )
            all_records.append(record)

        print(f"[充电联盟] {year_month} 筛选出 {len(all_records)} 条")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[充电联盟] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[充电联盟] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
