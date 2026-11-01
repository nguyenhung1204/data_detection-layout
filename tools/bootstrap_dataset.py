from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.console import configure_console

ROOT = Path(__file__).resolve().parents[1]
ASSIGNEES = ("duy", "van")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(path: Path) -> str:
    return sha256_file(path) if path.is_file() else ""


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Không phải PNG hợp lệ: {path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width < 1 or height < 1:
        raise ValueError(f"Kích thước ảnh không hợp lệ: {path}")
    return width, height


def candidate_annotation(
    record: dict[str, Any],
    review: dict[str, Any] | None,
    *,
    invoice_id: str,
    pdf_name: str,
    pdf_sha256: str,
    page_size: tuple[int, int],
    split: str,
    assigned_to: str,
) -> dict[str, Any]:
    coords = record.get("coords")
    if not isinstance(coords, (list, tuple)) or len(coords) != 4:
        raise ValueError(f"Hộp OCR không có 4 tọa độ: {record.get('id')}")
    try:
        x0, y0, x1, y1 = (float(value) for value in coords)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Tọa độ không phải số: {record.get('id')}") from exc
    width, height = page_size
    if width <= 0 or height <= 0 or x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0 or x1 > width or y1 > height:
        raise ValueError(f"Hộp nằm ngoài trang hoặc rỗng: {record.get('id')}")

    recognition_status = str((review or {}).get("status") or record.get("status") or "needs_review")
    if recognition_status not in {"verified", "rejected", "needs_review"}:
        recognition_status = "needs_review"
    transcript = str((review or {}).get("transcript") or record.get("ocr1") or record.get("text") or "")
    transcript_status = "verified" if recognition_status == "verified" else "needs_review"
    field_status = "rejected" if recognition_status == "rejected" else "needs_review"
    return {
        "annotation_id": str(record.get("id") or record.get("crop_id") or ""),
        "invoice_id": invoice_id,
        "pdf": pdf_name,
        "pdf_sha256": pdf_sha256,
        "page": int(record.get("page") or 1),
        "bbox_px": [round(x0), round(y0), round(x1), round(y1)],
        "page_size_px": [width, height],
        "bbox_norm": [round(x0 / width, 7), round(y0 / height, 7), round(x1 / width, 7), round(y1 / height, 7)],
        "annotation_kind": "text_region",
        "field_key": None,
        "layout_key": None,
        "row_id": "",
        "transcript": transcript,
        "transcript_status": transcript_status,
        "recognition_status": recognition_status,
        "field_status": field_status,
        "split": split,
        "assigned_to": assigned_to,
        "source": "existing_ocr_review_candidate",
        "source_crop_id": str(record.get("id") or record.get("crop_id") or ""),
        "confidence": record.get("confidence"),
        "updated_at": "",
        "history": [],
    }


def provider_key(row: dict[str, str]) -> str:
    tax = re.sub(r"\D", "", row.get("seller_tax_code", row.get("tax_code", "")))
    if len(tax) in {10, 13, 14}:
        return "tax:" + tax
    value = unicodedata.normalize("NFKD", row.get("source_title", row.get("supplier", "")))
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).upper()
    value = re.sub(r"[^A-Z0-9]", "", value)
    if value in {"PRESENT", "LOCALVIETNAMESEINVOICESOURCE", "UNKNOWN", "NA"} or len(value) < 4:
        return "invoice:" + row["document_id"]
    return "name:" + value


def assign_invoices(rows: list[dict[str, str]]) -> dict[str, str]:
    if len(rows) == 40:
        return {row["document_id"]: ("duy" if index < 20 else "van") for index, row in enumerate(rows)}
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[provider_key(row)].append(row["document_id"])
    n = len(rows)
    targets = {"duy": round(n / 2), "van": n - round(n / 2)}
    loads = {name: 0 for name in ASSIGNEES}
    assignments: dict[str, str] = {}
    for key, ids in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        assignee = min(ASSIGNEES, key=lambda name: (loads[name] / max(targets[name], 1), loads[name], ASSIGNEES.index(name)))
        for invoice_id in ids:
            assignments[invoice_id] = assignee
        loads[assignee] += len(ids)
    return assignments


