# Bổ sung dữ liệu SMS tiếng Anh — 28/10/2026

Đã bổ sung **338 SMS tiếng Anh mang nhãn nguồn phishing, thuộc 102 nhóm**,
sau lọc ngôn ngữ, bảo vệ dữ liệu lịch sử, rà phạm vi bằng AI và giới hạn trùng
lặp. Gói train tiếng Anh cho lần học tiếp theo có **3.991 tin**, gồm **469
nhãn 1**; tỷ lệ dương tăng từ 3,59% lên **11,75%**. Không huấn luyện lại hoặc
thay model đang chạy. Đây là cải thiện dữ liệu, chưa phải bằng chứng tăng độ
chính xác mô hình.

## Kết quả và tệp sử dụng

| Đầu ra | Số mẫu | Trạng thái |
|---|---:|---|
| SMS train bổ sung | 338 | Nhãn nguồn giữ lại sau AI sàng lọc template; 102 nhóm |
| Train tiếng Anh gộp | 3.991 | 3.522 nhãn 0 và 469 nhãn 1; không trùng đầu vào mô hình |
| Ứng viên validation mới | 95 | 37 nhóm; chưa có nhãn dự án để đánh giá |
| Ứng viên test mới | 96 | 64 nhóm; chưa có nhãn dự án để đánh giá |
| Pool train tiếng Anh chờ rà | 3.957 | `label=null`, chặn học |
| SMS cách ly/ngoài ngôn ngữ/phạm vi/dư thừa | 24.182 | Chặn học; không chuyển sang test mới |
| URL từ hồ sơ chiến dịch | 3.003 | Không có verdict từng URL; chặn học |

Năm nhóm SMS bổ sung, validation, test, pool chờ rà và cách ly đối soát đủ
28.668 mẫu sau gộp; ledger đối soát đủ 68.029 dòng nguồn. Không cộng 3.991 tin
gộp vào tổng mẫu mới vì nó đã bao gồm train cũ và 338 tin bổ sung.

300 template train đã được AI đọc và ghi quyết định: giữ nhãn nguồn cho 261,
loại khỏi phạm vi 17 template quảng cáo, và giữ 22 template ở trạng thái chưa
rõ. Sau loại trùng train cũ có 3.417 mẫu qua sàng lọc phạm vi; giới hạn tối đa
3 mẫu/template và 20 mẫu/nhóm giữ lại 338 mẫu để tránh một cụm crypto lấn át
toàn bộ phần bổ sung. Các mẫu dư vẫn có hồ sơ nguồn và nằm ngoài tập học.

Các bản ghi từ nguồn mới trùng đầu vào train hiện tại được cách ly (55 mẫu
toàn pool, trong đó 7 mẫu đã qua rà phạm vi); không đếm chúng là dữ liệu mới.

Các tệp dưới `ml_model/data/prepared/english_expansion_2026-10-28/`:

- `sms_train_additions.csv/.jsonl`: riêng phần bổ sung.
- `sms_train_english_merged.csv/.jsonl`: train tiếng Anh đã gộp, dùng cho lượt học mới có protocol riêng.
- `sms_validation_candidates`, `sms_test_candidates`: các nhóm giữ riêng, chưa phải gold benchmark.
- `blind_holdout_review/`: hai biểu mẫu gán nhãn độc lập, một đại diện cho mỗi nhóm test; chưa có câu trả lời của người thật.
- `sms_training_review_pool`, `sms_quarantine`: hàng chờ rà và hàng bị chặn.
- `url_source_review_pool`: URL, ID chiến dịch và khoảng thời gian nguồn; nhãn dự án vẫn để trống.
- `source_membership`, `scope_decisions.json`, `group_frozen.json`, `historical_inputs.json`, `final_report.json`: truy xuất và checksum.

[Báo cáo JSON tổng hợp](english-data-expansion-2026-10-28.json) chứa số liệu,
checksum và kiểm tra độc lập trên đầu ra cuối. Dữ liệu thô và bản xuất lớn ở
thư mục cục bộ được Git bỏ qua.

## Nguồn mới

