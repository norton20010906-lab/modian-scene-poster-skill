import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_repository import audit_repository
from scripts.preflight import run_preflight


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_preflight_reports_ready_with_required_host_capabilities(self):
        result = run_preflight(
            workspace=self.root,
            catalog_path=self.root / "data" / "products.yaml",
            templates_path=self.root / "data" / "layout_templates.yaml",
            model="D5 Ultra",
            host_capabilities={"vision", "image-generation"},
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["model"], "D5 Ultra")
        self.assertTrue(result["checks"]["workspace_writable"]["ok"])
        self.assertTrue(result["checks"]["pillow"]["ok"])

    def test_preflight_stops_when_image_generation_is_unavailable(self):
        result = run_preflight(
            workspace=self.root,
            catalog_path=self.root / "data" / "products.yaml",
            templates_path=self.root / "data" / "layout_templates.yaml",
            model="D5 Ultra",
            host_capabilities={"vision"},
        )
        self.assertFalse(result["ready"])
        self.assertFalse(result["checks"]["image_generation"]["ok"])
        self.assertIn("正式海报", result["checks"]["image_generation"]["remediation"])


class RepositoryAuditTests(unittest.TestCase):
    def _write_minimal_repo(self, root: Path, *, model: str = "D5 Ultra") -> None:
        (root / "data").mkdir()
        (root / "assets").mkdir()
        (root / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n", encoding="utf-8")
        (root / "assets" / "sample.webp").write_bytes(b"sample")
        catalog = {
            "products": [{
                "model": model,
                "sources": [{"path": "assets/sample.webp"}],
            }]
        }
        (root / "data" / "products.yaml").write_text(
            json.dumps(catalog, ensure_ascii=False), encoding="utf-8"
        )

    def test_audit_accepts_portable_d5_only_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_repo(root)
            result = audit_repository(root, allowed_models={"D5 Ultra"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["issues"], [])

    def test_audit_rejects_personal_temp_path_and_extra_model(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_repo(root, model="X3W")
            catalog_path = root / "data" / "products.yaml"
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
            data["products"][0]["sources"][0]["path"] = (
                "C:/Users/Administrator/AppData/Local/Temp/product.png"
            )
            catalog_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = audit_repository(root, allowed_models={"D5 Ultra"})
        issue_codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("unsupported_model", issue_codes)
        self.assertIn("absolute_path", issue_codes)

    def test_audit_rejects_missing_relative_asset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_repo(root)
            (root / "assets" / "sample.webp").unlink()
            result = audit_repository(root, allowed_models={"D5 Ultra"})
        self.assertIn("missing_asset", {issue["code"] for issue in result["issues"]})


if __name__ == "__main__":
    unittest.main()
