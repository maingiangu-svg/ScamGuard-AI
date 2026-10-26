# Triage image Docker — 26/10/2026

## Kết quả mới nhất: runtime Distroless

Image `scamguard-completion:final`, ID
`sha256:e24341d01486e14aafca029bcb7dc1c2ba334790344b4302a69baa8387bd880f`,
được Trivy 0.76.1 quét lại lúc 21:58 UTC+7: **0 High, 0 Critical**.
Runtime dùng `gcr.io/distroless/cc-debian13:nonroot` khóa theo digest trong
Dockerfile. Các công cụ OS không dùng bởi dịch vụ được loại khỏi image cuối;
không sửa mức severity, miễn trừ advisory hoặc giấu package inventory.

Scanner vẫn nhận diện 19 package OS, gồm đủ năm thư viện Python bổ sung
libbz2, libdb5.3, libffi, liblzma, libsqlite3. Script staging giữ control record
dpkg và copyright; gate yêu cầu inventory OS, Node và Python hợp lệ. Một báo
cáo trống hoặc thiếu các thư viện cần thiết không được coi là kết quả sạch.

Smoke test image cuối PASS: URL và SMS chạy model mới có hiệu chuẩn, UID10001,
root filesystem chỉ đọc, không có pip đang hoạt động hoặc các executable
shell/mount/nsenter/perl/infocmp/systemd-homed/apt/dpkg được kiểm tra.
Runtime này phục vụ các script suy luận cố định; không phải môi trường Python
đa dụng đầy đủ mọi thư viện hệ thống tùy chọn. CI đã thêm gate image High/Critical
sau smoke, nhưng CI của thay đổi mới còn chờ công khai nhánh được phê duyệt.

Bằng chứng: [scan](completion-evidence/2026-10-26/container-scan.json),
[smoke](completion-evidence/2026-10-26/container-smoke.json).
Kết quả chỉ có giá trị theo database scanner tại thời điểm quét; cần rebuild
và quét lại trước release. Những bảng bên dưới ghi lại **lịch sử image cũ**.

## Lịch sử trước chuyển runtime

Trivy 0.76.1, scanner vuln, severity HIGH/CRITICAL, không ignore-unfixed hoặc
miễn trừ CVE. Kết quả quét source/dependency trong audit trước không bao gồm
toàn bộ package hệ điều hành của image. CI hiện gate npm/pip dependency và
Docker smoke; ở snapshot cũ **chưa gate các cảnh báo OS liệt kê dưới đây**.

| Image local đã scan | OS | Bản ghi package–advisory | Advisory duy nhất | Critical | Có FixedVersion |
| --- | --- | ---: | ---: | ---: | ---: |
| trước: `sha256:0a3fa340ab42abde633700263cd0d5f17da3f73973ac8f096af9730dae04d51f` | Debian 12.15 | 67 | 20 | 2 | 4 |
| sau: `sha256:a920ceb66d0b2c2bd998108b77d1f3d8e905b6c56a74569b352677e6c131386c` | Debian 13.7 | 44 | 8 | 0 | 0 |

Thời điểm scan lần lượt 15:39 và 15:44 UTC+7. JSON đầy đủ có metadata/version,
package và trạng thái ở `readiness-evidence/2026-10-26/container-scan-before.json`
và `container-scan-after.json`. Số lượng bản ghi không phải số lỗ hổng độc lập.

## Thay đổi đã kiểm chứng

Chuyển runtime sang biến thể Python chính thức dùng [Debian 13 stable](https://www.debian.org/releases/).
Sau cài runtime requirements, chạy `pip check` rồi gỡ pip theo [lệnh uninstall
chính thức](https://pip.pypa.io/en/stable/cli/pip_uninstall/). Không nâng riêng
setuptools/urllib3 bên ngoài để cố sửa bản vendored trong pip. Python có thể
vẫn mang wheel [ensurepip](https://docs.python.org/3/library/ensurepip.html);
không tuyên bố mọi bản sao installer đã bị loại bỏ.

Image mới build và smoke PASS với Node/Next thực tế, cả SMS và URL, health200,
UID10001, read-only root. Node và Python image scan không có High/Critical.
Đây là kết quả tại thời điểm scan, không phải cam kết không có advisory mới.

## Tám advisory OS còn theo dõi

Tất cả 44 bản ghi sau cập nhật là High; scan không nêu FixedVersion cho trixie.
Bảng nhóm theo source package, không lặp một CVE cho mọi binary package:

| Nhóm/package đại diện | Phiên bản | Advisory của Debian |
| --- | --- | --- |
| util-linux/bsdutils | `1:2.41.5-0+deb13u1` | [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) |
| libacl1 | `2.3.2-2+b1` | [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) |
| ncurses | `6.5+20250216-2` | [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) |
| libsystemd0/libudev1 | `257.13-1~deb13u1` | [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) |
| perl-base | `5.40.1-6+deb13u1` | [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) |

Theo mô tả nhà phân phối, các đường tấn công liên quan mount/nsenter đặc quyền,
ACL qua pathname, infocmp, systemd-homed hoặc Perl Archive::Tar. Serving code chỉ
chạy các script Python cố định để xử lý text/URL, không gọi những công cụ này.
Đây là nhận xét từ code và advisory, **chưa phải chứng minh không khai thác được**.
UID10001, quota, body cap và read-only filesystem trong smoke giảm một phần rủi
ro; quyền/capabilities/filesystem thực tế của deployment cần xác minh riêng.

Không xóa metadata package hoặc miễn trừ toàn bộ OS để đạt số 0. Riêng cảnh báo
Bookworm zlib [CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853)
có ghi chú Debian rằng contrib/minizip không được build trong binary package;
không suy rộng ghi chú đó cho các CVE còn lại.

Chưa có quyết định chấp nhận rủi ro production. Trước release cần người sở hữu
deployment đánh giá đường tấn công/capabilities, cập nhật image và quét lại;
rà soát tiếp trước release hoặc ngày 02/11/2026, mốc nào đến trước. Có bản vá
trixie thì rebuild và chạy lại cả hai nhánh inference. Không trộn gói Debian
unstable vào runtime chỉ để xóa cảnh báo.
