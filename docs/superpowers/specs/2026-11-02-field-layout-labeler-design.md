# Hóa đơn: gán nhãn layout và trường

## Mục đích

Tạo app local giúp người dùng xác minh vùng chữ trên hóa đơn, gán khóa trường và liên kết các ô cùng dòng hàng. Dữ liệu bổ sung cho pipeline PaddleOCR Recognition đã fine-tune + detection/layout + post-processing gán trường.

## Phạm vi

- Import 208 PDF đang `included` trong `HoaDonBanHang_300/source_manifest.csv`, đối chiếu SHA-256 và sao chép vào repo public hiện có `nguyenhung1204/data_detection-layout`.
- Tận dụng 17.961 hộp OCR hiện có làm candidate vùng chữ. Transcript đã rà thủ công được đánh dấu là verified cho recognition; field/layout label vẫn bắt đầu ở trạng thái needs_review.
- App localhost hiển thị danh sách hóa đơn, PDF trang, hộp vùng, panel gán nhãn, lịch sử, trạng thái lưu.
- Một file annotation trên mỗi hóa đơn; hỗ trợ export/import, chia assignment, merge có phát hiện conflict.
- Notebook Colab clone repo public theo commit, validate manifest/schema, tạo report và export vào Google Drive.
- Không huấn luyện model; không sửa dữ liệu nguồn hoặc app recognition.

## Cách tiếp cận

1. Sửa/mở rộng app recognition 40 hóa đơn: không chọn vì schema và phạm vi app chỉ phục vụ crop-transcript recognition, có nguy cơ trộn dữ liệu và tiến độ cũ.
2. App Flask/SPA mới: có thêm framework không cần thiết và tạo phụ thuộc cài đặt.
3. **App độc lập trong `field_layout_labeler` dùng Python `ThreadingHTTPServer`, SQLite/JSON per invoice, vanilla JS canvas và PyPDFium2 (đề xuất/chọn).** Giữ app cũ nguyên vẹn; phụ thuộc runtime tối thiểu; annotation theo hóa đơn hoạt động tốt với fork/PR.

## Thiết kế đã chọn

- UI ba vùng: danh sách/search/filter hóa đơn; trang PDF có lớp canvas thao tác bbox; panel thuộc tính vùng, danh sách annotation, lịch sử.
- Render PDF 300 DPI trong máy người dùng và cache vào thư mục ignored. Tọa độ lưu cả pixel và normalized 0–1 theo đúng kích thước ảnh trang.
- Schema trường giữ nguyên từ `data/unpacked/40HD.json`: header `invoice_number`, `invoice_date`, `seller_tax_code`, `seller_name`, `total_amount`; item `item_description`, `unit`, `quantity`, `unit_price`, `tax_rate`, `line_total`. Mọi region có thể để unassigned. Không tự gán field dựa trên OCR.
- Structural labels hỗ trợ `seller_block`, `buyer_block`, `invoice_header`, `item_table`, `totals`, `signature_stamp`, `other`; `row_id` nối các item cell cùng dòng.
- `data/annotations/by_invoice/<invoice_id>.json` là nguồn làm việc/merge; API ghi atomically. Mỗi annotation có provenance, source crop ID, transcript state, field/layout labels, bbox, row ID, review status và timestamps.
- Import từ review_data/progress không sửa nguồn; gắn `recognition_status` riêng và để `field_status=needs_review`. Rejected crop vẫn giữ trạng thái để tra cứu, mặc định không tính là candidate field.
- Dataset split hiện có được dùng nếu mỗi PDF có đúng một split hợp lệ; assignment Duy/Vân/owner tạo riêng và ổn định theo manifest. Nếu đúng 40 hóa đơn, Duy 1–20, Vân 21–40; với tập hiện tại khác 40, chia theo provider group và ghi danh sách assignment.
- Export generic JSONL/CSV plus PaddleOCR DB detection annotation only for confirmed text regions; không tuyên bố PP-Structure training-ready cho tới khi xác định config/model tương thích.
- Repository public đã được chủ repo chấp thuận cho bộ dữ liệu chọn; giữ nguyên quyền truy nguyên nguồn/checksum và ghi nguồn/license.

## Không thuộc phạm vi

- Fine-tune bất kỳ model nào.
- Sửa recognition source/progress, benchmark hoặc MySQL demo.
- Tự động coi OCR prediction là nhãn field/layout chuẩn.
- Tạo repo khác, rewrite Git history, force push hoặc bỏ âm thầm file bị GitHub từ chối.

## Tiêu chí nghiệm thu

- App chạy bằng PowerShell trên localhost, không yêu cầu Node/Docker/GPU.
- Vẽ/sửa/xóa vùng, gán field, transcript, row_id, trạng thái, lưu và reload được.
- Có history, filters, chia assignment, import/export, merge conflict checks.
- Manifest 208 PDF khớp file/checksum; toàn bộ annotation trỏ về invoice/page hợp lệ.
- Colab notebook clone đúng commit, validate và xuất report/data vào Drive.
- PDF nguồn và recognition progress không thay đổi; GitHub public có app/data/docs/notebook, không có secrets.
