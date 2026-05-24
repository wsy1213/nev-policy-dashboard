"""
国际数据爬虫基类。
数据独立存放在 data/international/ 目录。
提供标题翻译（英→中）和英文关键词分类功能。
"""

import time
from pathlib import Path

from deep_translator import GoogleTranslator

from scrapers.industry_base import IndustryBaseScraper
from scrapers.intl_config import (
    INTL_DATA_DIR,
    INTL_TITLE_INDUSTRY_MAP,
    INTL_DATA_KEYWORDS,
    INTL_TITLE_EXCLUDE,
)


class IntlBaseScraper(IndustryBaseScraper):
    """国际新能源数据爬虫基类。"""

    def __init__(self, source_name: str):
        super().__init__(source_name)
        # 覆盖数据目录为 data/international/
        self.data_dir = Path(INTL_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._translator = None

    @property
    def translator(self):
        if self._translator is None:
            self._translator = GoogleTranslator(source="en", target="zh-CN")
        return self._translator

    def translate_title(self, title_en: str) -> str:
        """将英文标题翻译为中文。翻译失败时返回原文。"""
        if not title_en:
            return title_en
        try:
            result = self.translator.translate(title_en)
            return result if result else title_en
        except Exception as e:
            print(f"[{self.source_name}] 翻译失败: {e}")
            return title_en

    def translate_titles_batch(self, titles: list[str]) -> list[str]:
        """批量翻译标题（用换行符连接，一次API调用）。"""
        if not titles:
            return []
        try:
            joined = "\n".join(titles)
            result = self.translator.translate(joined)
            parts = result.split("\n") if result else titles
            # 确保数量对齐
            if len(parts) != len(titles):
                print(f"[{self.source_name}] 批量翻译数量不匹配 ({len(parts)} vs {len(titles)})，逐条翻译")
                return [self.translate_title(t) for t in titles]
            return parts
        except Exception as e:
            print(f"[{self.source_name}] 批量翻译失败: {e}，逐条翻译")
            return [self.translate_title(t) for t in titles]

    def classify_industry(self, title: str) -> str:
        """根据英文标题关键词判断子行业。"""
        lower = title.lower()
        for keyword, industry in INTL_TITLE_INDUSTRY_MAP.items():
            if keyword in lower:
                return industry
        return "综合/其他"

    def is_relevant(self, title: str) -> bool:
        """判断标题是否与新能源/清洁能源相关。"""
        lower = title.lower()
        for kw in INTL_TITLE_EXCLUDE:
            if kw in lower:
                return False
        for kw in INTL_DATA_KEYWORDS:
            if kw in lower:
                return True
        return False

    def make_intl_record(self, **kwargs) -> dict:
        """构建国际新闻记录（包含 title_en 字段）。"""
        record = self.make_record(**kwargs)
        if record is None:
            return None
        record["title_en"] = kwargs.get("title_en", "")
        return record
