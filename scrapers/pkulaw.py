"""
北大法宝新能源政策爬虫。
使用 Playwright 实现 IP 自动认证和 JS 渲染。
支持模式：backfill（按月回溯）和 daily（每日增量）。

核心机制：
- 北大法宝 URL 中的 publishfrom/publishto 参数无效
- 日期筛选需要通过左侧边栏的年份树（IssueDate）点击实现
- 分页通过 AJAX POST 表单提交，字段为 Pager.PageIndex（0-based）
- 最终在 Python 端按月份过滤
"""

import re
import math
import traceback
from datetime import datetime, timedelta, date
from urllib.parse import urlencode, quote

from playwright.sync_api import sync_playwright

from scrapers.base import BaseScraper
from scrapers.config import (
    PKULAW_BASE_URL,
    SEARCH_KEYWORDS,
    KEYWORD_INDUSTRY_MAP,
    LAW_CATEGORIES,
    BROWSER_HEADLESS,
    BROWSER_SLOW_MO,
    PAGE_SIZE,
    TITLE_BLACKLIST,
    ISSUER_BLACKLIST,
)

# 每次搜索最多抓取的页数上限（防止意外死循环）
MAX_PAGES = 100
# 页面加载失败时的最大重试次数
MAX_RETRIES = 3


