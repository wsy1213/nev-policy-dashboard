# ========== 行业数据源配置 ==========

# 行业数据输出目录（和政策数据分开）
INDUSTRY_DATA_DIR = "data/industry"

# ========== 国家能源局配置 ==========
NEA_BASE_URL = "https://www.nea.gov.cn"
NEA_NEWS_URL = "https://www.nea.gov.cn/xwfb/index.htm"  # 新闻发布列表页

# 标题关键词 → 子行业映射（用于自动分类 NEA 新闻）
NEA_TITLE_INDUSTRY_MAP = {
    "新能源汽车": "新能源汽车",
    "电动汽车": "新能源汽车",
    "充电": "新能源汽车",
    "充换电": "新能源汽车",
    "动力电池": "新能源汽车",
}

# NEA 标题过滤：包含这些关键词的新闻
NEA_DATA_KEYWORDS = [
    "新能源汽车", "电动汽车", "充电", "充换电", "动力电池",
    "汽车产销", "汽车销量",
    "智能网联", "自动驾驶", "换电站",
]

# NEA 标题排除：包含这些词的不是数据新闻
NEA_TITLE_EXCLUDE = [
    "巡视", "整改", "通报", "答复", "建议", "提案",
    "会议", "座谈", "调研", "培训",
    "招聘", "公示", "征求意见",
]

# ========== 乘联会配置 ==========
CPCA_BASE_URL = "https://www.cpcaauto.com"
CPCA_NEWS_URL = "https://www.cpcaauto.com/news.php?types=csjd"  # 车市解读

# 乘联会标题关键词过滤
CPCA_DATA_KEYWORDS = [
    "月度分析", "月份全国", "深度分析", "市场分析",
    "月度排名", "厂商销量", "新能源市场",
    "周度分析", "车市扫描", "新能源周报",
    "皮卡市场", "商用车",
    "乘用车", "车市", "扰透率", "零售",
    "出口", "产销快报", "走势",
]

# ========== 北极星储能网配置 ==========
BJX_BASE_URL = "https://chuneng.bjx.com.cn"
BJX_DATA_URL = "https://chuneng.bjx.com.cn/sj/"  # 数据栏目

# BJX 标题关键词 → 子行业映射
BJX_TITLE_INDUSTRY_MAP = {
    # 新能源汽车
    "新能源汽车": "新能源汽车",
    "乘用车": "新能源汽车",
    "汽车产销": "新能源汽车",
    "汽车销量": "新能源汽车",
    "电动汽车": "新能源汽车",
    "电动重卡": "新能源汽车",
    "智能网联": "新能源汽车",
    "自动驾驶": "新能源汽车",
    # 充电基础设施（归入新能源汽车）
    "充电": "新能源汽车",
    "充换电": "新能源汽车",
    "充电桩": "新能源汽车",
    "充电基础设施": "新能源汽车",
    "超充": "新能源汽车",
    "换电站": "新能源汽车",
    # 动力电池（归入新能源汽车）
    "电池装车": "新能源汽车",
    "动力电池": "新能源汽车",
    "锂电池": "新能源汽车",
    "固态电池": "新能源汽车",
}

# BJX 标题排除：企业新闻、招标等非数据类
BJX_TITLE_EXCLUDE = [
    "招标", "中标", "EPC", "采购",
    "发布会", "亮相", "展览", "峰会", "论坛",
    "首发", "新品", "解决方案",
]

# ========== 光伏行业协会 (CPIA) 配置 ==========
CPIA_BASE_URL = "https://www.chinapv.org.cn"
# 市场动态列表页
CPIA_MARKET_URL = "https://www.chinapv.org.cn/StaticPage/association_list29_1.html"
# 政策法规列表页
CPIA_POLICY_URL = "https://www.chinapv.org.cn/StaticPage/association_list28_1.html"
