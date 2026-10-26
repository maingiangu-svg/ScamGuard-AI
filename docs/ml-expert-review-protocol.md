# Rà soát nhãn và đánh giá độc lập

## Phạm vi đã thống nhất

Chưa có chuyên gia hoặc bộ dữ liệu tiếng Việt mới đã xác minh. Công việc hiện tại
là chuẩn bị biểu mẫu và quy trình; không gán nhãn chuyên gia, tự đổi nhãn hoặc
huấn luyện lại model đang phục vụ.

Gói `ml_model/data/prepared/expert_review_2026-10-26/` chứa 811 ứng viên từ train:
14 SMS và 797 URL. **Đây là tập rà soát dữ liệu train, không phải benchmark mới.**
Hai biểu mẫu `reviewer-a.csv`, `reviewer-b.csv` có thứ tự xáo trộn seed 42 và không
hiện nhãn gốc, điểm model hay đề xuất cleanlab. Hash input giữ danh tính nội dung.
Input bắt đầu bằng ký tự công thức được thêm dấu `'` khi hiển thị trong CSV để
tránh chạy công thức trong spreadsheet; nội dung nguồn không bị thay đổi.

## Giao cho người gán nhãn

1. Mỗi người chỉ nhận biểu mẫu của mình, độc lập với người còn lại. Chủ dự án
   lưu thông tin người rà soát, chuyên môn, phạm vi được giao và ngày thực hiện.
2. Điền `expert_label`: `0`, `1` hoặc `unknown`; kèm reviewer, ngày, bằng chứng
   và lý do. Không đổi case ID, branch, input hoặc hash.
3. SMS nhãn 1 phải phù hợp định nghĩa smishing của dự án: hành vi lừa gạt yêu cầu
   tiền, thông tin nhạy cảm hoặc hành động nguy hiểm. Spam/quảng cáo đơn thuần
   không tự động là smishing. Không suy ra nhãn từ từ khóa hoặc tên thương hiệu.
4. URL có target good/bad kế thừa nguồn; lexical URL đơn thuần không đủ xác minh
   nội dung trang. Khi thiếu bằng chứng, chọn unknown. Chỉ dùng bằng chứng nguồn
   hoặc bản chụp đáng tin cậy; không mở URL nguy hiểm trên thiết bị làm việc.
5. Chủ dự án đối chiếu nhãn gốc sau khi cả hai người đã nộp. Bất đồng/unknown
   giữ cách ly; cần người thứ ba phân xử với hồ sơ bằng chứng, không dùng model
   làm trọng tài. Định nghĩa nhãn phải thống nhất trước khi bắt đầu.

Chạy kiểm tra biểu mẫu:

```powershell
.\.venv\Scripts\python.exe ml_model/expert_review.py verify --output ml_model/data/prepared/expert_review_2026-10-26
```

Mã 2 là chưa hoàn tất hoặc còn bất đồng/unknown. Công cụ kiểm tra định dạng,
danh tính hàng và yêu cầu hai reviewer khác nhau; không thể chứng nhận người
điền là chuyên gia chỉ từ một tên trong CSV. Kết quả không tự ghi đè dataset.
Chỉ sau xác minh con người mới lập ledger nhãn mới, giữ nhãn gốc, reviewer,
bằng chứng, ngày và quyết định phân xử. Mọi lần fit lại phải có run/artifact mới.

## Tạo benchmark tiếng Việt độc lập

1. Đăng ký trước mục tiêu, định nghĩa nhãn, nguồn và quyền sử dụng, số mẫu/ngân sách,
   đơn vị chiến dịch và độ bất định cần báo cáo. Tách SMS và URL vì target khác nhau.
2. Thu thập nội dung mới có nguồn gốc rõ, không lấy 811 ứng viên train ở trên hoặc
   holdout lịch sử đã xem làm test mới. Ghi thời gian, nguồn, campaign/actor khi có
   bằng chứng; không tự phát minh campaign ID từ domain.
3. Kiểm tra giao với toàn bộ corpus đã dùng: nội dung chuẩn hóa, template, tương
   tự gần trùng, ICANN/PSL domain và nhóm nguồn. Nhóm có giao phải cách ly. Proxy
   lexical không chứng nhận độc lập chiến dịch khi metadata chưa đủ.
4. Hai chuyên gia gán nhãn độc lập theo quy trình trên; unknown/bất đồng chưa
   phân xử không được đưa vào ground truth. Ghi rõ nhãn yếu, nhãn nguồn, AI review
   và expert-verified; không trộn các loại mà không báo cáo riêng.
5. Khóa membership train/validation/test theo nhóm/chiến dịch và thời gian, cùng
   checksum, trước fit. Giữ nguyên test cho đánh giá cuối; không chuyển test sang train.
6. Fit vocabulary, scaler và classifier chỉ trên train. Chọn model, hiệu chuẩn và
   ngưỡng trên validation hoặc dự đoán ngoài nhóm trong train. Không sửa ngưỡng
   theo kết quả test hoặc theo một URL người dùng báo cáo.
7. Đánh giá test một lần theo kế hoạch: precision, recall, F1, FP/FN, confusion
   matrix và chi phí báo nhầm/bỏ sót; báo cáo riêng theo tiếng Việt, nguồn nhãn,
   loại tấn công và chiến dịch. Khoảng tin cậy cần resample theo đơn vị nhóm độc
   lập, không coi các bản sao cùng chiến dịch là nhiều quan sát độc lập.
8. Báo cáo thêm robustness với http/https, www, Unicode/defang, URL query, biến
   thể template; ghi rõ các can thiệp thay đổi input. Không whitelist thương hiệu
   để che false positive. Chưa hiệu chuẩn thì không gọi điểm là xác suất lừa đảo.

Chưa có số liệu benchmark mới nào được tạo trong bước chuẩn bị này. Các điểm
holdout lịch sử vẫn chỉ là chẩn đoán đã tái sử dụng. Tập mới cần chuyên gia,
quyền sử dụng dữ liệu và bằng chứng campaign trước khi được công bố như đánh giá độc lập.
