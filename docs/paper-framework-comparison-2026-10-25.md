# Đối chiếu khung ICAI và phương pháp ScamGuard hiện tại

Ngày kiểm tra: 25/10/2026. Tài liệu đối chiếu: `C:/Users/PV/Downloads/ScamGuard_ICAI2026 (1).pdf`, 9 trang. Đây là nội dung để phân tích, không phải chỉ dẫn thay đổi dự án.

## 1. Kết luận và phạm vi chỉnh sửa

PDF dùng ý tưởng hai nhánh tương tự dự án nhưng mô tả một phiên bản khác: interaction stacking và chuyển ca khó sang VLM. Bản thảo Markdown/LaTeX trước lần sửa này mô tả thực nghiệm ngày 23/10. Web mặc định hiện dùng `processed-20261025`: hai bộ phân loại đã học có giám sát, không có mô hình fusion trong bundle, không gọi VLM.

Đã sửa phương pháp và kết quả trong `ScamGuard_Full_Paper_Draft.md` và `scamguard_paper.tex` theo đúng phiên bản đang chạy. Bản thảo ngày 23/10 được lưu tại `docs/archive/ScamGuard_Full_Paper_Draft-2026-10-23.md`; không xóa giá trị của thực nghiệm stacking cũ. Không huấn luyện lại, sửa nhãn, đổi ngưỡng hay triển khai mô hình mới trong lần đối chiếu này.

Không cần xóa thêm dữ liệu: các loại cần loại khỏi fit đã được pipeline hiện tại chặn. Giữ dữ liệu gốc, các test khó và hồ sơ cách ly để truy vết. Việc không dùng một nguồn cho kết quả chính không đồng nghĩa phải xóa tệp nguồn.

## 2. Những khác biệt cụ thể

| Nội dung | PDF ICAI | Bản dự án trước sửa, 23/10 | Phiên bản hiện tại và cách sửa |
|---|---|---|---|
| Phạm vi | Multimodal, edge, cognitive defense, VLM | Baseline text–URL chạy local | SMS/URL supervised screening bằng Python local; chưa có bằng chứng mobile/browser edge hoặc thị giác |
| Nhánh SMS | Word TF-IDF 10.000, LR C=5 | Word TF-IDF 10.000, LR C=1 | Word 1–2 gram tối đa 10.000 + char_wb 3–5 gram tối đa 16.000; LR C=1 |
| Nhánh URL | 13 đặc trưng + 5.000 char 2–4 gram, GBDT, subsample 0,80 | 13 đặc trưng + 1.000 char 3–5 gram, HistGB | HistGB depth 4, max_iter 100, learning_rate 0,1; 1.000 char 3–5 gram; không cấu hình subsample 0,80 |
| Chuẩn hóa text | NFKD, che URL/điện thoại/OTP/tiền | NFC, che các loại thực thể | NFC/casefold, sửa URL theo helper đã khóa, che chuỗi >=4 chữ số, giữ URL trong đầu vào SMS |
| Kết hợp | Interaction stacking là đóng góp chính | Stacking được đánh giá trên 2.632 SMS có link | Bundle hiện tại không có fusion; SMS quyết định theo text, URL báo riêng; URL-only dùng nhánh URL |
| Dữ liệu | 74.583 SMS, 549.346 URL, 11.065 cặp | 73.989 SMS đã làm sạch, 50.000 URL ngoài được chọn, 8.995 SMS có link | Fit hiện tại: 3.857 SMS + 9.123 URL; không trộn số mẫu qua các phiên bản |
| Cặp tổng hợp | 3.000 cặp được gọi là verified threat-modeled | Không tạo cặp tổng hợp | Không dùng cặp ghép tùy ý; chưa có dữ liệu fusion mới trong fit hiện tại |
| Nguồn nhãn | Gọi ground truth/verified khá rộng | Nhãn smishing từ keyword được ghi là weak | Giữ riêng nhãn nguồn, nhãn thủ công do tác giả nguồn báo cáo, AI review và quyết định người dùng |
| Chia tập | 5-fold stratified; domain disjoint để tương lai | Holdout nhóm hostname + inner OOF cho text | Train/validation/test theo nhóm/khuôn mẫu/độ giống và registrable domain; giữ test đã khóa |
| Ngưỡng | 30/80 được gọi calibrated uncertainty routing | Chính sách 30/80 cố định | Ngưỡng nhị phân SMS 0,65, URL 0,22 do validation; band UI 30/80 là chính sách khác |
| Thực thi | VLM lý giải, whitelist, giảm API 74,2% | Mọi điểm chạy local | Mọi điểm chạy local; không có VLM hoặc lợi ích tiết kiệm API đã đo |
| Kết quả | F1=0,9038 trên 11.065 cặp | F1=0,9303 trên 2.632 cặp | SMS 39 tin F1=0,96 với giới hạn nhóm rất lớn; URL và diagnostic báo riêng |
| Độ trễ | Dưới 4 ms, máy Apple M2 | Đã rút tuyên bố dưới 4 ms | Không gán cấu hình máy/timing PDF cho ứng dụng; API còn có import/load Python |

