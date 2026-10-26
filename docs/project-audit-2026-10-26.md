# Đánh giá ScamGuard-AI — 26/10/2026

## Kết luận và phạm vi

Đã thực hiện kiểm thử phần mềm, quét dependency/secret/cấu hình/giấy phép bằng
Trivy, đo Lighthouse trên bản production, kiểm tra giao diện bằng Edge/Playwright,
rà soát API và extension theo các yêu cầu ASVS phù hợp, và chạy cleanlab trên
toàn bộ dữ liệu train hiện hành. Đây là đánh giá có bằng chứng tại thời điểm chạy,
không phải chứng nhận ASVS, kiểm thử xâm nhập đầy đủ hay chứng minh mô hình tốt
trên các chiến dịch lừa đảo mới.

Các sửa lỗi đã được kiểm chứng giúp giảm rủi ro phần mềm. Trước khi đưa dịch vụ
ra Internet vẫn cần hoàn thiện giới hạn truy cập theo môi trường triển khai,
chính sách dữ liệu và đánh giá ML độc lập. Các giới hạn còn lại được ghi bên dưới.

Bằng chứng gốc nằm trong [audit-evidence/2026-10-26](audit-evidence/2026-10-26/).
Các thay đổi đã tồn tại trước đợt đánh giá được giữ lại; không tạo commit hoặc
đẩy mã lên remote. Bản chụp diff ban đầu nằm ở `.local-runtime/audit/before.patch`.

## Kiểm chứng phần mềm

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Python unittest | 91/91 qua | `python-tests-after.log` |
| Node: assessment, JSON body, extension | 28/28 qua | `node-tests-after.log` |
| Vòng đời tiến trình suy luận | 3/3 qua | `inference-lifecycle.log` |
| API với model thật | 16/16 qua | `api-tests-after.log` |
| API khi thiếu model | 2/2 qua | `model-unavailable-tests-after.log` |
| ESLint, TypeScript | Qua | `lint-after.log`, `typecheck.log` |
| Production/standalone build | Qua, Next.js 16.4.3 | `build-after.log` |
| Trình duyệt: nhập liệu, API, đổi ngôn ngữ, responsive | Qua | `browser-audit.json` |

Tổng 140 test tự động qua, ngoài các assertion trong kiểm tra trình duyệt.
Kiểm thử API dùng server riêng và `RATE_LIMIT_PER_MINUTE=1000` để tránh quota
10 request/phút làm sai kết quả hồi quy; kiểm thử này không chứng nhận quota
production. Kiểm thử giới hạn đồng thời vẫn dùng ngưỡng thật là hai tiến trình.

Đã lưu các lần kiểm thử đỏ trước sửa. Mutation trong bộ nhớ loại bỏ điều kiện
`do_not_train` cũng bị test phát hiện; source thực tế không bị sửa bởi mutation.
Hai cổng `--require-campaigns` và `--require-expert-labels` tiếp tục trả mã 2,
đúng với việc thiếu bằng chứng tương ứng. Không hạ điều kiện để đạt PASS.

Build trong sandbox từng lỗi EPERM ở bước standalone trên Windows; build ngoài
sandbox thành công. Đây là giới hạn quyền môi trường, không phải lý do bỏ qua build.

## Bảo mật và dependency

| Hạng mục | Trước | Sau |
|---|---|---|
| npm audit, gồm development dependencies | 7 package có cảnh báo: 2 critical, 5 high | 0 cảnh báo đã biết |
| Trivy dependency scan | 21 bản ghi advisory trong dependency production | 0, đã bật thêm development dependencies |
| Docker chạy root | HIGH, DS-0002 | Đã cấu hình UID/GID 10001 |
| Docker healthcheck | LOW, DS-0026 | Còn, cần gắn với healthcheck của nền tảng triển khai |
| pip trong `.venv` | 25.2 có advisory | Cập nhật 26.2.2; quét môi trường thực tế còn 0 advisory |

