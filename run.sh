#!/bin/sh
# 单次爬取：./run.sh
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -u weibo.py "$@"
