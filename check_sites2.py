import requests
from bs4 import BeautifulSoup
import re
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

def check_site(name, url):
    result = {"name": name, "url": url}
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True, verify=True)
        enc = resp.apparent_encoding or 'utf-8'
        resp.encoding = enc
        text = resp.text
        result["status"] = resp.status_code
        result["length"] = len(text)
        result["encoding"] = enc
        result["content_type"] = resp.headers.get('Content-Type','N/A')
        if resp.url != url:
            result["redirect"] = resp.url
        
        soup = BeautifulSoup(text, 'html.parser')
        title_tag = soup.title
        result["title"] = title_tag.string.strip() if title_tag and title_tag.string else "无title"
        
        scripts = soup.find_all('script')
        body = soup.find('body')
        body_text = body.get_text(strip=True) if body else ""
        result["script_count"] = len(scripts)
        result["body_text_len"] = len(body_text)
        
        # JS框架检测
        vue_app = soup.find(id='app') or soup.find(id='__nuxt') or soup.find(id='root') or soup.find(id='__next')
        if vue_app:
            children = len(list(vue_app.children))
            vtext = vue_app.get_text(strip=True)
            result["js_framework"] = f"id='{vue_app.get('id')}', children={children}, text_len={len(vtext)}"
            if children <= 3 and len(vtext) < 50:
                result["js_rendered"] = True
            else:
                result["js_rendered"] = False
        else:
            result["js_rendered"] = False
        
        links = soup.find_all('a', href=True)
        result["link_count"] = len(links)
        
        date_pattern = re.compile(r'20\d{2}[-./年]\d{1,2}[-./月]?\d{0,2}')
        dates_found = date_pattern.findall(text)
        result["date_count"] = len(dates_found)
        result["sample_dates"] = dates_found[:5]
        
        lis = soup.find_all('li')
        result["li_count"] = len(lis)
        
        # 找文章列表结构 - 看li中带a和日期的
        article_items = []
        for li in lis[:30]:
            a = li.find('a', href=True)
            if a and a.get_text(strip=True):
                t = a.get_text(strip=True)
                h = a['href']
                # 找日期
                li_text = li.get_text()
                d = date_pattern.search(li_text)
                if d and len(t) > 5:
                    article_items.append({"title": t[:60], "href": h[:80], "date": d.group()})
        result["sample_articles"] = article_items[:5]
        
        result["html_head"] = text[:600]
        result["body_head"] = str(body)[:400] if body else ""
        
    except requests.exceptions.SSLError as e:
        result["error"] = f"SSL: {str(e)[:200]}"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接: {str(e)[:200]}"
    except requests.exceptions.Timeout:
        result["error"] = "超时15s"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    
    return result

import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Global timeout")

def safe_check(name, url):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(20)
    try:
        return check_site(name, url)
    except TimeoutError:
        return {"name": name, "url": url, "error": "全局超时20s"}
    except Exception as e:
        return {"name": name, "url": url, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    finally:
        signal.alarm(0)

import sys
import time

batch = int(sys.argv[1]) if len(sys.argv) > 1 else 1

all_sites = [
    ("中汽协 CAAM 产销", "http://www.caam.org.cn/chn/1/cate_2/list_1.html"),
    ("中汽协 CAAM 新能源", "http://www.caam.org.cn/chn/4/cate_39/list_1.html"),
    ("充电联盟 EVCIPA", "https://www.evcipa.org.cn/"),
    ("中国汽车流通协会 CADA", "http://www.cada.cn/"),
    ("风能专委会 CWEA", "https://www.cwea.org.cn/"),
    ("中国氢能联盟 h2cn.org.cn", "https://www.h2cn.org.cn/"),
    ("中国氢能联盟 h2cn.org", "https://www.h2cn.org/"),
    ("工信部首页", "https://www.miit.gov.cn/"),
    ("工信部数据", "https://www.miit.gov.cn/gxsj/index.html"),
    ("国家统计局首页", "https://www.stats.gov.cn/"),
    ("国家统计局最新发布", "https://www.stats.gov.cn/sj/zxfb/"),
    ("中电联 CEC", "https://www.cec.org.cn/"),
    ("北极星光伏网数据", "https://guangfu.bjx.com.cn/sj/"),
    ("北极星风电网数据", "https://feng.bjx.com.cn/sj/"),
    ("北极星氢能网数据", "https://h2.bjx.com.cn/sj/"),
]

if batch == 1:
    sites = all_sites[:5]
elif batch == 2:
    sites = all_sites[5:10]
elif batch == 3:
    sites = all_sites[10:]
else:
    sites = all_sites

results = []
for name, url in sites:
    print(f"检测中: {name}...", file=sys.stderr)
    r = safe_check(name, url)
    results.append(r)
    time.sleep(1)

print(json.dumps(results, ensure_ascii=False, indent=2))
