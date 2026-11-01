from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.console import configure_console

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "invoice_manifest.csv"
ANNOTATIONS = ROOT / "data" / "annotations" / "by_invoice"
FIELDS = json.loads((ROOT / "schema" / "fields.json").read_text(encoding="utf-8"))
FIELD_KEYS = {key for group in FIELDS["field_groups"].values() for key in group}
LAYOUT_KEYS = set(FIELDS["layout_classes"])
STATUS = set(FIELDS["annotation_statuses"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(root: Path = ROOT) -> dict[str, Any]:
    manifest = root / "data" / "manifests" / "invoice_manifest.csv"
    annotations_dir = root / "data" / "annotations" / "by_invoice"
    pdf_dir = root / "data" / "pdfs"
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        invoices = list(csv.DictReader(stream))
    errors, warnings = [], []
    by_invoice, all_ids = {}, set()
    split_owners: dict[str, set[str]] = defaultdict(set)
    status_counts, field_counts = Counter(), Counter()
    invoice_ids = set()
    for inv in invoices:
        invoice_id = inv.get("invoice_id", "")
        if not invoice_id or invoice_id in invoice_ids:
            errors.append(f"invoice_id trống/trùng trong manifest: {invoice_id!r}")
            continue
        invoice_ids.add(invoice_id)
        pdf_name = Path(inv.get("pdf", "")).name
        pdf = pdf_dir / pdf_name
        if not pdf.is_file():
            errors.append(f"Thiếu PDF {invoice_id}: {pdf_name}")
        elif sha256_file(pdf) != inv.get("pdf_sha256"):
            errors.append(f"Checksum PDF không khớp: {invoice_id}")
        if inv.get("split") not in {"train", "val", "test"}:
            errors.append(f"Split không hợp lệ: {invoice_id}={inv.get('split')}")
        ann_path = annotations_dir / f"{invoice_id}.json"
        if not ann_path.is_file():
            errors.append(f"Thiếu annotation JSON: {invoice_id}")
            continue
        try:
            doc = json.loads(ann_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Không đọc được annotation {invoice_id}: {exc}")
            continue
        if doc.get("invoice_id") != invoice_id or doc.get("pdf_sha256") != inv.get("pdf_sha256"):
            errors.append(f"Invoice/checksum trong annotation không khớp manifest: {invoice_id}")
        if doc.get("split") != inv.get("split"):
            errors.append(f"Split annotation lệch manifest: {invoice_id}")
        by_invoice[invoice_id] = doc
        page_count = int(inv.get("page_count") or 0)
        local_ids = set()
        for index, ann in enumerate(doc.get("annotations", [])):
            label = f"{invoice_id}[{index}]"
            ann_id = ann.get("annotation_id")
            if not ann_id or ann_id in local_ids or ann_id in all_ids:
                errors.append(f"annotation_id trống/trùng: {label} {ann_id}")
            local_ids.add(ann_id); all_ids.add(ann_id)
            if ann.get("invoice_id") != invoice_id or ann.get("pdf_sha256") != inv.get("pdf_sha256"):
                errors.append(f"Nguồn annotation sai: {label}")
            page = ann.get("page", 0)
            size, px, norm = ann.get("page_size_px", []), ann.get("bbox_px", []), ann.get("bbox_norm", [])
            if not isinstance(page, int) or page < 1 or page > page_count:
                errors.append(f"Trang ngoài phạm vi: {label}")
            if len(size) != 2 or len(px) != 4 or len(norm) != 4:
                errors.append(f"Thiếu kích thước/tọa độ: {label}")
            else:
                w, h = size; x0, y0, x1, y1 = px
                if min(w, h) <= 0 or x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0 or x1 > w or y1 > h:
                    errors.append(f"BBox pixel sai: {label}")
                if min(norm) < 0 or max(norm) > 1 or norm[2] <= norm[0] or norm[3] <= norm[1]:
                    errors.append(f"BBox chuẩn hóa sai: {label}")
                elif max(abs(px[i] / size[i % 2] - norm[i]) for i in range(4)) > 0.005:
                    errors.append(f"BBox pixel/chuẩn hóa không nhất quán: {label}")
            field = ann.get("field_key")
            layout = ann.get("layout_key")
            status = ann.get("field_status")
            if field and field not in FIELD_KEYS: errors.append(f"Khóa trường ngoài schema: {label} {field}")
            if layout and layout not in LAYOUT_KEYS: errors.append(f"Loại vùng ngoài schema: {label} {layout}")
            if status not in STATUS: errors.append(f"Trạng thái ngoài schema: {label} {status}")
            if status == "verified" and not (field or layout): warnings.append(f"Vùng verified chưa có field/layout key: {label}")
            if field in FIELDS["field_groups"].get("item", {}) and not ann.get("row_id"):
                warnings.append(f"Trường dòng hàng chưa có row_id: {label}")
            if ann.get("recognition_status") == "verified" and status != "verified":
                # Recognition verification is not equivalent to field/layout verification.
                pass
            status_counts[status or "missing"] += 1
            field_counts[field or "unassigned"] += 1
            split_owners[invoice_id].add(inv.get("split", ""))
        if len(split_owners[invoice_id]) > 1:
            errors.append(f"Một hóa đơn có nhiều split: {invoice_id}")
    extras = {p.stem for p in annotations_dir.glob("*.json")} - invoice_ids
    if extras: warnings.append(f"Có {len(extras)} annotation không có trong manifest: {', '.join(sorted(extras)[:10])}")
    split_counts = Counter(row.get("split") for row in invoices)
    assignment_counts = Counter(row.get("assigned_to") for row in invoices)
    return {
        "valid": not errors,
        "invoice_count": len(invoices),
        "annotation_count": sum(len(doc.get("annotations", [])) for doc in by_invoice.values()),
        "split_invoice_counts": dict(split_counts),
        "assignment_invoice_counts": dict(assignment_counts),
        "annotation_status_counts": dict(status_counts),
        "field_counts": dict(field_counts),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate(args.root)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
