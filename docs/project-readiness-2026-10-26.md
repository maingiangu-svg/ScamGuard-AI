# Năm bước chuẩn bị vận hành — 26/10/2026

Phạm vi: tiếp tục sau [đợt audit ban đầu](project-audit-2026-10-26.md).
Người dùng chọn extension có cả thủ công/tự động; chưa có chuyên gia hoặc dữ
liệu tiếng Việt mới đã xác minh nên bước ML chỉ chuẩn bị rà soát và quy trình.
Các thay đổi hiện ở workspace; chưa triển khai lại website Cloud Run.

## 1. Bảo mật API và cấu hình production

- Hai endpoint dùng chung quota theo process, có giới hạn bộ nhớ bucket, từ
  chối khi đầy và trả `Retry-After`. Xoay header IP không vượt được quota tổng.
- Mặc định không tin `X-Forwarded-For`/`X-Real-IP`. Chỉ dùng số hop proxy đã
  cấu hình và địa chỉ IP hợp lệ. Chưa xác minh proxy production nên giữ hop 0.
- CORS dùng allowlist origin cụ thể; không suy ra quyền từ Host. Có regression
  cho Host/Origin giả, preflight, cache và giới hạn body theo byte.
- HTML dùng CSP nonce mới mỗi response, `private, no-store`; API `no-store`.
  CSS vẫn cho inline style vì giao diện hiện tại cần thuộc tính style.
- `/api/health` kiểm checksum hybrid artifact. Smoke test phải gọi dự đoán thật;
  endpoint health không tự chứng nhận Python runtime hay chất lượng mô hình.

Giới hạn: quota nằm trong bộ nhớ mỗi process, không phải quota toàn hệ thống
khi có nhiều replica hoặc restart. Chưa đo/cấu hình giới hạn ở tầng edge thực tế.
Các kiểm tra này là bằng chứng cục bộ, chưa xác nhận revision Cloud Run đang chạy.

## 2. Container và extension được cài thật

Container chạy UID/GID `10001:10001`, có Docker HEALTHCHECK và HTTP startup/
liveness probe trong script deploy. `scripts/container-smoke.mjs` kiểm root
filesystem read-only, health, dự đoán URL thật và không đóng gói `ml_model/data`;
chỉ xóa container thử nghiệm do chính script tạo.

Docker Desktop ban đầu không khởi động được do lỗi đổi tên socket
`sailor-ingest.sock` sang `.stale` (`The file cannot be accessed by the system`).
Lần kiểm tra sau engine đã trả phiên bản `29.7.2`; không xác định được tác nhân
làm engine phục hồi. Không reset/xóa Docker data để xử lý sự cố này.
**Build Linux image và smoke test thực tế đều PASS**: UID/GID 10001, filesystem
chỉ đọc, health 200, dự đoán URL thật 200 (858 ms trong lần kiểm này), không có
`ml_model/data` trong image. Container thử nghiệm đã được xóa sau kiểm tra.
Evidence: `readiness-evidence/2026-10-26/docker-build.log`, `container-smoke.json`
và `container.log`. Image local: `scamguard-readiness:20261026`.

Extension:

- Mặc định thủ công; popup cho đổi sang tự động và xin host permission tùy chọn.
- Service worker gọi API localhost; chỉ gửi URL đã bỏ user/password/query/hash,
  không gửi tiêu đề/nội dung trang. Path vẫn có thể chứa thông tin cá nhân.
- Đổi mode được tuần tự hóa; trang web không được tự bật chế độ tự động.
- Cài production manifest trong Chromium riêng: thủ công, popup → service worker
  → API → banner và chặn tự động thiếu quyền đều PASS.
- Kiểm tự động sau cấp quyền bằng manifest fixture được ghi rõ khác biệt;
  source script giữ nguyên. Bật/tắt và ngừng quét ở trang mới đều PASS.

**Còn kiểm thủ công trước release:** native permission prompt accept/deny, quyền
`activeTab` trên website ngoài localhost, cùng các phiên bản Chrome/Edge hỗ trợ.
Fixture không chứng minh các bước cấp quyền native này. Xem [hướng dẫn extension](../extension/README.md).

## 3. CI

Workflow `.github/workflows/quality.yml` trên Ubuntu dùng action pin theo commit,
quyền `contents: read`, dependency lock, test/build/typecheck, API/quota, trình
duyệt/extension, audit dependency, kiểm PDF và build/smoke Docker. Evidence được
upload cả khi có lỗi. Không có bước tự deploy hoặc merge.