def read_review_sources(recognition_root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    review_data_path = recognition_root / "automatic_review" / "review_data.json"
    progress_path = recognition_root / "automatic_review" / "manual_review_progress.json"
    if not review_data_path.is_file():
        raise FileNotFoundError(f"Thiếu OCR review data: {review_data_path}")
    records = json.loads(review_data_path.read_text(encoding="utf-8"))
    progress: dict[str, dict[str, Any]] = {}
    if progress_path.is_file():
        content = json.loads(progress_path.read_text(encoding="utf-8"))
        for item in content.get("annotations", []):
            crop_id = str(item.get("crop_id") or "")
            if crop_id:
                progress[crop_id] = item
    return records, progress


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def bootstrap(source_manifest: Path, source_pdf_dir: Path, recognition_root: Path, output_root: Path = ROOT) -> dict[str, Any]:
    with source_manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    active = [row for row in source_rows if row.get("review_status") == "included"]
    if not active:
        raise ValueError("Manifest không có hóa đơn included.")
    records, progress = read_review_sources(recognition_root)
    record_by_pdf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    split_by_pdf: dict[str, set[str]] = defaultdict(set)
    for record in records:
        name = Path(str(record.get("pdf_path") or record.get("pdf") or "")).name
        if name:
            record_by_pdf[name].append(record)
            if record.get("split") in {"train", "val", "test"}:
                split_by_pdf[name].add(str(record["split"]))
    assignments = assign_invoices(active)
    invoices: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    annotation_root = output_root / "data" / "annotations" / "by_invoice"
    pdf_out = output_root / "data" / "pdfs"
    pdf_out.mkdir(parents=True, exist_ok=True)
    annotation_counts: Counter[str] = Counter()
    skipped: list[dict[str, str]] = []

    for row in active:
        pdf_name = Path(row["filename"]).name
        source_pdf = source_pdf_dir / pdf_name
        if not source_pdf.is_file():
            raise FileNotFoundError(f"PDF trong manifest không tồn tại: {source_pdf}")
        actual_sha = sha256_file(source_pdf)
        expected_sha = str(row.get("sha256") or "").lower()
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(f"SHA-256 sai cho {pdf_name}: manifest và PDF không khớp.")
        target_pdf = pdf_out / pdf_name
        if target_pdf.exists():
            if sha256_file(target_pdf) != actual_sha:
                raise ValueError(f"Từ chối ghi đè PDF repo khác checksum: {target_pdf}")
        else:
            temp_pdf = target_pdf.with_suffix(target_pdf.suffix + ".tmp")
            shutil.copy2(source_pdf, temp_pdf)
            temp_pdf.replace(target_pdf)

        invoice_id = str(row.get("document_id") or Path(pdf_name).stem)
        existing_split = split_by_pdf.get(pdf_name, set())
        if len(existing_split) > 1:
            raise ValueError(f"Một hóa đơn xuất hiện ở nhiều split: {pdf_name} {sorted(existing_split)}")
        split = next(iter(existing_split), "train")
        assigned_to = assignments[invoice_id]
        existing_path = annotation_root / f"{invoice_id}.json"
        if existing_path.exists():
            current = json.loads(existing_path.read_text(encoding="utf-8"))
            if current.get("pdf_sha256") != actual_sha:
                raise ValueError(f"Annotation cũ trỏ tới checksum khác: {invoice_id}")
        else:
            current = {
                "schema_version": 1,
                "invoice_id": invoice_id,
                "pdf": f"data/pdfs/{pdf_name}",
                "pdf_sha256": actual_sha,
                "page_count": int(row.get("page_count") or 0),
                "split": split,
                "assigned_to": assigned_to,
                "annotations": [],
                "updated_at": "",
            }
        current["split"] = split
        current["assigned_to"] = assigned_to
        by_id = {str(item.get("annotation_id")): item for item in current.get("annotations", [])}
        for record in record_by_pdf.get(pdf_name, []):
            crop_id = str(record.get("id") or record.get("crop_id") or "")
            page_rel = str(record.get("page_image") or "").lstrip("/")
            page_image = recognition_root / page_rel
            if not crop_id or not record.get("geometry_valid") or not page_image.is_file():
                skipped.append({"invoice_id": invoice_id, "crop_id": crop_id, "reason": "missing_id_geometry_or_page_image"})
                continue
            try:
                page_size = png_size(page_image)
                incoming = candidate_annotation(
                    record,
                    progress.get(crop_id),
                    invoice_id=invoice_id,
                    pdf_name=pdf_name,
                    pdf_sha256=actual_sha,
                    page_size=page_size,
                    split=split,
                    assigned_to=assigned_to,
                )
            except (OSError, ValueError, TypeError) as exc:
                skipped.append({"invoice_id": invoice_id, "crop_id": crop_id, "reason": str(exc)})
                continue
            existing = by_id.get(crop_id)
            if existing:
                # Existing human field edits win; only fill missing provenance fields.
                merged = {**incoming, **existing}
                for key in ("source", "source_crop_id", "confidence", "recognition_status", "transcript_status"):
                    merged.setdefault(key, incoming[key])
                by_id[crop_id] = merged
            else:
                by_id[crop_id] = incoming
            annotation_counts[invoice_id] += 1
        current["annotations"] = sorted(by_id.values(), key=lambda item: (int(item.get("page", 1)), str(item.get("annotation_id"))))
        _write_json_atomic(existing_path, current)
        try:
            page_count = int(row.get("page_count") or 0)
        except ValueError:
            page_count = 0
        invoices.append({
            "invoice_id": invoice_id,
            "pdf": f"data/pdfs/{pdf_name}",
            "filename": pdf_name,
            "pdf_sha256": actual_sha,
            "page_count": page_count,
            "split": split,
            "assigned_to": assigned_to,
            "supplier": row.get("seller_tax_code") or row.get("source_title") or "",
            "source_url": row.get("source_url") or "",
            "review_status": row.get("review_status") or "included",
            "annotation_count": len(current["annotations"]),
        })
        assignment_rows.append({"invoice_id": invoice_id, "pdf": pdf_name, "assigned_to": assigned_to, "split": split, "sha256": actual_sha})

    manifest_headers = ["invoice_id", "filename", "pdf", "pdf_sha256", "page_count", "split", "assigned_to", "supplier", "source_url", "review_status", "annotation_count"]
    _write_csv(output_root / "data" / "manifests" / "invoice_manifest.csv", manifest_headers, invoices)
    _write_csv(output_root / "data" / "manifests" / "assignment_manifest.csv", ["invoice_id", "pdf", "assigned_to", "split", "sha256"], assignment_rows)
    if skipped:
        _write_csv(output_root / "data" / "manifests" / "bootstrap_skipped.csv", ["invoice_id", "crop_id", "reason"], skipped)
    snapshot = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_manifest": source_manifest.name,
        "source_manifest_sha256": json_sha256(source_manifest),
        "source_pdf_directory": "external input path omitted",
        "recognition_review_data_sha256": json_sha256(recognition_root / "automatic_review" / "review_data.json"),
        "recognition_progress_sha256": json_sha256(recognition_root / "automatic_review" / "manual_review_progress.json"),
        "included_invoice_count": len(invoices),
        "ocr_candidate_count": sum(annotation_counts.values()),
        "skipped_candidate_count": len(skipped),
        "assignments": {name: sum(1 for row in assignment_rows if row["assigned_to"] == name) for name in ASSIGNEES},
        "note": "OCR/text recognition provenance is separate from field/layout review. Imported candidates start with field_status=needs_review unless rejected.",
    }
    _write_json_atomic(output_root / "data" / "manifests" / "source_snapshot.json", snapshot)
    return snapshot


def main() -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="Copy verified source PDFs and OCR candidates into this repository.")
    parser.add_argument("--source-manifest", type=Path, required=True, help="Path to the source invoice manifest")
    parser.add_argument("--pdf-dir", type=Path, required=True, help="Path to the source PDF directory")
    parser.add_argument("--recognition-root", type=Path, required=True, help="Path to the existing recognition dataset")
    args = parser.parse_args()
    snapshot = bootstrap(args.source_manifest, args.pdf_dir, args.recognition_root)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