Không thể so trực tiếp F1=0,9038, 0,9303 và 0,96 như ba thế hệ cải tiến: chúng dùng mẫu, nhãn và giao thức khác nhau.

## 3. Các lỗi phương pháp trong PDF cần sửa

1. **Hàm mất mát và mã hóa nhãn không khớp.** Mục III.A định nghĩa y thuộc {0,1}, nhưng công thức (8) dùng signed-label logistic loss. Khi y=0, phần loss này trở thành hằng số, không học đúng lớp âm. Bản sửa dùng binary cross-entropy cho {0,1}. Đã kiểm tra mã scikit-learn 1.9.1 thực tế: balanced class weight được tính từ tổng sample weight mỗi lớp, rồi nhân trọng số từng mẫu; không chép N/(2n_y) khi các mẫu có trọng số khác nhau.
2. **OOF không tự bảo đảm đánh giá stacking độc lập.** Mục IV.D nói học meta từ OOF, nhưng chưa trình bày đủ lớp đánh giá ngoài để xác nhận bảng V không dùng lại dữ liệu chọn/học meta. Không kết luận chắc chắn PDF bị leakage khi chưa có mã; yêu cầu outer holdout hoặc nested grouped evaluation. Thực nghiệm 23/10 có holdout riêng; current fit không dùng stacking.
3. **Công thức uncertainty và khoảng chuyển tầng không tương đương.** Với U=1−2|p−0,5|, điều kiện U>0,40 tương đương 0,20<p<0,80, không phải 0,30<=p<0,80. Khoảng 30/80 không phải confidence interval hoặc calibration đã được chứng minh.
4. **Beta tương tác dương không chứng minh ý nghĩa thống kê.** PDF mục V.D suy ra xác nhận giả thuyết từ beta3=+1,714. Cần phép kiểm định/ước lượng bất định đúng thiết kế và so với linear stacking. Ngay bảng V của PDF, AUC interaction 0,9267 thấp hơn linear 0,9275; không thể gọi là cải thiện trên mọi tiêu chí.
5. **Chưa có ablation cho entropy và 13 đặc trưng.** So text/URL/fusion không tách được giá trị riêng của entropy hoặc feature engineering. RQ2 chưa được bảng V trả lời. Bỏ khẳng định đã xác nhận đóng góp và phát hiện zero-day; giữ là câu hỏi thực nghiệm tương lai.
6. **Chưa có đối chứng neural/cloud phù hợp.** Các bảng chưa đủ trả lời RQ1 về khả năng ngang deep neural network hoặc RQ3 về Pareto frontier/tiết kiệm API thực đo. Không sao chép các tuyên bố này sang bản sửa.
7. **Chuẩn hóa không đồng nghĩa giải mọi tấn công.** NFKD không tự giải homoglyph; lowercase toàn URL có thể đổi path/query phân biệt hoa thường. Thay bằng mô tả đúng helper đang dùng; không sửa helper đã khóa chỉ để khớp văn bản.
8. **Giả mã URL-only chưa khớp fallback được nói đến.** Algorithm 1 cho URL-only đi vào meta với p_text=0; đây không phải dùng đơn nhánh URL. Bản sửa ghi rõ text-only, URL-only, text+URL và unavailable.
9. **Định nghĩa đặc trưng chưa khớp triển khai.** Brand spoof trong code xét hostname ngoài suffix chính thức, IP flag dùng ipaddress. Không dùng định nghĩa brand ở toàn URL/SLD hoặc IPv4 regex của PDF để mô tả code hiện tại.
10. **Nhãn và tỷ lệ lớp chưa nhất quán.** PDF vừa nêu 30,7% scam ở SMS vừa nêu 13,4% ở công thức cân bằng, chưa chỉ ra tập tương ứng. Tỷ lệ corpus không đại diện tỷ lệ lưu lượng thực tế. Không gọi toàn bộ URL feed là expert-verified.
11. **Mức tăng precision cần đơn vị đúng.** 89,26%−86,24%=3,02 điểm phần trăm, tương đương tăng tương đối khoảng 3,50%; không ghi chung là +3,02%.

