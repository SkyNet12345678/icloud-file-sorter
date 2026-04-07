import { login, submit2FA, restartLogin } from './login.js';

document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
});
