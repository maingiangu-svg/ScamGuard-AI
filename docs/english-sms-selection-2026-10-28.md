# Chọn model SMS và chặn model không đạt — 28/10/2026

Đã bổ sung quy trình chọn cấu hình chỉ bằng train, chốt từ chối model bị đánh
dấu không đạt trong adapter suy luận, và health check thống nhất với chốt đó.
Ứng viên mới giảm lỗi trong CV lồng nhau nhưng vẫn không đạt chẩn đoán lịch
sử; **trọng số model đang dùng giữ nguyên**.

## Thay đổi phục vụ ứng dụng

`ml_model/predict_hybrid.py` từ chối nạp nếu manifest khai báo một trong các
trường `historical_nonregression_pass`, `all_policy_nonregression_pass`,
`release_approved` mà giá trị không phải boolean `true`. False, null, chuỗi
`"true"` hoặc số 1 không mở được chốt. Khi bị từ chối, API không trả điểm rủi ro.

Manifest cũ không có các trường này vẫn được hỗ trợ để giữ model hiện tại.
Đây là thực thi các kết luận được khai báo, không phải tự chứng nhận độ đúng
của model hoặc cơ chế xác thực nguồn gốc manifest.

`/api/health` đọc kết luận manifest ở mỗi request. Trước đây cache checksum có
thể giữ trạng thái khỏe dù manifest vừa bị từ chối hoặc đổi hash mong đợi.
Nay cờ từ chối được phản ánh ngay; đổi checksum mong đợi hoặc đường dẫn bundle
làm vô hiệu cache. Hash bundle vẫn được cache tối đa 10 giây. Health check này
không thay thế kiểm tra toàn bộ khả năng tương thích và suy luận bằng Python.

Đã thêm phép so sánh trạng thái `ml_model/model_state.py`: so sánh giá trị mảng,
tham số, RNG và trạng thái object. Nó không coi byte đệm trong mảng NumPy có
cấu trúc là trọng số thay đổi. Kiểm thử xác nhận thay giá trị node, threshold
hoặc RNG vẫn bị phát hiện, và xử lý được đồ thị có chu kỳ.

## Lựa chọn model bằng train

Giữ đúng 4.124 hàng có nhãn và 3.530 nhóm của lượt trước: 3.991 tiếng Anh,
133 tiếng Việt, gồm 338 mẫu tiếng Anh bổ sung. Không thêm hoặc đổi nhãn, không
fit các pool chưa có nhãn. Nhãn nguồn/AI không được nâng thành nhãn chuyên gia.

Tám cấu hình so sánh C = 0,25/1/4/16 và trọng số nguồn feed mới = 1/0,5.
Giữ nguyên đặc trưng, class balancing, trọng số tiếng Việt 3, nguồn người gán
2 và các ngưỡng. Trong các fold train, cấu hình phải không tăng FP hoặc giảm
TP ở cả hai ngôn ngữ so với C=1/trọng số mới=1. Sau đó ưu tiên ít FP, nhiều
TP, ít FP ở điểm thô 0,30; hòa thì chọn C nhỏ và trọng số nguồn yếu nhỏ hơn.

Outer 3-fold đo cả quy trình chọn cấu hình; mỗi outer train dùng inner 3-fold
để chọn và hiệu chuẩn sigmoid. Cấu hình cuối được chọn trên CV của toàn bộ
train, rồi fit cuối. Không dùng nhãn hoặc điểm test lịch sử để chọn cấu hình.
Các fold và manifest được khóa; các lượt trước không bị ghi đè.

Chọn cuối: **C=16, trọng số nguồn feed mới=0,5**. Ba outer fold chọn lần lượt
C=4/1/16, cho thấy kết quả lựa chọn còn thay đổi giữa các nhóm dữ liệu.

| Tiếng Anh, ngưỡng thô 0,65 | Ứng viên trước, OOF | Quy trình mới, nested OOF |
|---|---:|---:|
| Precision | 95,97% | 96,89% |
| Recall | 91,47% | 92,96% |
| F1 | 93,67% | 94,89% |
| Báo nhầm | 18 | 14 |
| Bỏ sót | 40 | 33 |

Nested OOF tiếng Việt giữ 9 FP, 10 FN như lượt trước. Đây là ước lượng của
quy trình chọn model theo nhãn hiện có, không phải benchmark chuyên gia độc
lập. Không đồng nhất nó với hiệu năng riêng của cấu hình cuối trên dữ liệu mới.
CV dùng để chọn cấu hình cuối có 13 FP/30 FN tiếng Anh, nhưng đó là ước lượng
lựa chọn và không được dùng thay nested OOF.

