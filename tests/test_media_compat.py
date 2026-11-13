"""Tests for the fork's GIF-versus-image classification."""

import unittest

from util import media_compat


class MediaCompatTest(unittest.TestCase):
    def test_gif_still_is_retained_but_animation_is_video(self):
        post = {
            "pics": [
                {
                    "type": "gif",
                    "large": {"url": "https://wx1.sinaimg.cn/mw690/a.gif"},
                    "videoSrc": "https://f.video.weibocdn.com/a.mp4?token=x",
                }
            ]
        }
        self.assertEqual(
            media_compat.get_pics(post), ["https://wx1.sinaimg.cn/large/a.gif"]
        )
        self.assertEqual(
            media_compat.get_video_url(post),
            "https://f.video.weibocdn.com/a.mp4?token=x",
        )

    def test_live_photo_video_stream_is_not_misclassified_as_gif(self):
        post = {
            "pics": [
                {
                    "type": "livephoto",
                    "large": {"url": "https://wx1.sinaimg.cn/large/a.jpg"},
                    "videoSrc": "https://f.video.weibocdn.com/a.mov",
                }
            ]
        }
        self.assertEqual(media_compat.get_pics(post), ["https://wx1.sinaimg.cn/large/a.jpg"])
        self.assertEqual(media_compat.get_video_url(post), "")

    def test_multi_video_card_is_not_a_still_image_or_gif(self):
        post = {
            "pics": [
                {
                    "type": "video",
                    "large": {"url": "https://wx1.sinaimg.cn/large/a.jpg"},
                    "videoSrc": "https://f.video.weibocdn.com/a.mp4",
                }
            ]
        }
        self.assertEqual(media_compat.get_pics(post), [])
        self.assertEqual(media_compat.get_video_url(post), "")

    def test_regular_video_extraction_is_preserved(self):
        post = {
            "pics": [],
            "page_info": {
                "type": "video",
                "urls": {"mp4_720p_mp4": "https://f.video.weibocdn.com/regular.mp4"},
            },
        }
        self.assertEqual(
            media_compat.get_video_url(post, lambda _post: "https://f.video.weibocdn.com/regular.mp4"),
            "https://f.video.weibocdn.com/regular.mp4",
        )


if __name__ == "__main__":
    unittest.main()
