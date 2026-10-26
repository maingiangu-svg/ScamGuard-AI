# Kết quả hoàn thiện — 26/10/2026

Các thay đổi dưới đây đã chạy và kiểm chứng local. PR #1 vẫn là draft; chưa
merge hoặc deploy website. CI của snapshot mới cần chạy sau khi chủ dự án duyệt
phạm vi công khai. OCR/phân tích ảnh và hội thoại nhập vai được hoãn theo yêu cầu.

## Extension 1.1.2

Giữ hai chế độ do người dùng chọn: thủ công mặc định và tự quét có xin quyền.
Sửa luồng tự quét để kiểm tra ngay tab hiện tại khi bật, khi chuyển tab hoặc
điều hướng; sửa trường hợp content listener không còn sau khi nâng/reload extension.
Background kiểm tra phiên bản listener và inject lại khi cần. Những lượt kiểm
tra đồng thời cùng tab/URL được gộp, kết quả cũ không được áp lên URL mới.

Badge hiển thị điểm cho mọi kết quả thành công, kể cả điểm thấp. Lỗi quyền,
inject hoặc backend hiện dấu `!` và hướng dẫn trong popup. Banner cảnh báo
vẫn dùng ngưỡng 80; không có banner không chứng minh trang an toàn. Footer
popup hiển thị phiên bản để người dùng xác nhận đã Reload bản mới.

Kiểm thử Chromium dùng profile riêng: thủ công, chặn tự bật khi thiếu quyền,
tự quét tab đang mở, trang mới, tắt tự quét và tự phục hồi receiver đều PASS.
Origin HTTPS YouTube được chặn mạng và thay bằng HTML fixture do test sở hữu;
không đọc video hoặc profile cá nhân. **Chưa tự động hóa hộp thoại quyền native
và thao tác Reload extension trong Edge của người dùng**. Người dùng báo thủ
công chạy được và đã cấp quyền; xác nhận tự quét bản 1.1.2 trong Edge còn chờ.

Để thử: chạy app ở `http://localhost:3000`, Reload tại `edge://extensions`,
mở popup có dòng `Phiên bản 1.1.2`, bật tự quét và cấp quyền truy cập site.
Tab HTTP/HTTPS hiện tại phải nhận badge điểm mà không bấm nút quét thủ công.
Chi tiết quyền và dữ liệu gửi ở [extension README](../extension/README.md).

## Runtime và bảo mật

Runtime Distroless khóa digest loại các công cụ OS không dùng khỏi image phục
vụ; giữ inventory và metadata cho các thư viện Python bổ sung. Gate không bỏ
qua advisory chưa có bản vá. Scanner nhận diện 19 package OS cùng inventory
Node/Python; báo cáo thiếu inventory bị từ chối.

Trivy 0.76.1 trên image cuối
`sha256:e24341d01486e14aafca029bcb7dc1c2ba334790344b4302a69baa8387bd880f`:
**0 High, 0 Critical**. So với image Python-slim trước đó có 44 bản ghi/8 CVE
High, các thành phần không dùng đã bị loại khỏi image cuối. Không tuyên bố
mọi advisory trong tương lai đều bằng 0. CI thêm quét image và gate sau smoke.

Smoke PASS với URL và SMS thật qua API, model mới, UID10001 và read-only root.
Kiểm tra không có pip đang hoạt động và executable OS không dùng. Runtime
không nhằm cung cấp toàn bộ công cụ hoặc extension stdlib Python tùy chọn.
[Triage và lịch sử scan](container-security-triage-2026-10-26.md).

## Rà soát nhãn có giám sát

AI đọc 14 SMS và kiểm tra tính đầy đủ của bằng chứng cho 797 URL: tổng 811 ứng
viên từ train. Ba SMS được đề xuất nhãn 0 phù hợp nhãn nguồn; một SMS được đề
xuất nhãn 1 và chủ dự án duyệt riêng. Nhãn override được ghi `user_decision`,
hash nội dung và lý do; không đổi nhãn nguồn, không điền biểu mẫu chuyên gia.

Mười SMS quảng cáo/thiếu ngữ cảnh và 797 URL thiếu bằng chứng giữ `unknown`:
807 ứng viên cách ly. Loại toàn bộ nhóm chứa chúng khỏi lần fit mới, tương ứng
1.492 hàng train. Còn **3.786 SMS và 31.299 URL**; không chuyển validation/test
sang train. Hai biểu mẫu chuyên gia vẫn chưa có nhãn. Không mở URL nghi vấn.

Ledger, quyết định người dùng và dữ liệu từng hàng được giữ riêng trong
`ml_model/data/prepared/`; bản công khai chỉ chứa tổng hợp, code và model.
Không có nhãn chuyên gia mới hoặc benchmark tiếng Việt độc lập mới.
[Quy trình gán nhãn và benchmark](ml-expert-review-protocol.md).

## Model và hiệu chuẩn

