import { beforeEach, describe, expect, it, vi } from "vitest";

const renderLoginDom = () => {
  document.body.innerHTML = `
    <div class="login-card" style="display: block;"></div>
    <div id="login-form" style="display: block;">
      <input id="appleId" type="text" />
      <input id="password" type="password" />
      <button id="loginBtn">Sign In</button>
    </div>
    <div id="2fa-form" style="display: none;">
      <input id="2faCode" type="text" />
      <button id="verifyBtn">Verify</button>
    </div>
    <p id="status"></p>
    <div id="albums-view" style="display: none;">
      <p id="albums-status" hidden></p>
      <ul id="albums-list"></ul>
      <button id="download-btn" data-sorting="false"></button>
      <button id="cancel-btn" hidden></button>
      <div id="sort-selection">No albums selected</div>
      <div id="sort-progress-content" hidden></div>
      <div id="sort-progress-fill"></div>
      <div id="sort-progress-percent"></div>
      <div id="sort-progress-message"></div>
    </div>
  `;
};

describe("login.js", () => {
  beforeEach(() => {
    vi.resetModules();
    renderLoginDom();
  });

  it("loads albums after a successful login", async () => {
    const login = vi.fn().mockResolvedValue({ success: true });
    const getAlbums = vi.fn().mockResolvedValue({
      success: true,
      albums: [{ id: "album-1", name: "Trips", item_count: 3, is_system_album: false }],
      error: null,
    });

    globalThis.pywebview = {
      api: {
        login,
        get_albums: getAlbums,
        verify_2fa: vi.fn(),
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.login();

    expect(login).toHaveBeenCalledWith("user@example.com", "super-secret");
    expect(getAlbums).toHaveBeenCalledTimes(1);
    expect(document.getElementById("albums-view").style.display).toBe("block");
    expect(document.querySelectorAll("#albums-list li")).toHaveLength(1);
  });

  it("shows invalid credentials message after entering incorrect credentials", async () => {
    const login = vi.fn().mockResolvedValue({
      success: false,
      message: "Invalid credentials",
    });

    globalThis.pywebview = {
      api: {
        login,
        get_albums: vi.fn(),
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.login();

    expect(login).toHaveBeenCalledWith("user@example.com", "super-secret");
    expect(document.getElementById("status").innerText).toBe("Invalid credentials");
    expect(document.getElementById("login-form").style.display).toBe("block");
  });

  it("loads albums after successful 2FA verification", async () => {
    const verify2fa = vi.fn().mockResolvedValue({ success: true });
    const getAlbums = vi.fn().mockResolvedValue({
      success: true,
      albums: [{ id: "album-1", name: "Trips", item_count: 3, is_system_album: false }],
      error: null,
    });

    globalThis.pywebview = {
      api: {
        verify_2fa: verify2fa,
        get_albums: getAlbums,
      },
    };

    document.getElementById("2faCode").value = "123456";

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.submit2FA();

    expect(verify2fa).toHaveBeenCalledWith("123456");
    expect(getAlbums).toHaveBeenCalledTimes(1);
    expect(document.querySelectorAll("#albums-list li")).toHaveLength(1);
  });
});
