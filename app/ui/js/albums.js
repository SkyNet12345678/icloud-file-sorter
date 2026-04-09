let sortTimer = null;

export async function loadAlbums() {
  document.getElementById('status').innerText = 'Loading albums...';

  try {
    const albums = await globalThis.pywebview.api.get_albums();
    console.log('Albums:', albums);
    showAlbums(albums);
  } catch (err) {
    console.error(err);
    document.getElementById('status').innerText = 'Failed to load albums.';
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
    checkbox.dataset.index = index;

    checkbox.addEventListener('change', updateSelection);

    const label = document.createElement('label');
    label.htmlFor = checkbox.id;
    label.innerHTML = `
      <strong>${album.name}</strong><br>
      <span>${album.photos} photos ${album.videos ? `• ${album.videos} videos` : ''}</span>
    `;

    li.appendChild(checkbox);
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
  const selected = Array.from(checkboxes).filter((cb) => cb.checked).length;
  const downloadButton = document.getElementById('download-btn');
  const isSorting = downloadButton.dataset.sorting === 'true';
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

  const indexes = Array.from(
    document.querySelectorAll('#albums-list input[type="checkbox"]:checked')
  ).map((checkbox) => Number(checkbox.dataset.index));

  if (indexes.length === 0) {
    return;
  }

  downloadButton.dataset.sorting = 'true';
  setCheckboxesDisabled(true);
  setSortProgress({
    percent: 0,
    message: 'Starting sort...',
    status: 'running',
  });

  try {
    const result = await globalThis.pywebview.api.start_sort(indexes);

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
          setCheckboxesDisabled(false);
          updateSelection();
        }
      } catch (error) {
        clearInterval(sortTimer);
        sortTimer = null;
        downloadButton.dataset.sorting = 'false';
        setCheckboxesDisabled(false);
        updateSelection();
        setSortProgress({
          percent: 0,
          message: 'Failed to fetch sort progress.',
          status: 'error',
        });
        console.error(error);
      }
    }, 100);
  } catch (error) {
    downloadButton.dataset.sorting = 'false';
    setCheckboxesDisabled(false);
    updateSelection();
    setSortProgress({
      percent: 0,
      message: error.message || 'Failed to start sort.',
      status: 'error',
    });
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
  const progressContainer = document.getElementById('sort-progress');
  progressContainer.hidden = true;
  setSortProgress({
    percent: 0,
    message: '',
    status: 'idle',
  });
}

function setSortProgress(progress) {
  const percent = Math.max(0, Math.min(progress.percent ?? 0, 100));
  const progressContainer = document.getElementById('sort-progress');
  const progressFill = document.getElementById('sort-progress-fill');
  const progressPercent = document.getElementById('sort-progress-percent');
  const progressLabel = document.getElementById('sort-progress-label');
  const progressMessage = document.getElementById('sort-progress-message');

  progressContainer.hidden = progress.status === 'idle';
  progressFill.style.width = `${percent}%`;
  progressPercent.innerText = `${percent}%`;
  if (progress.status === 'complete') {
    progressLabel.innerText = 'Sorting finished';
  } else if (progress.status === 'error') {
    progressLabel.innerText = 'Sorting failed';
  } else {
    progressLabel.innerText = 'Sorting photos...';
  }
  progressMessage.innerText = progress.message || '';
}
