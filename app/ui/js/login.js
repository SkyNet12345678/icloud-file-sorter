import { loadAlbums } from './albums.js';

export async function login() {
  if (!globalThis.pywebview?.api) {
    console.log('Bridge not ready');
    return;
  }

  const loginBtn = document.getElementById('loginBtn');
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

  loginBtn.disabled = false;
  document.getElementById('password').value = '';

  if (!result) {
    document.getElementById('status').innerText = 'Login failed.';
    return;
  }

  if (result.success) {
    // Logged in without 2FA
    await loadAlbums();
  } else if (result['2fa_required']) {
    // Show 2FA form
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('2fa-form').style.display = 'block';
    document.getElementById('status').innerText = result.message || 'Enter your verification code.';
  } else {
    // Other failures
    document.getElementById('status').innerText = result.message || 'Login failed.';
  }
}

export async function submit2FA() {
  const code = document.getElementById('2faCode').value;

  if (!code) {
    document.getElementById('status').innerText = 'Enter code';
    return;
  }

  document.getElementById('status').innerText = 'Verifying...';

  let result;
  try {
    result = await globalThis.pywebview.api.verify_2fa(code);
  } catch (err) {
    console.error(err);
    document.getElementById('status').innerText = 'Verification failed.';
    return;
  }

  if (result.success) {
    await loadAlbums();
  } else {
    document.getElementById('status').innerText = result.message || 'Invalid code';
  }
}

export function restartLogin() {
  document.getElementById('2fa-form').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('status').innerText = 'Please sign in again.';
}