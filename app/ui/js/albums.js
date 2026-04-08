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
  updateSelection();
}

function updateSelection() {
  const checkboxes = document.querySelectorAll('#albums-list input[type="checkbox"]');
  const selected = Array.from(checkboxes).filter((cb) => cb.checked).length;
  document.getElementById('download-btn').disabled = selected === 0;
}

export async function startSort() {
  if (!globalThis.pywebview?.api) {
    console.log('pywebview API not ready')
    return;
  }

  const indexes = Array.from(
    document.querySelectorAll('#albums-list input[type="checkbox"]:checked')
  ).map((checkbox) => Number(checkbox.dataset.index));

  const { job_id } = await globalThis.pywebview.api.start_sort(indexes);

  const timer = setInterval(async () => {
  const progress = await globalThis.pywebview.api.get_sort_progress(job_id);
  console.log(progress);

  if (progress.status === 'complete' || progress.status === 'error') {
    clearInterval(timer);
  }
}, 500);
}
