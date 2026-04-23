import { login, submit2FA, restartLogin } from './login.js';
import { startSort, cancelSort } from './albums.js';
import { loadSettings, saveSettings } from './settings.js';

document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  const verifyBtn = document.getElementById('verifyBtn');
  const restartBtn = document.getElementById('restartBtn');
  const startButton = document.getElementById('download-btn');
  const cancelButton = document.getElementById('cancel-btn');
  const sourceFolderInput = document.getElementById('source-folder-input');
  const sortingApproach = document.getElementById('sorting-approach');

  loginBtn.addEventListener('click', login);
  verifyBtn.addEventListener('click', submit2FA);
  restartBtn.addEventListener('click', restartLogin);
  startButton.addEventListener('click', startSort);
  cancelButton.addEventListener('click', cancelSort);

  if (sourceFolderInput) {
    sourceFolderInput.addEventListener('change', () => {
      saveSettings(sourceFolderInput.value, sortingApproach?.value);
    });
  }
  if (sortingApproach) {
    sortingApproach.addEventListener('change', () => {
      saveSettings(sourceFolderInput?.value, sortingApproach.value);
    });
  }

  loadSettings();
});