Đã cập nhật `next` và `eslint-config-next` từ 16.3.1 lên 16.4.3; cập nhật
DOMPurify, sharp và các dependency gián tiếp có cảnh báo trong phạm vi dependency
cho phép. Không dùng `audit fix --force`; install script bị tắt khi cập nhật.
NumPy, pandas, scikit-learn và artifact model phục vụ không được nâng phiên bản.

Trivy 0.76.1 được lấy từ GitHub release chính thức; SHA256 khớp cả digest asset
và file checksum của release. Đây là kiểm tra tính toàn vẹn, chưa phải xác minh
chữ ký Sigstore. Lần quét không phát hiện secret trong phạm vi quét; không quét
git history, dữ liệu train, môi trường cục bộ hoặc các báo cáo sinh ra.
Quét giấy phép có bật; license Python được kiểm tra bổ sung bằng metadata cục bộ.
Không suy ra dependency an toàn tuyệt đối từ việc không có advisory.

### Những lỗi đã sửa

- Cả hai API đọc JSON theo stream với giới hạn 256 KiB trước khi parse; JSON sai
  trả 400, media type không hỗ trợ trả 415, body quá lớn trả 413.
- Hai API chia sẻ giới hạn tối đa hai tiến trình Python trong mỗi server process.
  Khi hết chỗ, trả 503 thay vì tạo hàng đợi không giới hạn hoặc bịa điểm an toàn.
  Đã kiểm tra phục hồi sau khởi động Python thất bại, child exit lỗi và hoàn tất.
- Giữ timeout suy luận 15 giây và giới hạn stdout; không gửi stderr hoặc đường
  dẫn nội bộ cho client. Không thêm shell vào đường truyền input tới Python.
- Bổ sung MIME protection, frame restrictions, referrer policy, permissions policy
  và CSP cơ bản. CSP chưa có `script-src`/nonce nên chưa là CSP đầy đủ theo ASVS.
- Khai báo đường dẫn script Python tường minh: bản standalone trước sửa chứa
  405 file dữ liệu train, khoảng 1,257 tỷ byte; bản sau sửa không chứa file nào
  trong `ml_model/data/`. Cấu hình exclude đơn thuần không có tác dụng trong lần
  build Windows này; đã xác minh đầu ra thực tế sau sửa đường dẫn và include.
  Windows vẫn trace một file Python executable, không phải một môi trường chạy
  hoàn chỉnh; khi chạy standalone cần đặt `PYTHON_EXECUTABLE` tới Python hợp lệ.
- Dockerfile chuyển sang user không đặc quyền; Docker daemon trên máy chưa chạy,
  nên thay đổi container mới được kiểm tra cấu hình, chưa build/run image.

### Extension

Đã sửa request từ dạng `URL + Title` giả làm SMS sang URL-only, để điểm URL là
kết quả chính khi kiểm tra trang. Đã tái hiện lỗi cũ: nhánh URL có điểm 0,992311
nhưng nhánh SMS do extension tạo ra chỉ 79, khiến không hiện banner HIGH.

Extension hiện gửi scheme/host/port/path tới `http://localhost:3000/api/analyze`;
loại credentials, query, fragment và title. Điểm áp dụng cho URL đã tối giản;
đổi này giảm thu thập token nhưng cũng bỏ tín hiệu tấn công chỉ có trong query.
Path vẫn có thể chứa dữ liệu nhạy cảm; không được coi đây là ẩn danh hóa đầy đủ.
Banner vẫn theo chính sách HIGH/điểm >=80, không phải mọi nhãn URL dương >=0,50.

So sánh origin đã thay string-prefix: `http://localhost:3000@evil.example/` và
localhost ở cổng khác không còn bị bỏ qua. VM tests kiểm tra payload, banner,
protocol và background messaging. Chưa xác minh extension được cài thật trong
Chrome/Edge với local-network permissions/CORS. Manifest vẫn có `<all_urls>`;
cần quyết định mô hình opt-in và quyền tối thiểu trước khi phát hành extension.

