# Tập test giữ riêng từ dữ liệu đã dùng huấn luyện — 26/10/2026

Đây là toàn bộ các phân hoạch test của hai nhánh được tái sử dụng trong hybrid-20261025. Giữ nguyên tất cả mẫu và nhãn, không lọc theo điểm model. Các bản ghi test được tách khỏi phần fit train; chúng thuộc cùng nguồn/pool của lượt huấn luyện.

| Nhánh đang dùng | Train | Validation | Test xuất ở đây | Nhãn nguồn 0 / 1 |
|---|---:|---:|---:|---:|
| SMS processed | 3.857 | 962 | 39 | 14 / 25 |
| URL bundle | 40.004 | Không có tập validation riêng trong lượt bundle này | 9.996 | 7.716 / 2.280 |

## Các tệp

- SMS_TEST.jsonl: bản sao đúng byte của test.jsonl đã đóng băng của lượt SMS processed. Giữ toàn bộ nhãn/provenance gốc.
- URL_TEST.jsonl: đủ 9.996 URL test tái tạo theo nguồn, mã, seed và cách chia tập đã ghi của bundle 20261025T152344Z. Có source_record và selected_pool_index để đối chiếu. Export split local cũ không khớp lượt URL hiện tại; đây là bản tái tạo, không giả nhận là export gốc được ràng buộc checksum vào model.
- SMS_NOI_DUNG.txt và URL_NOI_DUNG.txt: dán riêng nội dung mỗi mẫu vào ứng dụng để kiểm tra tay.
- DAP_AN_SMS.txt và DAP_AN_URL.txt: ID và nhãn nguồn, dùng đối chiếu nhãn nhánh SMS/URL.
- CO_CANH_BAO_AUDIT.jsonl: cờ giao nhau tên miền đã phát hiện, giữ đủ mọi mẫu.
- manifest.json: số lượng, nguồn, model tương ứng, checksum và giới hạn.

## Cách kiểm tra

1. Mở ứng dụng, chọn Text or Link.
2. Dán nội dung MỘT mẫu, không dán ID/tiêu đề/đáp án.
3. So nhãn nhánh SMS (ngưỡng 0,65) hoặc URL (ngưỡng 0,50) với đáp án. Không xem tất cả điểm dưới 80 là nhãn 0.
4. Với test tự động, đọc từng dòng JSONL và gửi raw_text của SMS hoặc url của URL tới API. Không dùng các mẫu này để train hoặc chỉnh ngưỡng.

SMS: nhãn 1 là smishing theo nguồn, nhãn 0 là không smishing theo nguồn. URL: nhãn 1/0 kế thừa bad/good của nguồn. Không coi 0 là xác nhận website hiện còn an toàn hoặc nhãn URL đã được chuyên gia kiểm chứng.

## Giới hạn được giữ nguyên

Tách bản ghi test khỏi train không có nghĩa độc lập tên miền/chiến dịch. URL test có 3.074 mẫu nằm trên 519 tên miền gốc đã xuất hiện trong URL train. SMS validation/test còn chung gốc app.link. Bộ này giữ nguyên các vấn đề để phản ánh đúng lượt huấn luyện hiện tại, không phải bộ đã sửa rò rỉ. Các cờ theo từng ID nằm trong CO_CANH_BAO_AUDIT.jsonl.

SMS test gồm 25 mẫu nhãn 1 cùng một nhóm tương tự. Cả hai tập đã được đánh giá/quan sát trước đây, không phải benchmark mới. Không gộp kết quả hai nhánh để tuyên bố một accuracy chung. Bộ này không bao gồm các mẫu tiếng Việt chẩn đoán hoặc URL audit bên ngoài; đó là các nguồn kiểm tra khác với phân hoạch fit của nhánh URL hiện tại.

Không huấn luyện lại, sửa nhãn, đổi model, chạy dự đoán test mới hoặc ghi đè tập gốc khi xuất gói này.

## Nguồn và attribution

- SMS: SmishX, Yizhu Wang và cộng sự, SOUPS 2025; revision 116a8c827741e0572563f678d25ed04306b1e3ff: https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff . Giữ MIT license trong SMISHX_LICENSE.txt.
- URL: phishing_site_urls.csv, nguồn được dự án ghi nhận tại https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls . Giữ nhãn nguồn good/bad và checksum CSV; không suy diễn đây là nhãn chuyên gia hoặc cấp phép mới cho dữ liệu nguồn.
