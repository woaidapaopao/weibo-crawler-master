# 媒体直传 115 网盘

Actions 只备份文本（csv/json），媒体文件太大（60 天约 1GB），免费额度放不下，
所以勾选 `media=yes` 时，workflow 会直接把图片/视频通过 115 开放接口上传到你的网盘。

## 需要配置的 Secrets

在仓库 **Settings → Secrets and variables → Actions** 里添加：

| 名称 | 说明 |
|---|---|
| `P115_ACCESS_TOKEN` | 115 开放平台的 access_token |
| `P115_REFRESH_TOKEN` | 115 开放平台的 refresh_token（脚本会自动轮换并回写） |
| `P115_APP_ID` | 开放应用的 AppID（OpenList 115 配置里叫 `client_id` 的那个数字） |
| `P115_TARGET_CID` | 上传的目标目录 id，根目录填 `0` |
| `P115_REMOTE_DIR` | 可选，目标目录下的子目录名，默认 `weibo` |
| `GH_TOKEN_FOR_SECRET` | 可选，有仓库 Secrets 写权限的 PAT，用来回写轮换后的 refresh_token |

这些值在 OpenList 的 `data/config.json` 里对应 `drivers` 中 115 的
`access_token` / `refresh_token` / `client_id` 字段。

## 为什么需要 `GH_TOKEN_FOR_SECRET`

115 刷新 token 后，旧的 refresh_token 会作废。如果新值不回写 Secret，
下一次 Actions 就会因为 token 失效而失败。脚本会用这个 PAT 调 GitHub API
自动更新 `P115_REFRESH_TOKEN`。

不配置也能跑，只是每跑一次要手动更新一次 `P115_REFRESH_TOKEN`。

## 手动触发

GitHub App 或手机浏览器 → **Actions → 微博抓取 → Run workflow**，
`media` 选 `yes`，`since_days` 建议先填 2 试水。

## 目录结构

上传后在 115 的 `PD115_REMOTE_DIR/账号昵称/` 下，按 `img_原创微博图片`、
`video_原创微博视频`、`live_photo_原创微博Live Photo视频` 分目录存放。
