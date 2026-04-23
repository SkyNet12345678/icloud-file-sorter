let currentSettings = {};

async function getPywebviewApi() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (globalThis.pywebview?.api) {
      return globalThis.pywebview.api;
    }

    await new Promise((resolve) => {
      globalThis.setTimeout(resolve, 50);
    });
  }

  throw new Error("pywebview API not ready");
}

export async function loadSettings() {
  try {
    const api = await getPywebviewApi();
    const result = await api.get_settings();
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
    const api = await getPywebviewApi();
    const result = await api.save_settings(
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
    const api = await getPywebviewApi();
    const result = await api.detect_source_folder();
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
