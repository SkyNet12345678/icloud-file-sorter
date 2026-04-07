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

  if (!appleId || !password) {
    document.getElementById('status').innerText = 'Please enter credentials.';
    return;
  }

  loginBtn.disabled = true;

  let result;
  try {
    result = await globalThis.pywebview.api.login(appleId, password);
  } catch (err) {
    console.error(err);
    document.getElementById('status').innerText = 'Login failed. Try again.';
    loginBtn.disabled = false;
    return;
  }

  console.log(result);

  loginBtn.disabled = false;
  document.getElementById('password').value = '';

  if (!result) {
    document.getElementById('status').innerText = 'Login failed.';
    return;
  }

  if (result.success) {
    document.getElementById('status').innerText = 'Logged in!';
    document.getElementById('login-form').style.display = 'none';
  } else if (result['2fa_required']) {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('2fa-form').style.display = 'block';
    document.getElementById('status').innerText = result.message || '2FA required.';
  } else {
    document.getElementById('status').innerText = result.message || 'Login failed.';
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
