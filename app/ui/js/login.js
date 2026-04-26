import { loadAlbums } from './albums.js';

export async function initializeLogin() {
  const api = globalThis.pywebview?.api;
  if (!api?.get_auth_state) {
    document.getElementById('status').innerText = 'Loading sign-in state...';
    waitForAuthApi().then(loadAuthState);
    return;
  }

  await loadAuthState(api);
}

async function loadAuthState(api) {
  if (!api?.get_auth_state) {
    showFirstLogin('Sign in required. Please enter your Apple ID and password.');
    return;
  }

  try {
    const state = await api.get_auth_state();
    if (state?.has_remembered_apple_id && state.remembered_apple_id) {
      showReturningUser(state.remembered_apple_id);
      return;
    }
  } catch (err) {
    console.error(err);
  }

  showFirstLogin();
}

function waitForAuthApi(timeoutMs = 3000, intervalMs = 50) {
  return new Promise((resolve) => {
    let resolved = false;
    let timeoutId;
    let intervalId;

    const done = (api) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeoutId);
      clearInterval(intervalId);
      document.removeEventListener('pywebviewready', check);
      resolve(api);
    };

    const check = () => {
      const api = globalThis.pywebview?.api;
      if (api?.get_auth_state) {
        done(api);
      }
    };

    document.addEventListener('pywebviewready', check);
    intervalId = setInterval(check, intervalMs);
    timeoutId = setTimeout(() => done(globalThis.pywebview?.api), timeoutMs);
    check();
  });
}

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
    document.getElementById('returning-user').style.display = 'none';
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('2fa-form').style.display = 'block';
    document.getElementById('status').innerText = result.message || 'Enter your verification code.';
  } else {
    // Other failures
    document.getElementById('status').innerText = result.message || 'Login failed.';
  }
}

export async function continueSession() {
  if (!globalThis.pywebview?.api?.continue_session) {
    showFirstLogin('Sign in required. Please enter your Apple ID and password.');
    return;
  }

  const continueBtn = document.getElementById('continueBtn');
  continueBtn.disabled = true;
  document.getElementById('status').innerText = 'Checking saved session...';

  let result;
  try {
    result = await globalThis.pywebview.api.continue_session();
  } catch (err) {
    console.error(err);
    showFirstLogin('Session expired. Please sign in again.');
    return;
  } finally {
    continueBtn.disabled = false;
  }

  if (result?.success) {
    await loadAlbums();
    return;
  }

  showFirstLogin(result?.message || 'Session expired. Please sign in again.');
}

export async function notYou() {
  if (globalThis.pywebview?.api?.logout) {
    document.getElementById('status').innerText = 'Clearing saved session...';
    try {
      await globalThis.pywebview.api.logout();
    } catch (err) {
      console.error(err);
      document.getElementById('status').innerText = 'Could not clear saved session.';
      return;
    }
  }

  showFirstLogin('Please sign in with your Apple ID.');
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
  showFirstLogin('Please sign in again.');
}

function showReturningUser(appleId) {
  document.getElementById('rememberedAppleId').innerText = appleId;
  document.getElementById('returning-user').style.display = 'block';
  document.getElementById('login-form').style.display = 'none';
  document.getElementById('2fa-form').style.display = 'none';
  document.getElementById('status').innerText = '';
}

function showFirstLogin(message = '') {
  document.getElementById('returning-user').style.display = 'none';
  document.getElementById('2fa-form').style.display = 'none';
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('password').value = '';
  document.getElementById('status').innerText = message;
}
