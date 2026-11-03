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

- Lọc danh sách theo split/người phụ trách/trạng thái. Kéo chuột trên ảnh PDF để tự tạo vùng crop; chọn vùng để chỉnh lại kích thước hoặc di chuyển.
- Chỉ gán 11 trường mục tiêu trong bộ chọn **Trường cần nhận diện**. Khung nên ôm sát giá trị, không lấy nhãn mô tả hoặc tiêu đề cột; loại vùng bố cục được suy ra tự động từ trường.
- Để đỡ gõ transcript, sau khi vẽ/chọn vùng bấm **Chép chữ trong vùng PDF vào transcript (bản nháp)**. App lấy lớp chữ PDF nằm trong vùng rồi điền vào transcript; nó không tự xác nhận nhãn. Đọc lại trên PDF trước khi đổi trạng thái sang `verified`. Nếu PDF là ảnh scan hoặc vùng không có lớp chữ, app báo để bạn chép từ PDF gốc hoặc nhập theo ảnh.
- Bấm **Áp dụng** để cập nhật transcript, trường, loại vùng được suy ra tự động, `row_id` và trạng thái; `Delete` xóa vùng; **Hoàn tác xóa** khôi phục vùng gần nhất; `Ctrl+S` lưu. Nút lấy chữ PDF cũng chỉ tạo thay đổi nháp; cần bấm **Lưu nhãn** để lưu vào annotation.
- Bộ active hiện có 4,076 vùng trên 188 hóa đơn: 2,627 vùng thủ công và 1,449 crop đề xuất tự động; `field_status` hiện là {'verified': 4076}. 20 hóa đơn không có vùng đã được loại khỏi active; xem `data/manifests/excluded_unannotated_invoices_20261103.csv` và `reports/dataset_readiness_20261103.md`. Transcript là trạng thái riêng, không tự được xác nhận theo field/layout.
- Với bảng hàng, dùng ID số `1`, `2`, `3`…; mọi ô thuộc cùng mặt hàng dùng chung số ID. ID bắt đầu lại từ `1` ở mỗi hóa đơn. Không gán ID cho vùng không thuộc dòng hàng.
- Có thể để trường trống khi chưa chắc; trạng thái `verified` chỉ dùng khi đã đối chiếu PDF.
- **Lịch sử** tìm annotation đã lưu và mở lại đúng trang/vùng. Các thay đổi lưu theo từng hóa đơn trong `data/annotations/by_invoice/`.
- Khi hoàn tất phần được giao, chọn **Duy** hoặc **Vân** ở bộ lọc **Người phụ trách**, rồi bấm **Tải ZIP phần của tôi**. ZIP chỉ có annotation JSON và manifest của người đó, không lặp lại PDF; gửi nguyên ZIP cho bạn tổng hợp.

## Dữ liệu và phân công

`data/pdfs/` chứa 188 PDF active đã xác minh checksum; manifest giữ SHA-256, split và phân công. Hiện có 4,076 vùng (2,627 manual, 1,449 auto proposal), toàn bộ `field_status=verified`; transcript vẫn là nhãn độc lập. Phân công active hiện tại: Duy 91 hóa đơn, Vân 97 hóa đơn. 20 hóa đơn 0 vùng đã được loại; lịch sử loại ở manifest riêng. Các báo cáo import cũ chỉ phản ánh thời điểm import; trạng thái hiện tại nằm trong `reports/dataset_readiness_20261103.md`.

Mỗi invoice có một JSON riêng. Người làm có thể gửi ZIP trực tiếp từ app; chủ repo chạy merge tool lần lượt cho từng ZIP (xem `CONTRIBUTING.md`). Xung đột hai bản sửa sẽ được báo; merge tool tạo backup trước khi ghi.

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

- Nguồn ban đầu có 208 hóa đơn; active hiện có 188 sau khi loại 20 hóa đơn không có vùng annotation. `data/manifests/source_snapshot.json` là snapshot nhập dữ liệu lịch sử, còn `invoice_manifest.csv` là danh sách active hiện tại.
- Nhiều invoice source URL còn trống trong manifest nguồn; provenance được giữ như có sẵn, không tự bịa nguồn/license.
- `field_status=verified` là xác nhận trường/layout; `transcript_status=verified` chỉ xác nhận chữ. Không suy ra cái này từ cái kia.
- Bộ 40 hóa đơn đã tham gia đánh giá OCR trước đây; không xem chúng là tập test độc lập.
- Repo public có chứa dữ liệu hóa đơn theo yêu cầu của chủ dữ liệu. Chỉ sử dụng/chia sẻ theo quyền và điều kiện nguồn gốc tương ứng.

Xem `DATA_SCHEMA.md`, `CONTRIBUTING.md`, `COLAB_GUIDE.md` và `DATA_LICENSE.md`.
