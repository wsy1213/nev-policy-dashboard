# ========== 媒体报道数据源配置 ==========

# 媒体数据输出目录
MEDIA_DATA_DIR = "data/media"

# ========== 新能源关键词过滤 ==========
# 标题中包含以下任一关键词才保留
MEDIA_INCLUDE_KEYWORDS = [
    # 新能源汽车
    "新能源汽车", "电动汽车", "新能源车", "纯电",
    "插混", "混动", "比亚迪", "特斯拉", "蔚来",
    "小鹏", "理想汽车", "零跑汽车", "哪吒汽车",
    # 充电基础设施
    "充电桩", "充电站", "充换电", "充电基础设施", "超充",
    # 动力电池
    "动力电池", "电池装车", "宁德时代",
    # 汽车产销数据
    "汽车产销", "汽车销量", "乘用车",
]

# 标题排除词：包含这些词的即使匹配也不保留
MEDIA_EXCLUDE_KEYWORDS = [
    "招聘", "招标公告", "开庭", "判决",
    "股吧", "吧友",
]

# ========== 标题关键词 → 子行业映射 ==========
MEDIA_TITLE_INDUSTRY_MAP = {
    # 新能源汽车
    "新能源汽车": "新能源汽车",
    "电动汽车": "新能源汽车",
    "新能源车": "新能源汽车",
    "纯电": "新能源汽车",
    "插混": "新能源汽车",
    "比亚迪": "新能源汽车",
    "特斯拉": "新能源汽车",
    "蔚来": "新能源汽车",
    "小鹏": "新能源汽车",
    "理想汽车": "新能源汽车",
    "零跑汽车": "新能源汽车",
    "哪吒汽车": "新能源汽车",
    # 充电基础设施（归入新能源汽车）
    "充电桩": "新能源汽车",
    "充电站": "新能源汽车",
    "充换电": "新能源汽车",
    "充电基础设施": "新能源汽车",
    "超充": "新能源汽车",
    # 动力电池（归入新能源汽车）
    "动力电池": "新能源汽车",
    "宁德时代": "新能源汽车",
    "电池装车": "新能源汽车",
    # 汽车产销
    "汽车产销": "新能源汽车",
    "汽车销量": "新能源汽车",
    "乘用车": "新能源汽车",
}

# ========== 澎湃新闻 "能见度" 配置 ==========
THEPAPER_NODE_ID = 25436  # "能见度"栏目 node ID
THEPAPER_LIST_URL = "https://api.thepaper.cn/contentapi/nodeCont/getByNodeId"

# ========== 中国新闻网 财经频道 配置 ==========
CHINANEWS_BASE_URL = "https://www.chinanews.com.cn"
CHINANEWS_FINANCE_URL = "https://www.chinanews.com.cn/cj/gd.shtml"

# ========== 第一财经 配置 ==========
YICAI_BASE_URL = "https://www.yicai.com"
YICAI_NEWS_URL = "https://www.yicai.com/news/"
YICAI_ESG_URL = "https://www.yicai.com/esg/"

# ========== 界面新闻 配置 ==========
JIEMIAN_BASE_URL = "https://www.jiemian.com"
# 双碳频道
JIEMIAN_CARBON_URL = "https://www.jiemian.com/lists/877.html"
# ESG 频道
JIEMIAN_ESG_URL = "https://www.jiemian.com/lists/712.html"

# ========== 新华网 配置 ==========
XINHUA_SEARCH_URL = "https://search.news.cn/getNews"

# ========== 中国能源报 配置 ==========
CNENERGY_BASE_URL = "https://www.cnenergy.org"
