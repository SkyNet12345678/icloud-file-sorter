import { login, submit2FA, restartLogin } from './login.js';
import { startSort, cancelSort, testFetchAlbumAssets } from './albums.js';

document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');
  const startButton = document.getElementById('download-btn');
  const cancelButton = document.getElementById('cancel-btn');
  const testFetchBtn = document.getElementById('test-fetch-btn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
  startButton.addEventListener('click', startSort);
  cancelButton.addEventListener('click', cancelSort);
  testFetchBtn.addEventListener('click', testFetchAlbumAssets);
});
