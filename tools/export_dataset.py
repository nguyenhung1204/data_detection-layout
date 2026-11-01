from __future__ import annotations

import argparse
import csv
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.console import configure_console

from tools.validate_dataset import ROOT, validate


def export_dataset(root: Path = ROOT, output: Path | None = None) -> Path:
    report = validate(root)
    if report["errors"]:
        raise ValueError("Không xuất được: validation có lỗi. Xem reports/validation.json")
    output = output or root / "exports" / ("field_layout_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".zip")
    output.parent.mkdir(parents=True, exist_ok=True)
    inv_manifest = root / "data" / "manifests" / "invoice_manifest.csv"
    with inv_manifest.open(encoding="utf-8-sig", newline="") as stream:
        invoices = {r["invoice_id"]: r for r in csv.DictReader(stream)}
    files = {}
    for invoice_id in invoices:
        path = root / "data" / "annotations" / "by_invoice" / f"{invoice_id}.json"
        files[invoice_id] = json.loads(path.read_text(encoding="utf-8"))
    verified, review = [], []
    all_rows = []
    for invoice_id, doc in files.items():
        inv = invoices[invoice_id]
        for ann in doc.get("annotations", []):
            row = {"invoice_id": invoice_id, "pdf": inv["pdf"], "pdf_sha256": inv["pdf_sha256"], "split": inv["split"], "assigned_to": inv["assigned_to"], **ann}
            all_rows.append(row)
            (verified if ann.get("field_status") == "verified" else review).append(row)
    headers = ["annotation_id", "invoice_id", "pdf", "pdf_sha256", "page", "bbox_px", "page_size_px", "bbox_norm", "field_key", "layout_key", "row_id", "transcript", "recognition_status", "transcript_status", "field_status", "split", "assigned_to", "source", "confidence"]
    export_root = root / ".cache" / "exports"
    export_root.mkdir(parents=True, exist_ok=True)
    csv_path = export_root / "annotations.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore"); writer.writeheader()
        for row in all_rows: writer.writerow({k: json.dumps(row[k], ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k, "") for k in headers})
    (export_root / "verified.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in verified), encoding="utf-8")
    (export_root / "review.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in review), encoding="utf-8")
    summary = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "scope": "field/layout annotations; not a model-specific PaddleOCR training package", "validation": report, "confirmed_annotation_count": len(verified), "review_annotation_count": len(review), "invoice_count": len(invoices), "files": ["annotations.csv", "verified.jsonl", "review.jsonl", "schema/fields.json", "data/manifests/invoice_manifest.csv", "data/manifests/assignment_manifest.csv"]}
    (export_root / "export_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("annotations.csv", "verified.jsonl", "review.jsonl", "export_summary.json"):
            archive.write(export_root / name, name)
        for name in ("schema/fields.json", "data/manifests/invoice_manifest.csv", "data/manifests/assignment_manifest.csv"):
            archive.write(root / name, name)
    return output


def main():
    configure_console()
    parser = argparse.ArgumentParser(description="Export validated field/layout labels; verified and review records stay separate.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = export_dataset(args.root, args.output)
    print(f"Đã tạo gói: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
