# Dữ liệu tiếng Việt sau rà soát và huấn luyện — 27/10/2026

Đã kiểm tra toàn bộ 2.991 SMS, chuẩn hóa quy trình ba nhóm, rà mới 401 bản ghi
bằng AI, chuẩn bị phiếu mù 500 mẫu, đóng băng dữ liệu và huấn luyện một model
nghiên cứu riêng. **Chưa có bộ test mới gồm 300–500 SMS thật được hai người xác
minh độc lập. Model nghiên cứu chưa đủ kết quả để thay model đang chạy.**

Người dùng không có SMS cá nhân để cung cấp và cho phép AI gán nhãn, hỏi lại
các trường hợp khó. Các câu trả lời trong chat đã chốt: tin nhắc nợ hoặc người
quen xin tiền thiếu ngữ cảnh để chưa xác định; quảng cáo cờ bạc/vay tiền đơn
thuần là spam; giữ quyết định cũ về cho thuê tài khoản ngân hàng thuộc phạm vi
lừa đảo. Nhãn AI và quyết định người dùng không được nâng thành nhãn chuyên gia.

## Dữ liệu và phân vùng thực tế

Nguồn: [Vietnamese SMS Dataset](https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_dataset),
giấy phép CC BY 4.0, revision đã ghim của dự án. Tác giả mô tả nguồn là tin nhắn
thật; dự án chưa xác minh độc lập tuyên bố đó cho từng bản ghi. Nhãn nguồn gộp
spam/scam, vì vậy không tự chuyển toàn bộ nhãn 1 thành smishing. Ngày trong CSV
được giữ nguyên như metadata nguồn, không tự coi là ngày nhận tin đã xác thực.

Đối chiếu 121 tệp lịch sử, gồm 205.763 cặp nội dung/vai trò khác nhau. Các nhóm
nối theo nội dung, template, tên miền PSL/ICANN và cosine char-ngram từ 0,80.
Nhóm từng có test/validation hoặc quarantine được bảo vệ, kể cả khi nối qua
một bản ghi lịch sử. Đây là kiểm tra theo đại diện nội dung/tên miền; không
chứng minh độc lập chiến dịch thực tế.

| Trạng thái | Số mẫu |
|---|---:|
| Ứng viên train sau kiểm tra bảo thủ | 373 |
| Giữ riêng theo nhóm test lịch sử | 1.196 |
| Giữ riêng theo nhóm validation lịch sử | 175 |
| Cách ly hoặc thuộc nhóm từng cách ly | 1.247 |
| Tổng | 2.991 |

Không diễn giải 1.247 mẫu cách ly là 1.247 nhãn sai. Một tên miền dùng chung
hoặc một template thuộc nhóm cách ly có thể chặn nhiều tin khác nhau.

Rà mới 401 bản ghi và tái sử dụng các quyết định review cũ có truy vết tạo ra
1.128 mẫu có nhãn nội dung: 464 hợp lệ, 440 spam, 224 nghi lừa đảo. 1.863 mẫu
còn lại thiếu review đủ căn cứ hoặc chưa xác định. Trong 373 ứng viên train,
218 mẫu có nhãn dùng được: 146 hợp lệ, 44 spam, 28 nghi lừa đảo; 155 mẫu chưa
xác định không được fit. Không nối cả 1.128 mẫu vào train vì nhiều mẫu phải
giữ riêng hoặc cách ly.

CSV xuất cho người rà soát/model đã che email, các chuỗi số dài, thông tin
mật khẩu nhận diện được, và các tên/địa chỉ/đường dẫn cá nhân phát hiện trong
các mẫu đã đọc. Bản gốc và hash giữ cục bộ để truy vết. Kiểm tra này chưa phải
chứng nhận không còn PII trên toàn bộ dữ liệu; các gói không được đưa vào public/.

## Thí nghiệm có giám sát

Một cấu hình đã định trước: pipeline word+character TF-IDF và Logistic Regression
C=1, trọng số lớp cân bằng, quyết định argmax ba nhóm. Dùng 3 fold theo nhóm
trong train để chẩn đoán phát triển; từ vựng được fit lại bên trong mỗi fold.
Fit cuối trên 218 mẫu thuộc 189 nhóm, đóng băng dữ liệu, code và model trước
khi chấm chẩn đoán lịch sử. Không điều chỉnh tham số/ngưỡng theo kết quả đó.

| Chỉ số | OOF chỉ trong train | Chẩn đoán lịch sử |
|---|---:|---:|
| Số mẫu | 218 | 643 |
| Accuracy ba nhóm | 86,24% | 74,81% |
| Macro F1 | 78,03% | 72,48% |
| Precision nhóm nghi lừa đảo | 73,91% | 80,18% |
| Recall nhóm nghi lừa đảo | 60,71% | 47,85% |

Chẩn đoán lịch sử có 637 nhãn AI và 6 quyết định người dùng, thuộc 476 nhóm;
553/1.196 mẫu giữ riêng còn chưa xác định và không được chấm. Accuracy có khoảng
bootstrap 95% theo nhóm **69,16%–79,91%**, không bao quát sai số của nhãn nguồn/AI.
Phát hiện 89/186 mẫu nghi lừa đảo, bỏ sót 97, báo nhầm 22 mẫu còn lại.

