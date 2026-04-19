let sortTimer = null;
let sortState = 'idle';

export async function loadAlbums() {
  document.getElementById('status').textContent = 'Loading albums...';

  try {
    const result = await globalThis.pywebview.api.get_albums();
    const normalizedResult = normalizeAlbumResult(result);

    console.log('Albums:', normalizedResult);
    showAlbums(normalizedResult.albums);
    updateAlbumsStatus(getAlbumStatusMessage(normalizedResult), !normalizedResult.success);
  } catch (err) {
    console.error(err);
    showAlbums([]);
    updateAlbumsStatus('Failed to load albums.', true);
  }
}

export function showAlbums(albums) {
  const list = document.getElementById('albums-list');
  list.innerHTML = '';

  albums.forEach((album, index) => {
    const li = document.createElement('li');
    li.className = 'album-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `album-${index}`;
    checkbox.dataset.albumId = album.id;
    checkbox.dataset.albumName = album.name;

    checkbox.addEventListener('change', updateSelection);

    const label = document.createElement('label');
    label.htmlFor = checkbox.id;

    const title = document.createElement('strong');
    title.textContent = album.name;

    const lineBreak = document.createElement('br');

    const meta = document.createElement('span');
    meta.textContent = formatAlbumItemCount(album.item_count);

    li.appendChild(checkbox);
    label.appendChild(title);
    label.appendChild(lineBreak);
    label.appendChild(meta);
    li.appendChild(label);
    list.appendChild(li);
  });

  document.querySelector('.login-card').style.display = 'none';
  document.getElementById('albums-view').style.display = 'block';

  resetSortProgress();
  updateSelection();
}

function updateSelection() {
  const checkboxes = document.querySelectorAll('#albums-list input[type="checkbox"]');
  const selectedCheckboxes = Array.from(checkboxes).filter((cb) => cb.checked);
  const selected = selectedCheckboxes.length;
  const downloadButton = document.getElementById('download-btn');
  const isSorting = downloadButton.dataset.sorting === 'true';

  if (!isSorting) {
    if (selected > 0) {
      sortState = 'idle';
      showSelectionSummary();
      updateSelectionSummary(selectedCheckboxes.map((checkbox) => checkbox.dataset.albumName));
    } else if (sortState === 'idle') {
      showSelectionSummary();
      updateSelectionSummary([]);
    }
  }

  downloadButton.disabled = selected === 0 || isSorting;
}

export async function startSort() {
  if (!globalThis.pywebview?.api) {
    console.log('pywebview API not ready');
    return;
  }

  const downloadButton = document.getElementById('download-btn');
  if (downloadButton.dataset.sorting === 'true') {
    return;
  }

  const albumIds = Array.from(
    document.querySelectorAll('#albums-list input[type="checkbox"]:checked')
  ).map((checkbox) => checkbox.dataset.albumId);

  if (albumIds.length === 0) {
    return;
  }

  downloadButton.dataset.sorting = 'true';
  sortState = 'running';
  setSortControls(true);
  setCheckboxesDisabled(true);
  setSortProgress({
    percent: 0,
    message: 'Starting sort...',
    status: 'running',
  });

  try {
    const result = await globalThis.pywebview.api.start_sort(albumIds);

    if (!result?.job_id) {
      throw new Error(result?.error || 'Failed to start sort');
    }

    if (sortTimer) {
      clearInterval(sortTimer);
    }

    sortTimer = setInterval(async () => {
      try {
        const progress = await globalThis.pywebview.api.get_sort_progress(result.job_id);
        setSortProgress(progress);

        if (progress.status === 'complete' || progress.status === 'error') {
          clearInterval(sortTimer);
          sortTimer = null;
          downloadButton.dataset.sorting = 'false';
          setSortControls(false);
          setCheckboxesDisabled(false);
          sortState = progress.status;
          clearSelections();
          updateSelection();
        }
      } catch (error) {
        clearInterval(sortTimer);
        sortTimer = null;
        downloadButton.dataset.sorting = 'false';
        setSortControls(false);
        setCheckboxesDisabled(false);
        sortState = 'error';
        clearSelections();
        setSortProgress({
          percent: 0,
          message: 'Failed to fetch sort progress.',
          status: 'error',
        });
        updateSelection();
        console.error(error);
      }
    }, 100);
  } catch (error) {
    downloadButton.dataset.sorting = 'false';
    setSortControls(false);
    setCheckboxesDisabled(false);
    sortState = 'idle';
    showSelectionSummary();
    updateSelection();
    console.error(error);
  }
}

