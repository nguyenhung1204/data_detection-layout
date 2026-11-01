import unittest

from tools.bootstrap_dataset import assign_invoices, candidate_annotation


class CandidateAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "id": "crop-1",
            "page": 1,
            "coords": [100, 200, 400, 250],
            "ocr1": "Cong ty ABC",
            "confidence": 0.9,
            "geometry_valid": True,
        }

    def test_verified_transcript_stays_separate_from_field_label(self):
        result = candidate_annotation(
            self.record,
            {"crop_id": "crop-1", "status": "verified", "transcript": "Công ty ABC"},
            invoice_id="HD_001",
            pdf_name="HD_001.pdf",
            pdf_sha256="a" * 64,
            page_size=(1000, 500),
            split="train",
            assigned_to="duy",
        )

        self.assertEqual(result["bbox_norm"], [0.1, 0.4, 0.4, 0.5])
        self.assertEqual(result["transcript"], "Công ty ABC")
        self.assertEqual(result["recognition_status"], "verified")
        self.assertEqual(result["field_status"], "needs_review")
        self.assertIsNone(result["field_key"])
        self.assertEqual(result["row_id"], "")

    def test_rejected_recognition_crop_is_not_promoted_to_field_candidate(self):
        result = candidate_annotation(
            self.record,
            {"crop_id": "crop-1", "status": "rejected", "transcript": "bad box"},
            invoice_id="HD_001",
            pdf_name="HD_001.pdf",
            pdf_sha256="a" * 64,
            page_size=(1000, 500),
            split="train",
            assigned_to="duy",
        )

        self.assertEqual(result["field_status"], "rejected")
        self.assertEqual(result["recognition_status"], "rejected")

    def test_invalid_geometry_is_rejected(self):
        self.record["coords"] = [-1, 200, 400, 250]
        with self.assertRaises(ValueError):
            candidate_annotation(
                self.record,
                None,
                invoice_id="HD_001",
                pdf_name="HD_001.pdf",
                pdf_sha256="a" * 64,
                page_size=(1000, 500),
                split="train",
                assigned_to="duy",
            )


class AssignmentTests(unittest.TestCase):
    def test_exact_40_uses_requested_duy_van_ranges(self):
        rows = [{"document_id": f"HD_{i:03d}"} for i in range(1, 41)]
        assigned = assign_invoices(rows)
        self.assertEqual(list(assigned.values())[:20], ["duy"] * 20)
        self.assertEqual(list(assigned.values())[20:], ["van"] * 20)

    def test_non_40_has_three_assignment_pools_without_overlap(self):
        rows = [{"document_id": f"WEB_{i:03d}", "source_title": f"source-{i}"} for i in range(1, 11)]
        assigned = assign_invoices(rows)
        self.assertEqual(set(assigned), {row["document_id"] for row in rows})
        self.assertEqual(set(assigned.values()), {"duy", "van", "owner_review"})


if __name__ == "__main__":
    unittest.main()
