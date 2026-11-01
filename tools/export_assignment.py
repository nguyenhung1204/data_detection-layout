from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def export_assignment(root: Path, assignee: str) -> bytes:
    assignee = assignee.strip().casefold()
    if assignee not in {"duy", "van"}:
        raise ValueError("Chọn Duy hoặc Vân để xuất ZIP.")
    with (root / "data/manifests/invoice_manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        invoices = [row for row in csv.DictReader(stream) if row.get("assigned_to", "").casefold() == assignee]
    if not invoices:
        raise ValueError(f"Không có hóa đơn nào được phân công cho {assignee}.")

    entries: dict[str, bytes] = {}
    annotation_count = 0
    for invoice in invoices:
        invoice_id = invoice["invoice_id"]
        path = root / "data/annotations/by_invoice" / f"{invoice_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu file nhãn của {invoice_id}.")
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("invoice_id") != invoice_id or document.get("pdf_sha256") != invoice.get("pdf_sha256"):
            raise ValueError(f"ID hoặc checksum nhãn không khớp hóa đơn {invoice_id}.")
        annotation_count += len(document.get("annotations", []))
        entries[f"by_invoice/{invoice_id}.json"] = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    manifest = io.StringIO(newline="")
    writer = csv.DictWriter(manifest, fieldnames=["invoice_id", "pdf", "assigned_to", "split", "sha256"])
    writer.writeheader()
    for invoice in invoices:
        writer.writerow({"invoice_id": invoice["invoice_id"], "pdf": invoice["filename"], "assigned_to": assignee, "split": invoice["split"], "sha256": invoice["pdf_sha256"]})
    entries["assignment_manifest.csv"] = manifest.getvalue().encode("utf-8-sig")
    metadata = {
        "package_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "assigned_to": assignee,
        "invoice_count": len(invoices),
        "annotation_count": annotation_count,
        "contains_pdfs": False,
    }
    entries["package_manifest.json"] = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    entries["README.txt"] = (
        "Gói nhãn hóa đơn cho người được phân công. Không chứa PDF.\n"
        "Gửi nguyên ZIP này cho chủ repo để tổng hợp. Chủ repo giải nén ZIP rồi chạy:\n"
        "python -m tools.merge_annotations <thu_muc_vua_giai_nen>\n"
    ).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return output.getvalue()
