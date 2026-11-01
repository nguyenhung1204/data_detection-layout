# Gán nhãn trường và bố cục hóa đơn

App chạy cục bộ trên Windows để gán bbox, transcript nhìn thấy, khóa trường, vùng bố cục và `row_id` cho các ô cùng dòng hàng. PDF được render trên máy; app không gửi hóa đơn lên mạng. Chạy app không cần Node.js, Docker hay GPU.

## Chạy trên Windows

1. Cài Python 3.11 trở lên.
2. Mở thư mục repo đã clone, nhấp phải `start_labeler.ps1` → **Run with PowerShell**. Hoặc mở PowerShell ở thư mục đó và chạy:

   ```powershell
   Set-ExecutionPolicy -Scope Process Bypass
   .\start_labeler.ps1
   ```

3. Mở `http://127.0.0.1:8767/`. Lần đầu script tạo `.venv` và cài PyPDFium2; để dừng app, nhấn `Ctrl+C` trong cửa sổ PowerShell.

## Rà và gán nhãn

- Lọc danh sách theo split/người phụ trách/trạng thái. Mở PDF gốc để chọn và sao chép chữ nếu PDF có lớp văn bản; ảnh trang render để vẽ bbox.
- Kéo chuột trên trang để tạo vùng. Bấm vùng để di chuyển/chỉnh transcript, field key, layout class, `row_id` và trạng thái. `Delete` xóa vùng; **Hoàn tác xóa** khôi phục vùng gần nhất; `Ctrl+S` lưu.
- Các vùng PaddleOCR/crop cũ chỉ là gợi ý. Nhãn trường/layout mặc định chưa rà, kể cả khi transcript đã được xác nhận cho bài toán nhận dạng chữ.
- Với bảng hàng, dùng ID số `1`, `2`, `3`…; mọi ô thuộc cùng mặt hàng dùng chung số ID. ID bắt đầu lại từ `1` ở mỗi hóa đơn. Không gán ID cho vùng không thuộc dòng hàng.
- Có thể để trường trống khi chưa chắc; trạng thái `verified` chỉ dùng khi đã đối chiếu PDF.
- **Lịch sử** tìm annotation đã lưu và mở lại đúng trang/vùng. Các thay đổi lưu theo từng hóa đơn trong `data/annotations/by_invoice/`.

## Dữ liệu và phân công

`data/pdfs/` chứa snapshot các PDF included đã xác minh với manifest nguồn; `data/manifests/` giữ SHA-256, split và phân công. Snapshot hiện có 208 hóa đơn active, chia đều Duy 104 và Vân 104. Chủ repo không cần gán nhãn; chỉ tổng hợp PR/package khi hai bạn hoàn tất. Nếu chạy trên đúng bộ 40 hóa đơn tham chiếu, công cụ dùng Duy 1–20, Vân 21–40. Không chỉnh tay manifest để cùng hóa đơn thuộc hai người.

Mỗi invoice có một JSON riêng để PR dễ review. Người làm clone/fork, chỉ sửa JSON thuộc assignment, rồi gửi PR. Khi cần tổng hợp gói annotations đã tải về, dùng merge tool (xem `CONTRIBUTING.md`). Xung đột hai bản sửa sẽ được báo; merge tool tạo backup trước khi ghi.

## Kiểm tra và export

```powershell
.\.venv\Scripts\python.exe -m tools.validate_dataset
.\.venv\Scripts\python.exe -m tools.validate_assignment
.\.venv\Scripts\python.exe -m tools.export_dataset
```

Export tạo `exports/field_layout_<timestamp>.zip`, tách `verified.jsonl` và `review.jsonl`, kèm CSV, schema và manifests. Đây là dữ liệu annotation tổng quát, **chưa phải config/checkpoint hay gói train PaddleOCR cụ thể**. Việc fine-tune cần xác định task/model và format tương thích sau này. Recognition transcript, detector/layout box và logic gán trường là các nhãn/tác vụ khác nhau.

## Colab

Mở `notebooks/Prepare_Field_Layout_Data_Colab.ipynb`, chạy các ô theo thứ tự. Notebook clone repo, chốt SHA commit lúc bắt đầu, mount Drive, kiểm tra checksum/schema/split và lưu validation/export vào thư mục timestamp riêng. Notebook không fine-tune và không ghi ngược vào repo.

## Giới hạn và dữ liệu

- Bộ 208 hóa đơn là snapshot của manifest ngày 02/11/2026; kiểm tra lại nguồn trước khi cập nhật.
- Nhiều invoice source URL còn trống trong manifest nguồn; provenance được giữ như có sẵn, không tự bịa nguồn/license.
- `field_status=verified` là xác nhận trường/layout; `transcript_status=verified` chỉ xác nhận chữ. Không suy ra cái này từ cái kia.
- Bộ 40 hóa đơn đã tham gia đánh giá OCR trước đây; không xem chúng là tập test độc lập.
- Repo public có chứa dữ liệu hóa đơn theo yêu cầu của chủ dữ liệu. Chỉ sử dụng/chia sẻ theo quyền và điều kiện nguồn gốc tương ứng.

Xem `DATA_SCHEMA.md`, `CONTRIBUTING.md`, `COLAB_GUIDE.md` và `DATA_LICENSE.md`.
