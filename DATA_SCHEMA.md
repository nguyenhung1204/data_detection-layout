# Schema annotation

`schema/fields.json` là nguồn chuẩn khóa field/layout và phiên bản schema. Không đổi khóa field âm thầm; khi cần thay đổi tăng `schema_version` và ghi migration.

## Khóa trường

| Nhóm | Khóa | Hiển thị |
|---|---|---|
| Header | `invoice_number` | Số hóa đơn |
| Header | `invoice_date` | Ngày hóa đơn |
| Header | `seller_tax_code` | MST bên bán |
| Header | `seller_name` | Tên bên bán / nhà cung cấp |
| Header | `total_amount` | Tổng tiền hóa đơn |
| Item | `item_description` | Tên mặt hàng |
| Item | `unit` | Đơn vị tính |
| Item | `quantity` | Số lượng |
| Item | `unit_price` | Đơn giá |
| Item | `tax_rate` | Thuế suất |
| Item | `line_total` | Thành tiền dòng |

Các khóa lấy từ schema trong `PaddleOCR_Field_Improvement/data/unpacked/40HD.json`. Không thêm trường buyer nếu schema hiện tại không có.

## Annotation record

- `annotation_id`, `invoice_id`, `pdf`, `pdf_sha256`: định danh ổn định và nguồn.
- `page`: số trang bắt đầu từ 1.
- `bbox_px`: `[x0,y0,x1,y1]` trên `page_size_px`; gốc tọa độ góc trái trên.
- `bbox_norm`: cùng bbox chia theo chiều rộng/cao, khoảng 0–1.
- `transcript`: nội dung nhìn thấy trong vùng; không tự sửa dự đoán OCR.
- `field_key`: một khóa trong nhóm header/item hoặc `null`.
- `layout_key`: một class như `invoice_header`, `seller_block`, `buyer_block`, `item_table`, `totals`, `signature_stamp`, `other` hoặc `null`.
- `row_id`: định danh dòng hàng; các cell cùng mặt hàng dùng chung ID.
- `recognition_status`: trạng thái nhãn nhận dạng chữ cũ; tách biệt với field/layout.
- `transcript_status`: xác nhận transcript; không kéo theo xác nhận field.
- `field_status`: `needs_review`, `verified`, hoặc `rejected` cho nhãn field/layout.
- `split`: `train`, `val`, `test` theo invoice.
- `assigned_to`: `duy`, `van`, `owner_review`.
- `source`, `source_crop_id`, `confidence`, `updated_at`, `history`: provenance và lịch sử.

## Export

`verified.jsonl` chứa record `field_status=verified`; `review.jsonl` chứa các trạng thái còn lại. `annotations.csv` là bảng phẳng với các mảng tọa độ JSON-encoded. Hiện tại export được thiết kế trung lập theo model; không tuyên bố tương thích huấn luyện detection/layout của PaddleOCR nếu chưa chốt model/config.
