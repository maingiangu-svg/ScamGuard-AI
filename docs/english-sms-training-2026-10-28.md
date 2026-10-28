# Huấn luyện SMS bổ sung tiếng Anh — 28/10/2026

**Đã huấn luyện xong ứng viên `english-sms-20261028` trên 4.124 SMS có nhãn.**
Ứng viên gồm nhánh SMS mới và nhánh URL kế thừa nguyên tham số từ model đang
chạy. Hiệu chuẩn qua điều kiện đã chốt, nhưng báo nhầm tăng trên dữ liệu lịch
sử; vì vậy **không thay model đang chạy** và không triển khai từ xa.

## Dữ liệu và cách học

- 3.786 hàng fit SMS của model hiện tại, gồm 133 tin tiếng Việt, cộng đúng 338
  hàng tiếng Anh đã được nhận từ [đợt bổ sung dữ liệu](english-data-expansion-2026-10-28.md).
- Tổng: **3.991 tiếng Anh + 133 tiếng Việt**; **3.601 nhãn 0 + 523 nhãn 1**.
- Giữ nguồn nhãn: 2.966 nhãn ham/non-smishing nguồn; 483 nhãn thủ công SmishX;
  334 AI review cũ; 3 quyết định người dùng/phạm vi; 338 nhãn feed nguồn sau AI
  sàng lọc template. Không nâng nhãn yếu thành nhãn chuyên gia.
- Gom lại 3.530 nhóm cho cross-validation bằng nội dung, template, tên miền
  PSL/ICANN, nhóm fit cũ, nhóm nguồn bổ sung và cosine ký tự từ 0,80. Tên miền
  của các bản nguồn gộp cũng được giữ. Nhóm là chỉ báo bảo thủ, không phải
  chứng nhận độc lập chiến dịch.
- Dùng lại TF-IDF word/character và Logistic Regression của nhánh SMS hiện tại.
  Không tìm lại siêu tham số hoặc ngưỡng. Trọng số vẫn là tiếng Việt 3, nguồn
  người gán 2, còn lại 1; ngưỡng SMS **0,65**, URL **0,50**.
- Outer 3-fold theo nhóm cho đánh giá ngoài mẫu; mỗi fold fit hiệu chuẩn sigmoid
  bằng inner 3-fold theo nhóm. Vocabulary và estimator chỉ fit trong phần học
  tương ứng. Sau đó fit cuối trên toàn bộ 4.124 hàng được nhận.

Protocol, hàng fit, mã fit và checksum được ghi trước khi fit estimator. Các
ứng viên validation/test mới chưa có nhãn và 3.003 URL chờ rà đều không được
fit hoặc dùng để chấm chất lượng. Model URL không được huấn luyện lại.

## Kết quả ngoài mẫu từ các fold train

| Phần dữ liệu | Số tin | Precision | Recall | F1 | TN / FP / FN / TP |
|---|---:|---:|---:|---:|---|
| Tiếng Anh | 3.991 | 95,97% | 91,47% | 93,67% | 3.504 / 18 / 40 / 429 |
| Tiếng Việt | 133 | 83,02% | 81,48% | 82,24% | 70 / 9 / 10 / 44 |
| Toàn bộ | 4.124 | 94,60% | 90,44% | 92,47% | 3.574 / 27 / 50 / 473 |

Đây là mức đồng ý với nhãn nguồn/AI/người dùng trong đánh giá chéo theo nhóm,
không phải độ chính xác ngoài thực tế hoặc bộ test chuyên gia độc lập. Các
fold còn được dùng kiểm tra phương pháp hiệu chuẩn đã chốt; không gọi kết
quả đó là benchmark ngoài quy trình phát triển.

Hiệu chuẩn làm Brier giảm **0,01960 → 0,01420**, log-loss giảm
**0,09891 → 0,04877**; đạt cả hai điều kiện không xấu đi. Xác suất hiệu chuẩn
chỉ ước lượng nhãn nguồn, không phải xác suất lừa đảo đã được chuyên gia xác
minh. Cảnh báo vẫn dùng điểm thô và ngưỡng cố định.

## Chẩn đoán lịch sử và quyết định

Chỉ đánh giá một lần sau khi khóa trọng số. Các tập này đã được dùng ở các
thí nghiệm trước; không phải test mới và không dùng để sửa ngưỡng hoặc học lại.

