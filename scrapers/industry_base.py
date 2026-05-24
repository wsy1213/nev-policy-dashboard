import hashlib
import json
import random
import time
from datetime import datetime
from pathlib import Path

from scrapers.industry_config import INDUSTRY_DATA_DIR
from scrapers.config import REQUEST_DELAY_MIN, REQUEST_DELAY_MAX
from scrapers.summarizer import fetch_and_summarize


class IndustryBaseScraper:
    """行业数据爬虫基类。数据独立存放在 data/industry/ 目录。"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.data_dir = Path(INDUSTRY_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_id(url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()[:12]

    @staticmethod
    def random_delay():
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def get_data_file(self, year_month: str) -> Path:
        """如 data/industry/2026-03.json"""
        return self.data_dir / f"{year_month}.json"

    def load_existing(self, year_month: str) -> list[dict]:
        filepath = self.get_data_file(year_month)
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_data(self, year_month: str, records: list[dict]):
        filepath = self.get_data_file(year_month)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"[{self.source_name}] 已保存 {len(records)} 条到 {filepath}")

    def merge_and_save(self, year_month: str, new_records: list[dict]) -> int:
        """合并新旧数据，按 URL 去重，返回新增条数。"""
        existing = self.load_existing(year_month)
        existing_urls = {r["url"] for r in existing}

        added = 0
        for record in new_records:
            if record["url"] not in existing_urls:
                existing.append(record)
                existing_urls.add(record["url"])
                added += 1

        existing.sort(key=lambda r: r.get("pub_date", ""), reverse=True)
        self.save_data(year_month, existing)
        print(f"[{self.source_name}] 新增 {added} 条，总计 {len(existing)} 条")
        return added

    def make_record(self, **kwargs) -> dict:
        """构建行业新闻/数据记录。无法获取正文时返回 None。"""
        url = kwargs.get("url", "")
        title = kwargs.get("title", "")
        summary = kwargs.get("summary", "")
        # 如果没有提供摘要，尝试从 URL 抓取并用 LLM 生成
        if not summary and url:
            _text, summary = fetch_and_summarize(url, title)
            if not summary:
                print(f"  [跳过] 无法获取正文或生成摘要: {title}")
                return None
        return {
            "id": self.generate_id(url),
            "title": title,
            "pub_date": kwargs.get("pub_date", ""),
            "source": kwargs.get("source", self.source_name),
            "sub_industry": kwargs.get("sub_industry", "综合/其他"),
            "summary": summary,
            "url": url,
            "scraped_at": datetime.now().isoformat(),
        }

    @staticmethod
    def fetch_summary(url, title=""):
        """用 LLM 生成文章摘要。无法获取正文时返回空字符串。"""
        _text, summary = fetch_and_summarize(url, title)
        return summary
