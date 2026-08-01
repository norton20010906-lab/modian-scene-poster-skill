import json
import tempfile
import unittest
from pathlib import Path

from scripts.load_product_info import ProductCatalogError, load_product
from scripts.validate_content import ContentValidationError, validate_content
from scripts.validate_input import InputValidationError, validate_input


class ProductCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.catalog = self.root / "products.yaml"
        self.catalog.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "products": [
                        {
                            "model": "M1-PRO",
                            "aliases": ["M1 PRO", "m1-pro"],
                            "enabled": True,
                            "category": "刷脸门禁机",
                            "verified_features": ["人脸识别", "门禁通行"],
                            "selling_points": [
                                {"id": "face", "text": "刷脸快速通行", "verified": True},
                                {"id": "entry", "text": "适用于企业入口", "verified": True},
                                {"id": "attendance", "text": "支持考勤管理", "verified": True},
                            ],
                            "recommended_scenes": ["企业办公入口"],
                            "prohibited_claims": ["绝对零误识"],
                            "sources": [{"label": "用户提供的官方资料", "status": "verified"}],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_exact_alias_match_returns_enabled_product(self):
        product = load_product(self.catalog, "  m1 pro ")
        self.assertEqual(product["model"], "M1-PRO")

    def test_unknown_model_is_rejected_without_fuzzy_matching(self):
        with self.assertRaisesRegex(ProductCatalogError, "未收录型号"):
            load_product(self.catalog, "M1-P")

    def test_disabled_placeholder_product_is_rejected(self):
        data = json.loads(self.catalog.read_text(encoding="utf-8"))
        data["products"][0]["enabled"] = False
        self.catalog.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ProductCatalogError, "尚未启用"):
            load_product(self.catalog, "M1-PRO")

    def test_bundled_d5_ultra_record_is_enabled_and_has_three_verified_points(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "products.yaml"
        product = load_product(catalog, "D5Ultra")
        self.assertEqual(product["model"], "D5 Ultra")
        self.assertEqual(
            [point["id"] for point in product["selling_points"]],
            ["face-recognition", "attendance-access", "visual-screen"],
        )


class InputValidationTests(unittest.TestCase):
    def test_missing_image_is_rejected(self):
        with self.assertRaisesRegex(InputValidationError, "产品图片不存在"):
            validate_input(Path("missing.png"), "M1-PRO", "")

    def test_empty_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "product.png"
            image.write_bytes(b"not inspected yet")
            with self.assertRaisesRegex(InputValidationError, "产品型号不能为空"):
                validate_input(image, "  ", "")

    def test_overlong_requirement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "product.png"
            image.write_bytes(b"not inspected yet")
            with self.assertRaisesRegex(InputValidationError, "补充需求不能超过"):
                validate_input(image, "M1-PRO", "场" * 201)


class ContentValidationTests(unittest.TestCase):
    def setUp(self):
        self.product = {
            "model": "M1-PRO",
            "recommended_scenes": ["企业办公入口", "企业前台"],
            "selling_points": [
                {"id": "face", "text": "刷脸快速通行", "verified": True},
                {"id": "entry", "text": "适用于企业入口", "verified": True},
                {"id": "attendance", "text": "支持考勤管理", "verified": True},
                {"id": "install", "text": "安装部署便捷", "verified": True},
            ],
            "prohibited_claims": ["绝对零误识"],
        }

    def test_valid_content_returns_normalized_copy(self):
        content = {
            "brand": "魔点门禁",
            "model": "M1-PRO",
            "title": "让通行更从容",
            "subtitle": "面向企业入口的智能通行体验",
            "scene": "企业前台",
            "status_badge": "识别成功",
            "selling_point_ids": ["face", "entry", "attendance"],
        }
        result = validate_content(content, self.product)
        self.assertEqual(result["selling_points"][0], "刷脸快速通行")
        self.assertEqual(result["scene"], "企业前台")
        self.assertEqual(result["status_badge"], "识别成功")

    def test_unknown_status_badge_is_rejected(self):
        content = {
            "brand": "魔点门禁",
            "model": "M1-PRO",
            "title": "让通行更从容",
            "subtitle": "面向企业入口的智能通行体验",
            "scene": "企业办公入口",
            "status_badge": "百分百识别成功",
            "selling_point_ids": ["face", "entry", "attendance"],
        }
        with self.assertRaisesRegex(ContentValidationError, "状态标签"):
            validate_content(content, self.product)

    def test_scene_outside_product_catalog_is_rejected(self):
        content = {
            "brand": "魔点门禁",
            "model": "M1-PRO",
            "title": "让通行更从容",
            "subtitle": "面向企业入口的智能通行体验",
            "scene": "机场安检口",
            "selling_point_ids": ["face", "entry", "attendance"],
        }
        with self.assertRaisesRegex(ContentValidationError, "使用场景"):
            validate_content(content, self.product)

    def test_unverified_selling_point_is_rejected(self):
        content = {
            "brand": "魔点门禁",
            "model": "M1-PRO",
            "title": "让通行更从容",
            "subtitle": "面向企业入口的智能通行体验",
            "selling_point_ids": ["face", "entry", "invented"],
        }
        with self.assertRaisesRegex(ContentValidationError, "未经验证的卖点"):
            validate_content(content, self.product)

    def test_prohibited_claim_is_rejected_anywhere_in_copy(self):
        content = {
            "brand": "魔点门禁",
            "model": "M1-PRO",
            "title": "绝对零误识",
            "subtitle": "面向企业入口的智能通行体验",
            "selling_point_ids": ["face", "entry", "attendance"],
        }
        with self.assertRaisesRegex(ContentValidationError, "禁用表述"):
            validate_content(content, self.product)


if __name__ == "__main__":
    unittest.main()
