from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from app.console import configure_console

ROOT = Path(__file__).resolve().parents[1]


def validate_assignment(path: Path = ROOT / "data" / "manifests" / "assignment_manifest.csv", expected_ids: set[str] | None = None) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    errors = []
    ids = [row.get("invoice_id", "") for row in rows]
    if len(ids) != len(set(ids)): errors.append("Có invoice_id bị phân công nhiều lần.")
    if expected_ids is not None and set(ids) != expected_ids:
        errors.append(f"Tập ID phân công lệch: thiếu={sorted(expected_ids-set(ids))[:10]}, thừa={sorted(set(ids)-expected_ids)[:10]}")
    counts = Counter(row.get("assigned_to") for row in rows)
    invalid = set(counts) - {"duy", "van", "owner_review"}
    if invalid: errors.append(f"Người phụ trách không hợp lệ: {sorted(invalid)}")
    splits: dict[str, set[str]] = {}
    for row in rows:
        if row.get("split") not in {"train", "val", "test"}: errors.append(f"Split không hợp lệ: {row.get('invoice_id')}")
        splits.setdefault(row.get("invoice_id", ""), set()).add(row.get("split", ""))
    if any(len(value) > 1 for value in splits.values()): errors.append("Hóa đơn bị rơi vào nhiều split.")
    return errors


def main():
    configure_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifests" / "assignment_manifest.csv")
    args = parser.parse_args()
    errors = validate_assignment(args.manifest)
    print("\n".join(errors) if errors else "Phân công hợp lệ, không chồng lấn.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
