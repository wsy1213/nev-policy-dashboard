"""
清理无关数据 + 回填摘要。
对 frontend/public/data 和 data/ 中所有 JSON 做：
1. 根据标题关键词删除不相关条目
2. 抓取每条 URL 的正文，截取前 150 字作为摘要
3. 去除重复
"""

import json
import glob
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ─── 相关性关键词 ───
# 标题中必须包含至少一个才保留
CN_RELEVANT = [
    "新能源汽车", "电动汽车", "新能源车", "纯电", "插混", "混动",
    "比亚迪", "特斯拉", "蔚来", "小鹏", "理想汽车", "零跑", "哪吒",
    "充电桩", "充电站", "充换电", "超充", "换电",
    "动力电池", "宁德时代", "电池装车", "电池装机",
    "汽车产销", "汽车销量", "乘用车", "新能源市场",
    "智能网联", "自动驾驶", "车联网",
    "机动车辆生产", "道路机动车", "汽车工业",
    "吉利", "长安汽车", "广汽", "上汽", "北汽",
]
EN_RELEVANT = [
    "electric vehicle", " ev ", "ev-", "evs ", "bev", "phev",
    "plug-in", "tesla", "byd", "nio", "xpeng", "li auto",
    "charging", "charger", "battery", "lithium",
    "electric car", "ev sales", "ev market",
    "autonomous driving", "self-driving",
]

def is_relevant(title):
    """判断标题是否与新能源汽车相关"""
    if not title:
        return False
    t = title.lower()
    for kw in CN_RELEVANT:
        if kw in title:
            return True
    for kw in EN_RELEVANT:
        if kw in t:
            return True
    return False

def fetch_summary(url, max_len=150):
    """抓取 URL 正文内容，返回前 max_len 个字符作为摘要"""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除无关标签
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
            tag.decompose()

        # 尝试提取正文区域
        content = None
        for selector in [
            "article",
            ".article-content", ".article_content", ".article-body",
            ".news-content", ".news_content", ".newsDetail",
            ".content", ".main-content",
            "#article-content", "#content",
            ".post-content", ".entry-content",
        ]:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.body if soup.body else soup

        # 提取所有 <p> 文本
        paragraphs = content.find_all("p")
        text_parts = []
        for p in paragraphs:
            t = p.get_text(strip=True)
            if len(t) > 20:  # 跳过太短的段落
                text_parts.append(t)

        if not text_parts:
            # fallback: 获取所有文本
            text = content.get_text(separator=" ", strip=True)
            # 清理多余空白
            text = re.sub(r'\s+', ' ', text).strip()
        else:
            text = " ".join(text_parts)

        # 截取
        if len(text) > max_len:
            text = text[:max_len] + "..."

        return text

    except Exception as e:
        print(f"  ⚠ 抓取失败 {url[:50]}...: {e}")
        return ""


def process_json_file(filepath):
    """处理单个 JSON 文件：过滤 + 摘要 + 去重"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return

    original_count = len(data)

    # 1. 过滤不相关条目
    filtered = [item for item in data if isinstance(item, dict) and is_relevant(item.get("title", ""))]
    removed = original_count - len(filtered)

    # 2. 去重（按 URL）
    seen_urls = set()
    deduped = []
    for item in filtered:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)
    dup_count = len(filtered) - len(deduped)

    # 3. 回填摘要
    summary_added = 0
    for item in deduped:
        if not item.get("summary", "").strip():
            url = item.get("url", "")
            title = item.get("title", "")[:40]
            print(f"  📄 抓取摘要: {title}...")
            summary = fetch_summary(url)
            if summary:
                item["summary"] = summary
                summary_added += 1
            time.sleep(random.uniform(0.5, 1.5))

    # 保存
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {Path(filepath).name}: {original_count}→{len(deduped)} (删除{removed}无关+{dup_count}重复, 新增{summary_added}条摘要)")
    return removed, dup_count, summary_added


def main():
    total_removed = 0
    total_dup = 0
    total_summary = 0

    # 处理 frontend/public/data 和 data/ 两个目录
    patterns = [
        "frontend/public/data/*.json",
        "frontend/public/data/industry/*.json",
        "frontend/public/data/international/*.json",
        "frontend/public/data/media/*.json",
        "data/*.json",
        "data/industry/*.json",
        "data/international/*.json",
        "data/media/*.json",
    ]

    for pattern in patterns:
        files = [f for f in sorted(glob.glob(pattern)) if "manifest" not in f and "brief" not in f]
        if not files:
            continue
        print(f"\n── {pattern} ──")
        for filepath in files:
            result = process_json_file(filepath)
            if result:
                r, d, s = result
                total_removed += r
                total_dup += d
                total_summary += s

    print(f"\n{'='*50}")
    print(f"总计: 删除 {total_removed} 条无关 + {total_dup} 条重复, 新增 {total_summary} 条摘要")


if __name__ == "__main__":
    main()
