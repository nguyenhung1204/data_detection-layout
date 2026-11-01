from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from app.config import ANNOTATION_DIR, CACHE, DATA, MANIFEST, PDF_DIR, ROOT, SCHEMA
from app.console import configure_console
from tools.bootstrap_dataset import png_size, sha256_file

MAX_BODY = 12 * 1024 * 1024
FIELDS = {key for group in SCHEMA["field_groups"].values() for key in group}
LAYOUTS = set(SCHEMA["layout_classes"])
STATUSES = set(SCHEMA["annotation_statuses"])


def load_invoices():
    with MANIFEST.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


INVOICES = {row["invoice_id"]: row for row in load_invoices()}


def safe_annotation_path(invoice_id: str) -> Path:
    if invoice_id not in INVOICES or not re.fullmatch(r"[A-Za-z0-9_-]+", invoice_id):
        raise ValueError("Mã hóa đơn không hợp lệ.")
    return ANNOTATION_DIR / f"{invoice_id}.json"


def load_annotation(invoice_id: str):
    path = safe_annotation_path(invoice_id)
    return json.loads(path.read_text(encoding="utf-8"))


def validate_annotation(invoice_id: str, item: dict, invoices: dict | None = None) -> dict:
    invoices = invoices or INVOICES
    invoice = invoices.get(invoice_id)
    if not invoice:
        raise ValueError("Mã hóa đơn không có trong manifest.")
    if not isinstance(item, dict):
        raise ValueError("Nhãn phải là object JSON.")
    ann_id = str(item.get("annotation_id", ""))
    if not ann_id or len(ann_id) > 200:
        raise ValueError("Thiếu annotation_id hợp lệ.")
    if item.get("invoice_id") != invoice_id:
        raise ValueError("invoice_id không khớp hồ sơ đang lưu.")
    if item.get("pdf_sha256") != invoice["pdf_sha256"]:
        raise ValueError("Checksum PDF đã thay đổi; từ chối lưu nhãn cũ.")
    field = item.get("field_key") or None
    layout = item.get("layout_key") or None
    if field and field not in FIELDS:
        raise ValueError(f"Khóa trường không có trong schema: {field}")
    if layout and layout not in LAYOUTS:
        raise ValueError(f"Loại vùng không có trong schema: {layout}")
    status = item.get("field_status", "needs_review")
    if status not in STATUSES:
        raise ValueError("Trạng thái nhãn không hợp lệ.")
    try:
        page = int(item.get("page", 0))
        px = list(map(float, item.get("bbox_px", [])))
        norm = list(map(float, item.get("bbox_norm", [])))
        size = list(map(int, item.get("page_size_px", [])))
    except (TypeError, ValueError):
        raise ValueError("Trang hoặc tọa độ không hợp lệ.")
    if page < 1 or page > int(invoice.get("page_count") or 0) or len(px) != 4 or len(norm) != 4 or len(size) != 2 or min(size) < 1:
        raise ValueError("Thiếu trang/kích thước/toạ độ bbox.")
    x0, y0, x1, y1 = px
    if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0 or x1 > size[0] or y1 > size[1]:
        raise ValueError("BBox pixel nằm ngoài trang hoặc rỗng.")
    nx0, ny0, nx1, ny1 = norm
    if min(norm) < 0 or max(norm) > 1 or nx1 <= nx0 or ny1 <= ny0:
        raise ValueError("BBox chuẩn hóa phải nằm trong khoảng 0–1.")
    if any(abs(px[i] / size[i % 2] - norm[i]) > 0.005 for i in range(4)):
        raise ValueError("Tọa độ pixel và chuẩn hóa không khớp.")
    item["pdf"] = invoice["filename"]
    item["split"] = invoice["split"]
    item["assigned_to"] = invoice["assigned_to"]
    item["field_key"] = field
    item["layout_key"] = layout
    item["field_status"] = status
    item["transcript"] = str(item.get("transcript", ""))
    item["row_id"] = str(item.get("row_id", ""))
    return item


