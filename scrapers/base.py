import hashlib
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

from scrapers.config import DATA_DIR, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX


class BaseScraper:
    """爬虫基类，提供数据保存、去重、延迟等通用功能。"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.data_dir = Path(DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_id(url: str) -> str:
        """根据 URL 生成唯一 ID。"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    @staticmethod
    def random_delay():
        """随机等待，模拟人类行为。"""
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        time.sleep(delay)

    def get_data_file(self, year_month: str) -> Path:
        """获取按月分的数据文件路径，如 data/2026-03.json。"""
        return self.data_dir / f"{year_month}.json"

    def load_existing_data(self, year_month: str) -> list[dict]:
        """加载已有的月度数据。"""
        filepath = self.get_data_file(year_month)
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_data(self, year_month: str, records: list[dict]):
        """保存数据到月度 JSON 文件。"""
        filepath = self.get_data_file(year_month)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"[{self.source_name}] 已保存 {len(records)} 条数据到 {filepath}")

    def merge_and_save(self, year_month: str, new_records: list[dict]) -> int:
        """将新数据与已有数据合并（按 URL 去重），返回新增条数。"""
        existing = self.load_existing_data(year_month)
        existing_urls = {r["url"] for r in existing}

        added = 0
        for record in new_records:
            if record["url"] not in existing_urls:
                existing.append(record)
                existing_urls.add(record["url"])
                added += 1

        # 按发布日期倒序排列
        existing.sort(key=lambda r: r.get("pub_date", ""), reverse=True)
        self.save_data(year_month, existing)
        print(f"[{self.source_name}] 新增 {added} 条，总计 {len(existing)} 条")
        return added

    def make_record(self, **kwargs) -> dict:
        """构建标准化的数据记录。"""
        url = kwargs.get("url", "")
        return {
            "id": self.generate_id(url),
            "title": kwargs.get("title", ""),
            "doc_number": kwargs.get("doc_number", ""),
            "issuing_body": kwargs.get("issuing_body", ""),
            "pub_date": kwargs.get("pub_date", ""),
            "impl_date": kwargs.get("impl_date", ""),
            "effectiveness": kwargs.get("effectiveness", ""),
            "category": kwargs.get("category", ""),
            "sub_industry": kwargs.get("sub_industry", ""),
            "search_keyword": kwargs.get("search_keyword", ""),
            "url": url,
            "scraped_at": datetime.now().isoformat(),
        }
