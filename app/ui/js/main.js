import { login, submit2FA, restartLogin } from './login.js';
import { loadAlbums } from './albums.js';

document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
});

window.addEventListener('pywebviewready', async () => {
  try {
    const shouldBypassLogin = await globalThis.pywebview.api.is_dev_bypass_enabled();
    if (shouldBypassLogin) {
      await loadAlbums();
    }
  } catch (err) {
    console.error('Failed to determine startup mode.', err);
  }
});
