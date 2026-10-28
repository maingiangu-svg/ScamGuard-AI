const status = document.getElementById('status');
const result = document.getElementById('result');
const check = document.getElementById('check');
const viewId = new URLSearchParams(location.search).get('check');
let displayedId = viewId, revision = 0;

document.getElementById('version').textContent = 'Phiên bản ' + chrome.runtime.getManifest().version;
document.getElementById('instructions').hidden = !!viewId;
document.getElementById('close').hidden = !viewId;
document.body.classList.toggle('result-view', !!viewId);
document.getElementById('close').addEventListener('click', () => window.close());

function render(job) {
  result.hidden = !job;
  if (!job) {
    status.textContent = viewId ? 'Kết quả đã hết hạn. Hãy chọn kiểm tra lại từ menu chuột phải.' : 'Chọn link hoặc tin nhắn để kiểm tra.';
    return;
  }
  displayedId = job.id ?? displayedId;
  const done = job.status === 'done';
  result.dataset.level = done ? job.level : 'UNKNOWN';
  document.getElementById('kind').textContent = job.kind === 'message' ? 'Tin nhắn đã chọn'
    : job.kind === 'page' ? 'Trang bạn yêu cầu kiểm tra' : 'Liên kết bạn chọn';
  document.getElementById('target').textContent = job.target ?? '';
  document.getElementById('score').textContent = done ? job.score + '/100' : '';
  document.getElementById('level').textContent = done ? {LOW: 'Rủi ro thấp', MEDIUM: 'Cần thận trọng', HIGH: 'Rủi ro cao'}[job.level] : '';
  document.getElementById('summary').textContent = done ? job.summary : job.status === 'error' ? job.error : 'Đang chờ kết quả từ mô hình local…';
  const note = document.getElementById('url-note');
  note.hidden = !done || !Number.isInteger(job.urlScore);
  note.textContent = note.hidden ? '' : 'Link trong tin nhắn: ' + job.urlScore + '/100 — cần xác minh độc lập. Điểm chính của tin nhắn được giữ nguyên.';
  status.textContent = job.status === 'pending' ? 'Đang kiểm tra…' : job.status === 'error' ? 'Chưa kiểm tra được.' : 'Đã kiểm tra theo yêu cầu của bạn.';
}

async function load() {
  const current = revision;
  const job = await chrome.runtime.sendMessage({action: 'GET_RESULT', ...(viewId ? {id: viewId} : {})});
  if (current !== revision) return;
  if (job?.error && !job.status) throw new Error(job.error);
  render(job);
}
load().catch(error => {status.textContent = error.message;});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'session' || !changes.checks) return;
  const job = changes.checks.newValue?.[viewId ?? displayedId];
  if (job) {revision++; render(job);}
});

check.addEventListener('click', async () => {
  revision++;
  displayedId = null;
  check.disabled = true;
  render({kind: 'page', status: 'pending'});
  try {
    const job = await chrome.runtime.sendMessage({action: 'CHECK_ACTIVE_TAB'});
    if (job?.error && !job.status) throw new Error(job.error);
    render(job);
  } catch (error) {
    render({kind: 'page', status: 'error', error: error.message});
  } finally {check.disabled = false;}
});