## Đối chiếu ASVS 5.0 có chọn lọc

| Yêu cầu | Đánh giá trong phạm vi này |
|---|---|
| V1.2.1 — output encoding | React escaping và extension `textContent`; rà soát tĩnh không thấy sink HTML từ input |
| V1.5.2 — deserialization | Hybrid kiểm tra SHA256 model/code trước pickle; chỉ chấp nhận artifact cục bộ tin cậy, không chứng minh cho mọi legacy mode |
| V2.1.3, V2.2.1, V2.2.2 — giới hạn và validation | Đã kiểm chứng byte cap, validation phía server và admission dùng chung; quota phân tán chưa có |
| V4.1.3 — header từ proxy | Còn thiếu: limiter tin `x-forwarded-for`/`x-real-ip`; phải cấu hình proxy tin cậy |
| V3.4.2 — CORS | Wildcard vẫn tồn tại cho API public không có session; cần đánh giá lại theo topology/extension và dữ liệu trả về |
| V3.4.3 — CSP | Một phần: object/base/frame restrictions; chưa có script allowlist/nonce |
| V3.4.5, V3.4.6 — referrer và frame | Đã xác minh response headers trên standalone |
| V14.3.3 — browser storage | Rà soát tĩnh thấy tùy chọn ngôn ngữ/theme/onboarding, không thấy lưu nội dung phân tích vào storage |
| V15.1.1 — component maintenance | Có lockfile và kết quả quét; chưa có CI tự động hoặc lịch cập nhật được cấu hình |
| V16.5.1 — lỗi không lộ nội bộ | Test thiếu model và lỗi đầu vào qua; không thấy traceback/path trong response |
| V6/V7/V9/V10 | Không áp dụng cho tính năng hiện hành: chưa có account/session/token/OAuth |

Danh mục trên không bao phủ mọi yêu cầu của ASVS và không gán cấp L1/L2/L3.

## Hiệu năng và giao diện

Lighthouse 13.5.0 chạy trên Edge headless với profile riêng, bản production
localhost, chế độ mobile mặc định. Báo cáo HTML/JSON trước và sau được lưu nguyên
trong thư mục bằng chứng. Các điểm và metric cuối nằm ở `summary.json`.

| Chỉ số mobile | Trước | Sau |
|---|---:|---:|
| Performance | 83 | 89 |
| Accessibility | 89 | 100 |
| Best practices / SEO | 100 / 100 | 100 / 100 |
| Largest Contentful Paint | 3,254 giây | 2,238 giây |
| Total Blocking Time | 97 ms | 73 ms |
| CLS | 0,194 | 0,194 |
| JavaScript transfer ở lần tải đầu | 336.228 byte | 165.275 byte |

Đây là hai snapshot lab, không phải thử nghiệm có kiểm soát để quy toàn bộ
chênh lệch thời gian cho một thay đổi. Mức giảm JavaScript phù hợp với việc tách
tải thư viện PDF; chưa thu thập dữ liệu RUM hoặc kiểm tra nhiều lần để đo phương sai.

Đã bỏ giới hạn zoom, sửa màu chữ disclaimer và đồng bộ `html.lang` khi đổi sang
tiếng Việt. Đã chuyển html2canvas/jsPDF sang tải khi xuất PDF để giảm JavaScript
ở lần tải đầu. Browser audit kiểm tra chiều rộng 320/390/768/1024/1440, không
tràn ngang; luồng phân tích model thật và đổi ngôn ngữ qua, không có lỗi console,
request thất bại hoặc request ngoài origin trong luồng đã thử.

