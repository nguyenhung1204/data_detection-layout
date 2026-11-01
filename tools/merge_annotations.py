from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools.validate_dataset import ROOT, validate
from app.server import validate_annotation
from app.console import configure_console

CORE = ("bbox_px", "bbox_norm", "page", "field_key", "layout_key", "row_id", "transcript", "field_status")


def merge_package(package: Path, root: Path = ROOT) -> dict:
    if package.is_file() and package.suffix.casefold() == ".zip":
        with tempfile.TemporaryDirectory(prefix="invoice-label-package-") as temp_dir:
            extracted = Path(temp_dir)
            total_size = 0
            with zipfile.ZipFile(package) as archive:
                for member in archive.infolist():
                    name = Path(member.filename)
                    if name.is_absolute() or ".." in name.parts or member.is_dir():
                        raise ValueError(f"Đường dẫn không an toàn trong ZIP: {member.filename}")
                    allowed = len(name.parts) == 2 and name.parts[0] == "by_invoice" and name.suffix == ".json"
                    allowed = allowed or member.filename in {"assignment_manifest.csv", "package_manifest.json", "README.txt"}
                    if not allowed:
                        raise ValueError(f"File không được phép trong ZIP: {member.filename}")
                    total_size += member.file_size
                    if member.file_size > 50 * 1024 * 1024 or total_size > 500 * 1024 * 1024:
                        raise ValueError("ZIP nhãn vượt giới hạn kích thước giải nén.")
                    destination = extracted / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(member))
            return merge_package(extracted, root)
    source = package / "data" / "annotations" / "by_invoice"
    if not source.is_dir():
        source = package / "by_invoice"
    if not source.is_dir():
        raise FileNotFoundError("Gói phải chứa data/annotations/by_invoice hoặc by_invoice.")
    target_dir = root / "data" / "annotations" / "by_invoice"
    with (root / "data" / "manifests" / "invoice_manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        merge_invoices = {row["invoice_id"]: row for row in csv.DictReader(stream)}
    backup = root / "data" / "manifests" / f"pre_merge_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    merged, unchanged, conflicts, unknown = [], [], [], []
    manifest_ids = {p.stem for p in target_dir.glob("*.json")}
    for incoming_path in sorted(source.glob("*.json")):
        invoice_id = incoming_path.stem
        if invoice_id not in manifest_ids:
            unknown.append(invoice_id); continue
        target_path = target_dir / incoming_path.name
        local = json.loads(target_path.read_text(encoding="utf-8"))
        incoming = json.loads(incoming_path.read_text(encoding="utf-8"))
        if local.get("pdf_sha256") != incoming.get("pdf_sha256") or local.get("invoice_id") != invoice_id:
            conflicts.append({"invoice_id": invoice_id, "reason": "checksum_or_invoice_mismatch"}); continue
        local_map = {a["annotation_id"]: a for a in local.get("annotations", [])}
        incoming_map = {a["annotation_id"]: a for a in incoming.get("annotations", [])}
        conflict_for_invoice = []
        candidate = dict(local)
        new_map = dict(local_map)
        invoice_actions = []
        for ann_id, remote in incoming_map.items():
            try:
                remote = validate_annotation(invoice_id, dict(remote), merge_invoices)
            except (ValueError, KeyError) as exc:
                conflict_for_invoice.append({"annotation_id": ann_id, "reason": "invalid_annotation", "detail": str(exc)})
                continue
            current = local_map.get(ann_id)
            if current is None:
                new_map[ann_id] = remote; invoice_actions.append({"invoice_id": invoice_id, "annotation_id": ann_id, "action": "added"}); continue
            if all(current.get(k) == remote.get(k) for k in CORE):
                unchanged.append({"invoice_id": invoice_id, "annotation_id": ann_id}); continue
            local_edited = bool(current.get("updated_at"))
            remote_edited = bool(remote.get("updated_at"))
            if local_edited and remote_edited:
                conflict_for_invoice.append({"annotation_id": ann_id, "reason": "both_versions_edited", "local": {k: current.get(k) for k in CORE}, "incoming": {k: remote.get(k) for k in CORE}})
            elif remote_edited:
                new_map[ann_id] = remote; invoice_actions.append({"invoice_id": invoice_id, "annotation_id": ann_id, "action": "updated_from_package"})
        if conflict_for_invoice:
            conflicts.append({"invoice_id": invoice_id, "items": conflict_for_invoice})
            continue
        if new_map != local_map:
            shutil.copy2(target_path, backup / target_path.name)
            candidate["annotations"] = sorted(new_map.values(), key=lambda a: (int(a.get("page", 1)), str(a.get("annotation_id"))))
            tmp = target_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(target_path)
        merged.extend(invoice_actions)
        omitted = set(local_map) - set(incoming_map)
        if omitted:
            conflicts.append({"invoice_id": invoice_id, "reason": "omitted_annotations_not_deleted", "annotation_ids": sorted(omitted)})
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "merged": merged, "unchanged": unchanged, "conflicts": conflicts, "unknown_invoices": unknown, "backup_dir": str(backup)}
    (root / "data" / "manifests" / "last_merge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if validate(root)["errors"]:
        report["validation"] = validate(root)
    return report


def main():
    configure_console()
    parser = argparse.ArgumentParser(description="Merge annotator ZIP/folder without silently overwriting conflicts.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = merge_package(args.package, args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
