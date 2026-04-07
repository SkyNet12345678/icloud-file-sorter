document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
});

async function login() {
  if (!globalThis.pywebview?.api) {
    console.log('Bridge not ready');
    return;
  }

  const appleId = document.getElementById('appleId').value;
  const password = document.getElementById('password').value;

  const result = await globalThis.pywebview.api.login(appleId, password);

  console.log(result);

  if (result.success) {
    document.getElementById('status').innerText = 'Logged in!';
    document.getElementById('login-form').style.display = 'none';
  } else if (result['2fa_required']) {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('2fa-form').style.display = 'block';
    document.getElementById('status').innerText = result.message;
  } else {
    document.getElementById('status').innerText = result.message;
  }
}

async function submit2FA() {
  const code = document.getElementById('2faCode').value;

  document.getElementById('status').innerText = 'Verifying...';

  const result = await globalThis.pywebview.api.verify_2fa(code);

  console.log(result);

  if (result.success) {
    document.getElementById('status').innerText = 'Logged in!';
    document.getElementById('2fa-form').style.display = 'none';
  } else {
    document.getElementById('status').innerText = result.message;
  }
}

function restartLogin() {
  document.getElementById('2fa-form').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('status').innerText = 'Please sign in again.';
}
