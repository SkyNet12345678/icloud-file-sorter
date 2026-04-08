import { login, submit2FA, restartLogin } from './login.js';
import { loadAlbums, startSort } from './albums.js';

// to stop skipping login, use the commented-out code
document.addEventListener('DOMContentLoaded', async () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');
  const startButton = document.getElementById('download-btn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
  startButton.addEventListener('click', startSort);
});

window.addEventListener('pywebviewready', async () => {
  await loadAlbums();
});


// document.addEventListener('DOMContentLoaded', () => {
//   const loginBtn = document.getElementById('loginBtn');
//   const verifyBtn = document.getElementById('verifyBtn');
//   const restartBtn = document.getElementById('restartBtn');
//   const startButton = document.getElementById('download-btn');

//   loginBtn.addEventListener('click', login);
//   verifyBtn.addEventListener('click', submit2FA);
//   restartBtn.addEventListener('click', restartLogin);
//   startButton.addEventListener('click', startSort)
// });
