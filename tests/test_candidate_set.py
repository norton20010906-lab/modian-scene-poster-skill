import tempfile
import unittest
import json
from pathlib import Path

from PIL import Image

from scripts.compose_candidate_set import build_contact_sheet, load_template_library


class CandidateSetTests(unittest.TestCase):
    def test_bundled_library_has_four_internal_default_templates(self):
        catalog = Path(__file__).resolve().parents[1] / "data" / "layout_templates.yaml"
        library = load_template_library(catalog)
        self.assertTrue(library["internal_only"])
        self.assertEqual(len(library["candidate_defaults"]), 4)
        self.assertTrue(
            set(library["candidate_defaults"]).issubset(
                {template["id"] for template in library["templates"]}
            )
        )

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
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            expanded = Path(temp_dir) / "layouts.json"
            expanded.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            library = load_template_library(expanded)
        self.assertEqual(len(library["templates"]), 5)
        self.assertEqual(len(library["candidate_defaults"]), 4)

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
            template_ids = ["layout-a", "layout-b", "layout-c", "layout-d"]
            output = root / "contact-sheet.png"
            build_contact_sheet(posters, output, template_ids=template_ids)
            manifest = json.loads(
                output.with_name("candidate_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [candidate["template_id"] for candidate in manifest["candidates"]],
                template_ids,
            )


if __name__ == "__main__":
    unittest.main()