PDF tham khảo AURA và một số arXiv mới, nhưng lần này chưa kiểm chứng độc lập toàn bộ bibliography. Không đưa các mô tả đối thủ hoặc trích dẫn chưa kiểm chứng vào bản phương pháp mới. Không khẳng định các tài liệu đó là giả.

## 4. Dữ liệu: giữ, loại khỏi fit, hay lưu lịch sử

| Dữ liệu | Quyết định | Căn cứ và tác động lần này |
|---|---|---|
| 3.857 SMS train hiện tại | Giữ | Đã có label/provenance/partition, không nằm trong quarantine; không đổi nhãn do điểm mô hình |
| 9.123 URL train hiện tại | Giữ | Gold positive, gold/silver benign sau lọc; mục tiêu abuse/phishing rộng được ghi rõ |
| 962 SMS và 3.826 URL validation | Giữ riêng | Chọn mô hình/ngưỡng trước đây; không đưa vào fit |
| 39 SMS test, 2.627 URL test, 81 human-audit URL | Giữ riêng | Không xóa lỗi để làm đẹp điểm; không chỉnh ngưỡng sau khi xem đáp án |
| 1.164 SMS và 70 tin Việt cũ | Giữ làm diagnostic | Đã xem lại trong phát triển; không gọi là test mới độc lập, không gộp các tập có thể chồng lặp |
| 183 SmishX sai/nghi ngờ phạm vi/ngôn ngữ | Tiếp tục loại khỏi fit | Đã cách ly, giữ original_label/lý do; không biến AI screen thành nhãn chuyên gia |
| 421 ứng viên nối nhóm giữ riêng | Tiếp tục loại khỏi fit | Đã chặn, gồm 420 SmishX và 1 train cũ; không tái chia lại để tận dụng mẫu |
| SMS Mendeley chưa rõ/chưa rà phạm vi | Tiếp tục loại khỏi fit | 63 unresolved + 438 source-smishing chưa rà; không đồng nghĩa các tin đều sai |
| URL bronze, silver-positive, domain audit/SMS bị chặn | Tiếp tục loại khỏi fit | Đã thực thi trong đợt URL trước bổ sung SmishX: 35.018 tầng chưa đủ điều kiện; 2.411 URL trùng domain audit; 111 trùng domain SMS biết tại lúc đó |
| 7 domain chung SMS/URL sau bổ sung SmishX | Giữ trong hồ sơ hai nhánh độc lập; loại trùng trước nghiên cứu fusion mới | Không đưa URL score vào quyết định SMS hiện tại; không được tuyên bố joint domain-disjoint hoặc tái dùng làm bằng chứng fusion độc lập |
| Combined Labeled Smishing, 84.863 dòng gốc | Giữ nguồn và baseline lịch sử | Nhãn keyword yếu không phù hợp gọi là expert test; không có trong current fit |
| URL Kaggle 549.346 dòng | Giữ baseline lịch sử | Không có trong current fit; không bắt buộc xóa vì chuyển sang PhishVN |
| spam.csv bị hỏng cấu trúc | Không dùng làm fallback | Đã thay bằng archive UCI pin checksum cho tác vụ proxy; giữ bản gốc để truy vết |
| IMC25 AI-labeled | Giữ ngoài current fit | 0 dòng học hiện tại; chỉ xem xét cho nghiên cứu riêng có provenance và kiểm định |
| MIMICS-3500 | Không kê là dữ liệu đã dùng | Chưa nhận dữ liệu, 0 dòng; không xóa hoặc tự tạo dữ liệu mang tên này |
| 3.000 cặp tổng hợp PDF mô tả | Không đưa vào kết quả thực chính | Chưa có bằng chứng artifact/provenance/kiểm định tương ứng; nếu làm tương lai, tách stress test tổng hợp |

