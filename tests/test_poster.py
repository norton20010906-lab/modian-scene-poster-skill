import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.compose_poster import PosterCompositionError, compose_poster
from scripts.compose_reference_poster import compose_reference_poster
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
                    "status_badge": "识别成功",
                    "selling_point_ids": ["face", "entry", "attendance"],
                    "selling_points": ["刷脸快速通行", "适用于企业入口", "支持考勤管理"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.analysis = self.root / "analysis.json"
        self.analysis.write_text(
            json.dumps(
                {
                    "confidence": 0.9,
                    "fallback_used": False,
                    "scene_product_bbox_normalized": [0.62, 0.43, 0.86, 0.68],
                    "scene_product_width_ratio": 0.24,
                },
                ensure_ascii=False,
            ),
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
        with Image.open(output) as image:
            self.assertEqual(image.size, (1080, 1350))
        self.assertTrue(result.manifest_path.exists())
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "complete")
        self.assertFalse(manifest["layout"]["text_overflow"])
        self.assertTrue(manifest["layout"]["status_badge_drawn"])
        self.assertEqual(manifest["status_badge"], "识别成功")

    def test_reference_template_creates_black_editorial_layout(self):
        output = self.root / "reference-poster.png"
        result = compose_reference_poster(
            self.background, self.content, self.analysis, self.brand, output
        )
        with Image.open(output) as image:
            self.assertEqual(image.size, (1080, 1350))
            self.assertEqual(image.getpixel((10, 10)), (14, 14, 20))
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["layout"]["template"], "reference-editorial-black-v1")

    def test_reference_template_rejects_a_small_product(self):
        analysis = json.loads(self.analysis.read_text(encoding="utf-8"))
        analysis["scene_product_width_ratio"] = 0.12
        self.analysis.write_text(json.dumps(analysis), encoding="utf-8")
        with self.assertRaisesRegex(PosterCompositionError, "产品主体宽度"):
            compose_reference_poster(
                self.background,
                self.content,
                self.analysis,
                self.brand,
                self.root / "reference-poster.png",
            )

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

    def test_compose_rejects_scene_where_product_is_too_small(self):
        self.analysis.write_text(
            json.dumps(
                {
                    "confidence": 0.9,
                    "fallback_used": False,
                    "scene_product_bbox_normalized": [0.75, 0.5, 0.84, 0.62],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PosterCompositionError, "产品主体宽度"):
            compose_poster(
                self.background,
                self.content,
                self.analysis,
                self.brand,
                self.root / "poster.png",
            )

    def test_verify_output_rejects_manifest_point_not_in_catalog(self):
        output = self.root / "poster.png"
        Image.new("RGB", (1080, 1350), "white").save(output)
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "status": "complete",
                    "brand": "魔点门禁",
                    "model": "M1-PRO",
                    "scene": "企业办公入口",
                    "fallback_used": False,
                    "selling_point_ids": ["face", "entry", "invented"],
                    "layout": {"text_overflow": False},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        catalog = self.root / "products.yaml"
        catalog.write_text(
            json.dumps(
                {
                    "products": [
                        {
                            "model": "M1-PRO",
                            "aliases": [],
                            "enabled": True,
                            "category": "刷脸门禁机",
                            "verified_features": ["人脸识别"],
                            "selling_points": [
                                {"id": "face", "text": "刷脸快速通行", "verified": True},
                                {"id": "entry", "text": "适用于企业入口", "verified": True},
                                {"id": "attendance", "text": "支持考勤管理", "verified": True},
                            ],
                            "recommended_scenes": ["企业办公入口"],
                            "prohibited_claims": ["绝对零误识"],
                            "sources": [{"label": "官方资料", "status": "verified"}],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(OutputVerificationError, "资料库"):
            verify_output(output, manifest, catalog)


if __name__ == "__main__":
    unittest.main()
