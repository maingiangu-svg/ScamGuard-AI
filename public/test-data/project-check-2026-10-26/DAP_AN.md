# Đáp án nguồn — bộ kiểm tra dự án 26/10/2026

Đối chiếu **nhãn nhánh** trong ứng dụng: SMS dùng ngưỡng 0,65, URL dùng 0,50. Các mốc cảnh báo 30/80 là chính sách khác.

SMS: 1 = smishing theo nguồn; 0 = không smishing theo nguồn, có thể gồm spam. URL: 1 = phishing theo nguồn audit; 0 = legitimate tại thời điểm bằng chứng. Nhãn 0 không xác nhận website hiện còn an toàn.

Không gộp ba phần thành một chỉ số accuracy. Phần tiếng Việt chỉ có nhãn AI tham khảo; các phần còn lại dùng nhãn người của nguồn, chưa phải thẩm định chuyên gia mới của dự án.

## SMS_EN

| ID | Nhãn nguồn | Nhóm |
|---|---:|---|
| SMISHX-0019 | 0 | SX-G-3743 |
| SMISHX-0028 | 0 | SX-G-3752 |
| SMISHX-0031 | 0 | SX-G-3755 |
| SMISHX-0041 | 0 | SX-G-3765 |
| SMISHX-0042 | 0 | SX-G-3765 |
| SMISHX-0043 | 0 | SX-G-3765 |
| SMISHX-0044 | 0 | SX-G-3768 |
| SMISHX-0610 | 0 | SX-G-4334 |
| SMISHX-0617 | 1 | SX-G-4341 |
| SMISHX-0631 | 0 | SX-G-4355 |
| SMISHX-0639 | 1 | SX-G-4341 |
| SMISHX-0676 | 1 | SX-G-4341 |
| SMISHX-0685 | 1 | SX-G-4341 |
| SMISHX-0687 | 1 | SX-G-4341 |
| SMISHX-0710 | 1 | SX-G-4341 |
| SMISHX-0755 | 1 | SX-G-4341 |
| SMISHX-0783 | 1 | SX-G-4341 |
| SMISHX-0786 | 1 | SX-G-4341 |
| SMISHX-0818 | 1 | SX-G-4341 |
| SMISHX-0844 | 1 | SX-G-4341 |
| SMISHX-0854 | 1 | SX-G-4341 |
| SMISHX-0856 | 0 | SX-G-4580 |
| SMISHX-0861 | 1 | SX-G-4341 |
| SMISHX-0912 | 1 | SX-G-4341 |
| SMISHX-0927 | 1 | SX-G-4341 |
| SMISHX-0956 | 1 | SX-G-4341 |
| SMISHX-1040 | 1 | SX-G-4341 |
| SMISHX-1048 | 1 | SX-G-4341 |
| SMISHX-1105 | 1 | SX-G-4341 |
| SMISHX-1113 | 1 | SX-G-4341 |
| SMISHX-1116 | 1 | SX-G-4341 |
| SMISHX-1145 | 1 | SX-G-4341 |
| SMISHX-1147 | 1 | SX-G-4341 |
| SMISHX-1154 | 0 | SX-G-4580 |
| SMISHX-1188 | 1 | SX-G-4341 |
| SMISHX-1194 | 0 | SX-G-4580 |

## URL

