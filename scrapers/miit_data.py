"""
工信部装备工业统计分析爬虫（MIIT）。
抓取 miit.gov.cn/gxsj/tjfx/zbgy/ 的汽车工业经济运行等数据文章。
页面为JS渲染，使用 Playwright 抓取。
"""

import asyncio
from playwright.async_api import async_playwright

from scrapers.industry_base import IndustryBaseScraper

# 装备工业统计分析页面
MIIT_URL = "https://www.miit.gov.cn/gxsj/tjfx/zbgy/index.html"

# 标题关键词 → 子行业映射
MIIT_TITLE_INDUSTRY_MAP = {
    "汽车": "新能源汽车",
    "新能源汽车": "新能源汽车",
    "电动汽车": "新能源汽车",
    "造船": "综合/其他",
    "船舶": "综合/其他",
    "航空": "综合/其他",
    "机械": "综合/其他",
}

# 只保留包含这些关键词的文章
MIIT_DATA_KEYWORDS = [
    "汽车", "新能源汽车", "造船", "船舶",
    "运行情况", "产销", "产量", "销量",
    "工业经济", "装备工业",
]


class MIITScraper(IndustryBaseScraper):
    """工信部装备工业统计分析爬虫（Playwright）。"""

    def __init__(self):
        super().__init__(source_name="工信部")

    def _classify_industry(self, title: str) -> str:
        """根据标题关键词判断子行业。"""
        for keyword, industry in MIIT_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return "综合/其他"

    def _is_relevant(self, title: str) -> bool:
        """判断标题是否和装备工业数据相关。"""
        for kw in MIIT_DATA_KEYWORDS:
            if kw in title:
                return True
        return False

    async def _fetch_list(self) -> list[dict]:
        """使用 Playwright 抓取列表页。"""
        items = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(MIIT_URL, wait_until="networkidle", timeout=30000)
                # 额外等待确保内容渲染
                await page.wait_for_timeout(2000)

                # 提取所有 li.cf 列表项
                raw = await page.eval_on_selector_all(
                    "li.cf",
                    """els => els.map(el => {
                        const a = el.querySelector('a.fl');
                        const span = el.querySelector('span.fr');
                        return {
                            title: a ? (a.getAttribute('title') || a.textContent.trim()) : '',
                            href: a ? a.href : '',
                            date: span ? span.textContent.trim() : ''
                        };
                    })"""
                )

                for item in raw:
                    title = item.get("title", "").strip()
                    href = item.get("href", "").strip()
                    date = item.get("date", "").strip()

                    if not title or not href or len(title) < 5:
                        continue

                    items.append({
                        "title": title,
                        "pub_date": date,
                        "url": href,
                    })

                print(f"[工信部] 共抓取到 {len(items)} 条文章")
            finally:
                await browser.close()

        return items

    def scrape(self, year_month: str) -> list[dict]:
        """抓取并筛选指定月份的装备工业数据。"""
        items = asyncio.run(self._fetch_list())
        all_records = []

        for item in items:
            title = item["title"]
            pub_date = item["pub_date"]

            # 按发布日期过滤月份
            if pub_date and not pub_date.startswith(year_month):
                continue

            # 只要与装备工业数据相关的
            if not self._is_relevant(title):
                continue

            sub_industry = self._classify_industry(title)

            record = self.make_record(
                title=title,
                pub_date=pub_date,
                source="工信部",
                sub_industry=sub_industry,
                summary="",
                url=item["url"],
            )
            if record:
                all_records.append(record)

        print(f"[工信部(MIIT)] {year_month} 筛选出 {len(all_records)} 条数据文章")
        if all_records:
            self.merge_and_save(year_month, all_records)
        return all_records

    def run(self, mode: str = "backfill", year_month: str = ""):
        if mode == "backfill" and year_month:
            print(f"\n{'='*60}")
            print(f"[工信部] 回溯模式: {year_month}")
            print(f"{'='*60}")
            return self.scrape(year_month)
        elif mode == "daily":
            from datetime import date
            today = date.today()
            ym = today.strftime("%Y-%m")
            print(f"\n{'='*60}")
            print(f"[工信部] 每日增量模式: {ym}")
            print(f"{'='*60}")
            return self.scrape(ym)
