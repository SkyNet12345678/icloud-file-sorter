import { login, submit2FA, restartLogin } from './login.js';
import { loadAlbums } from './albums.js';

// to stop skipping login, use the commented-out code
document.addEventListener('DOMContentLoaded', async () => {
  // document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
});

window.addEventListener('pywebviewready', async () => {
  await loadAlbums();
});
