import requests
from bs4 import BeautifulSoup
import re
import json
import sys
import socket

socket.setdefaulttimeout(12)

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

name = sys.argv[1]
url = sys.argv[2]
result = {"name": name, "url": url}

try:
    resp = requests.get(url, headers=headers, timeout=(8,12), allow_redirects=True, verify=True)
    enc = resp.apparent_encoding or 'utf-8'
    resp.encoding = enc
    text = resp.text
    result["status"] = resp.status_code
    result["length"] = len(text)
    result["encoding"] = enc
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
        result["js_container"] = f"id={vue_app.get('id')}, children={children}, text={len(vtext)}"
        result["js_rendered"] = children <= 3 and len(vtext) < 50
    else:
        result["js_rendered"] = False
    
    result["link_count"] = len(soup.find_all('a', href=True))
    
    date_pattern = re.compile(r'20\d{2}[-./年]\d{1,2}[-./月]?\d{0,2}')
    dates_found = date_pattern.findall(text)
    result["date_count"] = len(dates_found)
    result["sample_dates"] = dates_found[:5]
    result["li_count"] = len(soup.find_all('li'))
    
    # 找文章列表
    article_items = []
    for li in soup.find_all('li')[:40]:
        a = li.find('a', href=True)
        if a and a.get_text(strip=True):
            t = a.get_text(strip=True)
            h = a['href']
            li_text = li.get_text()
            d = date_pattern.search(li_text)
            if d and len(t) > 5:
                article_items.append({"t": t[:60], "h": h[:80], "d": d.group()})
    result["articles"] = article_items[:5]
    result["html_snippet"] = text[:500]

except Exception as e:
    result["error"] = f"{type(e).__name__}: {str(e)[:300]}"

print(json.dumps(result, ensure_ascii=False))