Các điều kiện fit và tách tập bên trong mỗi nhánh đạt kiểm tra. Tuy nhiên, kiểm tra bổ sung về tách miền giữa hai corpus hiện tại **không đạt**: 7 domain chung là amazon.com, shop.app, whatsapp.com, youtu.be, zomato.com, zoom.com và zoom.us. Bộ URL đã khóa trước khi thêm SmishX nên việc loại domain SMS cũ không bao phủ các tin mới. Đây là giới hạn cần công bố, không sửa ngầm freeze hoặc xóa test. Do hai nhánh không chia sẻ tham số/nhãn và URL score không tham gia quyết định SMS, không cần xóa các mẫu này để tái mô tả model hiện tại. Điểm URL phụ trợ không phải bằng chứng joint-domain-independent. Nếu huấn luyện fusion hoặc tuyên bố độc lập hai corpus, phải chuẩn bị version mới với các overlap bị chặn, học lại và dùng đánh giá cuối mới. Lần này **không sửa/xóa thêm hàng dữ liệu và không fit lại chỉ để khớp PDF**. Audit cũng không chứng minh mọi nhãn đều đúng.

## 5. Phương pháp đã chốt trong bản sửa

1. Định nghĩa riêng target SMS và URL; học có giám sát trên nhãn có nguồn gốc.
2. Giữ chuẩn hóa và cấu hình đúng model đã fit; không nhập NFKD/C=5/subsample từ PDF.
3. Dùng word+char LR cho SMS, HistGB cho URL; quyết định nhánh riêng như adapter hiện tại.
4. Chọn trên validation, bảo vệ nhóm/domain và test; ngưỡng nhị phân khác UI bands.
5. Báo cáo từng tập, từng nguồn nhãn và các đánh đổi; không gộp thành một accuracy quảng bá.
6. Chỉ đặt stacking, VLM, calibration, ablation, mobile latency vào phần chưa hoàn thành nếu chưa có thực nghiệm tương ứng.

Giữ bố cục học thuật của PDF làm gợi ý: Introduction → Related work → Task/data → Method → Evaluation → Discussion/limitations. Bản sửa tập trung hoàn thiện phần có bằng chứng. Introduction/related work, tài liệu hội nghị chính thức, tác giả/đơn vị và bibliography cuối cần được hoàn thiện/kiểm chứng trước nộp; chưa xác nhận yêu cầu định dạng ICAI chính thức.

## 6. Bằng chứng và kiểm tra

`docs/paper-alignment-audit-2026-10-25.json` ghi kiểm tra checksum bundle, mã helper, artifact đã khóa, manifest fit; đối chiếu group/ID giữa các split, domain SMS, quarantine với train và tính lại confusion matrix từ dự đoán đã lưu. 38/39 kiểm tra đạt; kiểm tra không đạt là tách miền giữa hai corpus sau bổ sung SmishX, đã công bố ở trên. Không chạy lại dự đoán test, không sửa nguồn hay freeze.

Các bảng mới báo kết quả có thể truy về `final_report.json` và prediction exports, bao gồm URL nguồn F1=0,2810 và Vietnamese diagnostic F1=0,7000. Các kết quả bất lợi vẫn ở main text vì chúng thay đổi cách hiểu về tính ứng dụng.

