# Nhập crop tự động đã được Duy xác nhận

- Thời gian UTC: 2026-11-03T09:08:10+00:00
- ZIP nguồn: `data_detection-layout-main.zip`
- SHA-256 ZIP: `26269f103faed4326f8c23b1124ad37b3d420cf5515be1565e88cc46d8303c46`
- Đã nhập: **1,449** annotation thuộc **84** hóa đơn.
- Nguồn được giữ nguyên: `automatic_crop_proposal`; `field_status=verified`; `assigned_to=duy`.
- Theo trường: `{"invoice_date": 80, "invoice_number": 76, "item_description": 141, "line_total": 238, "quantity": 240, "seller_name": 64, "seller_tax_code": 61, "tax_rate": 53, "total_amount": 55, "unit": 195, "unit_price": 246}`
- Crop có `row_id`: 1,113.
- Bỏ ngoài active: 110 crop `needs_review`, 1 crop `rejected`, và các annotation OCR review cũ.
- Trùng hình học với 522 vùng manual Duy: 8.013 cặp được so trong cùng hóa đơn/trang; 3 cặp có giao nhau rất nhỏ, không cặp nào IoU ≥ 0,5 hoặc bbox trùng hoàn toàn.
- Tổng sau nhập: 4,075 vùng; Duy 1,971, Vân 2,104.
- Kiểm tra schema/checksum/tọa độ: **đạt**, 0 lỗi, 1 cảnh báo.
- Bản sao trước nhập: `data\manifests\pre_auto_crop_import_20261103_090810`.
