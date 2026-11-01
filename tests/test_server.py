import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import server


class ServerValidationTests(unittest.TestCase):
    def setUp(self):
        self.invoice = {"invoice_id": "T-1", "filename": "T-1.pdf", "pdf": "data/pdfs/T-1.pdf", "pdf_sha256": "a" * 64, "page_count": "2", "split": "train", "assigned_to": "duy"}
        self.item = {"annotation_id": "r1", "invoice_id": "T-1", "pdf": "T-1.pdf", "pdf_sha256": "a" * 64, "page": 1, "bbox_px": [10, 20, 30, 40], "page_size_px": [100, 100], "bbox_norm": [.1, .2, .3, .4], "field_key": "invoice_number", "layout_key": None, "row_id": "", "transcript": "42", "field_status": "verified", "split": "test", "assigned_to": "wrong"}
        self.invoice_patch = patch.object(server, "INVOICES", {"T-1": self.invoice})
        self.invoice_patch.start()

    def tearDown(self):
        self.invoice_patch.stop()

    def test_server_overrides_client_assignment_and_split(self):
        result = server.validate_annotation("T-1", dict(self.item))
        self.assertEqual(result["split"], "train")
        self.assertEqual(result["assigned_to"], "duy")

    def test_invalid_field_and_pixel_norm_mismatch_rejected(self):
        item = dict(self.item, field_key="invented")
        with self.assertRaises(ValueError): server.validate_annotation("T-1", item)
        item = dict(self.item, bbox_norm=[.2, .2, .3, .4])
        with self.assertRaises(ValueError): server.validate_annotation("T-1", item)

    def test_checksum_mismatch_rejected(self):
        with self.assertRaises(ValueError): server.validate_annotation("T-1", dict(self.item, pdf_sha256="b" * 64))

    def test_row_id_uses_positive_integer_strings(self):
        self.assertEqual(server.validate_annotation("T-1", dict(self.item, row_id="3"))["row_id"], "3")
        with self.assertRaisesRegex(ValueError, "row_id"):
            server.validate_annotation("T-1", dict(self.item, row_id="row-003"))

    def test_atomic_save_reload_and_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            doc = {"schema_version": 1, "invoice_id": "T-1", "pdf": "data/pdfs/T-1.pdf", "pdf_sha256": "a" * 64, "page_count": 2, "split": "train", "assigned_to": "duy", "annotations": [dict(self.item)], "updated_at": ""}
            folder = root / "T-1.json"
            folder.write_text(json.dumps(doc), encoding="utf-8")
            with patch.object(server, "ANNOTATION_DIR", root):
                changed = dict(self.item, transcript="43")
                result = server.atomic_save("T-1", dict(doc, annotations=[changed]))
                loaded = server.load_annotation("T-1")
            self.assertEqual(loaded["annotations"][0]["transcript"], "43")
            self.assertTrue(loaded["annotations"][0]["history"])
            self.assertEqual(result["invoice_id"], "T-1")

    def test_path_traversal_invoice_id_rejected(self):
        with self.assertRaises(ValueError): server.safe_annotation_path("..\\secret")


if __name__ == "__main__":
    unittest.main()
