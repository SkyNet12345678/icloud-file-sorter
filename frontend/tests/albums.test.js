import { beforeEach, describe, expect, it, vi } from "vitest";

const renderAlbumsDom = () => {
  document.body.innerHTML = `
    <div class="login-card" style="display: block;">
      <p id="status"></p>
    </div>
    <div id="albums-view" style="display: none;">
      <p id="albums-status" hidden></p>
      <ul id="albums-list"></ul>
      <button id="download-btn" data-sorting="false" hidden="false"></button>
      <button id="cancel-btn" hidden></button>
      <div id="sort-selection">No albums selected</div>
      <div id="sort-progress-content" hidden></div>
      <div id="sort-progress-fill"></div>
      <div id="sort-progress-percent"></div>
      <div id="sort-progress-message"></div>
    </div>
  `;
};

describe("albums.js", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    renderAlbumsDom();
  });

  it("renders album summaries from the structured payload", async () => {
    globalThis.pywebview = {
      api: {
        get_albums: vi.fn().mockResolvedValue({
          success: true,
          albums: [
            { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
            { id: "album-2", name: "Family", item_count: 1, is_system_album: false },
          ],
          error: null,
        }),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    await albums.loadAlbums();

    const checkboxes = Array.from(document.querySelectorAll("#albums-list input"));
    expect(checkboxes).toHaveLength(2);
    expect(checkboxes[0].dataset.albumId).toBe("album-1");
    expect(document.getElementById("albums-list").textContent).toContain("Trips");
    expect(document.getElementById("albums-list").textContent).toContain("12 items");
    expect(document.getElementById("albums-view").style.display).toBe("block");
    expect(document.getElementById("albums-status").hidden).toBe(true);
  });

  it("shows an empty state when the album payload succeeds with no albums", async () => {
    globalThis.pywebview = {
      api: {
        get_albums: vi.fn().mockResolvedValue({
          success: true,
          albums: [],
          error: null,
        }),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    await albums.loadAlbums();

    expect(document.getElementById("albums-status").textContent).toBe(
      "No albums found in iCloud Photos.",
    );
    expect(document.getElementById("albums-status").hidden).toBe(false);
    expect(document.querySelectorAll("#albums-list li")).toHaveLength(0);
  });

  it("shows a visible failure state when album loading fails", async () => {
    globalThis.pywebview = {
      api: {
        get_albums: vi.fn().mockResolvedValue({
          success: false,
          albums: [],
          error: "Session expired",
        }),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    await albums.loadAlbums();

    expect(document.getElementById("albums-status").textContent).toBe("Session expired");
    expect(document.getElementById("albums-status").hidden).toBe(false);
    expect(document.querySelectorAll("#albums-list li")).toHaveLength(0);
  });

  it("renders a safe default when item_count is missing", async () => {
    const albums = await import("../../app/ui/js/albums.js");

    albums.showAlbums([{ id: "album-1", name: "Trips", is_system_album: false }]);

    expect(document.getElementById("albums-list").textContent).toContain("0 items");
  });

  it("renders a safe default when item_count is null", async () => {
    const albums = await import("../../app/ui/js/albums.js");

    albums.showAlbums([{ id: "album-1", name: "Trips", item_count: null, is_system_album: false }]);

    expect(document.getElementById("albums-list").textContent).toContain("0 items");
  });

  it("shows error state on exception from bridge", async () => {
    globalThis.pywebview = {
      api: {
        get_albums: vi.fn().mockRejectedValue(new Error("Network failure")),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    await albums.loadAlbums();

    expect(document.getElementById("albums-status").textContent).toBe("Failed to load albums.");
    expect(document.getElementById("albums-status").hidden).toBe(false);
    expect(document.querySelectorAll("#albums-list li")).toHaveLength(0);
  });

  it("normalizes a legacy array response", async () => {
    globalThis.pywebview = {
      api: {
        get_albums: vi.fn().mockResolvedValue([
          { id: "a1", name: "Beach", item_count: 5, is_system_album: false },
        ]),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    await albums.loadAlbums();

    const checkboxes = Array.from(document.querySelectorAll("#albums-list input"));
    expect(checkboxes).toHaveLength(1);
    expect(checkboxes[0].dataset.albumId).toBe("a1");
    expect(document.getElementById("albums-list").textContent).toContain("Beach");
  });

  it("submits selected album ids when sorting starts", async () => {
    const startSort = vi.fn().mockResolvedValue({ job_id: "job-1" });
    const getSortProgress = vi.fn().mockResolvedValue({
      job_id: "job-1",
      status: "running",
      processed: 50,
      total: 100,
      percent: 50,
      message: "Processing photo 50 of 100",
    });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: getSortProgress,
      },
    };

    const setIntervalMock = vi.fn(() => 1);
    const clearIntervalMock = vi.fn();
    vi.stubGlobal("setInterval", setIntervalMock);
    vi.stubGlobal("clearInterval", clearIntervalMock);

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
      { id: "album-2", name: "Family", item_count: 4, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();

    expect(startSort).toHaveBeenCalledWith(["album-1"]);
    expect(setIntervalMock).toHaveBeenCalledTimes(1);
  });
});
