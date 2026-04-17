import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const loadAlbums = vi.fn();
let pywebviewReadyHandler;

vi.mock("../../app/ui/js/login.js", () => ({
  login: vi.fn(),
  submit2FA: vi.fn(),
  restartLogin: vi.fn(),
}));

vi.mock("../../app/ui/js/albums.js", () => ({
  loadAlbums,
}));

const renderMainDom = () => {
  document.body.innerHTML = `
    <button id="loginBtn">Sign In</button>
    <button id="verifyBtn">Verify</button>
    <button id="restartBtn">Try Again</button>
  `;
};

describe("main.js", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    renderMainDom();
    pywebviewReadyHandler = undefined;

    vi.spyOn(window, "addEventListener").mockImplementation((type, listener, options) => {
      if (type === "pywebviewready") {
        pywebviewReadyHandler = listener;
        return;
      }

      return EventTarget.prototype.addEventListener.call(window, type, listener, options);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads albums automatically when dev bypass is enabled", async () => {
    globalThis.pywebview = {
      api: {
        is_dev_bypass_enabled: vi.fn().mockResolvedValue(true),
      },
    };

    await import("../../app/ui/js/main.js");

    await pywebviewReadyHandler(new Event("pywebviewready"));

    await vi.waitFor(() => expect(loadAlbums).toHaveBeenCalledTimes(1));
  });

  it("keeps the login flow when dev bypass is disabled", async () => {
    globalThis.pywebview = {
      api: {
        is_dev_bypass_enabled: vi.fn().mockResolvedValue(false),
      },
    };

    await import("../../app/ui/js/main.js");

    await pywebviewReadyHandler(new Event("pywebviewready"));

    await vi.waitFor(() => {
      expect(globalThis.pywebview.api.is_dev_bypass_enabled).toHaveBeenCalledTimes(1);
    });
    expect(loadAlbums).not.toHaveBeenCalled();
  });
});
