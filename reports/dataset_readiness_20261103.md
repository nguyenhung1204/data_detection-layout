# Trạng thái bộ dữ liệu detection/layout — 2026-11-03

## Thay đổi trong lần cập nhật này

- Loại 20 hóa đơn có 0 vùng annotation khỏi manifest active, thư mục PDF active và thư mục annotation active.
- Lưu ID, split cũ, người phụ trách cũ và SHA-256 trong `data/manifests/excluded_unannotated_invoices_20261103.csv` để truy nguyên.
- Các file bị loại đã được xóa khỏi cây làm việc hiện tại; bản lịch sử Git trước commit vẫn chứa nội dung cũ.

## Tình trạng active sau khi loại

- Hóa đơn/PDF: 188; vùng annotation: 4076.
- `field_status`: {"verified": 4076}.
- `transcript_status`: {"needs_review": 4076} (độc lập với xác nhận trường/layout).
- Nguồn vùng: {"manual": 2627, "automatic_crop_proposal": 1449}.
- Hóa đơn theo split: {"val": 36, "train": 117, "test": 35}.
- Vùng theo split: {"val": 650, "train": 2551, "test": 875}.
- Hóa đơn theo người phụ trách: {"duy": 91, "van": 97}.

### Số vùng theo trường

| Field key | Số vùng |
|---|---:|
| `invoice_date` | 184 |
| `invoice_number` | 189 |
| `item_description` | 601 |
| `line_total` | 588 |
| `quantity` | 600 |
| `seller_name` | 182 |
| `seller_tax_code` | 186 |
| `tax_rate` | 176 |
| `total_amount` | 180 |
| `unit` | 601 |
| `unit_price` | 589 |

### Hóa đơn bị loại

| Invoice ID | Split trước đó | Người phụ trách | SHA-256 PDF |
|---|---|---|---|
| `WEB_001` | train | duy | `e859b96130cd60be9cbd78a619e2837664d0e5a8488b8a23cf522fc2741f532b` |
| `WEB_004` | train | duy | `8309c8ef317522f24335f262dc582562e9578a34175c00a4f0f9de443ee44019` |
| `WEB_011` | train | duy | `bb9644c29cde040212c7c9ca127bbcab1e2859cc251ae033cb7accaec4f5403b` |
| `WEB_013` | val | duy | `a920e92d2095987eee363e8e295cb67810f79fa3432370348092ed37317c0c9a` |
| `WEB_015` | train | duy | `79195143cacb59d4b6471c81b538dcba75833de55faa688fcedc109749d44d66` |
| `WEB_022` | train | duy | `e5eee83d61c22d179cec20ed5e2e59f63f4624ae595cd8f850c2449409be0cbf` |
| `WEB_076` | train | van | `204941ceaed4bcea3c1753d789496a81cf7fa4262f31ccc2557f4035a0eb4cd7` |
| `WEB_077` | test | van | `8394e4cfb74bc5d183aefcd6e5de7b8c5791f700ad1739b5e11d664ab45870eb` |
| `WEB_078` | test | van | `62f6dab1000d928a72b7c1bd1d9ccf6fc1e313ad1be9fd4d74073e9d45ba1ccf` |
| `WEB_079` | train | van | `adc5ee77c948c4380173b1025ffce25d5ac8b8c8c176bc893434d63a7c0247c6` |
| `WEB_081` | test | duy | `1238cd9798131bcd5f97fb28721efb5d35640d15ceacb064415ad8d9e860cbab` |
| `WEB_082` | test | duy | `ee2383c815fecb5fae5a15646f34c4bfc551134a6296855b08478fc589da3831` |
| `WEB_109` | train | van | `fa7a72613262bc15cde8cc70c438283e7225753bb6a6018ac18cadaa70aa9ab2` |
| `WEB_176` | test | van | `ef175502f2aac78024daa7e1468907c15eb2a89b26f92267f267d82125b4e6dc` |
| `WEB_182` | test | van | `a82e34788b6489e615780f509e6547505a95ade54a8ee8d0748029d3222614a9` |
| `WEB_216` | val | duy | `897da72f83ff3842d11066da21d37af1cef8f8d4fdb7a6997f87d53153dcabd6` |
| `WEB_217` | val | duy | `0e82530acbd11c0d41c94be2f33028c12bdf9f08e08d3397ab8768994f797075` |
| `WEB_218` | val | duy | `b162caacce63dce92d5a0fc478d68eee80940991b5868e382b8d3f1c3c3403d1` |
| `WEB_219` | val | duy | `01c626924370092d5cd0f9ffbec2488495b0ab99a2affa5ce9650fe4025610a8` |
| `WEB_237` | train | duy | `69373f2acbb435e715fda7f87ebb11763de97cbde130e7f39d4e0844ee77f5e9` |

Đây là bộ nhãn tổng quát cho field/layout, chưa phải cấu hình huấn luyện gắn với một model cụ thể. Trình kiểm tra cấu trúc không đánh giá độ chính xác thị giác của từng bbox.
