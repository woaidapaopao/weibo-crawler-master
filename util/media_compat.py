"""Media compatibility helpers for this fork.

This module retains the historical Baidu image proxy in ``weibo.handle_download``
(we do not rewrite that method), classifies GIF animation ``videoSrc`` separately
from its still image, and ports upstream's configurable media timestamp prefix.

Install once after importing :mod:`weibo`; it is safe to call repeatedly.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from datetime import datetime

DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
SUPPORTED_TIMESTAMP_FORMATS = (DEFAULT_TIMESTAMP_FORMAT, "%Y%m%d_%H%M%S")
_IMAGE_SIZE_RE = re.compile(r"/(?:mw\d+|bmiddle|thumb\d+|orj\d+|woriginal)/")
DTFORMAT = "%Y-%m-%dT%H:%M:%S"


def get_pics(weibo_info):
    """Return still-image URLs, excluding video cards and GIF animation streams."""
    result = []
    for pic in weibo_info.get("pics") or []:
        if not isinstance(pic, dict) or str(pic.get("type") or "").lower() == "video":
            continue
        url = (pic.get("large") or {}).get("url")
        if not url:
            continue
        url = _IMAGE_SIZE_RE.sub("/large/", url)
        if url not in result:
            result.append(url)
    return result


def is_gif_video(pic):
    """Whether a ``pics`` entry carries a separate GIF animation video stream."""
    if not isinstance(pic, dict) or not pic.get("videoSrc"):
        return False
    pic_type = str(pic.get("type") or "").lower()
    if pic_type in {"livephoto", "video"}:
        return False
    image_url = str((pic.get("large") or {}).get("url") or "")
    path = urlparse(image_url).path.lower()
    return pic_type == "gif" or path.endswith(".gif")


def get_video_url(weibo_info, original_get_video_url=None):
    """Keep ordinary upstream video extraction and append GIF animation streams."""
    base = original_get_video_url(weibo_info) if original_get_video_url else ""
    urls = [url for url in str(base or "").split(";") if url]
    for pic in weibo_info.get("pics") or []:
        if is_gif_video(pic) and pic["videoSrc"] not in urls:
            urls.append(pic["videoSrc"])
    return ";".join(urls)


def timestamp_prefix(created_at, weibo_id=None, format_string=None):
    """Format the media timestamp using one of upstream's supported patterns."""
    fmt = format_string or DEFAULT_TIMESTAMP_FORMAT
    if fmt not in SUPPORTED_TIMESTAMP_FORMATS:
        raise ValueError(
            "timestamp_prefix_format must be one of: "
            + ", ".join(SUPPORTED_TIMESTAMP_FORMATS)
        )
    try:
        prefix = datetime.strptime(str(created_at), DTFORMAT).strftime(fmt)
    except (TypeError, ValueError):
        prefix = str(created_at or "")[:11].replace("-", "") or "unknown_time"
    return f"{prefix}_{weibo_id}" if weibo_id else prefix


def _image_suffix(url):
    path = urlparse(str(url or "")).path
    suffix = os.path.splitext(path)[1].lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"} else ".jpg"


def install(weibo_module):
    """Install fork/upstream media compatibility on the imported ``Weibo`` class."""
    cls = weibo_module.Weibo
    if getattr(cls, "_fork_media_compat_installed", False):
        return

    original_init = cls.__init__
    original_get_video_url = cls.get_video_url
    original_handle_download = cls.handle_download
    original_get_download_file_names = getattr(cls, "get_download_file_names", None)
    original_download_weibo_images = getattr(cls, "_download_weibo_images", None)
    original_markdown_image_filenames = getattr(cls, "get_markdown_image_filenames", None)

    def _init(self, config, *args, **kwargs):
        original_init(self, config, *args, **kwargs)
        fmt = config.get("timestamp_prefix_format", DEFAULT_TIMESTAMP_FORMAT)
        if fmt not in SUPPORTED_TIMESTAMP_FORMATS:
            raise ValueError(
                "timestamp_prefix_format must be one of: "
                + ", ".join(SUPPORTED_TIMESTAMP_FORMATS)
            )
        include_id = config.get("timestamp_prefix_include_id", 0)
        if include_id not in (0, 1, False, True):
            raise ValueError("timestamp_prefix_include_id must be 0 or 1")
        self.timestamp_prefix_format = fmt
        self.timestamp_prefix_include_id = int(include_id)

    def _get_pics(self, weibo_info):
        # Legacy fork stores lists of URLs; upstream stores comma-delimited strings.
        urls = get_pics(weibo_info)
        return urls if isinstance(getattr(self, "pics_as_list", True), bool) else ",".join(urls)

    def _get_video_url(self, weibo_info):
        return get_video_url(weibo_info, original_get_video_url)

    def _get_timestamp_prefix(self, created_at):
        weibo_id = getattr(self, "_fork_media_current_id", None)
        if getattr(self, "timestamp_prefix_include_id", 0) and not weibo_id:
            # Callers that only know the timestamp retain the old behavior; media
            # download/name methods below set the ID context for collision-safe names.
            weibo_id = None
        return timestamp_prefix(
            created_at,
            weibo_id,
            getattr(self, "timestamp_prefix_format", DEFAULT_TIMESTAMP_FORMAT),
        )

    def _with_weibo_id(self, weibo, callback, *args, **kwargs):
        previous = getattr(self, "_fork_media_current_id", None)
        self._fork_media_current_id = str((weibo or {}).get("id") or "") or None
        try:
            return callback(self, *args, **kwargs)
        finally:
            self._fork_media_current_id = previous

    def _handle_download(self, file_type, file_dir, urls, weibo):
        return _with_weibo_id(self, weibo, original_handle_download, file_type, file_dir, urls, weibo)

    def _get_download_file_names(self, file_type, urls, weibo):
        if original_get_download_file_names is None:
            return []
        return _with_weibo_id(self, weibo, original_get_download_file_names, file_type, urls, weibo)

    def _download_weibo_images(self, weibo, img_dir, is_retweet=False):
        """Keep Markdown image download names aligned with configured media names."""
        if original_download_weibo_images is None:
            return
        return _with_weibo_id(self, weibo, original_download_weibo_images, weibo, img_dir, is_retweet)

    def _get_markdown_image_filenames(self, weibo, fallback_created_at=""):
        if original_markdown_image_filenames is None:
            return []
        return _with_weibo_id(
            self, weibo, original_markdown_image_filenames, weibo, fallback_created_at
        )

    cls.__init__ = _init
    cls.get_pics = _get_pics
    cls.get_video_url = _get_video_url
    cls._get_timestamp_prefix = _get_timestamp_prefix
    cls.handle_download = _handle_download
    if original_get_download_file_names is not None:
        cls.get_download_file_names = _get_download_file_names
    if original_download_weibo_images is not None:
        cls._download_weibo_images = _download_weibo_images
    if original_markdown_image_filenames is not None:
        cls.get_markdown_image_filenames = _get_markdown_image_filenames
    cls._fork_media_compat_installed = True