CLS mobile còn khoảng 0,194, chủ yếu liên quan nội dung onboarding xuất hiện
sau hydration. Một số sample/feed dùng div có click nên vẫn cần kiểm tra và sửa
khả năng thao tác bàn phím. Điểm accessibility tự động không thay kiểm tra WCAG
thủ công. Chưa kiểm chứng chức năng xuất PDF trong đợt này. Thời gian API gồm
khởi động Python và nạp model, khoảng vài giây; Lighthouse không đo được độ trễ
phân loại. Số đo lab không phải Core Web Vitals của người dùng thực.

## Dữ liệu và supervised ML

cleanlab 2.9.0 chạy local, với môi trường riêng; không tải corpus lên cloud.
Chỉ dùng 3.800 SMS train và 32.777 URL train đã được đóng băng. Chia 5 fold theo
`repair_group` bằng StratifiedGroupKFold, seed 42. Mỗi fold fit lại toàn bộ pipeline
đặc trưng và classifier trên phần train của fold; mỗi hàng có đúng một dự đoán
ngoài nhóm. Cả 10 fold có giao nhóm bằng 0. Các nhóm là proxy nội dung/domain,
chưa phải chiến dịch đã được chuyên gia xác minh.

| Nhánh | Mẫu train | Mẫu cần xem lại | Nguồn nhãn của mẫu được gợi ý |
|---|---:|---:|---|
| SMS | 3.800 | 14 | 11 AI review, 1 nguồn nghiên cứu, 2 nhãn nguồn ham/spam |
| URL | 32.777 | 797 | Tất cả kế thừa nguồn good/bad, chưa được chuyên gia xác minh |

Đây là 811 **ứng viên rà soát**, không phải 811 nhãn đã được chứng minh sai.
Không tự đổi nhãn, không fit lại hoặc activate model phục vụ. SHA256 bundle và
manifest trước/sau khớp. Không dùng dự đoán validation/test để fit hay xếp hạng;
chỉ đọc metadata holdout để kiểm tra tính toàn vẹn và cách ly dữ liệu.

Đầu ra riêng tư nằm ở `ml_model/data/prepared/label_audit_2026-10-26/`:

- `sms_findings.jsonl`, `url_findings.jsonl`: điểm, fold và nguồn gốc nhãn.
- `sms_blind_review.jsonl`, `url_blind_review.jsonl`: nội dung cho người gán nhãn,
  không hiển thị nhãn gốc hoặc đề xuất model; trường chuyên gia còn trống.
- `*_out_of_group_predictions.jsonl`: dự đoán ngoài nhóm để tái kiểm tra.
- `summary.json`: hash dữ liệu/code và bằng chứng mỗi fold.

Không đưa các file nội dung rà soát lên `public/` hoặc báo cáo được version hóa.
Chỉ bản tổng hợp được sao chép vào thư mục bằng chứng.

Các hạn chế ML vẫn còn: SMS test lịch sử có 38 tin/24 dương cùng nhóm nguồn;
holdout đã được dùng ở các thí nghiệm trước; thiếu campaign ID xác minh; nhãn URL
chưa được chuyên gia xác nhận; chưa có URL validation độc lập để chọn ngưỡng;
điểm chưa hiệu chuẩn; dữ liệu train URL hiện chỉ dùng scheme http. Cần thu thập
tập tiếng Việt có nhãn độc lập và đánh giá theo chiến dịch/thời gian trước khi
tuyên bố hiệu quả ngoài thực tế. Không dùng cleanlab thay cho đánh giá này.

## Kiến trúc, vận hành và phần việc còn lại

- Module assessment/inference/URL context đã tách; input đi qua JSON stdin,
  không nối vào shell và không fetch URL mục tiêu trong đường suy luận đã xem.
- `page.tsx` còn lớn, chứa cả UI, sample và xuất báo cáo. Nên tách theo tính năng
  khi phát triển tiếp; đợt đánh giá không thực hiện refactor diện rộng.