Hiệu chuẩn đạt điều kiện: Brier **0,01528 → 0,01292**, log-loss
**0,06845 → 0,04498** trên các dự đoán outer fold. Điểm cảnh báo vẫn dùng
model thô; xác suất hiệu chuẩn chỉ ước lượng nhãn nguồn.

## Chẩn đoán lịch sử và quyết định

Sau khi khóa trọng số, chấm mỗi tập lịch sử một lần cho ứng viên này:

| Ngưỡng thô 0,65 | FP model đang dùng → ứng viên | FN model đang dùng → ứng viên |
|---|---:|---:|
| Validation tiếng Anh, 904 tin | **4 → 11** | 3 → 2 |
| Validation tiếng Việt, 41 tin | 2 → 2 | **1 → 2** |
| Test tiếng Anh, 38 tin | **3 → 5** | 0 → 0 |

Điều kiện không tăng FP/FN từng phần dữ liệu không đạt. Ứng viên
`english-selected-20261028` được lưu nhưng **không kích hoạt**; adapter phục vụ
từ chối nó đúng thiết kế. Nhánh URL giữ nguyên giá trị tham số từ model đang dùng.

Ở điểm thô 0,30, FP validation Anh/Việt giảm 22→14 và 10→3, test giữ 9; nhưng
ở 0,80 một số FP tăng. Các điểm tích cực này không thay điều kiện đã chốt.
Bảng 0,30/0,80 là chẩn đoán trên điểm thô, không phải thống kê hành động đầy
đủ của giao diện: giao diện còn làm tròn điểm và xét URL độc lập.

Các tập lịch sử đã được dùng trước đó, test 38 tin có 24 tin dương cùng một
nhóm. Đây là chẩn đoán tái sử dụng, không phải chứng nhận khả năng tổng quát.
95 ứng viên validation, 96 ứng viên test mới chưa có nhãn và pool URL chưa
có verdict vẫn không được fit hoặc chấm.

## Kiểm tra và tái lập

- **166 kiểm thử Python**, **68 kiểm thử JavaScript** qua; không bỏ qua hoặc
  hạ điều kiện kiểm thử. Lint, TypeScript và production build qua.
- **10 kiểm tra HTTP** trên bản sao standalone: health và ba API trả 503 khi
  manifest bị từ chối; sai kiểu cờ duyệt cũng bị chặn; control hợp lệ trả 200.
  Body lỗi không chứa điểm rủi ro giả, traceback hoặc đường dẫn model.
- Fixture HTTP dùng bản sao bundle đang chạy có checksum đúng, chỉ đổi cờ ở
  manifest của fixture. Nó kiểm tra guard, không phê duyệt chất lượng ứng viên.
- Trọng số và manifest model thật giữ nguyên checksum. Các tệp nguồn/holdout
  được protocol bảo vệ không thay đổi. Không triển khai từ xa.

```powershell
.venv/Scripts/python.exe -X utf8 -m unittest discover -s ml_model -p "test_*.py"
npm.cmd test
npm.cmd run lint
npm.cmd run build
node scripts/model-release-gate.mjs
```

Trên Windows sandbox, build/HTTP có thể cần quyền thực thi ngoài sandbox như
đã xảy ra ở lượt này. Kiểm thử Python dùng TEMP/TMP trong workspace để tránh
lỗi quyền thư mục tạm hệ thống. Không đổi logic test để né các lỗi môi trường.

Ứng viên và bằng chứng ở
`ml_model/data/prepared/english_sms_selection_2026-10-28/`: `candidate_bundle.pkl`,
`candidate_manifest.json`, `protocol.json`, `selection_frozen.json`, các lựa chọn
outer fold, dự đoán OOF/lịch sử, `release_decision.json`, kiểm tra API và
`verify_state.py` để kiểm tra trạng thái model theo chế độ chỉ đọc.

[JSON tổng hợp và checksum](english-sms-selection-2026-10-28.json).

Không chạy lặp các lượt với test cũ để chọn kết quả đẹp. Muốn cải thiện tiếp
cần protocol mới, dữ liệu tin hợp lệ khó phân biệt có nhãn đáng tin hơn và bộ
đánh giá độc lập đủ đa dạng; chưa có cơ sở tuyên bố accuracy ngoài thực tế tăng.
