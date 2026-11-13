# 配置 `timestamp_prefix_format` / `timestamp_prefix_include_id`

媒体文件名和 Markdown 链接的时间前缀由 `util/media_compat.py` 统一格式化，默认格式是 `%Y-%m-%d_%H-%M-%S`。如需兼容旧的紧凑时间名，可配置：

```json
{
  "timestamp_prefix_format": "%Y%m%d_%H%M%S",
  "timestamp_prefix_include_id": 1
}
```

`timestamp_prefix_format` 只接受 `%Y-%m-%d_%H-%M-%S` 或 `%Y%m%d_%H%M%S`；`timestamp_prefix_include_id` 为 `0`/`1`，默认 `0`。开启后微博 ID 加在时间前缀后，再接多图/多视频的序号。此设置只影响后续生成的文件名，不会重命名已有媒体文件。