function setCheckboxesDisabled(disabled) {
  const checkboxes = document.querySelectorAll('#albums-list input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    checkbox.disabled = disabled;
  });
}

function resetSortProgress() {
  sortState = 'idle';
  setSortControls(false);
  showSelectionSummary();
  updateSelectionSummary([]);
  setSortProgress({
    percent: 0,
    message: '',
    status: 'idle',
  });
}

function setSortProgress(progress) {
  const percent = Math.max(0, Math.min(progress.percent ?? 0, 100));
  const selectionSummary = document.getElementById('sort-selection');
  const progressContent = document.getElementById('sort-progress-content');
  const progressFill = document.getElementById('sort-progress-fill');
  const progressPercent = document.getElementById('sort-progress-percent');
  const progressMessage = document.getElementById('sort-progress-message');

  selectionSummary.hidden = progress.status !== 'idle';
  progressContent.hidden = progress.status === 'idle';
  progressFill.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
  progressMessage.textContent = progress.message || '';
}

function updateSelectionSummary(selectedAlbums) {
  const selectionSummary = document.getElementById('sort-selection');

  if (selectedAlbums.length === 0) {
    selectionSummary.textContent = 'No albums selected';
    return;
  }

  selectionSummary.textContent = selectedAlbums.join(', ');
}

function showSelectionSummary() {
  const selectionSummary = document.getElementById('sort-selection');
  const progressContent = document.getElementById('sort-progress-content');

  selectionSummary.hidden = false;
  progressContent.hidden = true;
}

function clearSelections() {
  const checkboxes = document.querySelectorAll('#albums-list input[type="checkbox"]');
  checkboxes.forEach((checkbox) => {
    checkbox.checked = false;
  });
}

export function cancelSort() {
  // TODO: Wire this to a real backend cancel endpoint once cancellation is supported.
  console.log('Cancel sort requested, but backend cancellation is not implemented yet.');
}

function setSortControls(isSorting) {
  const downloadButton = document.getElementById('download-btn');
  const cancelButton = document.getElementById('cancel-btn');

  downloadButton.hidden = isSorting;
  cancelButton.hidden = !isSorting;
}

function normalizeAlbumResult(result) {
  if (Array.isArray(result)) {
    return {
      success: true,
      albums: result,
      error: null,
    };
  }

  return {
    success: result?.success === true,
    albums: Array.isArray(result?.albums) ? result.albums : [],
    error: result?.error || null,
  };
}

function getAlbumStatusMessage(result) {
  if (!result.success) {
    return result.error || 'Failed to load albums.';
  }

  if (result.albums.length === 0) {
    return 'No eligible albums found in iCloud Photos.';
  }

  return '';
}

function updateAlbumsStatus(message, isError = false) {
  const albumsStatus = document.getElementById('albums-status');
  albumsStatus.hidden = message.length === 0;
  albumsStatus.textContent = message;
  albumsStatus.dataset.state = isError ? 'error' : 'info';
}

function formatAlbumItemCount(itemCount) {
  const normalizedCount = Number.isFinite(itemCount) ? itemCount : 0;
  const suffix = normalizedCount === 1 ? 'item' : 'items';
  return `${normalizedCount} ${suffix}`;
}
