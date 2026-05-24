import requests
from bs4 import BeautifulSoup
import time
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

sites = [
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

for name, url in sites:
    print(f"\n{'='*70}")
    print(f"[{name}] {url}")
    print('='*70)
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True, verify=True)
        enc = resp.apparent_encoding or 'utf-8'
        resp.encoding = enc
        text = resp.text
        print(f"状态码: {resp.status_code}")
        print(f"编码: {enc}")
        print(f"响应长度: {len(text)} 字符")
        print(f"Content-Type: {resp.headers.get('Content-Type','N/A')}")
        if resp.url != url:
            print(f"重定向到: {resp.url}")
        
        soup = BeautifulSoup(text, 'html.parser')
        title_tag = soup.title
        title = title_tag.string.strip() if title_tag and title_tag.string else "无title"
        print(f"页面标题: {title}")
        
        scripts = soup.find_all('script')
        body = soup.find('body')
        body_text = body.get_text(strip=True) if body else ""
        print(f"Script标签数: {len(scripts)}")
        print(f"Body文本长度: {len(body_text)} 字符")
        
        # JS框架检测
        vue_app = soup.find(id='app') or soup.find(id='__nuxt') or soup.find(id='root') or soup.find(id='__next')
        if vue_app:
            children = len(list(vue_app.children))
            print(f"JS框架容器: id='{vue_app.get('id')}', 子元素数={children}")
            if children <= 3 and len(vue_app.get_text(strip=True)) < 50:
                print("  -> 可能是纯JS渲染(容器内容为空)")
        
        if body_text and len(body_text) < 100:
            print("Body文本很少，可能是JS渲染页面")
        
        links = soup.find_all('a', href=True)
        print(f"链接总数: {len(links)}")
        
        date_pattern = re.compile(r'20\d{2}[-./年]\d{1,2}[-./月]?\d{0,2}')
        dates_found = date_pattern.findall(text)
        print(f"日期模式匹配数: {len(dates_found)}")
        if dates_found[:5]:
            print(f"示例日期: {dates_found[:5]}")
        
        # 看看有没有典型的列表结构
        lis = soup.find_all('li')
        print(f"<li>标签数: {len(lis)}")
        
        # 输出HTML片段
        print(f"\n--- HTML前1200字符 ---")
        print(text[:1200])
        print(f"\n--- Body前800字符 ---")
        if body:
            print(str(body)[:800])
        
    except requests.exceptions.SSLError as e:
        print(f"SSL错误: {str(e)[:300]}")
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {str(e)[:300]}")
    except requests.exceptions.Timeout:
        print(f"超时(15s)")
    except Exception as e:
        print(f"错误: {type(e).__name__}: {str(e)[:300]}")
    
    time.sleep(1.5)

print("\n\n===== 全部检测完成 =====")
