import {jsPDF} from 'jspdf';

type Report = {caseId: string; language: 'vi' | 'en'; score: number; level: string;
  summary: string; reasons: string[]; actions: string[]; illustrative: boolean};

export async function downloadReport(report: Report) {
  const response = await fetch('/fonts/NotoSans-Regular.ttf');
  if (!response.ok) throw new Error('Report font unavailable');
  const bytes = new Uint8Array(await response.arrayBuffer());
  let binary = '';
  for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192));
  const pdf = new jsPDF({unit: 'mm', format: 'a4'});
  pdf.addFileToVFS('NotoSans-Regular.ttf', btoa(binary));
  pdf.addFont('NotoSans-Regular.ttf', 'NotoSans', 'normal');
  pdf.setFont('NotoSans');
  let y = 22;
  function write(text: string, size = 11) {
    pdf.setFontSize(size);
    for (const line of pdf.splitTextToSize(text, 170)) {
      if (y > 274) {pdf.addPage(); y = 22;}
      pdf.text(String(line), 20, y);
      y += size * .45 + 2;
    }
    y += 3;
  }
  const vi = report.language === 'vi';
  write(vi ? 'ScamGuard — Báo cáo kiểm tra' : 'ScamGuard — Screening report', 18);
  write(`${vi ? 'Mã báo cáo' : 'Case ID'}: ${report.caseId}`);
  if (report.illustrative) write(vi ? 'VÍ DỤ MINH HỌA — không phải kết quả chạy mô hình.' : 'ILLUSTRATIVE EXAMPLE — not a live model result.');
  write(`${vi ? 'Điểm mô hình' : 'Model score'}: ${report.score}/100 — ${report.level}`, 14);
  write(report.summary);
  if (report.reasons.length) {
    write(vi ? 'Tín hiệu cần xem lại' : 'Signals to review', 13);
    for (const reason of report.reasons) write('• ' + reason);
  }
  if (report.actions.length) {
    write(vi ? 'Hành động đề xuất' : 'Suggested actions', 13);
    for (const action of report.actions) write('• ' + action);
  }
  write(vi ? 'Giới hạn: điểm chưa được hiệu chuẩn, không phải xác suất lừa đảo. Trang đích chưa được xác minh trực tiếp. Hãy kiểm tra qua kênh độc lập.'
    : 'Limitations: the score is uncalibrated and is not a fraud probability. The target website has not been verified live. Verify through an independent channel.');
  const pages = pdf.getNumberOfPages();
  for (let page = 1; page <= pages; page++) {
    pdf.setPage(page); pdf.setFontSize(9); pdf.text(`${page}/${pages}`, 190, 287, {align: 'right'});
  }
  pdf.save(`ScamGuard-${report.caseId || 'report'}.pdf`);
}
