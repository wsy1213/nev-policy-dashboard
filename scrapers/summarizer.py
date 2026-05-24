"""
LLM 摘要生成模块 — 调用 DeepSeek API 对文章正文进行总结。
"""

import os
import re

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = None

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

_CONTENT_SELECTORS = [
    "article", ".article-content", ".article_content", ".article-body",
    ".news-content", ".news_content", ".newsDetail",
    ".content", ".main-content", "#article-content", "#content",
    ".post-content", ".entry-content",
    ".TRS_Editor",  # 政府网站常用
]

_NOISE_MARKERS = [
    "请使用浏览器访问本站", "打开微信", "JavaScript",
    "请升级浏览器", "该内容需要登录", "您的浏览器版本过低",
]

SYSTEM_PROMPT = (
    "你是一个新能源汽车行业资讯分析师。"
    "请用1-2句中文概括以下文章的核心内容，突出关键数据和要点。"
    "不要超过100字。不要使用\"本文\"等词语，直接概述内容。"
)


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("未配置 DEEPSEEK_API_KEY")
        _client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return _client


def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    """抓取 URL 正文内容，返回纯文本（最多 max_chars 字符）。
    
    返回空字符串表示无法获取正文。
    """
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=12, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer",
                         "aside", "form", "noscript", "iframe"]):
            tag.decompose()

        content = None
        for sel in _CONTENT_SELECTORS:
            content = soup.select_one(sel)
            if content:
                break
        if not content:
            content = soup.body if soup.body else soup

        paragraphs = content.find_all("p")
        text_parts = [p.get_text(strip=True) for p in paragraphs
                      if len(p.get_text(strip=True)) > 15]

        if text_parts:
            text = "\n".join(text_parts)
        else:
            text = content.get_text(separator="\n", strip=True)

        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        # 噪音检测 — 如果正文太短或包含典型阻拦信息，认为无法获取
        if len(text) < 80:
            return ""
        for marker in _NOISE_MARKERS:
            if marker in text[:200]:
                return ""

        return text[:max_chars]
    except Exception:
        return ""


def generate_summary(text: str, title: str = "") -> str:
    """调用 DeepSeek 生成摘要。"""
    if not text:
        return ""
    try:
        client = _get_client()
        user_msg = f"标题：{title}\n\n正文：\n{text}" if title else text
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        summary = resp.choices[0].message.content.strip()
        # 去掉可能的引号包裹
        summary = summary.strip('"').strip('"').strip('"')
        return summary
    except Exception as e:
        print(f"  [LLM摘要] 生成失败: {e}")
        return ""


def fetch_and_summarize(url: str, title: str = "") -> tuple[str, str]:
    """抓取文章 + 生成摘要。
    
    返回 (full_text, summary)。
    如果无法获取正文，两个都返回空字符串。
    """
    text = fetch_article_text(url)
    if not text:
        return "", ""
    summary = generate_summary(text, title)
    return text, summary
