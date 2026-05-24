"""
澎湃新闻「能见度」栏目爬虫。
能见度是澎湃新闻的能源频道，覆盖光伏、储能、油气、电力等领域。
调用澎湃内部 JSON API 获取文章列表。
"""

import requests

from scrapers.media_base import MediaBaseScraper
from scrapers.media_config import THEPAPER_NODE_ID


class ThepaperScraper(MediaBaseScraper):
    """澎湃新闻「能见度」爬虫（JSON API）。"""

    API_URL = "https://api.thepaper.cn/contentapi/nodeCont/getByNodeId"

    def __init__(self):
        super().__init__(source_name="澎湃新闻")

    def _fetch_page(self, page: int = 1, page_size: int = 20) -> list[dict]:
        """获取一页文章列表。"""
        payload = {
            "nodeId": THEPAPER_NODE_ID,
            "pageNum": page,
            "pageSize": page_size,
        }
        headers = {
            **self.HEADERS,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[澎湃新闻] API 请求失败: {e}")
            return []

        # 提取文章列表
        result = data.get("data", {})
        if isinstance(result, dict):
            return result.get("list", []) or result.get("data", [])
        return []

    def scrape(self, year_month: str, max_pages: int = 5):
        all_items = []

        for page in range(1, max_pages + 1):
            print(f"[澎湃新闻] 正在抓取第 {page} 页 ...")
            raw_list = self._fetch_page(page=page, page_size=20)
            if not raw_list:
                print(f"[澎湃新闻] 第 {page} 页无数据，停止翻页")
                break

            stop_early = False
            for item in raw_list:
                title = (item.get("name") or item.get("title", "")).strip()
                if not title:
                    continue

                # 日期：优先使用 pubTimeLong (毫秒时间戳)
                pub_date = ""
                pub_time_long = item.get("pubTimeLong")
                if pub_time_long:
                    from datetime import datetime
                    try:
                        pub_date = datetime.fromtimestamp(pub_time_long / 1000).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        pass

                if not pub_date:
                    pub_time_str = item.get("pubTime", "")
                    # pubTime 可能是 "7小时前" 这种相对时间，跳过
                    if pub_time_str and pub_time_str[:4].isdigit():
                        pub_date = pub_time_str[:10]

                if not pub_date:
                    continue

                # 月份过滤
                item_ym = pub_date[:7]
                if item_ym < year_month:
                    stop_early = True
                    break
                if item_ym != year_month:
                    continue

                # 新能源相关性过滤
                if not self._is_relevant(title):
                    continue

                # 构建 URL
                cont_id = item.get("contId") or item.get("id", "")
                url = f"https://www.thepaper.cn/newsDetail_forward_{cont_id}" if cont_id else ""

                summary = (item.get("summary") or item.get("subtitle", "")).strip()
                if summary and len(summary) > 200:
                    summary = summary[:200]

                record = self.make_record(
                    title=title,
                    pub_date=pub_date,
                    source="澎湃新闻",
                    sub_industry=self._classify_industry(title),
                    url=url,
                )
                if record:
                    all_items.append(record)

            if stop_early:
                print(f"[澎湃新闻] 已到达目标月份之前的数据，停止翻页")
                break
            self.random_delay()

        print(f"[澎湃新闻] {year_month} 筛选出 {len(all_items)} 条新能源报道")
        if all_items:
            self.merge_and_save(year_month, all_items)
        return all_items

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[澎湃新闻] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month, max_pages=10)
        elif mode == "daily":
            from datetime import date
            ym = date.today().strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[澎湃新闻] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym, max_pages=3)
