# Dữ liệu SMS lừa đảo tiếng Anh — 25/10/2026

**Đính chính và cập nhật:** tệp SmishX gốc có nhiều ngôn ngữ, không phải toàn bộ
1.200 tin đều là tiếng Anh. Các tệp có tên `smishx_english_*` của đợt tải đầu
là bản xuất nguồn chưa lọc. Đợt tiếp theo đã lọc còn 1.017 mẫu phù hợp ngôn ngữ
và phạm vi, xử lý nhóm và hoàn thành huấn luyện thử nghiệm. Xem
[báo cáo mới](smishx-training-2026-10-25.md) và dữ liệu trong
`ml_model/data/prepared/smishx_training_2026-10-25/`.
Phần bên dưới ghi lại trạng thái tại thời điểm tải ban đầu.

Đã tải và xuất dữ liệu tiếng Anh vào
`ml_model/data/prepared/english_sms_2026-10-25/`. Đây là bước cung cấp dữ liệu;
chưa thêm các mẫu mới vào huấn luyện hoặc thay mô hình ứng dụng. MIMICS-3500
không thuộc phạm vi bổ sung này theo quyết định của người dùng.

## Nguồn ưu tiên: SmishX, SOUPS 2025

- [Kho chính thức](https://github.com/yizhu-joy/SmishX).
- [Bài nghiên cứu tại USENIX](https://www.usenix.org/system/files/soups2025-wang.pdf), mục 4.1.
- Commit cố định: `116a8c827741e0572563f678d25ed04306b1e3ff`.
- Tệp gốc: `data/dataset.csv`, SHA-256
  `8d65e373b17477c34e8f1c619e6f59d249e8fca21276cabdd03a55d11a469285`.

| Nhãn gốc | Số tin | Nhãn nhị phân smishing |
|---|---:|---:|
| smishing | 259 | 1 |
| spam | 319 | 0 |
| legitimate | 622 | 0 |
| Tổng | 1.200 | 259 nhãn 1, 941 nhãn 0 |

Bài nghiên cứu mô tả một nhà nghiên cứu gán nhãn toàn bộ 1.200 tin và xây dựng
codebook; người thứ hai gán nhãn độc lập toàn bộ rồi hai người giải quyết bất
đồng. Vì vậy nguồn nhãn là **gán nhãn thủ công của nhóm nghiên cứu**, không phải
nhãn mới do Codex hoặc quy tắc từ khóa tạo ra. Dự án chưa xác minh lại từng mẫu
và không khẳng định trình độ chuyên gia của từng người gán nhãn.

Nguồn có SMS tiếng Anh, nhưng không có cột ngôn ngữ theo từng dòng. Bản xuất
ghi `language_hint=en` cùng giới hạn này; không dịch các tin khác sang tiếng Anh.
Giữ nội dung gốc và một bản NFC, gộp khoảng trắng để đọc. Giữ nguyên nhãn ba lớp.
Trong paper SmishX, spam và phishing cùng nằm trong nhóm malicious; dự án này
**không** chép cách gộp đó thành nhãn smishing. Nhãn 0 không chứng nhận rằng một
quảng cáo hoặc dịch vụ hợp pháp, đáng tin hay phù hợp mọi phạm vi phân loại fraud.

Kho công bố giấy phép MIT. Dữ liệu có thành phần lấy từ các nguồn thứ ba; giữ
giấy phép kho, trích dẫn bài báo và nguồn gốc, không tự suy thêm quyền cho dữ
liệu nguồn thứ ba.

### Tệp đã chuẩn bị

- `smishx_english_human_labels.csv` và `.jsonl`: toàn bộ 1.200 mẫu, nhãn gốc,
  nhãn nhị phân, nguồn gán nhãn, checksum và thông tin trùng với dữ liệu hiện có.
- `smishx_english_smishing_259.csv` và `.jsonl`: riêng 259 mẫu nguồn gán nhãn smishing.
- `smishx_existing_holdout_overlap.csv` và `.jsonl`: 177 dòng trùng chuẩn hóa với
  các tập validation/test hiện có; phải tiếp tục bảo vệ khi bổ sung dữ liệu học.
- `smishx_existing_label_disagreements.csv` và `.jsonl`: 17 dòng có nhãn khác với
  ít nhất một bản ghi đã rà soát của dự án, để đối chiếu nguồn và phạm vi nhãn.
- `smishx_preparation_report.json`: số liệu và metadata đầy đủ.

Có 95 dòng trùng khi dùng bộ chuẩn hóa đầu vào mô hình, còn 1.105 nội dung khác
nhau theo tiêu chí đó. Có 606 dòng trùng chuẩn hóa với các nguồn SMS cũ. Đây là
nguồn bổ sung nhãn có giá trị, **không phải một bộ kiểm tra độc lập mới nguyên**.
Sàng lọc này mới đối chiếu trùng nội dung chuẩn hóa; trước khi tích hợp vẫn phải
nối nhóm gần trùng, khuôn mẫu và tên miền rồi giữ các nhóm ngoài tập học riêng.
Mọi dòng mới hiện được đánh dấu `do_not_train=true` để tránh vô tình gộp trước
khi hoàn tất bước này. Nhãn từ nguồn vẫn được giữ đầy đủ.

Ba cột phụ URL/phone/email đều có hai dòng không phải cờ nhị phân chuẩn, ví dụ
`1 1`. Giữ giá trị gốc, không đoán hoặc đưa chúng thành đặc trưng mô hình. Số
cờ URL trong CSV công khai khác số bài báo mô tả; thống kê bản xuất dựa trên
tệp thực tế. Không truy cập các URL trong SMS khi tải và chuẩn bị dữ liệu.

## Nguồn bổ sung lớn: IMC 2025

- [Kho chính thức](https://github.com/reportsmishing/Smishing-Dataset-IMC25).
- [Bài nghiên cứu của tác giả](https://sharad1126.github.io/files/IMC_2025_Smishing.pdf), DOI `10.1145/3730567.3764431`.
- Commit: `a6175560b57387199871e51fbef6bc523d2516b4`.
- Giấy phép CC BY 4.0.
- Tệp gốc có 33.869 dòng; lọc cột ngôn ngữ nguồn `English` được **22.078 dòng**.
- Sau gộp trùng theo bộ chuẩn hóa mô hình còn **15.477 nội dung**. Đây chưa phải
  số chiến dịch hoặc số nhóm độc lập.

| Loại nguồn gán | Số dòng tiếng Anh |
|---|---:|
| banking | 10.495 |
| delivery | 1.676 |
| government | 1.922 |
| telecom | 1.630 |
| hey mum/dad | 77 |
| wrong number | 304 |
| others | 4.586 |
| spam | 1.387 |
| thiếu loại | 1 |

**Nhãn loại scam và ngôn ngữ do GPT-4o tạo.** Paper báo cáo kiểm tra thủ công
150 mẫu để đánh giá và chỉnh prompt; tệp công khai không chỉ ra 150 dòng đó.
Không đánh dấu các dòng là được con người kiểm định. Sáu loại scam cụ thể chỉ
được ghi thành đề xuất nhãn nguồn yếu, không phải nhãn cuối của dự án. Các dòng
Others/Spam vẫn cần xem phạm vi thay vì tự gán 1 hoặc coi chắc chắn không lừa đảo.

Các tệp:

- `imc25_english_original_source_labels.csv` và `.jsonl`: 22.078 dòng tiếng Anh
  gốc cùng loại scam do nguồn gán, không dùng trường bản dịch.
- `imc25_english_unique_review_pool.csv` và `.jsonl`: 15.477 nội dung sau gộp
  trùng; giữ danh sách ID nguồn và các trường hợp loại nguồn mâu thuẫn.
- `preparation_report.json`: thống kê nguồn IMC và các bản tách tiếng Anh cũ.

Mọi mẫu IMC mới có `label=null`, `do_not_train=true` và trạng thái chờ rà phạm
vi nhãn. Nguồn đã ẩn URL thành placeholder nên không ghép chúng với URL tự tạo
hoặc sử dụng như các cặp SMS–URL thật. Đây là nguồn để mở rộng học sau khi rà,
không thay thế bộ kiểm tra có nhãn thủ công.

## Dữ liệu tiếng Anh đã được dùng trong lần huấn luyện trước

| Tập | Tổng | Nhãn smishing 1 | Nhãn 0 |
|---|---:|---:|---:|
| Train | 3.584 | 68 | 3.516 |
| Validation | 891 | 15 | 876 |
| Test | 1.110 | 18 | 1.092 |

Đã xuất riêng thành `existing_english_train/validation/test.csv` và `.jsonl`,
cùng `existing_english_smishing_train/validation/test.csv` và `.jsonl` chỉ chứa
nhãn 1. Giữ nguyên phân vùng, nhãn và nguồn nhãn nguồn/AI; không xem các nhãn
này là kiểm định thủ công chỉ vì được đặt cùng thư mục với SmishX.

Tất cả tệp nguồn tải được nằm trong
`ml_model/data/reference/english_sms_2026-10-25/`, kèm manifest URL, commit,
checksum và giấy phép. Đã kiểm tra đủ số dòng, tập giá trị nhãn, checksum,
đối chiếu trùng và xác nhận checksum của mô hình cùng thực nghiệm đã khóa không đổi.
JSONL dùng Unicode escape để các ký tự phân cách dòng Unicode bên trong SMS
không làm bộ đọc hiện có tách sai bản ghi; nội dung gốc sau giải mã vẫn giữ nguyên.
Các bản CSV và JSONL đã được đối chiếu khớp số dòng và nội dung từng SMS.
