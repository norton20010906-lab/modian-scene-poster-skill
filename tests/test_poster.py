import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.compose_poster import compose_poster
from scripts.verify_output import OutputVerificationError, verify_output


class PosterPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.background = self.root / "scene.png"
        Image.new("RGB", (1024, 1536), "#80909d").save(self.background)
        self.content = self.root / "copy.json"
        self.content.write_text(
            json.dumps(
                {
                    "brand": "魔点门禁",
                    "model": "M1-PRO",
                    "title": "让每一次通行\n自然发生",
                    "subtitle": "面向企业入口的智能通行体验",
                    "selling_point_ids": ["face", "entry", "attendance"],
                    "selling_points": ["刷脸快速通行", "适用于企业入口", "支持考勤管理"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.analysis = self.root / "analysis.json"
        self.analysis.write_text(
            json.dumps({"confidence": 0.9, "fallback_used": False}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.brand = self.root / "brand.yaml"
        self.brand.write_text(
            json.dumps(
                {
                    "brand_name": "魔点门禁",
                    "canvas": {"width": 1080, "height": 1350},
                    "colors": {"accent": "#58E6C0", "text": "#FFFFFF"},
                    "font_candidates": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compose_poster_creates_expected_png_and_manifest(self):
        output = self.root / "poster.png"
        result = compose_poster(
            self.background, self.content, self.analysis, self.brand, output
        )
        self.assertEqual(Image.open(output).size, (1080, 1350))
        self.assertTrue(result.manifest_path.exists())
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "complete")
        self.assertFalse(manifest["layout"]["text_overflow"])

    def test_verify_output_rejects_wrong_dimensions(self):
        output = self.root / "poster.png"
        Image.new("RGB", (100, 100), "white").save(output)
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "status": "complete",
                    "brand": "魔点门禁",
                    "model": "M1-PRO",
                    "scene": "企业办公入口",
                    "fallback_used": False,
                    "selling_point_ids": ["face", "entry", "attendance"],
                    "layout": {"text_overflow": False},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OutputVerificationError, "尺寸"):
            verify_output(output, manifest)


if __name__ == "__main__":
    unittest.main()
