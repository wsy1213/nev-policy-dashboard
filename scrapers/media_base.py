"""
媒体报道爬虫基类 — 继承 IndustryBaseScraper，覆盖 data_dir。
所有媒体爬虫共享标题过滤 + 子行业分类逻辑。
"""

from pathlib import Path

from scrapers.industry_base import IndustryBaseScraper
from scrapers.media_config import (
    MEDIA_DATA_DIR,
    MEDIA_INCLUDE_KEYWORDS,
    MEDIA_EXCLUDE_KEYWORDS,
    MEDIA_TITLE_INDUSTRY_MAP,
)


class MediaBaseScraper(IndustryBaseScraper):
    """媒体报道爬虫公共基类。"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, source_name: str):
        super().__init__(source_name)
        self.data_dir = Path(MEDIA_DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _is_relevant(self, title: str) -> bool:
        """标题是否包含新能源相关关键词。"""
        if not title:
            return False
        for ex in MEDIA_EXCLUDE_KEYWORDS:
            if ex in title:
                return False
        for kw in MEDIA_INCLUDE_KEYWORDS:
            if kw in title:
                return True
        return False

    def _classify_industry(self, title: str) -> str:
        """根据标题关键词判断子行业。"""
        for keyword, industry in MEDIA_TITLE_INDUSTRY_MAP.items():
            if keyword in title:
                return industry
        return "综合/其他"