- Limiter theo IP còn dùng Map không dọn entry hết hạn và tin header forwarding.
  Cần xác định proxy tin cậy rồi bổ sung quota phù hợp; hai-process admission
  chỉ bảo vệ từng server process, số lượng tăng theo số replica.
- Chưa có CI/CD kiểm tra tự động, logging/monitoring vận hành đầy đủ hoặc
  healthcheck được kiểm chứng. Không triển khai hay tạo tích hợp ngoài trong đợt này.
- Repo chưa có LICENSE ở gốc. Không tự chọn giấy phép thay chủ dự án; cần rà soát
  quyền phân phối source, model và từng dataset. Các gói trong `public/test-data`
  được phục vụ công khai khi deploy; cần xác nhận phạm vi xuất bản dự kiến.

## Chạy lại

```powershell
npm.cmd test
npm.cmd run test:inference
.\.venv\Scripts\python.exe -m unittest discover -s ml_model -v
npm.cmd run lint
npm.cmd run check:types
npm.cmd run build
# Với server test production tại 3101, quota đủ cho kiểm thử:
$env:TEST_APP_URL = 'http://127.0.0.1:3101'
npm.cmd run test:api
node scripts/browser-audit.mjs
```

Môi trường audit tách khỏi runtime ứng dụng:

```powershell
python -m venv .local-runtime/audit/python-env
.\.local-runtime\audit\python-env\Scripts\python.exe -m pip install -r ml_model/requirements-audit.txt
# Mỗi lần dùng một thư mục output MỚI; không ghi đè lần rà soát đã đóng băng.
.\.local-runtime\audit\python-env\Scripts\python.exe ml_model/audit_labels.py --output ml_model/data/prepared/label_audit_NEW
npm.cmd install --prefix .local-runtime/audit/node-tools --ignore-scripts --save-exact lighthouse@13.5.0 playwright@1.64.1
$env:CHROME_PATH = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
node .local-runtime/audit/node-tools/node_modules/lighthouse/cli/index.js http://127.0.0.1:3101 --chrome-flags='--headless=new --no-first-run' --output=json --output=html --output-path=.local-runtime/audit/lighthouse-NEW
```

Khi chạy standalone cục bộ, copy `public` và `.next/static` vào standalone theo
tài liệu Next.js, đặt `HOSTNAME=127.0.0.1`, `PORT=3101` và `PYTHON_EXECUTABLE` là
đường dẫn tuyệt đối tới `.venv/Scripts/python.exe`, rồi chạy
`node .next/standalone/server.js`. Test thiếu model dùng server riêng 3102 và
`SCAMGUARD_MODEL_PATH` trỏ tới file không tồn tại; không đổi tên model thật.

Trivy dùng `fs --scanners vuln,secret,misconfig,license --include-dev-deps`, xuất
JSON, không lọc riêng HIGH/CRITICAL. Các thư mục loại trừ: node_modules, .next,
.git, .venv, .local-runtime, ml_model/data, public/test-data, docs/audit-evidence.
Lock của công cụ và SHA256 Trivy được lưu cùng bằng chứng để tái lập.

## Nguồn chính thức

- [Next.js 16.4.3 release](https://github.com/vercel/next.js/releases/tag/v16.4.3)
- [Trivy 0.76.1 release](https://github.com/aquasecurity/trivy/releases/tag/v0.76.1)
- [Trivy filesystem scanners](https://trivy.dev/docs/latest/target/filesystem/)
- [Lighthouse](https://github.com/GoogleChrome/lighthouse)
- [cleanlab 2.9.0 API/source](https://github.com/cleanlab/cleanlab/blob/v2.9.0/cleanlab/filter.py)
- [cleanlab 2.9.0 LICENSE: Apache-2.0](https://github.com/cleanlab/cleanlab/blob/v2.9.0/LICENSE)
- [OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS/tree/v5.0.0/5.0/en)
