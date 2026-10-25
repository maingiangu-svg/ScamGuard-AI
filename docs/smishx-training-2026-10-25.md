# Huấn luyện bổ sung SMS tiếng Anh từ SmishX — 25/10/2026

Đã hoàn thành rà dữ liệu, bảo vệ các tập giữ riêng, huấn luyện và chấm điểm một
lần bản thử nghiệm mới. Mô hình ứng dụng và toàn bộ kết quả thực nghiệm trước
được giữ nguyên. Không dùng MIMICS-3500 hoặc bộ IMC gán nhãn AI trong lần học này.

## Đính chính dữ liệu nguồn

[SmishX tại SOUPS 2025](https://github.com/yizhu-joy/SmishX) công bố **1.200 SMS
đa ngôn ngữ**, gồm 259 nhãn smishing, 319 spam và 622 legitimate. Trước đây dự
án gọi toàn bộ tệp là tiếng Anh; kiểm tra nội dung cho thấy cách gọi đó không
chính xác. Các tệp có tên `smishx_english_human_labels` và
`smishx_english_smishing_259` ở thư mục đợt tải đầu được giữ nguyên như hồ sơ
nguồn, **không phải tập tiếng Anh đã lọc**. Dùng bản xuất của đợt này bên dưới.

[Bài nghiên cứu, mục 4.1](https://www.usenix.org/system/files/soups2025-wang.pdf)
mô tả hai nhà nghiên cứu gán nhãn thủ công toàn bộ và giải quyết bất đồng. Đây
là nguồn gán nhãn của tác giả, chưa phải kiểm định lại của dự án. Dự án không
khẳng định danh tính hoặc trình độ chuyên gia của từng người gán nhãn.

Commit nguồn: `116a8c827741e0572563f678d25ed04306b1e3ff`.
SHA-256 tệp CSV: `8d65e373b17477c34e8f1c619e6f59d249e8fca21276cabdd03a55d11a469285`.
Giữ giấy phép MIT của kho và nguồn trích dẫn; dữ liệu tổng hợp từ bên thứ ba
không được suy thêm quyền sử dụng ngoài điều kiện đã công bố.

## Đã xử lý những gì

AI đã đọc nội dung 1.200 tin trước khi chọn mô hình và ghi quyết định theo ID:

| Kết quả sàng lọc | Số dòng |
|---|---:|
| Tiếng Anh phù hợp phạm vi dự án | 1.017 |
| Ngôn ngữ khác hoặc trộn ngôn ngữ chưa phù hợp | 77 |
| Mẩu tin/URL không đủ để xác định ngôn ngữ | 19 |
| Phạm vi nhãn chưa rõ hoặc khác định nghĩa dự án | 87 |

Trong 1.017 dòng phù hợp có **141 nhãn 1** và **876 nhãn 0** theo nhãn thủ công
gốc. Sàng lọc ngôn ngữ/phạm vi là đánh giá của AI, không phải một lần xác minh
chuyên gia mới. Chỉ giữ nhãn nguồn cho các mẫu phù hợp; các mẫu bị tách có
`label=null` và vẫn giữ `original_label` cùng lý do. Không sửa bản tải gốc.

Ví dụ: `SMISHX-0828` quảng cáo thêm phút gọi, nêu phí £1.50/phút, nhưng nguồn
gán smishing. Vì dự án đã chọn quảng cáo dịch vụ có phí chưa đủ căn cứ là
smishing, mẫu được tách vì khác phạm vi nhãn. `SMISHX-0619` là tiếng Pháp nên
không đưa vào phần tiếng Anh. `SMISHX-0756` nguồn gán spam nhưng lời mời làm
nhiệm vụ trên Amazon hứa $100–500/ngày có dấu hiệu khác phạm vi spam quảng cáo;
mẫu cũng được tách, không tự đổi thành nhãn 1 để học.

Cả 17 dòng mâu thuẫn đã phát hiện trong đợt tải đầu nằm trong nhóm khác phạm
vi/chưa rõ. Không dùng nhãn nguồn mới để ghi đè nhãn lịch sử. Nhãn khác nhau
trên cùng đầu vào chuẩn hóa sẽ bị cách ly thay vì tự ưu tiên người hoặc AI.

Nhóm nối nội dung chuẩn hóa trùng, khuôn mẫu, tên miền đăng ký theo Public
Suffix List và độ tương tự ký tự từ 0,80. Giữ liên kết nhóm của tập trước.
Mẫu nối tới validation/test cũ, các tập tiếng Việt lịch sử hoặc tên miền kiểm
định URL đều bị chặn khỏi học. Tên miền rút gọn cũng được nhóm bảo thủ; số dòng
bị chặn không đồng nghĩa từng nội dung đều trùng hệt.

Sau nối nhóm, có 421 dòng ứng viên bị chặn vì liên quan tập giữ riêng/tên miền
kiểm định, gồm 420 dòng SmishX và 1 dòng train cũ. Các dòng còn lại được gộp
trùng, giữ danh sách ID và nguồn nhãn. Nhóm đã từng học chỉ được vào train,
không chuyển sang bộ test mới. Không có nhóm hoặc tên miền đăng ký trùng giữa
train, validation và test mới.

## Dữ liệu thực sự dùng

| Tập | Số tin | Nhãn 1 | Nhãn thủ công SmishX |
|---|---:|---:|---:|
| Train | 3.857 | 193 | 497 |
| Validation | 962 | 49 | 30 |
| Test tiếng Anh, nhóm giữ riêng mới | 39 | 25 | 39 |

Train có **3.716 tin tiếng Anh**, gồm **139 tin lừa đảo**, và 141 tin tiếng Việt,
gồm 54 nhãn 1. Trước lần bổ sung, train có 3.584 tin tiếng Anh với 68 nhãn 1.
497 dòng mang nhãn thủ công trong train bao gồm cả nội dung trùng nguồn cũ;
không có nghĩa là thêm 497 nội dung hoàn toàn mới.

Validation gồm 932 tin validation cũ cùng 30 tin SmishX ở nhóm mới. Test mới có
25 nhãn smishing và 14 nhãn không smishing, thuộc các nhóm ngoài dữ liệu đã
học và các tập giữ riêng cũ của bản nghiên cứu trước. Đây là tập công khai được
biên soạn từ nhiều nguồn; không khẳng định nó là một nguồn thu thập độc lập
hoàn toàn hoặc tách biệt với tập học của mô hình ứng dụng cũ.

Chỉ huấn luyện nhánh text SMS. Thử hai cấu hình TF-IDF word và word+character
với Logistic Regression có sẵn. Trọng số cố định: tiếng Việt 3, nhãn thủ công
tiếng Anh 2, các dòng còn lại 1. Chọn F2 validation cao nhất với tỷ lệ báo nhầm
validation tối đa 10%. Không thay đổi cấu hình/ngưỡng theo test.
Validation chọn **word+character, ngưỡng 0,65**. Đây là ngưỡng nghiên cứu,
không thay chính sách cảnh báo 30/80 của ứng dụng. Không huấn luyện lại URL.

## Kết quả sau khi khóa mô hình và ngưỡng

| Bộ 39 tin có nhãn thủ công | Bản nghiên cứu trước | Bản bổ sung SmishX |
|---|---:|---:|
| Phát hiện đúng smishing | 23/25 | 24/25 |
| Bỏ sót smishing | 2 | 1 |
| Báo nhầm tin không smishing | 3/14 | 1/14 |
| Precision | 88,5% | 96,0% |
| Recall | 92,0% | 96,0% |

Kiểm tra đơn vị nhóm cho thấy 39 tin nằm trong **11 nhóm: 25 tin smishing chỉ
thuộc 1 nhóm, còn 14 tin không smishing thuộc 10 nhóm**. Những bản gần trùng
không phải 25 trường hợp lừa đảo độc lập. Vì vậy không dùng 96% làm bằng chứng
khả năng khái quát qua nhiều chiến dịch, không coi 39 tin là 39 quan sát độc lập
để suy độ chắc chắn thống kê. Không sửa cách chia tập sau khi đã thấy kết quả.

39 tin là tập nhỏ, đã sàng lọc phạm vi và không đại diện lưu lượng thực tế.
96% ở đây không chứng minh Agent đạt 96% trên mọi tin nhắn hoặc mọi ngôn ngữ.
Đây là so sánh hai bản nghiên cứu trên cùng đầu vào; không phải so với mô hình
ứng dụng và không tách riêng tác động của nhãn, trọng số hay ngưỡng.

Các tập cũ dưới đây chỉ được chấm lại làm **chẩn đoán**, không phải test độc lập mới:

| Bộ cũ | Phát hiện đúng nhãn 1, trước → sau | Báo nhầm nhãn 0, trước → sau |
|---|---|---|
| SMS hỗn hợp, 1.164 tin | 36/38 → 29/38 | 17/1.126 → 6/1.126 |
| Riêng tiếng Việt trong tập trên, 54 tin | 20/20 → 17/20 | 8/34 → 4/34 |
| Tiếng Việt lịch sử, 70 tin | 17/17 → 14/17 | 20/53 → 9/53 |

Bản mới giảm báo nhầm nhưng bỏ sót nhiều hơn trên các tập cũ chủ yếu mang nhãn
AI/nguồn. Chưa thay mô hình ứng dụng. Cần xem lỗi, thêm đánh giá tiếng Việt
độc lập và đánh giá khả năng tổng quát trước khi triển khai. Giữ test đã chấm
làm hồ sơ; vòng chỉnh tiếp theo cần kế hoạch đánh giá mới, không thử nhiều lần
trên 39 tin để chọn kết quả đẹp.

## Tệp để xem dữ liệu và tái lập

Thư mục: `ml_model/data/prepared/smishx_training_2026-10-25/`.

- `smishx_source_screened.csv/.jsonl`: 1.200 dòng nguồn, kết quả lọc và lý do.
- `smishx_english_scope_eligible.csv/.jsonl`: 1.017 dòng tiếng Anh phù hợp phạm vi,
  bao gồm cả dòng sau đó bị chặn vì trùng nhóm; không gộp thẳng tệp này vào train.
- `train.csv/.jsonl`, `validation.csv/.jsonl`, `test.csv/.jsonl`: các tập thực sự dùng.
- `quarantine.csv/.jsonl`: dữ liệu bị tách và lý do.
- `data_usage_manifest.csv/.jsonl`: đối chiếu đủ 4.925 ID ứng viên cũ + mới sau gộp/tách.
- `source_scope_review_notes.json`: các ID quyết định ngôn ngữ/phạm vi của AI.
- `research_model.pkl`: mô hình SMS thử nghiệm, không tương thích trực tiếp với app.
- `test_predictions.csv/.jsonl`, `test_errors.csv/.jsonl`: dự đoán và lỗi trên 39 mẫu.
- `historical_*_predictions.csv/.jsonl`: kết quả chẩn đoán trên các tập cũ.
- `metrics_for_paper.csv/.jsonl`, `final_report.json`: số liệu thực tế để viết paper.
- `selection_frozen.json`, `verification_report.json`: checksum và kết quả kiểm tra.
- `test_group_audit.json`: số nhóm thực tế, giới hạn chỉ có 1 nhóm positive và
  đối chiếu nhóm với toàn bộ mẫu từng học của bản nghiên cứu trước.

41 kiểm thử Python đã qua; phép đảo điều kiện chặn holdout cố ý bị phát hiện
và được khôi phục. Đối chiếu riêng từ các dự đoán lưu sẵn khớp báo cáo. CSV và
JSONL khớp nội dung/số dòng, kể cả ký tự phân cách dòng Unicode. Nguồn tải,
mô hình đang chạy và các thực nghiệm đã khóa giữ nguyên checksum.

Các bước đã chạy thành công, không chạy lại select/test trong cùng thực nghiệm:

```powershell
.\.venv\Scripts\python.exe ml_model\smishx_training.py prepare --allow-mixed-labels
.\.venv\Scripts\python.exe ml_model\smishx_training.py select --allow-mixed-labels
.\.venv\Scripts\python.exe ml_model\smishx_training.py test --allow-mixed-labels
```

Thử một tin mới với mô hình đã học:

```powershell
.\.venv\Scripts\python.exe ml_model\smishx_training.py predict --allow-mixed-labels --text "Hello, can we meet at 3 tomorrow?"
```
