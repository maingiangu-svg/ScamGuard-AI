# Bổ sung dữ liệu và huấn luyện có giám sát — 25/10/2026

Đã tải, kiểm tra checksum, rà phạm vi nhãn, chuẩn hóa, chia nhóm, huấn luyện và
đánh giá một lần bản thử nghiệm với hai nguồn mới. Mô hình đang chạy trong ứng
dụng được giữ nguyên vì bản thử nghiệm còn báo nhầm nhiều với tiếng Việt và
bỏ sót nhiều URL trong tập kiểm tra của nguồn.

## Nguồn thực sự sử dụng

| Nguồn | Dữ liệu gốc | Nguồn nhãn và cách sử dụng |
|---|---:|---|
| [SMS Phishing Dataset, Mishra & Soni, v1](https://data.mendeley.com/datasets/f45bkkt8pr/1) | 5.971 SMS | Giữ nhãn gốc ham/spam/smishing. Rà nội dung 240 mẫu bằng AI để đối chiếu phạm vi smishing của dự án; chưa phải chuyên gia kiểm định. |
| [PhishVN, dataset v4 / release v3.1.0](https://data.mendeley.com/datasets/b97hxbxtpd/4) | 53.116 URL | Chỉ lấy positive tầng gold và benign tầng gold/silver. Nhãn positive của nguồn gồm các dạng abuse khác, không chỉ trang lấy cắp thông tin. |
| [Bộ kiểm định thủ công do tác giả PhishVN công bố](https://github.com/vuthainguyen1602/phishvn/tree/2e2974144ee2e77170ddf06e1ec615d8586854a0/docs/verify) | 200 trường hợp | Ghép kết quả hai người gán nhãn và phân xử bất đồng. Giữ riêng 81 trường hợp phishing/legitimate có loại bằng chứng archive/capture/urlscan/registry. Không đưa vào học. |

Hai bộ Mendeley công bố giấy phép CC BY 4.0. Kho kiểm định được cố định ở commit
`2e2974144ee2e77170ddf06e1ec615d8586854a0`. Đây là kiểm định do tác giả công bố;
dự án không kiểm tra lại từng trang đích và không khẳng định người gán nhãn là
chuyên gia. Không truy cập các URL nguy hiểm trong dữ liệu để huấn luyện.

Các tin tiếng Việt và SMS cũ đủ điều kiện sau đợt rà soát trước được giữ lại,
với nguồn nhãn riêng. Hai tin cho thuê tài khoản `VITRAIN-2262` và
`VITRAIN-2385` đã vào tập train với nhãn 1 theo quyết định của người dùng.
Các tập validation/test tiếng Việt trước đây tiếp tục được giữ riêng.

## Những trường hợp bị tách ra

- 63 SMS trong mẫu rà soát chưa đủ căn cứ chốt nhãn.
- 438 SMS mang nhãn smishing của nguồn nhưng chưa rà nội dung theo phạm vi dự án.
- 43 SMS bị chặn vì trùng nhóm với tập đã giữ riêng hoặc tên miền trong kiểm định URL.
- 35.018 URL tầng bronze hoặc positive tầng silver chưa đủ điều kiện.
- 2.411 URL có tên miền đăng ký trùng bộ kiểm định thủ công và 111 URL trùng tên miền SMS.

Tệp quarantine giữ nội dung gốc, nhãn gốc và lý do. Sửa định dạng không biến
nhãn nguồn/nhãn AI thành nhãn chuyên gia. Spam quảng cáo không tự động là smishing.
Không suy nhãn URL từ nhãn SMS hoặc ghép SMS với URL bất kỳ.

## Chia tập và huấn luyện

| Nhánh | Train | Validation | Test |
|---|---:|---:|---:|
| SMS đã gộp và loại trùng | 3.725 (122 nhãn 1) | 932 (31 nhãn 1) | 1.164 (38 nhãn 1) |
| URL đạt chính sách nguồn | 9.123 (1.284 nhãn 1) | 3.826 (321 nhãn 1) | 2.627 (69 nhãn 1) |
| URL kiểm định thủ công, giữ riêng | 0 | 0 | 81 (22 phishing, 59 legitimate) |

Nhóm SMS nối các bản gần trùng, cùng khuôn mẫu và cùng tên miền đăng ký. Tên
miền đăng ký được tính bằng Public Suffix List có checksum, kể cả hậu tố
`com.vn`, `co.uk`, quy tắc wildcard và ngoại lệ. Không có nhóm hoặc tên miền
đăng ký trùng giữa train/validation/test; nhánh URL còn loại mọi tên miền SMS.
Toàn bộ 200 trường hợp kiểm định, tương ứng 192 tên miền đăng ký, đều được giữ
ngoài các tập học và chọn mô hình, kể cả các trường hợp không dùng để chấm điểm.
Điều này không chứng minh độc lập hoàn toàn giữa mọi chiến dịch lừa đảo.

Nhánh URL giữ test của nhà cung cấp. Vì validation gốc không có positive tầng
gold, một phần nhóm trong train gốc được tách làm validation rồi thêm benign
validation gốc. Không chuyển test gốc vào train hoặc validation.

SMS thử hai cấu hình TF-IDF word và word+character với Logistic Regression,
trọng số mẫu tiếng Việt cố định bằng 3. URL dùng mô hình đặc trưng từ URL hiện
có của dự án. Chỉ dùng đặc trưng tính lại từ URL; không đưa source, tier,
status, scenario, split hoặc nhãn vào đặc trưng. HTTP/HTTPS được quy về cùng
scheme để tránh học dấu hiệu giả do quy trình thu thập. URL gốc vẫn được lưu.

Nhánh kết hợp dùng điểm text ngoài fold theo nhóm và URL thực sự có trong SMS.
Chọn mô hình/ngưỡng theo F2 validation với tỷ lệ báo nhầm validation tối đa 10%.
Validation chọn **word+character cho SMS, không dùng điểm fusion**, ngưỡng SMS
0,39; ngưỡng URL 0,22. Đây là ngưỡng của bản thử nghiệm, không thay chính sách
30/80 trong ứng dụng. Không điều chỉnh ngưỡng theo kết quả test bên dưới.

## Kết quả thực tế sau khi khóa mô hình

| Tập kiểm tra | Phát hiện đúng nhãn 1 | Bỏ sót | Báo nhầm nhãn 0 | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| SMS, nhãn nguồn/AI | 36/38 | 2 | 17/1.126 | 67,9% | 94,7% |
| Riêng tiếng Việt trong SMS test | 20/20 | 0 | 8/34 | 71,4% | 100% |
| URL, nhãn nguồn | 34/69 | 35 | 139/2.558 | 19,7% | 49,3% |
| URL, kiểm định thủ công có bằng chứng | 16/22 | 6 | 7/59 | 69,6% | 72,7% |

Tập tiếng Việt 70 tin cũ chỉ là chẩn đoán được xem lại: phát hiện 17/17 nhưng
báo nhầm 20/53. Không coi đây là bộ kiểm tra mới. Các tập SMS vẫn chủ yếu là nhãn
AI hoặc nhãn nguồn, chưa có một bộ tiếng Việt được xác minh độc lập đầy đủ.
Tập URL nguồn cũng đo mục tiêu abuse rộng hơn tập kiểm định credential-phishing.
Không gộp các số liệu thành một độ chính xác duy nhất hoặc suy ra hiệu quả thực tế.

Chưa triển khai bản mới. Cần bổ sung kiểm định độc lập SMS tiếng Việt, thêm các
tin quảng cáo hợp lệ khó phân biệt và cải thiện độ ổn định URL trên tập validation
mới trước khi cân nhắc thay mô hình. Giữ test đã dùng làm hồ sơ kết quả; các vòng
phát triển tiếp theo cần một tập đánh giá cuối mới. Không so với điểm mô hình cũ
trên các nguồn này vì dữ liệu học cũ có thể đã chứa các mẫu trùng.

## MIMICS-3500: đã tìm nhưng chưa lấy được dữ liệu

**Cập nhật ngày 25/10/2026 sau khi người dùng cung cấp trang GVIS:** đã xác nhận
[trang cấp dữ liệu chính thức của nhóm nghiên cứu](https://gvis.unileon.es/datasets-mimics-3500/).
Bộ dữ liệu được cấp theo yêu cầu qua email `gvis@unileon.es`, chưa có tệp tải
trực tiếp trên trang. Yêu cầu cần nêu tên cơ sở, mô tả dự án và mục tiêu nghiên
cứu cụ thể. Phải gửi từ email của cơ sở; nếu là sinh viên, người hướng dẫn tại
cơ sở đó phải đứng ra gửi yêu cầu. Trang không công bố thời hạn phản hồi hoặc
giấy phép tái sử dụng cụ thể; cần xác nhận điều kiện khi được cấp dữ liệu.
Đợt tìm trước đã bỏ sót trang này. Chưa gửi yêu cầu, chưa nhận dữ liệu và chưa
đưa MIMICS vào huấn luyện. Báo cáo và checksum của lần huấn luyện đã khóa được
giữ nguyên; cập nhật này ghi nhận đường tiếp cận vừa được xác minh.

Đã kiểm tra [bài nghiên cứu chính thức](https://doi.org/10.1016/j.engappai.2025.112864),
hồ sơ DOI, kho dữ liệu và mã nguồn công khai, cùng
[hồ sơ Đại học León](https://hdl.handle.net/10612/27150).
Chưa tìm được tệp dữ liệu MIMICS-3500 có thể xác minh nguồn và điều kiện sử dụng.
Hồ sơ trường hiện liệt kê một tệp PDF bài báo, với trạng thái embargo đến
31/12/2028. **Đây là hạn truy cập bài báo, không phải bằng chứng rằng bộ dữ liệu
bị embargo đến ngày đó.** Những kho mang tên MIMICS nhưng thuộc tác vụ khác
không được thay thế cho bộ này. MIMICS-3500 đóng góp **0 mẫu** vào lần huấn luyện.

Bằng chứng đã lưu tại `ml_model/data/reference/external_2026-10-25/`, gồm
`mimics_unileon_access.json`, `mimics_unileon_files.json` và metadata tìm kiếm.
Không tự tạo dữ liệu rồi ghi tên nguồn MIMICS; chưa gửi thư cho tác giả.

## Tệp kết quả và kiểm tra

Các tệp dưới đây ở `ml_model/data/prepared/external_training_2026-10-25/`:

- `sms_train.csv`, `sms_validation.csv`, `sms_test.csv`: dữ liệu SMS được sử dụng.
- `url_train.csv`, `url_validation.csv`, `url_test.csv`: dữ liệu URL được sử dụng.
- `sms_quarantine.csv`, `url_quarantine.csv`: các trường hợp bị tách ra và lý do.
- Các bản `.jsonl` tương ứng giữ kiểu dữ liệu và nguồn nhãn để xử lý bằng chương trình.
- `*_predictions.csv`, `*_errors.csv`: dự đoán và lỗi cụ thể của từng tập.
- `selection_frozen.json`: mô hình, ngưỡng, checksum dữ liệu/mã trước khi test.
- `research_bundle.pkl`: mô hình đã học; chỉ nạp bằng mã nghiên cứu trong dự án.
- `preparation_report.json`, `final_report.json`, `verification_report.json`: báo cáo đầy đủ.

37 kiểm thử Python đã qua. Một phép đảo nhãn cố ý đã làm kiểm thử thất bại rồi
được khôi phục đúng byte. Đối chiếu độc lập từ các dự đoán lưu sẵn khớp mọi ma
trận lỗi trong báo cáo. Toàn bộ 5.971 SMS và 53.116 URL gốc được đối chiếu đủ sau
khi gộp/tách; checksum dữ liệu cũ, nguồn tải và mô hình ứng dụng đều giữ nguyên.
Các bước select/test từ chối chạy lại để tránh chọn mô hình theo test.

Checksum các tệp tải chính:

```text
Dataset_5971.zip
9bbf3188fdad81495d8e82825648b9b63b53fc86841a3d26c02629990b233cc3
PhishVN_v3.1.0_open.zip
308351e9d0c0fca13a81f2f63524a7dee08ccba6c775848d125b3da5525d0ab5
public_suffix_list.dat
0232f4df0831911356e8ee1f4d5c3b6b12c0ed3f6bd66b0f81c8ab5d3d49e9ca
```

Lệnh thử mô hình và quy trình các bước có trong `ml_model/README.md`.
