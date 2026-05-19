from __future__ import annotations

import struct
import unittest

from backend.app.segmentation import SilenceSegmenter, pcm_duration_ms, pcm_rms


def pcm_frame(value: int, samples: int = 1600) -> bytes:
    return struct.pack("<" + "h" * samples, *([value] * samples))


class SegmentationTest(unittest.TestCase):
    def test_pcm_duration(self) -> None:
        self.assertEqual(pcm_duration_ms(pcm_frame(0, samples=16000)), 1000)

    def test_rms(self) -> None:
        self.assertGreater(pcm_rms(pcm_frame(1200)), 1000)
        self.assertEqual(pcm_rms(b""), 0)

    def test_silence_after_voice_closes_segment(self) -> None:
        segmenter = SilenceSegmenter(silence_ms=300, min_audio_ms=200, energy_threshold=500)
        self.assertFalse(segmenter.ingest(pcm_frame(1200), "奶奶说"))
        self.assertFalse(segmenter.ingest(pcm_frame(0), "奶奶说"))
        self.assertFalse(segmenter.ingest(pcm_frame(0), "奶奶说"))
        self.assertTrue(segmenter.ingest(pcm_frame(0), "奶奶说"))


if __name__ == "__main__":
    unittest.main()
