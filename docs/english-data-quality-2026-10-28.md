# Đánh giá chất lượng dữ liệu SMS và URL — 28/10/2026

**Kết luận:** SMS tiếng Anh dùng được cho thử nghiệm học có giám sát, nhưng thiếu mẫu lừa đảo và thiếu bộ test đủ đa dạng. URL có kiểm soát phân vùng và truy xuất tốt hơn, nhưng độ đúng của nhãn ngoài thực tế chưa được xác minh độc lập. Chưa đủ bằng chứng để gọi hai bộ dữ liệu là chuẩn đánh giá độ chính xác thực tế.

Đánh giá áp dụng cho model cục bộ `url-ensemble-20261027`, không lấy trạng thái model ngày 26/10 làm trạng thái hiện tại. Checksum bundle và toàn bộ tệp dữ liệu được manifest hiện tại ràng buộc đều khớp. Không huấn luyện, sửa nhãn, chạy dự đoán mới hoặc truy cập các URL. Chỉ tính lại số liệu từ dữ liệu và dự đoán đã lưu.

## 1. SMS tiếng Anh thực sự đang dùng

| Phân vùng | Số tin tiếng Anh | Nhãn 0 | Nhãn 1 |
|---|---:|---:|---:|
| Train | 3.653 | 3.522 | 131 |
| Validation | 904 | 871 | 33 |
| Test | 38 | 14 | 24 |

Train SMS tổng cộng có 3.786 tin, trong đó 133 tin tiếng Việt. Số tiếng Anh dựa trên metadata `language=en`, chưa phải kiểm định ngôn ngữ độc lập từng dòng. Không cộng các bản xuất lịch sử vào số liệu này.

**Điểm tốt:** trong các tập SMS đã kiểm tra không có nội dung trống, nhãn nhị phân lỗi hoặc nội dung trùng theo NFC/casefold/gộp khoảng trắng. Không phát hiện giao nhau nội dung theo tiêu chí đó, tên miền gốc, template đã lưu hoặc nhóm sửa dữ liệu giữa train, validation và test. Không có dòng train mang cờ `do_not_train=true`.

**Mất cân bằng lớn:** 131/3.653 tin train tiếng Anh mang nhãn 1, chỉ **3,59%**, tương đương khoảng 26,9 tin nhãn 0 cho mỗi tin nhãn 1. Mô hình luôn đoán 0 đã đạt 96,41% accuracy trên chính phân bố train này; đây là phép minh họa mất cân bằng, không phải kết quả test. Các tin dương train tiếng Anh thuộc 79 nhóm sửa dữ liệu, không phải 131 chiến dịch được xác minh.

Nguồn nhãn train tiếng Anh:

| Nguồn nhãn | Tổng số tin | Trong đó nhãn 1 |
|---|---:|---:|
| Nhãn ham/non-smishing spam kế thừa nguồn | 2.966 | 0 |
| Nhãn thủ công của nhóm nghiên cứu SmishX | 483 | 68 |
| AI semantic review | 203 | 62 |
| Quyết định người dùng | 1 | 1 |

Nhãn thủ công SmishX có giá trị, nhưng không phải lượt kiểm định độc lập mới của dự án. Có 62/131 nhãn dương train tiếng Anh đến từ AI review. Không được báo cáo toàn bộ dữ liệu như nhãn chuyên gia. Nhãn 0 trong phạm vi smishing cũng không tự chứng nhận một quảng cáo hoặc dịch vụ là an toàn.

**Hạn chế test nghiêm trọng:** 38 tin test có nhãn thủ công nguồn nhưng chỉ thuộc 11 nhóm; cả 24 tin dương nằm trong **một nhóm**. Tập này đã được sử dụng trong các thực nghiệm trước. Nó có thể phát hiện hồi quy trên các ví dụ đã biết, nhưng không đủ để ước lượng khả năng nhận ra nhiều chiến dịch mới. Tỷ lệ dương test 63,16% cũng khác xa train 3,59%; chưa có cơ sở coi một trong hai là phân bố lưu lượng thực tế.

## 2. URL đang dùng

**Chưa xác định được tập URL tiếng Anh:** manifest URL không có thông tin ngôn ngữ trang đích. Tên miền, đường dẫn hoặc ký tự Latin không đủ để kết luận ngôn ngữ. Phần này đánh giá corpus URL hiện tại của dự án.

