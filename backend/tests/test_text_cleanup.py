from __future__ import annotations

import unittest

from backend.app.text_cleanup import clean_transcript, compress_repetitions, strip_fillers


class TextCleanupTest(unittest.TestCase):
    def test_strip_fillers(self) -> None:
        self.assertEqual(strip_fillers("嗯，那个我小时候住在村口"), "我小时候住在村口")

    def test_compress_repetitions(self) -> None:
        self.assertEqual(compress_repetitions("我我我记得记得那年下雪"), "我记得那年下雪")

    def test_clean_transcript_adds_period(self) -> None:
        self.assertEqual(clean_transcript("嗯我我记得那年下雪"), "我记得那年下雪。")


if __name__ == "__main__":
    unittest.main()