| ID | Nhãn nguồn | Nhóm |
|---|---:|---|
| PHISHVN-AUDIT-V0005 | 1 | 854107.vip |
| PHISHVN-AUDIT-V0006 | 0 | thanhhoa.gov.vn |
| PHISHVN-AUDIT-V0008 | 0 | kairyudo.co.jp |
| PHISHVN-AUDIT-V0009 | 1 | shopeevn6.com |
| PHISHVN-AUDIT-V0011 | 0 | phukiensongtoan.com |
| PHISHVN-AUDIT-V0012 | 0 | grass.io |
| PHISHVN-AUDIT-V0022 | 1 | yd516.com |
| PHISHVN-AUDIT-V0025 | 1 | vietnamxcm.vip |
| PHISHVN-AUDIT-V0027 | 0 | blogtamsu.vn |
| PHISHVN-AUDIT-V0030 | 1 | lz002.com |
| PHISHVN-AUDIT-V0031 | 1 | exoduuss.online |
| PHISHVN-AUDIT-V0033 | 1 | hi-go.org |
| PHISHVN-AUDIT-V0034 | 1 | arroyowhipsnake.com |
| PHISHVN-AUDIT-V0036 | 0 | asj-muenster.de |
| PHISHVN-AUDIT-V0039 | 0 | cpmstar.com |
| PHISHVN-AUDIT-V0040 | 0 | gialai.gov.vn |
| PHISHVN-AUDIT-V0046 | 0 | backan.gov.vn |
| PHISHVN-AUDIT-V0047 | 1 | amrsd.com |
| PHISHVN-AUDIT-V0048 | 0 | caobang.gov.vn |
| PHISHVN-AUDIT-V0051 | 0 | congluan.vn |
| PHISHVN-AUDIT-V0053 | 0 | hosting.net.np |
| PHISHVN-AUDIT-V0054 | 0 | baohiemxahoi.gov.vn |
| PHISHVN-AUDIT-V0055 | 0 | caobang.gov.vn |
| PHISHVN-AUDIT-V0056 | 0 | now.vn |
| PHISHVN-AUDIT-V0057 | 0 | mofa.gov.vn |
| PHISHVN-AUDIT-V0058 | 0 | denisland.com |
| PHISHVN-AUDIT-V0059 | 0 | hochiminhcity.gov.vn |
| PHISHVN-AUDIT-V0060 | 1 | vdvbnhg6y.com |
| PHISHVN-AUDIT-V0066 | 0 | dienmayxanhantam.com |
| PHISHVN-AUDIT-V0067 | 0 | eso-community.net |
| PHISHVN-AUDIT-V0068 | 1 | asp7890.com |
| PHISHVN-AUDIT-V0069 | 0 | vlute.edu.vn |
| PHISHVN-AUDIT-V0071 | 0 | haiphong.edu.vn |
| PHISHVN-AUDIT-V0072 | 0 | nilssonlee.se |
| PHISHVN-AUDIT-V0074 | 0 | quangngai.gov.vn |
| PHISHVN-AUDIT-V0076 | 0 | zim.vn |
| PHISHVN-AUDIT-V0082 | 0 | thuathienhue.gov.vn |
| PHISHVN-AUDIT-V0091 | 1 | vizonegeek.com |
| PHISHVN-AUDIT-V0092 | 0 | gskygo.com |
| PHISHVN-AUDIT-V0094 | 0 | aschumsseafoodab.com |
| PHISHVN-AUDIT-V0102 | 1 | vitemac.com |
| PHISHVN-AUDIT-V0103 | 0 | goldencollections.net |
| PHISHVN-AUDIT-V0105 | 0 | rent-my-tesla.de |
| PHISHVN-AUDIT-V0107 | 0 | ozio.tw |
| PHISHVN-AUDIT-V0111 | 0 | ninhbinh.gov.vn |
| PHISHVN-AUDIT-V0113 | 0 | myleague.vn |
| PHISHVN-AUDIT-V0114 | 0 | bfgoodrich.vn |
| PHISHVN-AUDIT-V0118 | 1 | i-goda.shop |
| PHISHVN-AUDIT-V0120 | 1 | vitructuyen24-7.com |
| PHISHVN-AUDIT-V0123 | 0 | torzilla.de |
| PHISHVN-AUDIT-V0126 | 0 | uscloudminer.com |
| PHISHVN-AUDIT-V0133 | 0 | ngocrongonline.com |
| PHISHVN-AUDIT-V0136 | 0 | mail.az |
| PHISHVN-AUDIT-V0138 | 0 | sailportal.it |
| PHISHVN-AUDIT-V0139 | 0 | tancangwarehousing.com.vn |
| PHISHVN-AUDIT-V0143 | 0 | haiphong.edu.vn |
| PHISHVN-AUDIT-V0144 | 0 | gplxgov.org |
| PHISHVN-AUDIT-V0145 | 0 | ibiblioteka.lt |
| PHISHVN-AUDIT-V0147 | 0 | haiphong.edu.vn |
| PHISHVN-AUDIT-V0149 | 0 | vnskills.edu.vn |
| PHISHVN-AUDIT-V0150 | 1 | sd9490.xyz |
| PHISHVN-AUDIT-V0151 | 0 | lamdong.gov.vn |
| PHISHVN-AUDIT-V0152 | 0 | catholic-forum.com |
| PHISHVN-AUDIT-V0155 | 0 | hdndbinhduong.vn |
| PHISHVN-AUDIT-V0156 | 0 | bambooairlines.com.vn |
| PHISHVN-AUDIT-V0161 | 0 | senooee.com |
| PHISHVN-AUDIT-V0162 | 0 | mekongasean.vn |
| PHISHVN-AUDIT-V0163 | 0 | pink.rs |
| PHISHVN-AUDIT-V0164 | 1 | vn924364shop.com |
| PHISHVN-AUDIT-V0167 | 1 | tianaicn.com |
| PHISHVN-AUDIT-V0172 | 0 | securitytrails.com |
| PHISHVN-AUDIT-V0177 | 1 | lienquanmobilevn.site |
| PHISHVN-AUDIT-V0178 | 0 | mofa.gov.vn |
| PHISHVN-AUDIT-V0186 | 0 | haiphong.edu.vn |
| PHISHVN-AUDIT-V0188 | 1 | xvbwmht.cn |
| PHISHVN-AUDIT-V0190 | 1 | meta88.com |
| PHISHVN-AUDIT-V0192 | 0 | thanhhoa.gov.vn |
| PHISHVN-AUDIT-V0194 | 0 | petrosains.com.my |
| PHISHVN-AUDIT-V0196 | 0 | benxehoabinh.com.vn |
| PHISHVN-AUDIT-V0197 | 1 | lovelive-app.com |

