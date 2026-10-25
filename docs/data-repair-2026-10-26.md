# Sửa dữ liệu và huấn luyện lại — 26/10/2026

Model mặc định hiện tại là `hybrid-isolated-20261026-icann`, đã được fit lại
từ đầu trên các hàng train được giữ lại. Không tái sử dụng trọng số cũ sau khi
chỉ lọc file test. SHA256 artifact:
`9a49b7278cfb1b9da00f8ebc6970653a9de3320f3037db3ee190109926d1bd3a`.

## Kết quả có thể kiểm chứng

| Hạng mục | Trước sửa | Sau sửa |
|---|---|---|
| URL train/test chung tên miền gốc theo PSL | 519 tên miền | 0 |
| SMS validation/test chung tên miền gốc | `app.link` | 0 |
| ICANN owner domain chung các tập | Kiểm tra chéo phát hiện thêm 11 tên miền nền tảng | 0 |
| Nhãn SMS mâu thuẫn giữa nguồn | 14, gồm 10 train và 4 validation | Cách ly cả 14; không tự đổi nhãn |
| URL chứa backslash/ký tự phân dòng escape | 176, gồm 141 train và 35 test | Cách ly cả 176 |
| Hàng holdout/quarantine được fit | Model trước còn nhóm train liên quan holdout | 0 |
| Toàn bộ nhãn được chuyên gia độc lập xác minh | Chưa có | Vẫn chưa có |
| Độc lập theo chiến dịch thực | Chưa chứng minh | Vẫn chưa chứng minh |

Các kiểm tra sau sửa thực hiện trên **cả hai nhánh gộp lại**, với ba cặp
train/validation, train/test, validation/test. Cả tên miền ICANN và PSL gồm
private suffixes, nội dung SMS đã chuẩn hóa, danh tính URL, template SMS,
nhóm nguồn và các cạnh tương tự đã kiểm tra đều có giao bằng 0.
Số giao `campaign_id=0` không có giá trị chứng nhận khi trường này còn thiếu.

## Cách sửa nguyên nhân

1. Kiểm tra mã băm nguồn, bảng phân vùng và ledger của audit cũ. Đối chiếu
   lại 4.858 SMS với bản ghi nguồn/quyết định đã lưu; đối chiếu 50.000 URL với
   đúng hàng `source_record`, URL đã chuẩn hóa và nhãn good/bad trong CSV gốc.
   Đây là kiểm tra truy vết, không xác nhận nhãn nguồn phản ánh đúng thực tế.
2. Tách lại host từ nội dung, gồm URL trần có đường dẫn và dạng defang, không
   truy cập các URL. Cách ly các chuỗi tên miền còn mơ hồ. Bước này cũng xét
   các tên miền xuất hiện trong đường dẫn/query một cách bảo thủ.
3. Dùng PSL được ghim SHA256, gồm luật wildcard/exception. Kiểm tra đồng thời
   PSL có private suffixes và phần ICANN. Hai tenant `a.blogspot.com` và
   `b.blogspot.com` vì thế vẫn chung nhóm chủ quản `blogspot.com`.
4. Hợp nhất các thành phần liên thông theo cả hai loại tên miền, nội dung
   chuẩn hóa, template, nhóm nguồn và cặp SMS có char-ngram cosine >= 0,80.
   539 cạnh được lưu để tái kiểm tra; similarity chỉ là đại diện nội dung.
5. Giữ nguyên vai trò test/validation cũ; nhóm có test được dành cho test,
   nhóm chỉ có validation được dành cho validation. Cách ly các thành viên
   thuộc vai trò trước đó. Holdout bị cách ly vẫn giữ quyền bảo vệ cả nhóm.
6. Cách ly nhãn mâu thuẫn, URL lỗi và truy vết không đạt. Không ghi đè nhãn
   gốc và không biến đề xuất AI thành nhãn chuyên gia. Các nhãn nguồn/AI còn
   lại vẫn được giữ đúng provenance và báo cáo riêng khi đánh giá.
7. Đóng băng hàng và phân vùng bằng SHA256 **trước khi fit**. Fit vocabulary,
   scaler và classifier chỉ trên train. Dùng lại estimator, trọng số mẫu và
   ngưỡng cố định 0,65/0,50; không chọn lại theo điểm test.
8. Ràng buộc artifact mới với `frozen.json`, mã băm từng file train và code
   fit. Lệnh đóng gói head lịch sử bị chặn nếu định ghi đè model đã sửa.