Các test Python đã bỏ phụ thuộc fixture dữ liệu riêng nhưng giữ kiểm checksum,
holdout và bảo toàn điểm. Bản sao sạch chỉ có `.py`, ba model artifact đã track
và thư mục prepared rỗng chạy **94/94 PASS**.

Workflow chưa được push/chạy trên GitHub. Cũng chưa thiết lập branch protection;
tài khoản hiện tại có quyền push nhưng không có quyền admin repo. Kiểm tra local
không được gọi là một remote CI run đã thành công.

## 4. Rà soát nhãn và benchmark độc lập

Đã chuẩn bị **811 ứng viên train: 14 SMS, 797 URL**, hai CSV độc lập, thứ tự
xáo trộn, không hiện nhãn gốc/điểm model; có danh tính input và chống công thức CSV.
Gói nằm trong `ml_model/data/prepared/expert_review_2026-10-26/`, được gitignore.
Không đưa nội dung tập rà soát lên GitHub qua thay đổi này.

Gate hiện **811 pending, 0 agreed, complete=false**; exit 2 là trạng thái chưa
hoàn thành theo thiết kế. Không có nhãn chuyên gia được tạo hoặc tự chứng nhận.
[Quy trình](ml-expert-review-protocol.md) mô tả hai reviewer, phân xử, nhãn yếu/
nhãn chuyên gia, provenance, benchmark tiếng Việt mới độc lập theo nhóm/thời gian,
khóa test trước fit và báo cáo độ bất định. 811 ca train không phải test mới.

Giữ hướng supervised learning. Không fit lại model hay thay dataset trong bước này.
SHA-256 vẫn giữ nguyên:

```text
hybrid_bundle.pkl  9a49b7278cfb1b9da00f8ebc6970653a9de3320f3037db3ee190109926d1bd3a
hybrid_manifest.json  27225103284ed36354a0c370eade49448324e09994e6cf44bb29fb50e63c3e7f
```

## 5. CLS, bàn phím và PDF

SSR đọc cookie ngôn ngữ/theme/onboarding để tránh chèn nội dung sau hydration;
đổi lựa chọn hoặc đóng hướng dẫn vẫn giữ qua reload. Giao diện có thể zoom;
sample/feed dùng bàn phím Enter/Space, textarea có nhãn truy cập.

Xuất PDF bằng jsPDF và Noto Sans đóng gói tại chỗ, có tiếng Việt, ngắt trang,
đánh số trang và ghi rõ demo/giới hạn mô hình. Lỗi tải PDF hiện thông báo lỗi.
Đã kiểm file tải thực tế, Unicode tiếng Việt, demo disclaimer, giới hạn mô hình
và render trực quan. Font giữ giấy phép OFL trong `public/fonts/`.

Lighthouse mobile, production standalone trên máy local:

| Chỉ số | Audit trước | Sau năm bước |
| --- | ---: | ---: |
| Performance | 89 | 99 |
| Accessibility | 100 | 100 |
| CLS | 0,194 | 0 |
| LCP | — | 2,207 giây |
| TBT | — | 42 ms |

Đây là một phép đo lab, không phải field data, SLA hay cam kết WCAG đầy đủ.
Kiểm browser ở 320/390/768/1024/1440 px không tràn ngang; không ghi nhận lỗi
console, request lỗi hoặc request ngoài origin trong kịch bản được kiểm.

## Bằng chứng và trạng thái kiểm tra

Trong [thư mục evidence](readiness-evidence/2026-10-26/):

- **150 test PASS:** Python 94 + Node 34 + inference lifecycle 3 + API 17 +
  model-unavailable 2. Gate pending nhãn không nằm trong số test lỗi.
- Full integration runner exit 0: quota chung, browser/PDF và extension cài thật.
- Lint, TypeScript và production build PASS.
- Docker build và container smoke PASS trên Linux engine 29.7.2.
- npm audit: 0 vulnerability; Trivy: 0 vulnerability, 0 misconfiguration fail,
  0 secret finding trong phạm vi scan tại thời điểm chạy.
- `browser-audit.json`, `extension-browser.json`, `ci-integration-final.log`,
  `clean-python-tests.log`, `lighthouse-mobile.report.json`, `trivy.json`.

Những việc cần bằng chứng ngoài workspace: remote CI run và bảo vệ nhánh, kiểm
native permission/activeTab, xác minh cấu hình sau deploy; sau đó mới quyết định
release. Nhãn chuyên gia/benchmark mới cần người và dữ liệu thực tế theo quy trình.