| Vai trò | Tổng | Nhãn good/0 | Nhãn bad/1 |
|---|---:|---:|---:|
| Train hai mô hình URL cơ sở | 71.309 | 51.034 | 20.275 |
| Fit calibration | 3.000 | 2.062 | 938 |
| Validation calibration | 3.000 | 2.022 | 978 |
| Test mới của lượt 27/10 | 4.000 | 2.707 | 1.293 |

74.309 hàng URL trong manifest fit gồm 71.309 hàng train mô hình cơ sở và 3.000 hàng fit calibration. Trong 71.309 hàng đầu có 71.299 nhãn nguồn và 10 URL chính thức được AI rà bằng chứng; 10 hạt giống này không phải chứng nhận an toàn toàn bộ tên miền.

**Kiểm soát kỹ thuật tốt:** tính lại tên miền bằng PSL đã ghim, gồm cả biến thể ICANN owner và PSL private. Không phát hiện giao nhau tên miền gốc giữa các vai trò URL trong bảng, hoặc với hai bộ test URL lịch sử đã kiểm tra. Không có URL trống, nhãn nhị phân lỗi hoặc URL bị hàm sửa định dạng hiện tại từ chối. Không có dòng fit mang cờ cấm học.

Đối chiếu trực tiếp URL sau sửa và nhãn với đúng dòng CSV nguồn cho **95.234 hàng nguồn** thuộc train/calibration/validation/các test đã kiểm tra: không có sai khác. Mười URL hạt giống thuộc nguồn riêng được báo tách. Đây là xác minh truy xuất, không xác minh tính đúng của nhãn good/bad.

Còn **5 cặp** URL train cơ sở và **1 cặp** fit calibration tương đương theo tiêu chí URL identity, khác đường dẫn rỗng với `/`. Các cặp này cùng nhãn, không vượt phân vùng; không có bản URL trùng chuỗi hoàn toàn trong các phân vùng đó. Đây là vấn đề nhỏ cần xử lý ở lượt chuẩn bị tiếp theo, không sửa trực tiếp dữ liệu đã đóng băng.

Có một tên miền chung giữa **SMS train và URL train**, `nokia.com`; không có giao nhau train–test tương ứng trong phạm vi kiểm tra. Không diễn giải điều này là rò rỉ test, nhưng cũng không khẳng định hai corpus train hoàn toàn tách biệt tên miền.

**Điểm yếu chính là nhãn và tính đại diện:** nhãn URL hầu hết kế thừa `good/bad`, chưa được thẩm định độc lập bằng bằng chứng trang đích tại thời điểm thu thập. Không có trường thời gian thu thập/capture hoặc campaign ID trong các manifest được kiểm tra. Tách tên miền gốc chưa chứng minh độc lập chiến dịch; các mẫu có cùng mẫu trang hoặc hạ tầng khác tên miền vẫn có thể liên quan. Test mới của lượt 27/10 lấy từ cùng CSV nguồn với train và hiện đã được chấm, nên không phải nguồn đánh giá bên ngoài chưa từng xem.

Tính lại dự đoán đã lưu trên 4.000 URL khớp kết quả: **accuracy 95,175%; precision 95,99%; recall 88,79%**, gồm 48 báo nhầm và 145 bỏ sót. Đây là mức đồng ý với nhãn nguồn. Báo cáo bootstrap theo owner đã lưu có khoảng 95% cho accuracy khoảng **94,47%–95,80%**; chưa chứng minh accuracy quần thể vượt 95%. Không dùng các số này làm điểm chất lượng nhãn.

## 3. Dữ liệu nguồn và các nguồn bổ sung

| Nguồn | Kết quả kiểm tra | Ý nghĩa |
|---|---|---|
| Combined SMS | 84.863 hàng; 10.105 hàng trùng hoàn toàn (11,91%); 34 nhóm cùng chuỗi message nhưng khác nhãn smishing | Là nguồn SMS lịch sử, không phải toàn bộ train tiếng Anh hiện tại. Nhãn smishing nguồn dựa trên từ khóa, không thích hợp làm chuẩn chuyên gia. |
| Cột phụ spam của Combined | 1.076 giá trị thiếu; 624 giá trị `Smishing` ngoài miền 0/1 | Không tự điền bằng nhãn smishing hoặc dùng thẳng làm mục tiêu huấn luyện. |
| CSV URL gốc | 549.346 hàng; 42.150 hàng trùng hoàn toàn (7,67%); 1 nhóm URL trùng chuỗi có nhãn mâu thuẫn | Không học trực tiếp từ CSV thô. Các chỉ số lỗi nguồn không được gán cho tập train đã xử lý. |
| SmishX | 1.200 SMS đa ngôn ngữ; đợt sàng lọc lưu 1.017 mẫu tiếng Anh/phù hợp phạm vi, gồm 141 nhãn 1 | Các tệp tải ban đầu mang tên `english` không phải tập tiếng Anh sạch. Sàng lọc ngôn ngữ/phạm vi do AI thực hiện. |
| IMC25 | Kiểm đếm 22.078 dòng tiếng Anh nguồn; 15.477 nội dung trong pool đã gộp trùng | Nhãn loại scam/ngôn ngữ do AI nguồn tạo. Cả hai bản xuất vẫn có `label=null`, `do_not_train=true`; chưa phải dữ liệu học hoặc gold test. |

