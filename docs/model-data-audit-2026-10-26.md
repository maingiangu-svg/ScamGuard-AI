# Kiểm định nhãn và rò rỉ dữ liệu — 26/10/2026

**Kết luận: không đạt yêu cầu độc lập theo tên miền gốc; chưa chứng minh độc lập
chiến dịch và chưa xác minh độc lập được toàn bộ nhãn.** Việc kiểm định không
thay nhãn, chia lại dữ liệu gốc, huấn luyện, chạy lại dự đoán test hay đổi model.

## Phạm vi và tính truy xuất

Bộ hybrid hiện tại dùng SMS processed (3.857 mẫu train) và URL từ bundle
`20261025T152344Z` (40.004 mẫu train). Nhánh SMS gốc của bundle và nhánh URL
processed được kiểm tra riêng để đối chiếu; chúng không phải hai nhánh đang
được hybrid sử dụng.

Đã đối chiếu checksum nguồn CSV, model, dữ liệu SMS đóng băng, nguồn SmishX và
các tài liệu kiểm định PhishVN. Mã huấn luyện sau chuẩn hóa xuống dòng, mã sửa
dữ liệu và phiên bản sklearn khớp metadata bundle. Tất cả đầu vào được bảo vệ
giữ nguyên sau kiểm định.

`ml_model/models/split_ids.json` local **không thuộc đúng lượt huấn luyện URL
đang chạy**: nó ghi 39.983/10.017 mẫu train/test, trong khi model ghi
40.004/9.996. Không dùng tệp này để xác nhận độc lập. Kiểm định tái tạo bằng
đúng nguồn, mã, seed, cách lấy mẫu và chia tập đã ghi; không fit estimator.
Phần SMS tái tạo khớp toàn bộ chỉ số trong export cũ, phần URL không khớp.

Giới hạn truy xuất: phân hoạch tái tạo khớp công thức và số lượng của lượt
huấn luyện; export từng dòng cũ không được ràng buộc bằng checksum vào model
URL mới. Đợt huấn luyện tiếp theo phải lưu hash manifest từng tập cùng model.

## Tên miền gốc và nhóm chiến dịch

Dùng Public Suffix List đã ghim checksum, gồm các quy tắc nhiều cấp, wildcard,
exception và private suffix. Kiểm định bổ sung nhận dạng URL trần có đường
dẫn và URL defang; không chỉ lặp lại bộ trích xuất dùng khi huấn luyện.

| Thành phần | Cặp tập | Số tên miền gốc chung |
|---|---|---:|
| URL bundle — đang dùng | Train / test | **519** |
| SMS processed — đang dùng | Train / validation | 0 |
| SMS processed — đang dùng | Train / test | 0 |
| SMS processed — đang dùng | Validation / test | **1** |
| SMS gốc của bundle — đối chiếu | Train / test | 49 |
| URL processed — đối chiếu | Các cặp train/validation/test | 0 |

Ở URL bundle, 5.282 dòng train và 3.074/9.996 dòng test thuộc các tên miền
gốc chung. Ví dụ `askville.amazon.com` trong train và `www.amazon.com` trong
test cùng gốc `amazon.com`. Đây là vi phạm yêu cầu tách theo tên miền gốc;
không đồng nghĩa các URL này đều sai nhãn hoặc mức tăng điểm đánh giá đã
được định lượng.

Ở SMS processed, validation có `SMISHX-0011`, chứa URL trần
`grubhub.app.link/sms`; test có `SMISHX-0920`, chứa `qvay.app.link`.
Cả hai cùng gốc `app.link`. Bộ trích xuất cũ bỏ sót URL trần có TLD `.link`,
nên kiểm tra chỉ dùng parser cũ báo 0 giao nhau. Không sửa parser đóng băng
trong lần kiểm định này.

SMS gốc của bundle còn có 315 chữ ký mẫu câu chung giữa train và test. Chữ
ký này chỉ là dấu hiệu tương tự, không chứng minh cùng người gửi hoặc chiến
dịch. Tên miền nền tảng dùng chung cũng không tự chứng minh cùng chiến dịch.
Dữ liệu đang dùng thiếu campaign ID, bằng chứng đích chuyển hướng/capture,
sender/kit ID và mốc thời gian đầy đủ. Vì thế **không cấp chứng nhận độc lập
chiến dịch**. Các chuỗi tên miền có thể chỉ là dấu câu trong văn bản được
giữ thành danh sách mơ hồ riêng (50 dòng SMS processed), không tự coi là URL
đã xác nhận. Số 0 trong bảng chỉ áp dụng cho các chỉ báo trích xuất được.

## Nhãn: điều gì đã và chưa xác minh

Toàn bộ 4.858 dòng SMS processed (train/validation/test) khớp nội dung, nhãn
nguồn và quyết định review đã ghi. Với 143 dòng legacy bị thiếu trường
`source_record`, chỉ số nguồn được truy lại từ `OLD-N` và đối chiếu đúng bản
review gốc. Đây là kiểm tra tính truy xuất, không phải xác nhận sự thật của nhãn.

Đối chiếu nội dung chính xác với nhãn SmishX tìm được **14 trường hợp khác
nhãn: 10 train, 4 validation**. Tất cả đang mang 0 trong processed, còn nguồn
SmishX mang 1. Các nhóm gồm tin mời nhắn/gọi dịch vụ có phí, trúng thưởng,
dịch vụ nội dung, kết bạn và thông báo tài khoản. Phạm vi spam/smishing giữa
các nguồn có thể khác nhau; không tự đổi 0 thành 1 hoặc coi một nguồn luôn đúng.

