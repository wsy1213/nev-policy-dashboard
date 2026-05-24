#!/usr/bin/env python3
"""
新能源汽车行业政策+行业数据爬虫 CLI 入口。

用法:
    # 回溯爬取政策数据
    python run.py --backfill 2026-03

    # 每日增量爬取政策
    python run.py --daily

    # 回溯爬取行业数据
    python run.py --industry --backfill 2026-03

    # 每日增量爬取行业数据
    python run.py --industry --daily

    # 回溯爬取国际动态
    python run.py --international --backfill 2026-03

    # 同时爬取政策+行业+国际
    python run.py --all --backfill 2026-03
"""

import argparse
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_policy(mode, months):
    """运行政策爬虫（北大法宝）。"""
    from scrapers.pkulaw import PKULawScraper
    scraper = PKULawScraper()
    if mode == "backfill":
        for ym in months:
            scraper.run(mode="backfill", year_month=ym)
    else:
        scraper.run(mode="daily")


def run_industry(mode, months):
    """运行行业新闻爬虫（工信部+乘联会+百人会+第一电动+盖世汽车）。"""
    from scrapers.miit_data import MIITScraper
    from scrapers.cpca_news import CPCAScraper
    from scrapers.chinaev100_news import ChinaEV100Scraper
    from scrapers.d1ev_news import D1evScraper
    from scrapers.gasgoo_nev import GasgooScraper

    scrapers = [
        MIITScraper(), CPCAScraper(), ChinaEV100Scraper(),
        D1evScraper(), GasgooScraper(),
    ]
    for scraper in scrapers:
        if mode == "backfill":
            for ym in months:
                scraper.run(mode="backfill", year_month=ym)
        else:
            scraper.run(mode="daily")


def run_international(mode, months):
    """运行国际数据爬虫（EIA+IRENA+IEA+CleanTechnica+InsideEVs+ACEA）。"""
    from scrapers.eia_data import EIAScraper
    from scrapers.irena_data import IRENAScraper
    from scrapers.iea_data import IEAScraper
    from scrapers.cleantechnica_data import CleanTechnicaScraper
    from scrapers.insideevs_data import InsideEVsScraper
    from scrapers.acea_data import ACEAScraper

    scrapers = [
        EIAScraper(), IRENAScraper(), IEAScraper(),
        CleanTechnicaScraper(), InsideEVsScraper(), ACEAScraper(),
    ]
    for scraper in scrapers:
        if mode == "backfill":
            for ym in months:
                scraper.run(mode="backfill", year_month=ym)
        else:
            scraper.run(mode="daily")


def run_media(mode, months):
    """运行媒体报道爬虫（澎湃+中新网+第一财经+界面+新华网+中国能源报+汽车之家）。"""
    from scrapers.thepaper_energy import ThepaperScraper
    from scrapers.chinanews_energy import ChinanewsScraper
    from scrapers.yicai_energy import YicaiScraper
    from scrapers.jiemian_energy import JiemianScraper
    from scrapers.xinhua_energy import XinhuaScraper
    from scrapers.cnenergy_news import CnenergyScraper
    from scrapers.autohome_nev import AutohomeScraper

    scrapers = [
        ThepaperScraper(), ChinanewsScraper(), YicaiScraper(),
        JiemianScraper(), XinhuaScraper(), CnenergyScraper(),
        AutohomeScraper(),
    ]
    for scraper in scrapers:
        if mode == "backfill":
            for ym in months:
                scraper.run(mode="backfill", year_month=ym)
        else:
            scraper.run(mode="daily")


def main():
    parser = argparse.ArgumentParser(
        description="新能源汽车行业政策+行业数据爬虫"
    )
    parser.add_argument(
        "--backfill",
        action="append",
        metavar="YYYY-MM",
        help="回溯爬取指定月份的数据（可指定多个月份）",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="增量模式：爬取最新数据",
    )
    parser.add_argument(
        "--industry",
        action="store_true",
        help="爬取行业数据（能源局+乘联会）",
    )
    parser.add_argument(
        "--policy",
        action="store_true",
        help="爬取政策数据（北大法宝）",
    )
    parser.add_argument(
        "--international",
        action="store_true",
        help="爬取国际动态（EIA+IRENA+IEA）",
    )
    parser.add_argument(
        "--media",
        action="store_true",
        help="爬取媒体报道（澎湃+中新网+第一财经+界面+新华网+中国能源报）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="同时爬取政策+行业+国际+媒体数据",
    )

    args = parser.parse_args()

    if not args.backfill and not args.daily:
        parser.print_help()
        sys.exit(1)

    # 校验月份格式
    if args.backfill:
        for ym in args.backfill:
            if len(ym) != 7 or ym[4] != "-":
                print(f"错误: 月份格式应为 YYYY-MM，收到: {ym}")
                sys.exit(1)

    mode = "backfill" if args.backfill else "daily"
    months = args.backfill or []

    # 默认行为：如果没指定任何类型，按旧逻辑只跑政策
    has_specific = args.policy or args.industry or args.international or args.media or args.all
    run_p = args.policy or args.all or (not has_specific)
    run_i = args.industry or args.all
    run_intl = args.international or args.all
    run_m = args.media or args.all

    if run_p:
        run_policy(mode, months)

    if run_i:
        run_industry(mode, months)

    if run_intl:
        run_international(mode, months)

    if run_m:
        run_media(mode, months)


if __name__ == "__main__":
    main()
