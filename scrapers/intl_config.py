# ========== 国际数据源配置 ==========

# 国际数据输出目录
INTL_DATA_DIR = "data/international"

# ========== 英文标题关键词 → 子行业映射 ==========
INTL_TITLE_INDUSTRY_MAP = {
    # 新能源汽车
    "electric vehicle": "新能源汽车",
    "ev ": "新能源汽车",
    "ev-": "新能源汽车",
    "evs": "新能源汽车",
    "electric car": "新能源汽车",
    "plug-in": "新能源汽车",
    "tesla": "新能源汽车",
    "byd": "新能源汽车",
    # 充电基础设施（归入新能源汽车）
    "charging": "新能源汽车",
    "charger": "新能源汽车",
    "charging station": "新能源汽车",
    "charging infrastructure": "新能源汽车",
    # 动力电池（归入新能源汽车）
    "battery": "新能源汽车",
    "lithium": "新能源汽车",
}

# 只保留包含这些关键词的文章（宽松过滤）
INTL_DATA_KEYWORDS = [
    "electric vehicle", "ev", "plug-in", "tesla", "byd",
    "charging", "charger",
    "battery", "lithium",
    "automotive", "car sales", "vehicle",
]

# 排除的标题关键词（不太相关的新闻）
INTL_TITLE_EXCLUDE = [
    "podcast", "webinar", "training", "recruitment",
    "careers", "job", "internship", "vacancy",
    "cookie", "privacy policy",
]

# ========== EIA 配置 ==========
EIA_RSS_URL = "https://www.eia.gov/rss/todayinenergy.xml"

# ========== IRENA 配置 ==========
IRENA_RSS_URL = "https://www.irena.org/iapi/rssfeed/News"

# ========== IEA 配置 ==========
IEA_NEWS_URL = "https://www.iea.org/news"