Audit URL toàn nguồn đã lưu ở `data_frozen.json` ghi 502.428 ứng viên, 5.158 hàng cách ly và 41.760 bản trùng bị loại. Định nghĩa trùng sau sửa khác trùng hoàn toàn của CSV thô nên hai số không đồng nhất. Audit này là bằng chứng lịch sử đã kiểm tra checksum, không phải lượt chạy lại toàn bộ quy trình chuẩn bị trong đánh giá hôm nay.

## 4. Ưu tiên cải thiện

1. **Bổ sung test SMS tiếng Anh có nhãn người độc lập, đa dạng nhóm lừa đảo.** Giữ tách theo template/tên miền/nhóm nguồn; thu metadata thời gian và chiến dịch nếu có. Không dùng 24 biến thể thuộc một nhóm như 24 chiến dịch độc lập.
2. **Thẩm định nhãn trước khi tăng quy mô học.** Lấy mẫu phân tầng SMS dương/âm và URL good/bad, gồm lỗi mô hình và trường hợp khó. Ghi bằng chứng, người gán, bất đồng và kết luận; giữ riêng nhãn nguồn, AI, người nghiên cứu và chuyên gia. Với URL lịch sử cần bằng chứng đúng thời điểm; website hiện tại không đủ sửa nhãn cũ.
3. **Bổ sung SMS lừa đảo tiếng Anh thật và các tin hợp lệ dễ bị báo nhầm.** Ưu tiên thêm nhóm mới; không chỉ nhân bản/oversample 131 tin dương hiện tại. IMC có thể phục vụ hàng đợi gán nhãn sau kiểm tra trùng nhóm, không tự chuyển nhãn AI thành nhãn chuẩn.
4. **Đánh giá khác nguồn và khác thời gian.** Khóa bộ mới trước lựa chọn mô hình. Báo cáo precision/recall/F1 hoặc PR-AUC, tỷ lệ báo nhầm và độ bất định theo nhóm; accuracy đơn lẻ không phù hợp với SMS đang mất cân bằng.
5. **Chuẩn hóa URL identity ở lượt chuẩn bị mới.** Xử lý các cặp đường dẫn rỗng/`/`, giữ bằng chứng phiên bản và manifest mới; không thay tệp đã đóng băng rồi tiếp tục dùng kết quả đánh giá cũ.

**Xếp loại định tính:** SMS tiếng Anh — trung bình cho nghiên cứu, yếu về bằng chứng tổng quát hóa. URL — khá về xử lý/truy xuất/phân vùng, trung bình về độ tin cậy nhãn. Cả hai chưa đạt mức bộ kiểm định độc lập ngoài thực tế; không gán điểm số tổng hợp tùy ý.

## Bằng chứng

- [Kết quả máy đọc được của lượt kiểm tra này](english-data-quality-2026-10-28.json): số đếm, checksum, giao nhau từng cặp, truy xuất nhãn và chi tiết trùng.
- [Manifest model hiện tại](../ml_model/models/hybrid_manifest.json).
- [Báo cáo SmishX và giới hạn nguồn](smishx-training-2026-10-25.md).
- [Nguồn tiếng Anh ban đầu và provenance IMC](english-smishing-data-2026-10-25.md).
- [Lượt URL hiện tại và quy trình đánh giá](url-regression-repair-2026-10-27.md).

Kiểm tra này không tạo nhãn chuyên gia mới, không kiểm định ngôn ngữ độc lập, không chạy lại phép gom gần trùng toàn cặp và không chứng nhận độc lập chiến dịch. Các trường hợp URL đáng ngờ được lưu dưới dạng dữ liệu, không được truy cập.