Trong 3.857 mẫu train SMS:

- 497 mẫu khớp trực tiếp chính nguồn nhãn SmishX ban đầu; đây không phải một
  lượt gán nhãn độc lập thứ hai.
- 2 mẫu từ nguồn khác trùng nội dung và đồng ý với nhãn SmishX.
- 10 mẫu từ nguồn khác trùng nội dung nhưng khác nhãn SmishX.
- 3.348 mẫu không có nhãn đối chiếu chính xác trong nguồn người gán đã kiểm tra.

SMS gốc của bundle có thêm 27 trường hợp khác nhãn SmishX (21 train, 6 test).
Đây cũng là xung đột cần giải quyết về bằng chứng/phạm vi, không phải 27 lỗi
nhãn đã được chuyên gia kết luận.

Không có URL nào trong 50.000 URL bundle trùng chính xác với 81 trường hợp
nhị phân đủ bằng chứng trong bộ audit PhishVN có sẵn. Vì thế bộ audit này
**không xác nhận được đúng/sai độc lập cho 40.004 nhãn URL train**. Không lấy
điểm model, tên miền có vẻ chính thức, hoặc nhãn blocklist làm nhãn chuyên gia.
Kiểm chứng nhãn lịch sử cần capture/archive và thời điểm tương ứng; trạng thái
website hiện tại không đủ để sửa nhãn cũ.

Ngoài ra, 141 URL train và 35 URL test chứa dấu backslash hoặc ký tự xuống dòng
được ghi dưới dạng chuỗi literal. Một số bản ghi ghép đường dẫn và địa chỉ khác
bằng `\n`. Các dòng này cần cách ly để rà soát định dạng và đơn vị được gán nhãn.
Một URL có URL khác trong query chuyển hướng không tự bị coi là hỏng.

**Số nhãn chuyên gia mới tạo trong đợt này: 0.**

## Phương án sửa và bằng chứng có thể kiểm tra

Đã xuất kế hoạch cách ly theo thành phần liên thông gồm tên miền gốc, mẫu câu
và nhóm nguồn. Ưu tiên giữ nguyên test, loại validation chung nhóm với test,
và loại train chung nhóm với các tập giữ lại. Kế hoạch giữ nguyên nhãn và vai
trò nguồn để truy xuất; không chuyển dữ liệu test về train.

Sau khi áp dụng **kế hoạch trên giấy** vào các manifest, giao nhau tên miền
gốc và mẫu câu trích xuất được giữa các tập giữ lại đều bằng 0. Đây chưa phải
một model đã được sửa: trọng số hiện tại vẫn được học từ các phân hoạch cũ.
Kế hoạch này cũng không biến nhãn yếu thành nhãn đã xác minh, hoặc chứng minh
những chiến dịch không có metadata.

Thứ tự cần thực hiện tiếp: giải quyết xung đột/phạm vi nhãn, thu bằng chứng
nhãn URL, loại bản ghi hỏng, chốt các nhóm tách tập, rồi huấn luyện và đánh giá
lại trong một lượt mới có manifest được ghim checksum. Không dùng điểm 89 của
một link hoặc các kiểm thử phần mềm làm bằng chứng dữ liệu đạt chuẩn.

Các tệp dưới `ml_model/data/prepared/integrity_audit_2026-10-26-final/`:

- `report.json`: kết luận máy đọc được, checksum và số lượng.
- `*_partitions.csv/jsonl`: từng dòng trong các phân hoạch được kiểm tra.
- `cross_split_overlap.csv/jsonl`: tên miền/mẫu câu và ID ở từng tập.
- `label_verification_ledger.csv/jsonl`: trạng thái đối chiếu từng dòng.
- `label_conflicts_pending_review.csv/jsonl`: nội dung và nhãn đối chiếu cần xử lý.
- `url_format_issues_pending_review.csv/jsonl`: các URL có vấn đề định dạng.
- `active_training_label_review_queue.csv/jsonl`: nhãn train chưa đủ bằng chứng.
- `future_group_isolation_plan.csv/jsonl`: phương án cách ly cho lượt huấn luyện mới.
- `ambiguous_domain_mentions_pending_review.csv/jsonl`: các đề cập tên miền mơ hồ.

## Chạy lại và kiểm tra

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ml_model -p "test_*.py"
.\.venv\Scripts\python.exe -X utf8 ml_model\audit_training_integrity.py --output ml_model/data/prepared/integrity_audit_repeat_2026-10-26 --require-clean
```

66 kiểm thử Python đã qua, trong đó 10 kiểm thử dành cho công cụ kiểm định.
Lệnh kiểm định `--require-clean` trả mã **2**: chương trình đã chạy xong nhưng
dữ liệu không đạt điều kiện chứng nhận. Thư mục output phải mới để giữ nguyên
bằng chứng của các lượt trước. Không huấn luyện lại hoặc chạy lại dự đoán test.

## Nguồn đối chiếu

- [SmishX, revision được ghim](https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff): nhãn thủ công ba lớp; đối chiếu nguồn không phải thẩm định chuyên gia mới.
- [Nguồn Combined Smishing](https://github.com/shaghayegh-hp/Smishing_Dataset): công bố nhãn smishing dựa trên từ khóa.
- [PhishVN v4](https://data.mendeley.com/datasets/b97hxbxtpd/4): mô tả tầng bằng chứng, cách chia theo tên miền gốc và audit nhãn; không phải nguồn của 40.004 URL bundle.
- [Public Suffix List — quy tắc](https://github.com/publicsuffix/list/wiki/format): cơ sở tách hậu tố công cộng và tên miền gốc.
