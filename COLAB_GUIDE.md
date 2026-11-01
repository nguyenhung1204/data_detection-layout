# Chạy notebook kiểm tra trên Google Colab

1. Mở `notebooks/Prepare_Field_Layout_Data_Colab.ipynb` từ repo GitHub bằng Colab hoặc tải notebook lên Drive.
2. Chọn **Runtime → Run all**. Cho phép Google Drive mount khi Colab hỏi.
3. Notebook clone `main`, ghi SHA commit được giải quyết tại đầu lượt chạy và dùng checkout detached đúng SHA đó trong suốt lượt kiểm tra.
4. Kết quả được ghi vào `MyDrive/FieldLayoutLabeler/runs/<timestamp>/`; notebook không ghi lên dữ liệu nguồn trong Drive/repo.
5. Mở `validation.json` để xem lỗi/warning; `field_layout_export.zip` chứa nhãn verified/review tách riêng.

Notebook chỉ kiểm tra schema/checksum/split và export. Không cài PaddleOCR/PaddlePaddle, không tải model và không fine-tune. Nếu sau này xuất dữ liệu train, cần chọn rõ tác vụ, model/layout framework và format chính thức trước.
