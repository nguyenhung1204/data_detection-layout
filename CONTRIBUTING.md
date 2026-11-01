# Hướng dẫn cộng tác gán nhãn

## Duy và Vân

1. Fork repo public hoặc clone repo theo quyền truy cập.
2. Chạy app theo `README.md`; lọc theo tên mình trong mục **Người phụ trách**. Không chỉnh hóa đơn của người còn lại.
3. Đối chiếu từng vùng với PDF. Gán đúng `field_key`, `layout_key`, transcript hiển thị và `row_id` cho các ô cùng một dòng hàng. OCR cũ chỉ là gợi ý.
4. Lưu thường xuyên; dữ liệu nằm trong `data/annotations/by_invoice/<invoice_id>.json`.
5. Commit từng nhóm nhỏ vào nhánh riêng, không thay PDF/manifest/schema, rồi mở PR. Trong mô tả ghi invoice ID đã sửa, số vùng xác nhận và câu hỏi còn lại.

Phân công lấy từ `data/manifests/assignment_manifest.csv`; snapshot hiện tại gồm 208 hóa đơn, chia đều Duy 104 và Vân 104. Chủ repo không nhận phần gán nhãn. Dùng manifest làm nguồn chuẩn, không tự chia lại.

## Chủ repo: nhận và tổng hợp kết quả

Chủ repo không cần gán nhãn. Chỉ review/merge PR hoặc package sau khi Duy và Vân hoàn tất.

Nếu annotator gửi ZIP các file JSON, giải nén vào thư mục theo cấu trúc `data/annotations/by_invoice/*.json`, rồi chạy:

```powershell
python -m tools.merge_annotations C:\path\to\annotator-package
```

Merge kiểm checksum, invoice ID, schema fields và tọa độ. Nếu annotation cùng ID đã bị sửa ở cả hai bên, công cụ báo conflict và giữ nguyên file hiện tại. Backup và `data/manifests/last_merge_report.json` được tạo trước/sau lượt merge. Trường hợp annotation bị lược khỏi package không được hiểu là lệnh xóa.

Nếu dùng PR Git, xem diff JSON theo invoice, chạy `tools.validate_dataset` và `tools.validate_assignment`, rồi merge PR qua GitHub. Không force push hoặc reset nhánh cộng tác viên.

## Đóng góp dữ liệu

- Không đưa credentials, `.env`, logs có dữ liệu nhạy cảm hoặc checkpoint vào commit.
- Không thay PDF; checksum ở manifest bắt buộc giữ nguyên.
- Không chuyển một invoice sang split khác trong PR annotation.
- Khi bất đồng, mở issue/PR comment thay vì tự chọn ground truth.
