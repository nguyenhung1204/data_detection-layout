import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.export_dataset import export_dataset
from tools.export_assignment import export_assignment
from tools.merge_annotations import merge_package
from tools.validate_dataset import validate


class MergeExportTests(unittest.TestCase):
    def make_repo(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        (root / "schema").mkdir()
        (root / "schema" / "fields.json").write_text(Path(__file__).parents[1].joinpath("schema/fields.json").read_text(encoding="utf-8"), encoding="utf-8")
        (root / "data/pdfs").mkdir(parents=True)
        (root / "data/manifests").mkdir(parents=True)
        (root / "data/annotations/by_invoice").mkdir(parents=True)
        pdf = root / "data/pdfs/X-1.pdf"; pdf.write_bytes(b"test-pdf-bytes")
        import hashlib
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        invoice = {"invoice_id":"X-1","filename":"X-1.pdf","pdf":"data/pdfs/X-1.pdf","pdf_sha256":sha,"page_count":"1","split":"train","assigned_to":"duy"}
        with (root / "data/manifests/invoice_manifest.csv").open("w", encoding="utf-8", newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(invoice));w.writeheader();w.writerow(invoice)
        with (root / "data/manifests/assignment_manifest.csv").open("w", encoding="utf-8", newline="") as f:
            w=csv.DictWriter(f,fieldnames=["invoice_id","pdf","assigned_to","split","sha256"]);w.writeheader();w.writerow({"invoice_id":"X-1","pdf":"X-1.pdf","assigned_to":"duy","split":"train","sha256":sha})
        ann = {"annotation_id":"r1","invoice_id":"X-1","pdf":"X-1.pdf","pdf_sha256":sha,"page":1,"bbox_px":[10,20,30,40],"page_size_px":[100,100],"bbox_norm":[.1,.2,.3,.4],"field_key":None,"layout_key":None,"row_id":"","transcript":"","field_status":"needs_review","split":"train","assigned_to":"duy","updated_at":"","history":[]}
        doc = {"schema_version":1,"invoice_id":"X-1","pdf":"data/pdfs/X-1.pdf","pdf_sha256":sha,"page_count":1,"split":"train","assigned_to":"duy","annotations":[ann],"updated_at":""}
        ann_path=root / "data/annotations/by_invoice/X-1.json";ann_path.write_text(json.dumps(doc),encoding="utf-8")
        return sha,ann_path,doc

    def test_merge_applies_one_edited_invoice_and_reports_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"repo";pkg=Path(tmp)/"pkg";pkg.mkdir();sha,_,doc=self.make_repo(root)
            remote=json.loads(json.dumps(doc));remote["annotations"][0]["transcript"]="Mẫu đúng";remote["annotations"][0]["field_key"]="invoice_number";remote["annotations"][0]["updated_at"]="2026-11-02T00:00:00+00:00"
            incoming=pkg/"by_invoice";incoming.mkdir();(incoming/"X-1.json").write_text(json.dumps(remote),encoding="utf-8")
            result=merge_package(pkg,root)
            self.assertFalse(result["conflicts"])
            saved_transcript = json.loads((root/"data/annotations/by_invoice/X-1.json").read_text(encoding="utf-8"))["annotations"][0]["transcript"]
            self.assertEqual([ord(char) for char in saved_transcript], [77, 7851, 117, 32, 273, 250, 110, 103])
            self.assertTrue(Path(result["backup_dir"],"X-1.json").is_file())

            local_path=root/"data/annotations/by_invoice/X-1.json";local=json.loads(local_path.read_text());local["annotations"][0]["transcript"]="Bản local";local["annotations"][0]["updated_at"]="2026-11-02T00:01:00+00:00";local_path.write_text(json.dumps(local),encoding="utf-8")
            remote["annotations"][0]["transcript"]="Bản khác";remote["annotations"][0]["updated_at"]="2026-11-02T00:02:00+00:00";(incoming/"X-1.json").write_text(json.dumps(remote),encoding="utf-8")
            result=merge_package(pkg,root)
            self.assertTrue(result["conflicts"])
            self.assertEqual(json.loads(local_path.read_text())["annotations"][0]["transcript"],"Bản local")

    def test_export_separates_verified_and_review_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);sha,ann_path,doc=self.make_repo(root)
            doc["annotations"][0]["field_key"]="invoice_number";doc["annotations"][0]["field_status"]="verified";ann_path.write_text(json.dumps(doc),encoding="utf-8")
            output=root/"field.zip";export_dataset(root,output)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("verified.jsonl",archive.namelist());self.assertIn("review.jsonl",archive.namelist())
                records=[json.loads(line) for line in archive.read("verified.jsonl").decode().splitlines()]
                self.assertEqual(len(records),1);self.assertEqual(records[0]["field_status"],"verified")

    def test_assignment_zip_contains_only_assigned_annotations_and_no_pdfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,_,_=self.make_repo(root)
            package_bytes=export_assignment(root,"duy")
            package=Path(tmp)/"duy.zip";package.write_bytes(package_bytes)
            with zipfile.ZipFile(package) as archive:
                names=set(archive.namelist())
                self.assertEqual(names,{"by_invoice/X-1.json","assignment_manifest.csv","package_manifest.json","README.txt"})
                self.assertFalse(any(name.lower().endswith(".pdf") for name in names))
                metadata=json.loads(archive.read("package_manifest.json"))
                self.assertEqual(metadata["assigned_to"],"duy")
                self.assertEqual(metadata["invoice_count"],1)
            with self.assertRaisesRegex(ValueError,"Duy hoặc Vân"):
                export_assignment(root,"all")

    def test_merge_accepts_assignment_zip_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"repo";_,_,_=self.make_repo(root)
            package=Path(tmp)/"duy.zip";package.write_bytes(export_assignment(root,"duy"))
            report=merge_package(package,root)
            self.assertFalse(report["conflicts"])
            self.assertFalse(report["unknown_invoices"])


if __name__ == "__main__":
    unittest.main()
