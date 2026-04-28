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

  it("shows a visible error when sort start validation fails", async () => {
    const startSort = vi.fn().mockResolvedValue({
      error: "Source folder is not configured. Choose your iCloud Photos folder in Settings before starting a sort.",
    });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: vi.fn(),
      },
    };

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();

    expect(startSort).toHaveBeenCalledWith(["album-1"]);
    expect(document.getElementById("albums-status").textContent).toBe(
      "Source folder is not configured. Choose your iCloud Photos folder in Settings before starting a sort.",
    );
    expect(document.getElementById("albums-status").hidden).toBe(false);
    expect(document.getElementById("sort-progress-content").hidden).toBe(false);
    expect(document.getElementById("sort-progress-message").textContent).toBe(
      "Source folder is not configured. Choose your iCloud Photos folder in Settings before starting a sort.",
    );
    expect(document.getElementById("download-btn").hidden).toBe(false);
    expect(document.getElementById("cancel-btn").hidden).toBe(true);
  });

  it("renders matching-stage progress from lightweight polling payloads", async () => {
    const startSort = vi.fn().mockResolvedValue({ job_id: "job-1" });
    const getSortProgress = vi.fn().mockResolvedValue({
      job_id: "job-1",
      status: "matching",
      processed: 0,
      total: 0,
      percent: 0,
      message: "Preparing matching job...",
    });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: getSortProgress,
      },
    };

    let pollSortProgress;
    const setIntervalMock = vi.fn((callback) => {
      pollSortProgress = callback;
      return 1;
    });
    const clearIntervalMock = vi.fn();
    vi.stubGlobal("setInterval", setIntervalMock);
    vi.stubGlobal("clearInterval", clearIntervalMock);

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();
    await pollSortProgress();

    expect(getSortProgress).toHaveBeenCalledWith("job-1");
    expect(document.getElementById("sort-progress-message").textContent).toBe(
      "Preparing matching job...",
    );
    expect(document.getElementById("sort-progress-percent").textContent).toBe("0%");
    expect(document.getElementById("download-btn").hidden).toBe(true);
    expect(document.getElementById("cancel-btn").hidden).toBe(false);
  });

  it("keeps filename-only match quality visible in the sort status text", async () => {
    const startSort = vi.fn().mockResolvedValue({ job_id: "job-1" });
    const getSortProgress = vi
      .fn()
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "running",
        processed: 0,
        total: 1847,
        percent: 0,
        message:
          "Starting sort for 1 album(s). Filename-only matching: Exact: 1 | Not found: 2 | Ambiguous: 3",
        match_results: {
          matched: 1,
          fallback_matched: 0,
          not_found: 2,
          ambiguous: 3,
        },
      })
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "running",
        processed: 50,
        total: 1847,
        percent: 2,
        message:
          "Processing photo 50 of 1847. Filename-only matching: Exact: 1 | Not found: 2 | Ambiguous: 3",
        match_results: {
          matched: 1,
          fallback_matched: 0,
          not_found: 2,
          ambiguous: 3,
        },
      });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: getSortProgress,
      },
    };

    let pollSortProgress;
    const setIntervalMock = vi.fn((callback) => {
      pollSortProgress = callback;
      return 1;
    });
    vi.stubGlobal("setInterval", setIntervalMock);
    vi.stubGlobal("clearInterval", vi.fn());

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();
    await pollSortProgress();
    expect(document.getElementById("sort-progress-message").textContent).toBe(
      "Starting sort for 1 album(s). Filename-only matching: Exact: 1 | Not found: 2 | Ambiguous: 3",
    );

    await pollSortProgress();
    expect(document.getElementById("sort-progress-message").textContent).toBe(
      "Processing photo 50 of 1847. Filename-only matching: Exact: 1 | Not found: 2 | Ambiguous: 3",
    );
  });

  it("cancels the active sort job through the bridge", async () => {
    const startSort = vi.fn().mockResolvedValue({ job_id: "job-1" });
    const cancelSort = vi.fn().mockResolvedValue({
      job_id: "job-1",
      status: "cancelling",
      processed: 1,
      total: 10,
      percent: 10,
      message: "Cancelling sort after the current file operation...",
    });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: vi.fn(),
        cancel_sort: cancelSort,
      },
    };

    vi.stubGlobal("setInterval", vi.fn(() => 1));
    vi.stubGlobal("clearInterval", vi.fn());

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();
    await albums.cancelSort();

    expect(cancelSort).toHaveBeenCalledWith("job-1");
    expect(document.getElementById("sort-progress-message").textContent).toBe(
      "Cancelling sort after the current file operation...",
    );
    expect(document.getElementById("cancel-btn").disabled).toBe(true);
  });

  it("treats cancelled progress as a terminal sort status", async () => {
    const startSort = vi.fn().mockResolvedValue({ job_id: "job-1" });
    const getSortProgress = vi.fn().mockResolvedValue({
      job_id: "job-1",
      status: "cancelled",
      processed: 2,
      total: 10,
      percent: 20,
      message: "Sort cancelled. Completed operations were not rolled back.",
    });

    globalThis.pywebview = {
      api: {
        start_sort: startSort,
        get_sort_progress: getSortProgress,
      },
    };

    let pollSortProgress;
    vi.stubGlobal("setInterval", vi.fn((callback) => {
      pollSortProgress = callback;
      return 1;
    }));
    const clearIntervalMock = vi.fn();
    vi.stubGlobal("clearInterval", clearIntervalMock);

    const albums = await import("../../app/ui/js/albums.js");
    albums.showAlbums([
      { id: "album-1", name: "Trips", item_count: 12, is_system_album: false },
    ]);

    document.querySelector('#albums-list input[data-album-id="album-1"]').checked = true;

    await albums.startSort();
    await pollSortProgress();

    expect(clearIntervalMock).toHaveBeenCalledWith(1);
    expect(document.getElementById("download-btn").dataset.sorting).toBe("false");
    expect(document.getElementById("download-btn").hidden).toBe(false);
    expect(document.getElementById("cancel-btn").hidden).toBe(true);
  });
});