[SMS Phishing Data Releases của NCSU](https://github.com/wspr-ncsu/sms-phishing),
gắn với bài *On SMS Phishing Tactics and Infrastructure*, IEEE Symposium on
Security and Privacy 2024. Dữ liệu được thu từ các SMS gateway công khai; đây
là dữ liệu mới đối với dự án, không phải SMS mới thu trong năm 2026.

- Revision: `a4f18cedc9909cbf8234eea3c2028080a1e95cd4`.
- `phishing_messages.csv`: 68.029 dòng dữ liệu thực tế; SHA-256
  `d125c394af792faeb2b71b3f7100cad3b4cece02aff78cb4ec1fb9e7db90f230`.
- `phishing_campaigns.csv`: 35.128 dòng; SHA-256
  `f23a56037ca3e4d5aceb34536c11c7fff37174f7618ff943e855820f550600a5`.
- Giữ nguyên LICENSE MIT, README, bài báo và manifest URL/checksum của kho.

Nhãn nguồn đến từ quy trình chọn SMS có URL được các dịch vụ threat intelligence
nhận dạng phishing. Nó không phải nhãn chuyên gia mới của dự án và không đảm bảo
mọi dòng phù hợp định nghĩa smishing của dự án. Chính tệp CSV không có cột nhãn
riêng; `source_label=1` trong bản chuẩn bị biểu diễn tư cách thành viên trong
bản phát hành phishing của tác giả, có ghi provenance rõ ràng.

## Xử lý và giới hạn

CSV SMS có sáu tên cột nhưng tất cả 68.029 dòng có bảy trường. Bộ đọc xác nhận
đúng checksum/độ rộng, giữ nguyên message và trường thứ năm chưa có tên, rồi
đọc hai trường thời gian cuối theo vị trí phải. Không tự đặt ý nghĩa cho trường
thừa. Không dùng số điện thoại đích làm nhãn hoặc bằng chứng chiến dịch.

Gộp trùng theo đầu vào SMS hiện có còn 28.668 mẫu. `langid==1.1.6` chạy offline
trên toàn bộ 97 ngôn ngữ, bỏ URL khi nhận diện, yêu cầu tối thiểu năm từ và điểm
chuẩn hóa từ 0,95. Có 8.598 mẫu vượt bộ lọc tiếng Anh này. Đây là sàng lọc tự
động, không phải xác minh ngôn ngữ của con người hay bảo đảm đúng 95%.

Các bản ghi gộp giữ danh sách ID nguồn. Gom nhóm bảo thủ dùng nội dung, mẫu câu,
cả PSL private và ICANN owner, cùng cosine ký tự từ 0,80. Giữ tên miền của mọi
bản nguồn trước gộp, không chỉ URL trong tin đại diện. Đối chiếu các vai trò
train/validation/test/cách ly lịch sử và corpus SMS thô đã tiếp xúc; dữ liệu
cũ không được gọi lại là test mới. Các nhóm test/validation/cách ly cũ chặn
cả thành phần liên thông khỏi học.

Nhóm nguồn mới được phân train/validation/test theo hash cố định trước khi rà
phạm vi nhãn. Chỉ các template train được chọn mới được AI đọc nội dung; quyết
định gắn với checksum mẫu, ID và nội dung đại diện. Giữ nhãn nguồn cho mẫu có
nội dung phishing rõ; quảng cáo casino, OTP/thông báo mơ hồ hoặc trường hợp
chưa đủ căn cứ vẫn không có nhãn dự án để học. Các biến thể cùng template kế
thừa kết quả sàng lọc template; không gọi đó là kiểm định độc lập từng tin.

Giới hạn 3 mẫu/template và 20 mẫu/nhóm được chốt sau khi xem phân bố nguồn,
không sử dụng điểm mô hình hoặc kết quả test. Việc giữ mẫu theo thứ tự SHA-256
của ID là xác định và đã có kiểm thử chống phụ thuộc thứ tự đầu vào.

Nguồn mới tập trung SMS phishing; không dùng nó để chứng nhận bộ test cân bằng
hoặc đại diện lưu lượng thực tế. Các nhóm giữ riêng cần gán nhãn độc lập, cùng
bổ sung tin hợp lệ mới trước khi hình thành benchmark. Không chuyển các nhóm
đó sang train để tăng số lượng.

Danh sách URL từ tệp chiến dịch là nguồn ứng viên có ngữ cảnh và thời gian.
Không có verdict riêng cho từng URL trong bản xuất; có thể chứa link opt-out
hoặc link lành tính. Giữ `label=null`, `do_not_train=true`. Ngôn ngữ SMS không
được chép thành ngôn ngữ trang đích. Không mở bất kỳ URL nào trong dữ liệu.

## Tệp cục bộ và cách chạy

Nguồn nằm dưới `ml_model/data/reference/english_expansion_2026-10-28/`.
Gói chuẩn bị nằm dưới `ml_model/data/prepared/english_expansion_2026-10-28/`.
Hai thư mục dữ liệu đều được Git bỏ qua; không đưa nội dung SMS thô vào báo cáo
công khai. Dữ liệu gốc và các thí nghiệm đã khóa được giữ nguyên.

```powershell
.venv/Scripts/python.exe -m pip install --no-deps --target .local-runtime/english-data-libs -r ml_model/requirements-english-data.txt
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
.venv/Scripts/python.exe -X utf8 ml_model/english_data_expansion.py intake --output ml_model/data/prepared/english_expansion_NEW
.venv/Scripts/python.exe -X utf8 ml_model/english_data_expansion.py group --output ml_model/data/prepared/english_expansion_NEW
# Ghi scope_decisions.json theo đúng review sample đã đóng băng, rồi:
.venv/Scripts/python.exe -X utf8 ml_model/english_data_expansion.py finalize --output ml_model/data/prepared/english_expansion_NEW
```

`intake` yêu cầu nguồn đã tải đúng manifest; không tự cập nhật nguồn qua mạng.
Không chạy lại bước đã đóng băng hoặc ghi đè gói hoàn tất. Môi trường suy luận
không được thêm thư viện nhận diện ngôn ngữ; thư viện đó ở thư mục công cụ riêng.

## Kiểm tra hoàn tất

154 kiểm thử Python đều qua, gồm năm kiểm thử mới cho bộ đọc CSV, nhãn/phạm vi,
chặn holdout, Unicode và giới hạn mẫu dư thừa. Lỗi quyền thư mục tạm Windows
ở lượt kiểm thử đầu được giải quyết bằng thư mục tạm trong workspace; không
bỏ qua hoặc sửa nhẹ điều kiện kiểm thử cũ.

Kiểm tra trực tiếp đầu ra cuối xác nhận CSV/JSONL train khớp nội dung và nhãn,
không trùng đầu vào mô hình, tuân thủ giới hạn mẫu và đối soát đủ nguồn. Kiểm
tra tên miền gồm mọi bản nguồn trong các mẫu gộp, không chỉ tin đại diện:
giao nhau phần train mới với validation/test mới đều bằng 0. Toàn bộ tệp model
và 133 tệp lịch sử/nguồn được bảo vệ giữ nguyên checksum. Không chấm test mới,
không tạo nhãn chuyên gia và không thay model `url-ensemble-20261027`.
