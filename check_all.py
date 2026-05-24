#!/usr/bin/env python3
"""Check sites using subprocess with hard timeout"""
import subprocess
import sys
import json

sites = [
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

for name, url in sites:
    print(f"\n检测: {name}", file=sys.stderr, flush=True)
    try:
        proc = subprocess.run(
            [sys.executable, "check_one.py", name, url],
            capture_output=True, text=True, timeout=20
        )
        if proc.stdout.strip():
            try:
                r = json.loads(proc.stdout.strip())
                print(f"\n### {r['name']} ({r['url']})")
                if "error" in r:
                    print(f"  ERROR: {r['error']}")
                    continue
                print(f"  状态码={r['status']} 长度={r['length']}")
                print(f"  标题: {r.get('title','?')}")
                print(f"  Script数={r['script_count']} Body文本={r['body_text_len']}字符")
                print(f"  JS渲染={r['js_rendered']} {r.get('js_container','')}")
                print(f"  链接数={r['link_count']} <li>数={r['li_count']}")
                print(f"  日期数={r['date_count']} 示例={r.get('sample_dates',[])}")
                if r.get('redirect'):
                    print(f"  重定向: {r['redirect']}")
                if r.get('articles'):
                    print(f"  文章示例:")
                    for a in r['articles']:
                        print(f"    [{a['d']}] {a['t']} -> {a['h']}")
                print(f"  HTML片段: {r.get('html_snippet','')[:250]}")
            except json.JSONDecodeError:
                print(f"  RAW: {proc.stdout[:200]}")
        else:
            print(f"  无输出. stderr: {proc.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"\n### {name} ({url})")
        print(f"  ERROR: 子进程超时20s，网站不可达")