def atomic_save(invoice_id: str, payload: dict):
    path = safe_annotation_path(invoice_id)
    current = load_annotation(invoice_id)
    if payload.get("pdf_sha256") != current.get("pdf_sha256") or payload.get("pdf_sha256") != INVOICES[invoice_id]["pdf_sha256"]:
        raise ValueError("Checksum PDF không khớp; không lưu để tránh ghi nhầm hóa đơn.")
    annotations = payload.get("annotations")
    if not isinstance(annotations, list) or len(annotations) > 10000:
        raise ValueError("Danh sách nhãn không hợp lệ.")
    ids, cleaned = set(), []
    old = {x["annotation_id"]: x for x in current.get("annotations", [])}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for raw in annotations:
        item = validate_annotation(invoice_id, dict(raw))
        if item["annotation_id"] in ids:
            raise ValueError("annotation_id bị trùng trong cùng hóa đơn.")
        ids.add(item["annotation_id"])
        previous = old.get(item["annotation_id"])
        history = list(previous.get("history", [])) if previous else list(item.get("history", []))
        if previous and any(previous.get(k) != item.get(k) for k in ("bbox_px", "field_key", "layout_key", "row_id", "transcript", "field_status")):
            history.append({"at": now, "snapshot": {k: previous.get(k) for k in ("bbox_px", "field_key", "layout_key", "row_id", "transcript", "field_status")}})
            history = history[-20:]
        item["history"] = history
        item["updated_at"] = now
        cleaned.append(item)
    current["annotations"] = cleaned
    current["updated_at"] = now
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(current, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return current


def render_page(invoice_id: str, page_number: int, dpi: int = 300) -> tuple[Path, tuple[int, int]]:
    if invoice_id not in INVOICES or page_number < 1:
        raise ValueError("Hóa đơn/trang không hợp lệ.")
    pdf_path = (PDF_DIR / Path(INVOICES[invoice_id]["pdf"]).name).resolve()
    if pdf_path.parent != PDF_DIR.resolve() or not pdf_path.is_file():
        raise ValueError("Không tìm thấy PDF trong dữ liệu đã kiểm tra.")
    if sha256_file(pdf_path) != INVOICES[invoice_id]["pdf_sha256"]:
        raise ValueError("Checksum PDF sai; render bị chặn.")
    CACHE.mkdir(parents=True, exist_ok=True)
    output = CACHE / f"{invoice_id}_{page_number}_{dpi}.png"
    if not output.exists():
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError("Chưa cài phụ thuộc. Chạy start_labeler.ps1 trước.") from exc
        pdf = pdfium.PdfDocument(str(pdf_path))
        if page_number > len(pdf):
            raise ValueError("Số trang vượt quá số trang PDF.")
        bitmap = pdf[page_number - 1].render(scale=dpi / 72)
        bitmap.to_pil().save(output, format="PNG")
        pdf.close()
    return output, png_size(output)


class Handler(BaseHTTPRequestHandler):
    server_version = "FieldLayoutLabeler/1.0"

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def send_json(self, code, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 2 or length > MAX_BODY:
            raise ValueError("Kích thước dữ liệu gửi không hợp lệ.")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/schema":
                return self.send_json(200, SCHEMA)
            if path == "/api/invoices":
                query = parse_qs(parsed.query)
                q = query.get("q", [""])[0].casefold()
                split = query.get("split", [""])[0]
                status = query.get("status", [""])[0]
                assignee = query.get("assignee", [""])[0]
                rows = []
                for row in INVOICES.values():
                    if split and row["split"] != split: continue
                    if assignee and row["assigned_to"] != assignee: continue
                    if q and q not in (row["invoice_id"] + " " + row["filename"] + " " + row.get("supplier", "")).casefold(): continue
                    doc = load_annotation(row["invoice_id"])
                    anns = doc.get("annotations", [])
                    counts = {key: sum(1 for a in anns if a.get("field_status") == key) for key in STATUSES}
                    if status and counts.get(status, 0) == 0: continue
                    rows.append({**row, "annotation_count": len(anns), "counts": counts})
                return self.send_json(200, {"invoices": rows, "total": len(rows)})
            match = re.fullmatch(r"/api/invoices/([A-Za-z0-9_-]+)", path)
            if match:
                inv = INVOICES.get(match.group(1))
                if not inv: return self.send_json(404, {"error": "Không có hóa đơn."})
                doc = load_annotation(inv["invoice_id"])
                return self.send_json(200, {"invoice": inv, "annotation": doc})
            match = re.fullmatch(r"/api/pdf/([A-Za-z0-9_-]+)", path)
            if match:
                inv = INVOICES.get(match.group(1))
                if not inv: return self.send_json(404, {"error": "Không có hóa đơn."})
                pdf_path = (PDF_DIR / Path(inv["pdf"]).name).resolve()
                if pdf_path.parent != PDF_DIR.resolve() or sha256_file(pdf_path) != inv["pdf_sha256"]:
                    return self.send_json(409, {"error": "Checksum PDF sai; đã chặn truy cập."})
                body = pdf_path.read_bytes()
                self.send_response(200); self.send_header("Content-Type", "application/pdf"); self.send_header("Content-Length", str(len(body))); self.send_header("Content-Disposition", f'inline; filename="{inv["filename"]}"'); self.end_headers(); self.wfile.write(body)
                return
            match = re.fullmatch(r"/api/pages/([A-Za-z0-9_-]+)/([0-9]+)", path)
            if match:
                output, size = render_page(match.group(1), int(match.group(2)))
                body = output.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Page-Width", str(size[0]))
                self.send_header("X-Page-Height", str(size[1]))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/history":
                query = parse_qs(parsed.query)
                q = query.get("q", [""])[0].casefold()
                rows = []
                for inv_id in INVOICES:
                    for item in load_annotation(inv_id).get("annotations", []):
                        haystack = " ".join(str(item.get(k, "")) for k in ("invoice_id", "pdf", "annotation_id", "field_key", "layout_key", "transcript", "row_id", "assigned_to")).casefold()
                        if not q or q in haystack:
                            rows.append({k: item.get(k) for k in ("annotation_id", "invoice_id", "pdf", "page", "bbox_px", "field_key", "layout_key", "row_id", "transcript", "field_status", "updated_at")})
                rows.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
                return self.send_json(200, {"items": rows[:500], "total": len(rows)})
            if path == "/" or path.startswith("/static/"):
                file = (ROOT / "app" / "static" / "index.html").resolve() if path == "/" else (ROOT / "app" / "static" / path.removeprefix("/static/")).resolve()
                static = (ROOT / "app" / "static").resolve()
                if file != (ROOT / "app" / "static" / "index.html").resolve() and static not in file.parents:
                    return self.send_error(404)
                if not file.is_file(): return self.send_error(404)
                data = file.read_bytes()
                ctype = "text/html; charset=utf-8" if file.suffix == ".html" else "text/javascript; charset=utf-8" if file.suffix == ".js" else "text/css; charset=utf-8"
                self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
                return
            self.send_error(404)
        except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def do_PUT(self):
        match = re.fullmatch(r"/api/invoices/([A-Za-z0-9_-]+)", urlparse(self.path).path)
        if not match:
            return self.send_json(404, {"error": "Endpoint không tồn tại."})
        try:
            result = atomic_save(match.group(1), self.read_json())
            self.send_json(200, {"ok": True, "updated_at": result["updated_at"]})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


def main():
    configure_console()
    if os.name == "nt":
        os.environ.setdefault("PYTHONUTF8", "1")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    host, port = "127.0.0.1", int(os.environ.get("LABELER_PORT", "8767"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Gán nhãn layout đang chạy: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Đang dừng app…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