class PKULawScraper(BaseScraper):

    def __init__(self):
        super().__init__("北大法宝")
        self.browser = None
        self.context = None
        self.page = None
        self._pw = None

    # ========== 浏览器生命周期 ==========

    def start_browser(self):
        """启动 Playwright 浏览器。"""
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=BROWSER_HEADLESS,
            slow_mo=BROWSER_SLOW_MO,
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        self.page = self.context.new_page()
        print("[北大法宝] 浏览器已启动")

    def close_browser(self):
        """关闭浏览器。"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self._pw:
            self._pw.stop()
        print("[北大法宝] 浏览器已关闭")

    # ========== 登录认证 ==========

    def login(self):
        """通过 IP 自动认证登录北大法宝。"""
        print("[北大法宝] 正在登录（IP 自动认证）...")
        self.page.goto(PKULAW_BASE_URL, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(5000)

        if "cas.pkulaw.com" in self.page.url:
            print("[北大法宝] 检测到 CAS 认证页面，等待跳转...")
            try:
                self.page.wait_for_url(f"{PKULAW_BASE_URL}/**", timeout=15000)
            except Exception:
                print("[北大法宝] 自动认证超时，请确认 VPN 已连接")
                print(f"[北大法宝] 当前页面：{self.page.url}")
                print("[北大法宝] 请在浏览器中手动完成登录，然后回到终端按回车...")
                input()

        print(f"[北大法宝] 登录成功：{self.page.url}")

    # ========== 搜索辅助方法 ==========

    def _build_search_url(self, keyword, category_code):
        """构建搜索 URL（不含日期参数，日期通过左侧筛选）。"""
        base = f"{PKULAW_BASE_URL}/law/{category_code}"
        params = {"keywords": keyword, "match": "Exact"}
        return f"{base}?{urlencode(params, quote_via=quote)}"

    def _goto_with_retry(self, url, retries=MAX_RETRIES):
        """访问页面，失败时自动重试。"""
        for attempt in range(1, retries + 1):
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(3000)
                return True
            except Exception as e:
                if attempt < retries:
                    wait = attempt * 5
                    print(f"[北大法宝] 页面加载失败（第 {attempt}/{retries} 次），"
                          f"{wait} 秒后重试...")
                    self.page.wait_for_timeout(wait * 1000)
                else:
                    print(f"[北大法宝] 页面加载失败，已重试 {retries} 次，跳过")
                    return False

    def _wait_for_results(self):
        """等待搜索结果加载完成。"""
        try:
            self.page.wait_for_selector(".accompanying-wrap", timeout=20000)
            self.page.wait_for_timeout(4000)
        except Exception:
            self.page.wait_for_timeout(5000)

    def _get_total_count(self):
        """获取搜索结果总数。"""
        try:
            el = self.page.query_selector(".filtrater-box .total strong")
            if el:
                return int(el.inner_text().strip())
        except Exception:
            pass
        return 0

    def _expand_all_groups(self):
        """点击所有"更多"按钮，展开分组结果。"""
        max_clicks = 50
        clicked = 0
        while clicked < max_clicks:
            more_btns = self.page.query_selector_all(".accompanying-wrap + .more a")
            visible = [b for b in more_btns if b.is_visible()]
            if not visible:
                break
            for btn in visible:
                try:
                    btn.click()
                    self.page.wait_for_timeout(1500)
                    clicked += 1
                except Exception:
                    pass
            self.random_delay()
        if clicked:
            print(f"[北大法宝] 展开了 {clicked} 个分组")

    def _click_year_filter(self, year):
        """
        点击左侧边栏的年份筛选。
        年份树节点格式：<a cluster_code="2026" ...>2026 (6)</a>
        在 ul[portid="IssueDateport"] 下。
        """
        # 等待左侧边栏年份树加载
        try:
            self.page.wait_for_selector('ul[portid="IssueDateport"] a[cluster_code]', timeout=15000)
        except Exception:
            pass

        selector = f'ul[portid="IssueDateport"] a[cluster_code="{year}"]'
        el = self.page.query_selector(selector)
        if not el:
            print(f"[北大法宝] 左侧边栏未找到 {year} 年，可能该年没有结果")
            return False

        # 读取该年份的结果数
        span = el.query_selector("span.node_name")
        year_info = span.inner_text() if span else str(year)
        print(f"[北大法宝] 点击年份筛选：{year_info}")

        el.click()
        # 等待 AJAX 请求完成，页面内容刷新
        self.page.wait_for_timeout(3000)
        self._wait_for_results()
        return True

    def _submit_form_page(self, page_index):
        """
        通过 AJAX POST 表单跳转到指定页（0-based）。
        北大法宝的搜索表单 id="main_form"，分页字段为 Pager.PageIndex。
        """
        self.page.evaluate(f'''() => {{
            var form = document.getElementById('main_form');
            if (!form) return;
            var pi = form.querySelector('input[name="Pager.PageIndex"]');
            if (pi) pi.value = '{page_index}';
            $(form).submit();
        }}''')
        self.page.wait_for_timeout(3000)
        self._wait_for_results()

    # ========== 核心搜索逻辑 ==========

    def search_and_parse(self, keyword, category_code, category_name,
                         target_year, target_month_prefix=None):
        """
        执行搜索 + 年份筛选 + 分页 + 解析。

        参数：
            keyword: 搜索关键词
            category_code: 法规库代码（chl/lar）
            category_name: 法规库名称（中央法规/地方法规）
            target_year: 目标年份，如 "2026"
            target_month_prefix: 目标月份前缀，如 "2026-03"，用于最后过滤
        """
        print(f"\n[北大法宝] 搜索：关键词='{keyword}'，分类='{category_name}'，"
              f"年份={target_year}")

        url = self._build_search_url(keyword, category_code)
        print(f"[北大法宝] 地址：{url}")

        if not self._goto_with_retry(url):
            return []

        self._wait_for_results()

        # 点击左侧年份筛选，缩小范围到目标年份
        if not self._click_year_filter(target_year):
            return []

        total = self._get_total_count()
        print(f"[北大法宝] {target_year} 年结果总数：{total}")

        if total == 0:
            return []

        total_pages = min(math.ceil(total / PAGE_SIZE), MAX_PAGES)
        all_records = []

        # 第一页（年份筛选后已经加载）
        self._expand_all_groups()
        records = self._parse_current_page(keyword, category_name)
        all_records.extend(records)
        print(f"[北大法宝] 第 1/{total_pages} 页：解析到 {len(records)} 条")

        # 后续页面：通过表单提交翻页
        for page_idx in range(1, total_pages):
            self._submit_form_page(page_idx)
            self._expand_all_groups()
            records = self._parse_current_page(keyword, category_name)
            all_records.extend(records)
            print(f"[北大法宝] 第 {page_idx + 1}/{total_pages} 页：解析到 {len(records)} 条")

            if not records:
                print("[北大法宝] 当前页无结果，停止翻页")
                break

            self.random_delay()

        # 按月份过滤（只保留日期明确在目标月份的记录）
        if target_month_prefix:
            before_count = len(all_records)
            all_records = [r for r in all_records
                           if r.get("pub_date", "").startswith(target_month_prefix)]
            skipped = before_count - len(all_records)
            if skipped:
                print(f"[北大法宝] 月份过滤：保留 {len(all_records)} 条，"
                      f"跳过非 {target_month_prefix} 的 {skipped} 条")

        # 过滤非产业政策
        before_filter = len(all_records)
        all_records = [r for r in all_records if self._is_policy(r)]
        filtered = before_filter - len(all_records)
        if filtered:
            print(f"[北大法宝] 内容过滤：去除 {filtered} 条非产业政策")

        print(f"[北大法宝] 本次搜索完成：最终 {len(all_records)} 条")
        return all_records

    # ========== 内容过滤 ==========

    @staticmethod
    def _is_policy(record):
        """判断一条记录是否属于产业政策（过滤掉证券公告、个人备案、行政批复等）。"""
        title = record.get("title", "")
        issuer = record.get("issuing_body", "")

        # 发布机关黑名单
        for blacklisted in ISSUER_BLACKLIST:
            if blacklisted in issuer:
                return False

        # 标题关键词黑名单
        for blacklisted in TITLE_BLACKLIST:
            if blacklisted in title:
                return False

        return True

    # ========== 页面解析 ==========

    def _parse_current_page(self, keyword, category_name):
        """解析当前页面上的所有结果条目。"""
        records = []
        items = self.page.query_selector_all(".accompanying-wrap > .item")

        if not items:
            html = self.page.content()
            debug_file = self.data_dir / "debug_page.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[北大法宝] 未找到结果条目，已保存调试 HTML 到 {debug_file}")
            return records

        for item in items:
            try:
                record = self._extract_record(item, keyword, category_name)
                if record:
                    records.append(record)
            except Exception as e:
                print(f"[北大法宝] 解析条目出错：{e}")
        return records

    def _extract_record(self, item, keyword, category_name):
        """
        从单个 .item 元素中提取元数据。

        HTML 结构：
        <div class="item">
          <div class="col">
            <div class="t">
              <h4><a href="/chl/xxx.html?keyword=...">标题</a></h4>
            </div>
            <div class="info">
              <a>效力状态</a> | <a>效力位阶</a> | <a>发布机关</a>...
              <span class="text">文号</span>
              <span class="text">YYYY.MM.DD公布</span>
              <span class="text">YYYY.MM.DD施行</span>
            </div>
          </div>
        </div>
        """
        title_el = item.query_selector(".t h4 a[href]")
        if not title_el:
            return None

        title = (title_el.inner_text() or "").strip()
        href = title_el.get_attribute("href") or ""

        # 清理 URL
        if href and "?" in href:
            href = href.split("?")[0]
        if href and not href.startswith("http"):
            href = PKULAW_BASE_URL + href

        if not title or not href:
            return None

        # 从 .info 区块解析元数据
        info_el = item.query_selector(".col > .info")
        effectiveness = ""
        issuing_body = ""
        doc_number = ""
        pub_date = ""
        impl_date = ""

        if info_el:
            info_links = info_el.query_selector_all("a:not(.subscription)")
            link_texts = []
            for link in info_links:
                t = (link.inner_text() or "").strip()
                if t:
                    link_texts.append(t)

            if len(link_texts) >= 1:
                effectiveness = link_texts[0]
            if len(link_texts) >= 3:
                issuing_body = link_texts[2]

            text_spans = info_el.query_selector_all("span.text")
            for span in text_spans:
                t = (span.inner_text() or "").strip()
                if not t:
                    continue
                pub_m = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*(?:公布|发布)", t)
                if pub_m:
                    pub_date = pub_m.group(1).replace(".", "-")
                    continue
                impl_m = re.search(r"(\d{4}\.\d{2}\.\d{2})\s*施行", t)
                if impl_m:
                    impl_date = impl_m.group(1).replace(".", "-")
                    continue
                if not doc_number:
                    doc_number = t

        return self.make_record(
            title=title,
            doc_number=doc_number,
            issuing_body=issuing_body,
            pub_date=pub_date,
            impl_date=impl_date,
            effectiveness=effectiveness,
            category=category_name,
            sub_industry=KEYWORD_INDUSTRY_MAP.get(keyword, "综合/其他"),
            search_keyword=keyword,
            url=href,
        )

    # ========== 运行模式 ==========

    def run_backfill(self, year_month):
        """回溯模式：爬取指定月份的全部数据。"""
        year, month = year_month.split("-")

        print(f"\n{'=' * 60}")
        print(f"[北大法宝] 回溯模式：{year_month}")
        print(f"{'=' * 60}")

        all_records = []
        for keyword in SEARCH_KEYWORDS:
            for code, name in LAW_CATEGORIES.items():
                records = self.search_and_parse(
                    keyword=keyword,
                    category_code=code,
                    category_name=name,
                    target_year=year,
                    target_month_prefix=year_month,
                )
                all_records.extend(records)
                self.random_delay()

        added = self.merge_and_save(year_month, all_records)
        print(f"\n[北大法宝] 回溯完成：{year_month}，新增 {added} 条")

    def run_daily(self):
        """每日模式：爬取昨天发布的新政策。"""
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        target_year = yesterday.strftime("%Y")
        year_month = yesterday.strftime("%Y-%m")

        print(f"\n{'=' * 60}")
        print(f"[北大法宝] 每日模式：{target_date}")
        print(f"{'=' * 60}")

        all_records = []
        for keyword in SEARCH_KEYWORDS:
            for code, name in LAW_CATEGORIES.items():
                records = self.search_and_parse(
                    keyword=keyword,
                    category_code=code,
                    category_name=name,
                    target_year=target_year,
                    target_month_prefix=year_month,
                )
                # 每日模式：进一步过滤到具体日期
                records = [r for r in records if r.get("pub_date") == target_date]
                all_records.extend(records)
                self.random_delay()

        added = self.merge_and_save(year_month, all_records)
        print(f"\n[北大法宝] 每日爬取完成：{target_date}，新增 {added} 条")

    def run(self, mode="daily", year_month=""):
        """主入口。"""
        try:
            self.start_browser()
            self.login()
            if mode == "backfill":
                if not year_month:
                    raise ValueError("回溯模式需要指定月份，如 '2026-03'")
                self.run_backfill(year_month)
            elif mode == "daily":
                self.run_daily()
            else:
                raise ValueError(f"未知模式：{mode}")
        except Exception as e:
            print(f"[北大法宝] 出错：{e}")
            traceback.print_exc()
        finally:
            self.close_browser()
