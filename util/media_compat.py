"""Media compatibility helpers for the fork-specific GIF-video behavior.

The original fork already routes JPEG/PNG image downloads through the Baidu image
proxy in ``Weibo.handle_download``.  This module keeps that path untouched and
separates GIF animation streams from still images: GIF ``videoSrc`` URLs are
reported as normal video URLs, while their ``large.url`` poster remains an image.

Call :func:`install` once after importing ``weibo``.  The scheduled/Docker entry
point does this automatically; importing this module has no side effects.
"""

from __future__ import annotations

import os
import re


_IMAGE_SIZE_RE = re.compile(r"/(?:mw\d+|bmiddle|thumb\d+|orj\d+|woriginal)/")


def get_pics(weibo_info):
    """Return still-image URLs, excluding video cards and GIF animation streams."""
    result = []
    for pic in weibo_info.get("pics") or []:
        if not isinstance(pic, dict) or pic.get("type") == "video":
            continue
        large = pic.get("large") or {}
        url = large.get("url")
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
    if str(pic.get("type") or "").lower() == "livephoto":
        return False
    if str(pic.get("type") or "").lower() == "video":
        return False
    url = str((pic.get("large") or {}).get("url") or "").lower().split("?", 1)[0]
    return str(pic.get("type") or "").lower() == "gif" or url.endswith(".gif")


def get_video_url(weibo_info, original_get_video_url=None):
    """Keep upstream video extraction and append GIF-only animation streams."""
    base = original_get_video_url(weibo_info) if original_get_video_url else ""
    urls = [url for url in str(base or "").split(";") if url]
    for pic in weibo_info.get("pics") or []:
        if not is_gif_video(pic):
            continue
        url = pic["videoSrc"]
        if url not in urls:
            urls.append(url)
    return ";".join(urls)


def install(weibo_module):
    """Install the GIF/still-image split on the imported ``weibo.Weibo`` class.

    This is idempotent and preserves the class's existing ordinary-video parser.
    """
    cls = weibo_module.Weibo
    if getattr(cls, "_fork_media_compat_installed", False):
        return
    original_get_video_url = cls.get_video_url

    def _get_pics(self, weibo_info):
        return get_pics(weibo_info)

    def _get_video_url(self, weibo_info):
        return get_video_url(weibo_info, original_get_video_url)

    cls.get_pics = _get_pics
    cls.get_video_url = _get_video_url
    cls._fork_media_compat_installed = True
