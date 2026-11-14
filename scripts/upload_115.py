#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把抓取到的媒体上传到 115 网盘（Open API，无需跑 OpenList）。

依赖环境变量（都从 GitHub Secrets 注入）：
  P115_ACCESS_TOKEN   115 开放平台的 access_token
  P115_REFRESH_TOKEN  115 开放平台的 refresh_token（会被轮换，脚本负责回写）
  P115_APP_ID         开放应用的 AppID（OpenList 115 驱动里填的 client_id）
  P115_TARGET_CID     目标目录 id，根目录是 0
  P115_REMOTE_DIR     目标目录下的子目录名，默认 weibo
  SRC_DIR             本地要上传的目录，默认 weibo

可选（用于把轮换后的 refresh_token 写回 Secret，避免下次失效）：
  GH_TOKEN_FOR_SECRET  有 repo 权限的 PAT
  GH_REPO              owner/repo，默认 woaidapaopao/weibo-crawler-master
"""

import base64
import hashlib
import os
import sys
import time
from pathlib import Path

from p115client import P115OpenClient


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


ACCESS_TOKEN = env("P115_ACCESS_TOKEN")
REFRESH_TOKEN = env("P115_REFRESH_TOKEN")
APP_ID = int(env("P115_APP_ID", "0") or 0)
TARGET_CID = env("P115_TARGET_CID", "0")
REMOTE_DIR = env("P115_REMOTE_DIR", "weibo")
SRC_DIR = Path(env("SRC_DIR", "weibo"))
GH_TOKEN = env("GH_TOKEN_FOR_SECRET")
GH_REPO = env("GH_REPO", "woaidapaopao/weibo-crawler-master")

MEDIA_DIRS = ("img", "video", "live_photo")
RETRY = 3


def log(msg: str) -> None:
    print(msg, flush=True)


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_refresh_token(token: str) -> None:
    """把轮换后的 refresh_token 写回 GitHub Secret；没配 PAT 就只提示。"""
    if not token:
        return
    if not GH_TOKEN:
        log("提示：未配置 GH_TOKEN_FOR_SECRET，refresh_token 未回写，下次可能失效")
        return

    import requests
    from nacl import encoding, public

    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    base = f"https://api.github.com/repos/{GH_REPO}"
    key = requests.get(f"{base}/actions/secrets/public-key", headers=headers, timeout=30).json()
    sealed = public.SealedBox(
        public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
    ).encrypt(token.encode())
    resp = requests.put(
        f"{base}/actions/secrets/P115_REFRESH_TOKEN",
        headers=headers,
        json={
            "encrypted_value": base64.b64encode(sealed).decode(),
            "key_id": key["key_id"],
        },
        timeout=30,
    )
    log(f"refresh_token 回写 Secret: {resp.status_code}")


def list_children(client: P115OpenClient, cid: str) -> dict:
    """列出目录下的子项，返回 {名称: id}。"""
    result = {}
    offset = 0
    while True:
        resp = client.fs_files_open({"cid": cid, "limit": 200, "offset": offset, "show_dir": 1})
        data = resp.get("data") or []
        for item in data:
            if item.get("fc") == 0:  # 目录
                result[item.get("fn")] = str(item.get("fid"))
        if len(data) < 200:
            break
        offset += 200
    return result


def ensure_dir(client: P115OpenClient, parent: str, name: str) -> str:
    children = list_children(client, parent)
    if name in children:
        return children[name]
    resp = client.fs_mkdir_open({"file_name": name, "pid": parent})
    data = resp.get("data") or {}
    cid = data.get("cid") or data.get("fid") or data.get("file_id")
    if not cid:
        raise RuntimeError(f"创建目录失败: {name} -> {resp}")
    log(f"  建目录 {name} (cid={cid})")
    return str(cid)


def upload_file(client: P115OpenClient, path: Path, pid: str) -> bool:
    for attempt in range(1, RETRY + 1):
        try:
            resp = client.upload_file_open(
                file=str(path),
                pid=pid,
                filename=path.name,
                filesha1=sha1_of(path),
                filesize=path.stat().st_size,
            )
            state = resp.get("state")
            if state:
                log(f"  ✓ {path.relative_to(SRC_DIR)} ({path.stat().st_size // 1024} KB)")
                return True
            log(f"  ! {path.name} 返回异常: {resp}")
        except Exception as exc:  # noqa: BLE001
            log(f"  ! {path.name} 第{attempt}次失败: {exc}")
        time.sleep(2 * attempt)
    return False


def main() -> int:
    if not SRC_DIR.is_dir():
        log(f"源目录不存在: {SRC_DIR}")
        return 1
    if not REFRESH_TOKEN:
        log("缺少 P115_REFRESH_TOKEN")
        return 1

    client = P115OpenClient(
        access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, app_id=APP_ID
    )
    try:
        resp = client.refresh_access_token()
        data = resp.get("data") or {}
        new_refresh = data.get("refresh_token") or getattr(client, "refresh_token", "")
        log(f"token 刷新: {'成功' if resp.get('state') else resp}")
        save_refresh_token(new_refresh)
    except Exception as exc:  # noqa: BLE001
        log(f"token 刷新失败，继续尝试直连: {exc}")

    root = ensure_dir(client, TARGET_CID, REMOTE_DIR)
    total = ok = 0
    for account_dir in sorted(p for p in SRC_DIR.iterdir() if p.is_dir()):
        has_media = any((account_dir / d).exists() for d in MEDIA_DIRS)
        if not has_media:
            continue
        log(f"账号 {account_dir.name}")
        acc_cid = ensure_dir(client, root, account_dir.name)
        for media in MEDIA_DIRS:
            media_dir = account_dir / media
            if not media_dir.is_dir():
                continue
            for sub in sorted(p for p in media_dir.iterdir() if p.is_dir()):
                sub_cid = ensure_dir(client, acc_cid, f"{media}/{sub.name}".replace("/", "_"))
                for f in sorted(sub.iterdir()):
                    if not f.is_file() or f.name == "not_downloaded.txt":
                        continue
                    total += 1
                    if upload_file(client, f, sub_cid):
                        ok += 1

    log(f"上传完成：成功 {ok}/{total}")
    return 0 if total and ok == total else (0 if total == 0 else 2)


if __name__ == "__main__":
    sys.exit(main())
