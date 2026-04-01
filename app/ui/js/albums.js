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

  albums.forEach((album) => {
    const li = document.createElement('li');
    li.innerText = `${album.name} (${album.count})`;
    list.appendChild(li);
  });

  document.querySelector('.login-card').style.display = 'none';
  document.getElementById('albums-view').style.display = 'block';
}
