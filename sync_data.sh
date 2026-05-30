#!/bin/bash
# 同步爬虫数据到前端 public 目录（本地开发用）
# 用法: bash sync_data.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$PROJECT_DIR/data"
PUBLIC_DATA="$PROJECT_DIR/frontend/public/data"

mkdir -p "$PUBLIC_DATA"
mkdir -p "$PUBLIC_DATA/industry"
mkdir -p "$PUBLIC_DATA/international"
mkdir -p "$PUBLIC_DATA/media"

# 清理旧数据（保留目录结构）
find "$PUBLIC_DATA" -maxdepth 1 -name '*.json' ! -name 'manifest.json' -delete
find "$PUBLIC_DATA/industry" -maxdepth 1 -name '*.json' ! -name 'manifest.json' -delete
find "$PUBLIC_DATA/international" -maxdepth 1 -name '*.json' ! -name 'manifest.json' -delete
find "$PUBLIC_DATA/media" -maxdepth 1 -name '*.json' ! -name 'manifest.json' -delete

# 复制政策数据
if ls "$DATA_DIR"/*.json 1>/dev/null 2>&1; then
    cp "$DATA_DIR"/*.json "$PUBLIC_DATA/"
    echo "已复制政策数据到 $PUBLIC_DATA"
else
    echo "data/ 目录下无政策 JSON 文件"
fi

# 复制行业数据
if ls "$DATA_DIR/industry"/*.json 1>/dev/null 2>&1; then
    cp "$DATA_DIR/industry"/*.json "$PUBLIC_DATA/industry/"
    echo "已复制行业数据到 $PUBLIC_DATA/industry"
else
    echo "data/industry/ 目录下无行业 JSON 文件"
fi

# 复制国际动态数据
if ls "$DATA_DIR/international"/*.json 1>/dev/null 2>&1; then
    cp "$DATA_DIR/international"/*.json "$PUBLIC_DATA/international/"
    echo "已复制国际动态数据到 $PUBLIC_DATA/international"
else
    echo "data/international/ 目录下无国际 JSON 文件"
fi

# 生成政策 manifest.json
cd "$PUBLIC_DATA"
files=()
for f in *.json; do
    if [ "$f" != "manifest.json" ] && [ "$f" != "demo.json" ] && [ "$f" != "brief.json" ] && [ "$f" != "weekly_report.json" ]; then
        files+=("\"$f\"")
    fi
done

IFS=','
echo "{\"files\":[${files[*]}],\"last_updated\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\"}" > manifest.json
echo "政策 manifest.json 已更新: ${files[*]}"

# 生成行业 manifest.json
cd "$PUBLIC_DATA/industry"
ind_files=()
for f in *.json; do
    if [ "$f" != "manifest.json" ]; then
        ind_files+=("\"$f\"")
    fi
done

IFS=','
echo "{\"files\":[${ind_files[*]}],\"last_updated\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\"}" > manifest.json
echo "行业 manifest.json 已更新: ${ind_files[*]}"

# 生成国际动态 manifest.json
cd "$PUBLIC_DATA/international"
intl_files=()
for f in *.json; do
    if [ "$f" != "manifest.json" ]; then
        intl_files+=("\"$f\"")
    fi
done

IFS=','
echo "{\"files\":[${intl_files[*]}],\"last_updated\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\"}" > manifest.json
echo "国际动态 manifest.json 已更新: ${intl_files[*]}"

# 复制媒体报道数据
if ls "$DATA_DIR/media"/*.json 1>/dev/null 2>&1; then
    cp "$DATA_DIR/media"/*.json "$PUBLIC_DATA/media/"
    echo "已复制媒体报道数据到 $PUBLIC_DATA/media"
else
    echo "data/media/ 目录下无媒体 JSON 文件"
fi

# 生成媒体报道 manifest.json
cd "$PUBLIC_DATA/media"
media_files=()
for f in *.json; do
    if [ "$f" != "manifest.json" ]; then
        media_files+=("\"$f\"")
    fi
done

IFS=','
echo "{\"files\":[${media_files[*]}],\"last_updated\":\"$(date -u +%Y-%m-%dT%H:%M:%S)\"}" > manifest.json
echo "媒体报道 manifest.json 已更新: ${media_files[*]}"
