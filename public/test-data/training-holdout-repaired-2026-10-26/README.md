# Tập test sau sửa rò rỉ — 26/10/2026

Model: hybrid-isolated-20261026-icann. Test lấy từ cùng nguồn đã dùng train,
không thêm tập PhishVN so sánh hay dữ liệu tiếng Việt AI chẩn đoán bên ngoài.

| Nhánh | Train | Validation | Test sau cách ly | Cách ly tổng |
|---|---:|---:|---:|---:|
| SMS | 3.800 | 945 | 38 | 75 |
| URL | 32.777 | 0 | 9.935 | 7.288 |

SMS_TEST.jsonl và URL_TEST.jsonl dùng chạy theo lô. File NOI_DUNG.txt để copy
vào web. DAP_AN ghi nhãn nguồn 0/1; so với model_prediction_label của từng nhánh
với ngưỡng SMS=0,65, URL=0,50. Chính sách cảnh báo 30/80 không phải nhãn nhị phân.
Không dùng file test để train/tinh chỉnh. Đây là holdout lịch sử tái sử dụng,
không phải benchmark mới chưa từng xem. 24 SMS dương cùng một nhóm nguồn.

Nhãn URL good/bad là nhãn nguồn, chưa được chuyên gia độc lập xác minh. SMS
có nhãn người nghiên cứu nguồn; không đồng nghĩa tái thẩm định chuyên gia dự án.
14 nhãn SMS mâu thuẫn được đưa vào REVIEW_NHAN_MAU_THUAN.jsonl; chưa tự đổi
nhãn nào. REVIEW_URL_LOI.jsonl chứa 176 URL lỗi. Chúng không được fit/evaluate.
Các nhãn yếu còn lại vẫn được ghi đúng provenance; không được cấp chứng nhận.

Chạy offline: python CHECK_SPLITS.py
Chứng nhận chiến dịch nghiêm ngặt: python CHECK_SPLITS.py --require-campaigns
Chứng nhận nhãn chuyên gia: python CHECK_SPLITS.py --require-expert-labels
Hai lệnh nghiêm ngặt trả mã 2 vì thiếu bằng chứng, không được đổi thành PASS.

SPLIT_MEMBERSHIP kiểm tra tất cả 54.858 mẫu trước cách ly và sau phân vùng,
theo cả ICANN owner và PSL private suffixes. SIMILARITY_EDGES là 539 cặp SMS
có cosine >=0,80 trên chữ n-gram để phân nhóm, không phải mã chiến dịch thật.
Metadata campaign còn thiếu nên không chứng minh được độc lập chiến dịch thực.
MODEL_MANIFEST ràng buộc SHA256 model với các manifest dữ liệu train chính xác.
TRAINING_FROZEN giữ các mã băm dữ liệu đầy đủ nằm trong repo cục bộ ở
ml_model/data/prepared/repaired_training_2026-10-26-icann/.

Nguồn SMS SmishX: https://github.com/yizhu-joy/SmishX
Giấy phép MIT kèm SMISHX_LICENSE.txt. Nguồn URL: phishing_site_urls.csv của
nguồn Kaggle đã dùng train; nhãn nguồn được giữ nguyên, không truy cập URL.
