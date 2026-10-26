const status = document.getElementById('status');
const check = document.getElementById('check');
const modes = document.querySelectorAll('input[name="mode"]');
const origins = ['http://*/*', 'https://*/*'];
document.getElementById('version').textContent = `Phiên bản ${chrome.runtime.getManifest().version}`;

async function showSettings(ensure = false) {
  const settings = await chrome.runtime.sendMessage({action: 'GET_SETTINGS', ensure});
  if (settings.error) throw new Error(settings.error);
  document.querySelector(`input[value="${settings.automatic ? 'automatic' : 'manual'}"]`).checked = true;
  if (settings.automatic) {
    if (settings.unsupportedPage) {status.textContent = 'Trang này không hỗ trợ kiểm tra. Hãy mở một trang HTTP/HTTPS.'; return;}
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    const badge = tab && await chrome.action.getBadgeText({tabId: tab.id});
    status.textContent = badge === '!' ? 'Chưa kiểm tra được trang này. Hãy kiểm tra quyền extension và dịch vụ local.'
      : /^\d+$/.test(badge) ? `Kết quả trang hiện tại: ${badge}/100. Hãy xác minh độc lập.`
      : 'Tự quét đang bật. Trang web sẽ được kiểm tra khi tải xong.';
  }
}
showSettings(true).catch(error => {status.textContent = error.message;});
setInterval(() => {
  if (![...modes].some(radio => radio.disabled)) showSettings().catch(() => {});
}, 1000);

for (const mode of modes) mode.addEventListener('change', async () => {
  for (const radio of modes) radio.disabled = true;
  try {
    const automatic = mode.value === 'automatic';
    if (automatic && !await chrome.permissions.request({origins})) throw new Error('Bạn chưa cấp quyền tự quét.');
    const result = await chrome.runtime.sendMessage({action: 'SET_MODE', automatic});
    if (result.error) throw new Error(result.error);
    const removed = automatic || await chrome.permissions.remove({origins}).catch(() => false);
    status.textContent = automatic ? 'Đã bật tự quét và kiểm tra trang đang mở. Điểm sẽ hiện trên biểu tượng.'
      : 'Đã chuyển sang quét thủ công.' + (removed ? '' : ' Bạn có thể thu hồi quyền trang web trong cài đặt trình duyệt.');
  } catch (error) {
    status.textContent = error.message;
    await showSettings();
  } finally { for (const radio of modes) radio.disabled = false; }
});

check.addEventListener('click', async () => {
  check.disabled = true;
  status.textContent = 'Đang kiểm tra bằng mô hình local…';
  try {
    const result = await chrome.runtime.sendMessage({action: 'CHECK_ACTIVE_TAB'});
    if (result?.error) throw new Error(result.error);
    if (!Number.isFinite(result?.riskScore)) throw new Error('Chưa có kết quả. Hãy kiểm tra dịch vụ local.');
    status.textContent = `${result.riskScore}/100 — ${result.riskLevel}. ${result.summary ?? ''}`;
  } catch (error) { status.textContent = error.message; }
  finally { check.disabled = false; }
});
