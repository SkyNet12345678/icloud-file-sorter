let currentSettings = {};

export async function loadSettings() {
  try {
    const result = await window.pywebview.api.get_settings();
    if (result.success) {
      currentSettings = result.settings || {};
      updateSettingsUI(result.source_folder, result.sorting_approach);
      return result;
    }
  } catch (exc) {
    console.error("Failed to load settings:", exc);
  }
  return null;
}

function updateSettingsUI(sourceFolder, sortingApproach) {
  const folderInput = document.getElementById("source-folder-input");
  const approachSelect = document.getElementById("sorting-approach");
  const copyWarning = document.getElementById("copy-warning");

  if (folderInput) {
    folderInput.value = sourceFolder || "";
  }
  if (approachSelect) {
    approachSelect.value = sortingApproach || "first";
  }
  if (copyWarning) {
    copyWarning.style.display = sortingApproach === "copy" ? "block" : "none";
  }
}

export async function saveSettings(sourceFolder, sortingApproach) {
  try {
    const result = await window.pywebview.api.save_settings(
      sourceFolder,
      sortingApproach
    );
    if (result.success) {
      currentSettings = result.settings || {};
      return true;
    }
  } catch (exc) {
    console.error("Failed to save settings:", exc);
  }
  return false;
}

export async function detectSourceFolder() {
  try {
    const result = await window.pywebview.api.detect_source_folder();
    if (result.success) {
      return result.source_folder;
    }
  } catch (exc) {
    console.error("Failed to detect source folder:", exc);
  }
  return null;
}

export function getCurrentSettings() {
  return currentSettings;
}

export function showCopyWarning(show) {
  const copyWarning = document.getElementById("copy-warning");
  if (copyWarning) {
    copyWarning.style.display = show ? "block" : "none";
  }
}