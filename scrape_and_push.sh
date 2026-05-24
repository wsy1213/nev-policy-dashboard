#!/bin/bash
# 爬取完数据后自动同步 + 推送到 GitHub（每日定时用）
# 用法: bash scrape_and_push.sh [--backfill YYYY-MM | --daily]
#
# macOS 开机启动配置见: ~/Library/LaunchAgents/com.nev.scraper.plist

# 开机后等待 5 分钟，确保网络稳定后再执行
sleep 300

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 运行爬虫（传递所有参数）
python run.py "$@"

# 同步数据到前端
bash sync_data.sh

# 提交并推送
git add data/ frontend/public/data/
git commit -m "data: $(date +%Y-%m-%d) 自动更新政策数据" || echo "无新数据需要提交"
git push origin main || echo "推送失败，请检查网络"
