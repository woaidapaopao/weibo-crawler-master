#!/data/data/com.termux/files/usr/bin/bash
# Termux 一键部署：让爬虫脱离 DSH 独立运行
# 用法：把本文件放到 Termux 里执行  bash termux-setup.sh
set -e

REPO="https://github.com/woaidapaopao/weibo-crawler-master.git"
DIR="$HOME/weibo-crawler"
SHARED="$HOME/storage/shared"
OUT="$SHARED/Download/DSH-Go/weibo"

echo "==> 1/6 安装依赖（python/git/cronie）"
pkg update -y
pkg install -y python git cronie

echo "==> 2/6 申请手机存储访问权限（会弹窗，请允许）"
termux-setup-storage || true

echo "==> 3/6 拉取代码"
if [ -d "$DIR/.git" ]; then
  cd "$DIR" && git pull --ff-only || true
else
  git clone "$REPO" "$DIR"
fi
cd "$DIR"

echo "==> 4/6 创建虚拟环境并装依赖"
python -m venv .venv
.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple lxml requests tqdm schedule

echo "==> 5/6 把结果目录指到手机存储，方便网盘扫描上传"
mkdir -p "$OUT"
rm -rf "$DIR/weibo"
ln -s "$OUT" "$DIR/weibo"

echo "==> 6/6 配置定时任务（每天 03:00）"
cat > "$DIR/run_termux.sh" <<'EOS'
#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")" || exit 1
termux-wake-lock
.venv/bin/python weibo.py >> "$HOME/crawl.log" 2>&1
termux-wake-unlock
EOS
chmod +x "$DIR/run_termux.sh"

( crontab -l 2>/dev/null | grep -v run_termux.sh ; \
  echo "0 3 * * * $DIR/run_termux.sh" ) | crontab -

pkill crond 2>/dev/null || true
crond
termux-wake-lock

cat <<EOF

========================================
部署完成，还差两步（都是手工的）：

1) 写 cookie（从 m.weibo.cn 的请求头复制）：
   echo 'SUB=...; SUBP=...' > $DIR/cookie.txt

2) 写要抓的账号，每行 "id 昵称"：
   nano $DIR/user_id_list.txt

然后手工试跑一次：
   cd $DIR && ./run.sh

定时任务已加：每天 03:00 自动跑，日志在 ~/crawl.log
注意：Termux 需关闭电池优化，否则后台可能被系统杀掉。
========================================
EOF
