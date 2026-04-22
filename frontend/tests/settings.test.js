import { beforeEach, describe, expect, it, vi } from "vitest";

const renderSettingsDom = () => {
  document.body.innerHTML = `
    <input id="source-folder-input" type="text" placeholder="Auto-detecting..." />
    <select id="sorting-approach">
      <option value="first">Move to first matching album</option>
      <option value="copy">Copy to all matching albums</option>
    </select>
    <div id="copy-warning" style="display: none"></div>
  `;
};

describe("settings.js", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    renderSettingsDom();
  });

  it("populates the source folder when pywebview becomes ready after load starts", async () => {
    vi.useFakeTimers();

    const settings = await import("../../app/ui/js/settings.js");
    const loadPromise = settings.loadSettings();

    await vi.advanceTimersByTimeAsync(100);

    globalThis.pywebview = {
      api: {
        get_settings: vi.fn().mockResolvedValue({
          success: true,
          settings: {
            source_folder: "C:/Users/mac/Pictures/iCloud Photos",
            sorting_approach: "first",
          },
          source_folder: "C:/Users/mac/Pictures/iCloud Photos",
          sorting_approach: "first",
        }),
      },
    };

    await vi.advanceTimersByTimeAsync(100);
    await loadPromise;

    expect(document.getElementById("source-folder-input").value).toBe(
      "C:/Users/mac/Pictures/iCloud Photos",
    );
    expect(document.getElementById("sorting-approach").value).toBe("first");
  });
});