## VI_DIAGNOSTIC

| ID | Nhãn nguồn | Nhóm |
|---|---:|---|
| VITRAIN-1997 | 1 | R2-G-1997 |
| VITRAIN-2026 | 1 | R2-G-2026 |
| VITRAIN-0057 | 0 | R2-G-0057 |
| VITRAIN-0307 | 0 | R2-G-0307 |
| VITRAIN-0320 | 0 | R2-G-0320 |
| VITRAIN-0368 | 0 | R2-G-0324 |
| VITRAIN-0410 | 0 | R2-G-0230 |
| VITRAIN-0500 | 0 | R2-G-0500 |
| VITRAIN-0518 | 0 | R2-G-0507 |
| VITRAIN-0660 | 0 | R2-G-0660 |
| VITRAIN-0686 | 0 | R2-G-0686 |
| VITRAIN-0706 | 0 | R2-G-0081 |
| VITRAIN-0739 | 0 | R2-G-0739 |
| VITRAIN-0742 | 0 | R2-G-0742 |
| VITRAIN-0787 | 0 | R2-G-0787 |
| VITRAIN-0817 | 0 | R2-G-0817 |
| VITRAIN-0841 | 0 | R2-G-0818 |
| VITRAIN-0909 | 0 | R2-G-0909 |
| VITRAIN-0939 | 0 | R2-G-0939 |
| VITRAIN-0948 | 0 | R2-G-0948 |
| VITRAIN-0961 | 0 | R2-G-0961 |
| VITRAIN-0974 | 0 | R2-G-0974 |
| VITRAIN-1010 | 0 | R2-G-1010 |
| VITRAIN-1088 | 0 | R2-G-1088 |
| VITRAIN-1175 | 0 | R2-G-0935 |
| VITRAIN-1205 | 0 | R2-G-1205 |
| VITRAIN-1246 | 0 | R2-G-1230 |
| VITRAIN-1287 | 0 | R2-G-0329 |
| VITRAIN-1311 | 0 | R2-G-1311 |
| VITRAIN-1351 | 0 | R2-G-1351 |
| VITRAIN-1433 | 0 | R2-G-1433 |
| VITRAIN-1475 | 0 | R2-G-1292 |
| VITRAIN-1484 | 0 | R2-G-1381 |
| VITRAIN-1541 | 0 | R2-G-1541 |
| VITRAIN-1546 | 0 | R2-G-1546 |
| VITRAIN-1612 | 0 | R2-G-1612 |
| VITRAIN-1635 | 0 | R2-G-0370 |
| VITRAIN-1683 | 0 | R2-G-1683 |
| VITRAIN-1699 | 0 | R2-G-1699 |
| VITRAIN-1734 | 0 | R2-G-1734 |
| VITRAIN-1770 | 0 | R2-G-1770 |
| VITRAIN-1772 | 1 | R2-G-1772 |
| VITRAIN-1776 | 1 | R2-G-1776 |
| VITRAIN-1795 | 1 | R2-G-1795 |
| VITRAIN-1799 | 1 | R2-G-1765 |
| VITRAIN-1804 | 1 | R2-G-1804 |
| VITRAIN-1815 | 0 | R2-G-1815 |
| VITRAIN-1918 | 0 | R2-G-1918 |
| VITRAIN-1944 | 0 | R2-G-1944 |
| VITRAIN-1955 | 0 | R2-G-1955 |
| VITRAIN-1957 | 0 | R2-G-1957 |
| VITRAIN-1991 | 1 | R2-G-1991 |
| VITRAIN-1996 | 1 | R2-G-1996 |
| VITRAIN-2002 | 1 | R2-G-2002 |
| VITRAIN-2038 | 1 | R2-G-2038 |
| VITRAIN-2079 | 1 | R2-G-2079 |
| VITRAIN-2085 | 0 | R2-G-2085 |
| VITRAIN-2094 | 0 | R2-G-2094 |
| VITRAIN-2110 | 1 | R2-G-2110 |
| VITRAIN-2126 | 0 | R2-G-2126 |
| VITRAIN-2168 | 1 | R2-G-2168 |
| VITRAIN-2186 | 0 | R2-G-2086 |
| VITRAIN-2219 | 0 | R2-G-2219 |
| VITRAIN-2221 | 0 | R2-G-2221 |
| VITRAIN-2232 | 1 | R2-G-2232 |
| VITRAIN-2233 | 0 | R2-G-1080 |
| VITRAIN-2315 | 1 | R2-G-2267 |
| VITRAIN-2372 | 0 | R2-G-2293 |
