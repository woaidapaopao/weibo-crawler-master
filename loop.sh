#!/bin/sh
# 定时循环：./loop.sh 60  （每 60 分钟跑一次）
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -u __main__.py "${1:-60}"
