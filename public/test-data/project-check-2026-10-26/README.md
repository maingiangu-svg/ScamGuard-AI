# Bộ kiểm tra tay ScamGuard — 26/10/2026

1. Mở ứng dụng local, chọn Text or Link.
2. Mở tệp test, chỉ sao chép nội dung của MỘT mẫu, dán và bấm kiểm tra.
3. Đối chiếu nhãn nhánh SMS/URL với DAP_AN.md. Không coi tất cả điểm dưới 80 là nhãn 0.
4. Ghi lại ID, điểm SMS, điểm URL, nhãn nhánh, trạng thái REVIEW/BLOCK và nhận xét của bạn.

| Tệp | Số mẫu | Nguồn nhãn | Mục đích |
|---|---:|---|---|
| SMS_EN_TEST.txt | 36 | SmishX, người gán nhãn tại nguồn | Kiểm tra tay SMS tiếng Anh |
| URL_TEST.txt | 80 | PhishVN, audit người có bằng chứng | Kiểm tra tay URL |
| TIENG_VIET_THAM_KHAO.txt | 68 | Nhãn AI review lịch sử | Chẩn đoán tiếng Việt, không tính accuracy đã xác minh |

DAP_AN.md và cases.json chứa nhãn nguồn, provenance, nhóm và ngưỡng đối chiếu. Không có điểm dự đoán của model trong bộ này: bạn tự chạy để kiểm tra.

Đã đối chiếu với manifest train/validation của hai nhánh hybrid hiện tại và loại 6 trường hợp trùng chỉ báo hoặc có đề cập tên miền mơ hồ. Chi tiết nằm ở excluded.json. Không điều chỉnh ngưỡng hay chọn mẫu theo kết quả model.

Đây là tập con của dữ liệu đã từng được kiểm tra, được lọc sau đợt audit; không phải benchmark mới, không dùng để chọn model/huấn luyện. 24 mẫu SMS tiếng Anh nhãn 1 cùng một nhóm tương tự. Độc lập chiến dịch hoàn toàn chưa được chứng minh. Các chỉ báo lọc không bảo đảm phát hiện mọi biến thể/diễn đạt lại.

Chỉ áp dụng cho hybrid-20261025 có checksum ghi trong manifest.json; không suy rộng sang chế độ legacy hoặc phiên bản model khác. Giữ nguyên dữ liệu đóng băng gốc. Các URL là dữ liệu test để dán vào app, không cần mở website đích.

Nguồn và attribution:
- SmishX, Yizhu Wang và cộng sự, SOUPS 2025: https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff . MIT license được giữ trong SMISHX_LICENSE.txt.
- PhishVN v4, Thai Nguyen Vu: https://data.mendeley.com/datasets/b97hxbxtpd/4 . CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . Giữ nhãn/bằng chứng nguồn; bộ này chỉ chọn tập con và đổi định dạng, không phải xác nhận trạng thái website hiện tại.
- Phần tiếng Việt kế thừa dữ liệu project và review AI trong historical_vi_diagnostic.jsonl; source_file/source_sha256 và nhãn gốc được bảo toàn ở dữ liệu project, không đổi thành expert labels.