Kết quả cho thấy nhánh ba nhóm còn thiếu dữ liệu lừa đảo và chưa đủ tin cậy để
đưa vào ứng dụng. Không dùng các điểm trên như hiệu quả trên SMS thật mới.
Model cũ có thể từng học các mẫu trong những bộ chẩn đoán này; không trình bày
so sánh tổng quát hóa công bằng với model sản phẩm trên chúng.

Bundle và manifest sản phẩm giữ nguyên SHA256 trước/sau. Model ba nhóm nghiên
cứu được lưu riêng, chưa tích hợp hợp đồng API hai nhóm và chưa triển khai.

## Thu thập công khai và bộ test mới

Đã ghi sáu nguồn công khai vào `public_source_candidates.json`, gồm cảnh báo
từ ngân hàng/cơ quan nhà nước và hai trích đoạn có dẫn nguồn. Các trang như
[Techcombank](https://techcombank.com/thong-tin/thong-bao/canh-bao-thu-doan-lua-dao-email-tin-nhan-gia-mao-ngan-hang)
và [cảnh báo Vietcombank ngày 13/10/2026](https://www.vietcombank.com.vn/vi-VN/Trang-thong-tin-dien-tu/Articles/2026/10/13/2026_MKTTT_Website_Luu-y-doi-diem-VCB-Loyalty-an-toan)
có ích để đối chiếu thủ đoạn. Chúng không cung cấp một corpus SMS có nhãn mới
và quyền tái sử dụng rõ cho từng tin. **Số SMS thật mới được nhận vào benchmark: 0.**

Biểu mẫu thu nhận yêu cầu nội dung gốc, nguồn, ngày nhận nếu biết, ngày xuất bản
riêng, bằng chứng quyền sử dụng, loại nguồn và metadata chiến dịch nếu thực sự
có. Trích đoạn, nội dung minh họa, bản dịch và tin do AI tạo không được tự đổi
thành tin đã nhận. Không cần truy cập đường dẫn nguy hiểm trong SMS.

Hai phiếu mù mỗi phiếu 500 mẫu đã tạo; cả 500 trường hợp còn chờ hai người thật
rà soát. Đây là gói audit nguồn hiện có, không phải 500 SMS mới. Công cụ chặn
nhãn thiếu bằng chứng, bất đồng, reviewer AI và hai phiếu cùng người; kiểm tra
không chứng nhận được chuyên môn con người từ một tên điền trong CSV.

Mục tiêu 300–500 SMS thật mới, kiểm tra giao toàn bộ dữ liệu cũ và xác minh
độc lập vẫn còn phụ thuộc nguồn dữ liệu và người rà soát. Việc người dùng cho
phép AI gán nhãn đã được thực hiện cho thí nghiệm; không dùng sự cho phép đó
để tạo chữ ký chuyên gia hoặc tuyên bố test độc lập.

## Kiểm tra và sử dụng

- 149 kiểm thử Python và 65 kiểm thử JavaScript qua; không xóa/skip kiểm thử.
- Lint, TypeScript và build production qua. Build dùng bản sao cục bộ riêng
  vì thư mục standalone hiện có bị khóa; đóng gói Windows cần quyền ngoài sandbox.
- Kiểm tra chứng cứ PASS: 2.991 hàng khớp nguồn, 121 tệp lịch sử khớp hash,
  không giao nhóm/tên miền giữa các vai trò giữ lại, không fit hàng holdout/quarantine.
- Cổng hai người rà soát trả trạng thái chờ, đúng thực tế. Không sửa điều kiện để PASS.

Lần chuẩn bị đầu có lỗi nhận diện `latest` trong tên tệp là `test`; kiểm thử hồi
quy đã bắt lỗi và bản sửa chỉ nhận token tên tệp. Giữ nguyên kết quả trung gian,
bảo vệ các trường hợp thực sự đã được fit/chấm, và dùng bản phân vùng đã sửa.
Revision annotation cuối ràng buộc đúng 401 quyết định với corpus bằng hash;
không dùng bản trung gian gắn nhầm đường dẫn quyết định mặc định. Kết quả cuối
ở `ml_model/data/prepared/vi_readiness_2026-10-27-final/`.

Các lệnh an toàn để kiểm tra lại:

```powershell
.\.venv\Scripts\python.exe ml_model/data/prepared/vi_readiness_2026-10-27-final/verify_evidence.py
.\.venv\Scripts\python.exe ml_model/vi_data_workflow.py review-status --output ml_model/data/prepared/vi_readiness_2026-10-27-final/blind_review
```

Chạy `prepare` với một thư mục mới khi có đợt dữ liệu mới. Không ghi đè các run
đã hoàn thành, không xóa marker để chấm lại test. Chi tiết tệp và hướng dẫn sửa
nhãn nằm trong `HUONG_DAN.md` của gói. [Báo cáo số liệu JSON](vi-data-readiness-2026-10-27.json)
chỉ chứa thông tin tổng hợp; dữ liệu từng hàng và model nghiên cứu giữ cục bộ.