Giữ pipeline tiền xử lý trong estimator và chỉ fit train phù hợp với hướng dẫn
[tránh data leakage của scikit-learn](https://scikit-learn.org/stable/common_pitfalls#data-leakage).
Thông tin nhãn smishing/spam/legitimate gốc nằm trong
[SmishX](https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff).
Không đánh đồng spam với phishing khi các nguồn bất đồng phạm vi.

## Phân vùng cuối

| Nhánh | Train trước → sau | Validation trước → sau | Test trước → sau | Cách ly tổng |
|---|---:|---:|---:|---:|
| SMS | 3.857 → 3.800 | 962 → 945 | 39 → 38 | 75 |
| URL | 40.004 → 32.777 | Không có | 9.996 → 9.935 | 7.288 |

Tổng cách ly 7.363 hàng; một hàng có thể có nhiều lý do. Không cộng các lý do
để suy ra tổng hàng. Không chuyển bất kỳ validation/test nào sang train.
Phân vùng URL cũ được tái dựng từ nguồn/recipe/runtime đã ghim vì export
`split_ids.json` lịch sử bị cũ. Các phân vùng mới có manifest gắn trực tiếp
với lần fit mới, không kế thừa khẳng định về export lịch sử.

Nhãn SMS train còn lại: 2.971 nhãn nguồn ham/non-smishing spam, 484 nhãn người
nghiên cứu SmishX, 343 nhãn AI review, 2 quyết định phạm vi của người dùng.
32.777 nhãn URL train vẫn là nhãn good/bad kế thừa nguồn, không phải nhãn
chuyên gia mới. Không có nhãn chuyên gia nào được tạo ra trong lần sửa này.

## Đánh giá sau fit

| Tập | Số hàng | Precision | Recall | F1 | TN / FP / FN / TP |
|---|---:|---:|---:|---:|---|
| SMS validation | 945 | 0,8846 | 0,9388 | 0,9109 | 890 / 6 / 3 / 46 |
| SMS test | 38 | 0,9200 | 0,9583 | 0,9388 | 12 / 2 / 1 / 23 |
| URL test | 9.935 | 0,9228 | 0,7238 | 0,8113 | 7.570 / 135 / 616 / 1.614 |

Đây là chẩn đoán trên holdout lịch sử sau lọc, đã được dùng ở các thí nghiệm
trước. Không phải benchmark mới chưa từng xem, không dùng để tuyên bố model
tốt hơn tổng quát. 24 SMS dương vẫn cùng một nhóm nguồn; khả năng khái quát
sang chiến dịch mới chưa được kiểm định. Nhãn URL đánh giá chưa được xác minh
độc lập. Điểm không phải xác suất đã hiệu chuẩn.

## Tái kiểm tra và tệp bằng chứng

Code: `ml_model/repair_training_data.py`, `ml_model/train_repaired_hybrid.py`.
Đầu ra đầy đủ cục bộ: `ml_model/data/prepared/repaired_training_2026-10-26-icann/`.
[Báo cáo JSON](data-repair-2026-10-26.json) chứa số lượng, provenance, giao
từng cặp và kết quả đánh giá. Manifest runtime nằm ở
`ml_model/models/hybrid_manifest.json`.

```powershell
.venv/Scripts/python.exe ml_model/repair_training_data.py verify
.venv/Scripts/python.exe ml_model/repair_training_data.py verify --require-campaigns
.venv/Scripts/python.exe ml_model/repair_training_data.py verify --require-expert-labels
```

Lệnh đầu PASS; hai lệnh nghiêm ngặt trả mã 2, nêu rõ thiếu metadata chiến dịch
hoặc xác minh chuyên gia. Không hạ điều kiện để nhận PASS. Muốn chứng nhận
chiến dịch thật cần mã chiến dịch/actor/destination/time có nguồn đáng tin và
đủ độ phủ; muốn xác minh toàn bộ nhãn cần thẩm định chuyên gia độc lập, có
bằng chứng và xử lý bất đồng. Không thể suy ra hai chứng nhận đó từ lexical URL.

Chạy mới ở thư mục **chưa tồn tại**, với cùng nguồn và audit snapshot:

```powershell
.venv/Scripts/python.exe ml_model/repair_training_data.py prepare --output ml_model/data/prepared/new_repair_run
.venv/Scripts/python.exe ml_model/train_repaired_hybrid.py fit --data ml_model/data/prepared/new_repair_run
.venv/Scripts/python.exe ml_model/train_repaired_hybrid.py evaluate --data ml_model/data/prepared/new_repair_run
.venv/Scripts/python.exe ml_model/train_repaired_hybrid.py activate --data ml_model/data/prepared/new_repair_run
```

Không xóa freeze để fit/evaluate lại sau khi đã xem test. Dữ liệu gốc, nguồn
nhãn, artifact nguồn và các thí nghiệm đóng băng trước đó được giữ nguyên.
Hai lần chạy PSL-only trước khi kiểm tra chéo ICANN là kết quả trung gian,
không phải model mặc định cuối cùng và không có chứng nhận ICANN của bản này.

Gói tải: `/test-data/training-holdout-repaired-2026-10-26.zip`, gồm test 9.973
hàng, đáp án nguồn, danh sách 14 nhãn mâu thuẫn/176 URL lỗi, membership của
54.858 hàng, các cạnh tương tự, manifest và `CHECK_SPLITS.py` chạy offline.
Gói `training-holdout-2026-10-26.zip` cũ có 10.035 hàng là dữ liệu lịch sử
trước sửa; không dùng gói đó để đại diện cho phân vùng mới.

## Kiểm tra phần mềm

79 kiểm thử Python, 16 kiểm thử assessment, 10 kiểm thử API và 2 kiểm thử API
khi thiếu model đều qua (107 tổng). Lint và build production/standalone thành
công; SHA256 model trong standalone khớp artifact cuối. Hai đột biến trong bộ
nhớ (bỏ hợp nhóm domain hoặc bỏ cách ly nhãn mâu thuẫn) đều bị test bắt; mã
nguồn giữ nguyên. Hai cổng chứng nhận nghiêm ngặt đều trả mã 2 như yêu cầu.

API cục bộ xác nhận run `hybrid-isolated-20261026-icann`. URL báo cáo ban đầu
`https://qi.lv/F0i` đạt raw score 0,8765821242, hiển thị 88/100, HIGH; đây là
kiểm tra hồi quy suy luận, không xác minh nội dung trang đích. ZIP tải HTTP 200,
SHA256 `c4ccd089299b397149615c4c2775d7442bb4ead7e0a6659906ab590ce96e565a`.