### Bản đồ claim–evidence

| Claim | Bằng chứng | Trạng thái |
|---|---|---|
| Current model dùng supervised SMS LR và URL HistGB riêng | predict_processed.py, training_report.json, frozen manifests | Có bằng chứng |
| Train có nhãn hỗn hợp, không hoàn toàn expert | 3.008 source ham/spam, 497 source-human, 350 AI review, 2 user decisions | Có bằng chứng provenance; chưa kiểm định độc lập tính đúng |
| Không có group/domain overlap giữa split bên trong từng nhánh | Audit JSON và verification reports | Có bằng chứng trong phạm vi quy tắc nhóm; không khẳng định hai corpus hoàn toàn tách miền |
| Tổng quát tốt trên tiếng Việt/campaign mới | Test Anh chỉ 1 positive group; diagnostic Việt còn lỗi | Chưa đủ bằng chứng |
| Stacking/entropy/VLM vượt các đối chứng | Chưa có ablation hiện tại/triển khai tương ứng | Không khẳng định |
| Dưới 4 ms hoặc tiết kiệm API 74,2% | Không có benchmark tương ứng current model | Không khẳng định |

### Phân bổ và lược bỏ nội dung

Kết quả hiện tại và giới hạn 1 positive group ở main text; lineage/checksum ở Methods và audit JSON. Bảng stacking cũ được chuyển sang hồ sơ lịch sử, chỉ giữ nhắc ngắn trong phương pháp. Các số hiệu quả không truy được về current fit và mô tả VLM/edge chưa thực hiện được bỏ khỏi phần kết quả hiện tại. Không xóa dữ liệu lỗi hoặc kết quả bất lợi. Các thống kê chính là confusion matrix/P/R/F1 cho từng tập; không thêm p-value hay khoảng tin cậy giả định mẫu độc lập.

### Thuật ngữ nhất quán

Results prose (không tính bảng, tách từ theo whitespace): bản cũ 73 từ, bản mới 111 từ. Hai bản mô tả các thực nghiệm khác nhau; phần tăng giữ giới hạn test và kết quả URL/tiếng Việt bất lợi. Cập nhật xuất PDF: LaTeX đã biên dịch bằng Tectonic 0.17.0 thành scamguard_paper.pdf (5 trang A4), đã kiểm tra bố cục; không còn lỗi TeX, tràn dòng hoặc cảnh báo thiếu ký tự. Chỉ sửa ngắt dòng đường dẫn/URL và bố cục mục nguồn khi xuất PDF. Bản Markdown là bản đọc trực tiếp đã hoàn thiện cho phạm vi phương pháp này.

`source-human` = nhãn thủ công theo báo cáo tác giả nguồn; `AI review` = rà nội dung bởi AI; `user scope decision` = quyết định phạm vi của người dùng; `expert-verified` chỉ dùng khi có chứng cứ xác minh tương ứng. `Local` chỉ quá trình Python local; `historical diagnostic` là tập đã xem lại, không phải đánh giá cuối mới. `Interaction stacking` chỉ thực nghiệm lịch sử hoặc kế hoạch mới, không mô tả bundle hiện tại.

Nguồn sơ cấp đã đối chiếu:

- [Mishra–Soni v1](https://data.mendeley.com/datasets/f45bkkt8pr/1): quy mô và nhãn nguồn.
- [SmishX commit cố định](https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff): provenance nguồn.
- [PhishVN v4](https://data.mendeley.com/datasets/b97hxbxtpd/4): tier, abuse scope và HTTPS collection artifact.
- [Grouped evaluation](https://scikit-learn.org/stable/modules/cross_validation.html), [logistic regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression), [probability calibration](https://scikit-learn.org/stable/modules/calibration.html): căn cứ kỹ thuật; chọn threshold không tự tạo calibration.
- [Sample-weighted class balancing](https://scikit-learn.org/stable/modules/generated/sklearn.utils.class_weight.compute_class_weight.html): đối chiếu với mã scikit-learn 1.9.1 đã cài.
