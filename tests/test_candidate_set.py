import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image

from scripts.compose_candidate_set import build_contact_sheet, load_template_library
from scripts.promote_layout_template import promote_template


class CandidateSetTests(unittest.TestCase):
    def test_bundled_library_uses_three_library_slots_and_one_exploration_slot(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        library = load_template_library(catalog)
        self.assertTrue(library["internal_only"])
        strategy = library["candidate_strategy"]
        self.assertEqual(strategy["library_slots"], ["P1", "P2", "P3"])
        self.assertEqual(strategy["exploration_slot"], "P4")
        self.assertEqual(strategy["library_pick_count"], 3)
        self.assertEqual(strategy["exploration_count"], 1)
        promoted = next(
            item for item in library["templates"]
            if item["id"] == "asymmetric-campaign-hero"
        )
        self.assertEqual(promoted["status"], "approved")
        self.assertEqual(promoted["origin"], "experimental_promotion")

    def test_library_can_accumulate_more_than_four_templates(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        data = json.loads(catalog.read_text(encoding="utf-8"))
        data["templates"].append(
            {
                "id": "future-layout",
                "label": "未来模板",
                "source": "内部积累",
                "best_for": ["测试扩展"],
                "product_width_target": [0.2, 0.4],
                "scene_asset": "wide_interaction",
                "status": "approved",
                "origin": "internal_accumulation",
                "renderer": "future_renderer",
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            expanded = Path(temp_dir) / "layouts.json"
            expanded.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            library = load_template_library(expanded)
        self.assertEqual(len(library["templates"]), 5)

    def test_library_rejects_template_without_selection_metadata(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        data = json.loads(catalog.read_text(encoding="utf-8"))
        del data["templates"][0]["best_for"]
        with tempfile.TemporaryDirectory() as temp_dir:
            malformed = Path(temp_dir) / "layouts.json"
            malformed.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "模板元数据"):
                load_template_library(malformed)

    def test_contact_sheet_places_exactly_four_posters_in_two_by_two_grid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            posters = []
            for index, color in enumerate(("#111111", "#222222", "#333333", "#444444"), start=1):
                poster = root / f"p{index}.png"
                Image.new("RGB", (1080, 1350), color).save(poster)
                posters.append(poster)
            output = root / "contact-sheet.png"
            result = build_contact_sheet(posters, output)
            with Image.open(result) as image:
                self.assertEqual(image.size, (2160, 2700))
            manifest = json.loads(
                output.with_name("candidate_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(manifest["candidates"]), 4)
            self.assertEqual(manifest["selection_status"], "awaiting_user_selection")
            self.assertEqual(
                [item["source_type"] for item in manifest["candidates"]],
                ["library", "library", "library", "exploration"],
            )
            self.assertIn("左上为 1", manifest["user_guidance"])
            self.assertIn("加入模板库", manifest["user_guidance"])

    def test_contact_sheet_rejects_any_count_other_than_four(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            poster = root / "p1.png"
            Image.new("RGB", (1080, 1350), "black").save(poster)
            with self.assertRaisesRegex(ValueError, "4"):
                build_contact_sheet([poster], root / "contact-sheet.png")

    def test_contact_sheet_can_record_any_four_selected_internal_templates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            posters = []
            for index in range(4):
                poster = root / f"p{index}.png"
                Image.new("RGB", (1080, 1350), "black").save(poster)
                posters.append(poster)
            template_ids = ["layout-a", "layout-b", "layout-c", "experimental:new-layout"]
            output = root / "contact-sheet.png"
            build_contact_sheet(posters, output, template_ids=template_ids)
            manifest = json.loads(
                output.with_name("candidate_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [candidate["template_id"] for candidate in manifest["candidates"]],
                template_ids,
            )

    def test_contact_sheet_rejects_a_library_template_in_exploration_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            posters = []
            for index in range(4):
                poster = root / f"p{index}.png"
                Image.new("RGB", (1080, 1350), "black").save(poster)
                posters.append(poster)
            with self.assertRaisesRegex(ValueError, "P4.*experimental"):
                build_contact_sheet(
                    posters,
                    root / "contact-sheet.png",
                    template_ids=["layout-a", "layout-b", "layout-c", "layout-d"],
                )

    def test_promotes_an_explicitly_approved_p4_recipe(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        candidate = {
            "id": "new-layout",
            "label": "新布局",
            "source": "本轮 P4 探索",
            "best_for": ["产品主体突出"],
            "product_width_target": [0.35, 0.55],
            "scene_asset": "wide_interaction",
            "renderer": "compose_new_layout",
            "layout_recipe": {
                "composition": "左文右图",
                "text_hierarchy": "品牌、标题、副标题、卖点",
                "product_placement": "产品占画布宽度 35% 至 55%",
                "prompt_guidance": "保留人物与设备互动关系",
            },
            "promotion_evidence": {
                "user_approved": True,
                "run_id": "run-001",
                "selection_key": "P4",
                "sample_path": "output/run-001/p4/poster.png",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_path = root / "candidate.json"
            output_path = root / "catalog.json"
            candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
            result = promote_template(catalog, candidate_path, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))
        promoted = next(item for item in result["templates"] if item["id"] == "new-layout")
        self.assertEqual(promoted["status"], "approved")
        self.assertEqual(promoted["origin"], "experimental_promotion")
        self.assertEqual(written["templates"][-1]["id"], "new-layout")

    def test_rejects_promotion_without_explicit_user_approval(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        candidate = {
            "id": "unapproved-layout",
            "label": "未批准布局",
            "source": "本轮 P4 探索",
            "best_for": ["测试"],
            "product_width_target": [0.3, 0.5],
            "scene_asset": "wide_interaction",
            "renderer": "compose_layout",
            "layout_recipe": {
                "composition": "构图",
                "text_hierarchy": "层级",
                "product_placement": "位置",
                "prompt_guidance": "提示",
            },
            "promotion_evidence": {
                "user_approved": False,
                "run_id": "run-002",
                "selection_key": "P4",
                "sample_path": "output/run-002/p4/poster.png",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_path = Path(temp_dir) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "明确认可"):
                promote_template(catalog, candidate_path, Path(temp_dir) / "catalog.json")

    def test_rejects_duplicate_or_non_reusable_promotion(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        base_candidate = {
            "id": "editorial-feature-grid",
            "label": "重复布局",
            "source": "本轮 P4 探索",
            "best_for": ["测试"],
            "product_width_target": [0.3, 0.5],
            "scene_asset": "wide_interaction",
            "renderer": "compose_layout",
            "layout_recipe": {
                "composition": "构图",
                "text_hierarchy": "层级",
                "product_placement": "位置",
                "prompt_guidance": "提示",
            },
            "promotion_evidence": {
                "user_approved": True,
                "run_id": "run-003",
                "selection_key": "P4",
                "sample_path": "output/run-003/p4/poster.png",
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_path = root / "candidate.json"
            candidate_path.write_text(json.dumps(base_candidate, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "已存在"):
                promote_template(catalog, candidate_path, root / "catalog.json")
            base_candidate["id"] = "missing-recipe-layout"
            del base_candidate["layout_recipe"]["prompt_guidance"]
            candidate_path.write_text(json.dumps(base_candidate, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "可复用"):
                promote_template(catalog, candidate_path, root / "catalog.json")


if __name__ == "__main__":
    unittest.main()