Run local: `group-calibrated-20261026`; SHA256 bundle:
`6a0fd38b35570bff4b0ae56dd52a07747a6670d3dc2eceda304e1f10898314d0`.
Manifest ràng buộc checksum model, hàng fit, nguồn nhãn, protocol và parent
artifact. Báo cáo evaluation của model cha nằm trong parent lineage, không
được gán làm evaluation của model mới. Có backup model cũ trước khi kích hoạt.

Hiệu chuẩn sigmoid bằng 3 fold ngoài/3 fold trong theo nhóm, seed42, chỉ train.
Mỗi fold fit lại cả preprocessing và classifier; giữ weighting SMS và các
hyperparameter cũ. Gate yêu cầu Brier và log loss không tăng ở cả hai nhánh.
Không dùng historical test để fit, chọn ngưỡng hoặc quyết định kích hoạt.

| Dự đoán ngoài nhóm trong train | Brier trước → sau | Log loss trước → sau |
| --- | --- | --- |
| SMS, 3.786 hàng | 0.017119 → 0.013244 | 0.087363 → 0.044864 |
| URL, 31.299 hàng | 0.045293 → 0.042088 | 0.164525 → 0.138541 |

Bootstrap theo nhóm 500 lần: khoảng 95% của chênh Brier là
[-0.005190, -0.002662] cho SMS và [-0.004036, -0.002374] cho URL.
Đây là kiểm chứng theo nhãn nguồn pha trộn, chưa xác minh bởi chuyên gia.

API thêm `calibrated_probability`, `calibration_status` và
`calibrated_probability_expert_verified=false`; adapter cũ trả unavailable
thay vì tự tạo số. UI hiển thị ước lượng riêng theo nhãn nguồn. Điểm cảnh báo
0–100, ngưỡng SMS0.65/URL0.50 và chính sách30/80 vẫn là các giá trị riêng;
điểm cảnh báo không được đổi tên thành xác suất lừa đảo thực tế.

Chẩn đoán historical sau kích hoạt (không dùng để retune):

| Cohort đã tái sử dụng | Số hàng | Brier trước → sau |
| --- | ---: | --- |
| SMS validation | 945 | 0.014480 → 0.008965 |
| Tiếng Việt trong validation, nhãn AI | 41 | 0.091043 → 0.069191 |
| SMS test tiếng Anh | 38 | 0.108157 → 0.075281 |
| URL test | 9.935 | **0.059061 → 0.059717 (xấu hơn nhẹ)** |

Không có bằng chứng cải thiện trên mọi miền. Chỉ có 41 mẫu tiếng Việt ở cohort
trên, đều nhãn AI; 24 SMS dương tính trong test chia sẻ một nhóm nguồn. Các
proxy nhóm/domain không chứng nhận độc lập chiến dịch khi thiếu metadata.
Không coi các holdout đã xem là benchmark mới. Không bảo đảm nội dung an toàn.

## Tái lập và kiểm chứng

Với dữ liệu riêng và ledger đã được ràng buộc hash, chạy fit vào thư mục mới:

```powershell
.venv/Scripts/python.exe ml_model/calibrate_supervised.py --data ml_model/data/prepared/repaired_training_2026-10-26-icann --review ml_model/data/prepared/ai_review_2026-10-26 --review-package ml_model/data/prepared/expert_review_2026-10-26 --user-decisions ml_model/data/prepared/ai_review_2026-10-26/user_decisions.json --output ml_model/data/prepared/calibrated_candidate_NEW
```

Xác nhận đường dẫn data theo `protocol.json` của run; không ghi đè run cũ.
`--activate` chỉ dùng với candidate đạt gate và parent model khớp. Activation
kiểm checksum trước khi thay model và tạo backup. Source fit của run này được
lưu riêng với SHA256 `ba705641d1e48e24028b23791b63a085b2b1848767b615bfeaaae30a9d4acebe`;
module hiện tại có thêm kiểm tra activation/metadata sau fit. Không thay hash
của source thực sự đã fit bằng hash của phiên bản mới hơn.

Kết quả local: 108 test Python, 47 test Node và 3 test vòng đời suy luận PASS;
lint, typecheck và production build PASS. Integration API (17), model unavailable
(2), quota dùng chung, giao diện responsive/CSP và xuất PDF tiếng Việt PASS.
Extension browser và Docker smoke/scan cuối PASS. Mutation test đảo điều kiện
gate trong bản sao riêng bị test bắt lỗi; source phục vụ không bị thay đổi.

[Bằng chứng tổng hợp](completion-evidence/2026-10-26/summary.json) gồm scan đầy
đủ, smoke, calibration, chẩn đoán historical, log và kết quả browser. Không
đưa dữ liệu riêng hoặc nhãn từng mẫu vào thư mục bằng chứng công khai.

Trước phát hành còn cần xác nhận tự quét 1.1.2 và hộp thoại native trong browser
thật, dữ liệu tiếng Việt mới được chuyên gia xác minh, và CI xanh cho snapshot
mới sau khi được phép push. OCR/nhập vai tiếp tục hoãn. Các giới hạn nhãn và
khả năng bỏ sót của model phải luôn được hiển thị trung thực.