| Tập lịch sử, ngưỡng 0,65 | Số tin | FP cũ → mới | FN cũ → mới | Recall cũ → mới |
|---|---:|---:|---:|---:|
| Validation tiếng Anh | 904 | **4 → 8** | 3 → 2 | 90,91% → 93,94% |
| Validation tiếng Việt | 41 | 2 → 2 | 1 → 1 | 93,75% → 93,75% |
| Test tiếng Anh | 38 | **3 → 5** | 0 → 0 | 100% → 100% |

Điều kiện đã chốt yêu cầu không tăng FP hoặc FN trong từng phần dữ liệu.
Ứng viên **không đạt** vì tăng báo nhầm tiếng Anh. Test chỉ có 14 tin nhãn 0;
24 tin dương cùng một nhóm, nên kết quả cũng không chứng minh khả năng tổng
quát qua nhiều chiến dịch. Không bỏ hoặc đổi điều kiện sau khi xem kết quả.

Đối chiếu thêm chính sách giao diện 30/80 được lưu trong JSON. Ở ngưỡng review
0,30, FP validation tiếng Anh giảm 22 → 20 và tiếng Việt giảm 10 → 5, nhưng
FP test tiếng Anh tăng 9 → 10. Ở ngưỡng block 0,80, FP/FN test giữ nguyên.
Những điểm tốt này không thay thế điều kiện không hồi quy đã đăng ký.

## Model và bằng chứng

Thư mục `ml_model/data/prepared/english_sms_training_2026-10-28/` chứa:

- `candidate_bundle.pkl`: model ứng viên hoàn chỉnh, **chưa kích hoạt**.
- `candidate_manifest.json`: manifest training được khóa trước chẩn đoán lịch sử.
- `release_decision.json`: quyết định sau chẩn đoán, ràng buộc hash manifest,
  trọng số và kết quả; `activated=false`.
- `sms_fit_rows.csv/.jsonl`, `protocol.json`, `fit_code.py`: dữ liệu fit, phương
  pháp, trọng số mẫu và bản mã thực sự đã chạy.
- `sms_oof_predictions`, `training_report.json`, `historical_*_predictions`,
  `evaluation.json`, `verification_report.json`: dự đoán và các kiểm tra.

SHA-256 bundle ứng viên:
`59543857f66766917538cd392c1b7f86ff466bd4e8a09796fd47df70adfa3af1`.

157 kiểm thử Python đều qua. Kiểm tra tải qua `predict_hybrid.load_bundle`
thành công; năm smoke check xác nhận SMS thường, ví dụ thuộc train, URL
`qi.lv/F0i`, URL Facebook và đầu vào SMS kèm link đều suy luận được. Đây là
kiểm tra kỹ thuật, không phải năm mẫu accuracy mới. Nhánh URL khớp chính xác
về giá trị tham số, mảng đã học, RNG và trạng thái loss; điểm URL được đối
chiếu giữ nguyên. So sánh byte của pickle tái tuần tự hóa không được dùng làm
chuẩn đồng nhất trạng thái vì biểu diễn bộ nhớ có thể khác dù giá trị khớp.

Model hiện tại vẫn là `url-ensemble-20261027`, bundle SHA-256
`26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.
Checksum model, manifest, dữ liệu nguồn và các holdout được bảo vệ đều giữ
nguyên. Không đổi code suy luận hoặc chính sách cảnh báo của ứng dụng.

[Bằng chứng JSON tổng hợp](english-sms-training-2026-10-28.json).

## Chạy lại ở lượt mới

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv/Scripts/python.exe -X utf8 ml_model/english_sms_training.py fit --output ml_model/data/prepared/english_sms_training_NEW
.venv/Scripts/python.exe -X utf8 ml_model/english_sms_training.py evaluate --output ml_model/data/prepared/english_sms_training_NEW
```

`fit` từ chối ghi đè lượt đã tồn tại; `evaluate` từ chối chấm lặp. Không chạy
lượt khác để chọn model theo các test lịch sử đã xem. Một vòng cải thiện tiếp
cần protocol mới và chọn cấu hình trên train/validation phù hợp, cùng bộ đánh
giá mới đủ tin cậy trước khi đưa ra tuyên bố cải thiện ngoài thực tế.
