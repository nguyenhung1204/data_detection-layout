# Đối chiếu dữ liệu nhãn của Duy

- ZIP: `Nhan_duy_annotations (1).zip`
- SHA-256: `f0610faa21b10401e678938448847efaea13f2caca71e55db1e05982387e549a`
- Hóa đơn trong ZIP: 104
- Vùng `manual` do Duy vẽ: 522
- Trong đó đã gán trường: 519 (518 `verified`, 1 `needs_review`)
- Chưa gán trường: 3 (đều `needs_review`; được thêm vào dữ liệu active để rà tiếp)
- Vùng Duy đã gán trường trước đó trong repo: 519; đủ cả 519 ID và nội dung khớp ZIP mới. Có một khác biệt chỉ ở `updated_at`, không phải nhãn/bbox.
- Vùng OCR cũ trong ZIP: 9.121; crop tự động: 1.560. Hai nhóm này không phải vùng Duy tự vẽ nên vẫn bị loại theo lựa chọn trước.

## Phân bố 519 vùng đã gán trường

| Trường | Số vùng |
|---|---:|
| `invoice_date` | 8 |
| `invoice_number` | 12 |
| `item_description` | 150 |
| `line_total` | 43 |
| `quantity` | 52 |
| `seller_name` | 22 |
| `seller_tax_code` | 28 |
| `tax_rate` | 39 |
| `total_amount` | 30 |
| `unit` | 95 |
| `unit_price` | 40 |

## Ba vùng được khôi phục

| Hóa đơn | Annotation ID | Trạng thái | Transcript hiện có |
|---|---|---|---|
| `HD_037` | `region-a89a89c6-f7f0-4cf4-92db-03d0e3882443` | `needs_review` | (trống) |
| `WEB_046` | `region-869d33bc-6653-4f06-946b-7ffcc8da22b4` | `needs_review` | 00000011 |
| `WEB_055` | `region-03c6b3ba-8d79-4813-909a-513bc87a399b` | `needs_review` | Chai |

## Vì sao số crop nhìn ít

Lần import trước chủ ý chỉ giữ vùng Duy/Vân tự vẽ và đã gán trường, nên 519 vùng Duy là đúng. Các 9.121 vùng OCR cũ và 1.560 crop tự động trong ZIP là dữ liệu hệ thống sinh ra, không phải crop thủ công của Duy. Ba vùng manual chưa gán trường trước đây bị lọc mất; lần này đã khôi phục để rà tiếp.

## Phạm vi hóa đơn Duy đã có crop thủ công

- Được giao: 104 hóa đơn.
- Có ít nhất một vùng manual trong ZIP: 73 hóa đơn.
- Không có vùng manual nào trong ZIP: 31 hóa đơn.
- Các hóa đơn chưa có crop manual: `HD_022`, `HD_024`, `HD_026`, `WEB_001`, `WEB_004`, `WEB_011`, `WEB_013`, `WEB_015`, `WEB_022`, `WEB_064`, `WEB_074`, `WEB_075`, `WEB_081`, `WEB_082`, `WEB_247`, `WEB_117`, `WEB_124`, `WEB_127`, `WEB_135`, `WEB_216`, `WEB_217`, `WEB_218`, `WEB_219`, `WEB_220`, `WEB_232`, `WEB_237`, `WEB_250`, `WEB_253`, `WEB_254`, `WEB_261`, `WEB_264`.

Các JSON của những hóa đơn này vẫn có trong ZIP, nhưng không có vùng do Duy tự vẽ. Không lấy crop OCR/auto làm nhãn thay thế.
