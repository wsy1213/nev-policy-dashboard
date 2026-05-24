#!/usr/bin/env python3
"""Quick batch check of all sites with per-site timeout via threading"""
import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import threading
import queue

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

all_sites = [
    ("CWEA风能专委会", "https://www.cwea.org.cn/"),
    ("氢能联盟h2cn.org.cn", "https://www.h2cn.org.cn/"),
    ("氢能联盟h2cn.org", "https://www.h2cn.org/"),
    ("工信部首页", "https://www.miit.gov.cn/"),
    ("工信部数据", "https://www.miit.gov.cn/gxsj/index.html"),
    ("统计局首页", "https://www.stats.gov.cn/"),
    ("统计局最新发布", "https://www.stats.gov.cn/sj/zxfb/"),
    ("中电联CEC", "https://www.cec.org.cn/"),
    ("北极星光伏数据", "https://guangfu.bjx.com.cn/sj/"),
    ("北极星风电数据", "https://feng.bjx.com.cn/sj/"),
    ("北极星氢能数据", "https://h2.bjx.com.cn/sj/"),
]

def check_site(name, url, result_q, timeout_sec=12):
    result = {"name": name, "url": url}
    try:
        resp = requests.get(url, headers=headers, timeout=(6, timeout_sec), allow_redirects=True, verify=True)
        enc = resp.apparent_encoding or 'utf-8'
        resp.encoding = enc
        text = resp.text
        result["status"] = resp.status_code
        result["length"] = len(text)
        if resp.url != url:
            result["redirect"] = resp.url
        
        soup = BeautifulSoup(text, 'html.parser')
        title_tag = soup.title
        result["title"] = title_tag.string.strip() if title_tag and title_tag.string else "无title"
        
        body = soup.find('body')
        body_text = body.get_text(strip=True) if body else ""
        result["script_count"] = len(soup.find_all('script'))
        result["body_text_len"] = len(body_text)
        
        vue_app = soup.find(id='app') or soup.find(id='__nuxt') or soup.find(id='root') or soup.find(id='__next')
        if vue_app:
            children = len(list(vue_app.children))
            vtext = vue_app.get_text(strip=True)
            result["js_container"] = f"id={vue_app.get('id')}, ch={children}, txt={len(vtext)}"
            result["js_rendered"] = children <= 3 and len(vtext) < 50
        else:
            result["js_rendered"] = False
        
        result["link_count"] = len(soup.find_all('a', href=True))
        
        date_pattern = re.compile(r'20\d{2}[-./年]\d{1,2}[-./月]?\d{0,2}')
        dates = date_pattern.findall(text)
        result["date_count"] = len(dates)
        result["sample_dates"] = dates[:5]
        result["li_count"] = len(soup.find_all('li'))
        
        articles = []
        for li in soup.find_all('li')[:40]:
            a = li.find('a', href=True)
            if a and a.get_text(strip=True):
                t = a.get_text(strip=True)
                h = a['href']
                d = date_pattern.search(li.get_text())
                if d and len(t) > 5:
                    articles.append({"t": t[:60], "h": h[:80], "d": d.group()})
        result["articles"] = articles[:5]
        result["html_snippet"] = text[:400]

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    
    result_q.put(result)

results = []
for name, url in all_sites:
    print(f"检测: {name} ...", file=sys.stderr, flush=True)
    q = queue.Queue()
    t = threading.Thread(target=check_site, args=(name, url, q))
    t.daemon = True
    t.start()
    t.join(timeout=18)
    
    if not q.empty():
        r = q.get()
    else:
        r = {"name": name, "url": url, "error": "线程超时18s，网站不可达"}
    results.append(r)

# Output compact summary
for r in results:
    print(f"\n### {r['name']} ({r['url']})")
    if "error" in r:
        print(f"  ERROR: {r['error']}")
        continue
    print(f"  状态码={r['status']} 长度={r['length']} 编码={r.get('encoding','?')}")
    print(f"  标题: {r.get('title','?')}")
    print(f"  Script数={r['script_count']} Body文本长度={r['body_text_len']}")
    print(f"  JS渲染={r['js_rendered']} {r.get('js_container','')}")
    print(f"  链接数={r['link_count']} <li>数={r['li_count']}")
    print(f"  日期数={r['date_count']} 示例={r.get('sample_dates',[])}")
    if r.get('redirect'):
        print(f"  重定向: {r['redirect']}")
    if r.get('articles'):
        print(f"  文章示例:")
        for a in r['articles']:
            print(f"    [{a['d']}] {a['t']} -> {a['h']}")
    print(f"  HTML片段: {r.get('html_snippet','')[:200]}")
