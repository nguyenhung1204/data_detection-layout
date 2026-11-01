from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PDF_DIR = DATA / "pdfs"
ANNOTATION_DIR = DATA / "annotations" / "by_invoice"
MANIFEST = DATA / "manifests" / "invoice_manifest.csv"
SCHEMA = json.loads((ROOT / "schema" / "fields.json").read_text(encoding="utf-8"))
CACHE = ROOT / ".cache" / "pages"
