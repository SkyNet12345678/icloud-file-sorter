import { beforeEach, describe, expect, it, vi } from "vitest";

const renderLoginDom = () => {
  document.body.innerHTML = `
    <div class="login-card" style="display: block;"></div>
    <div id="returning-user" style="display: none;">
      <strong id="rememberedAppleId"></strong>
      <button id="continueBtn">Continue</button>
      <button id="notYouBtn">Not you?</button>
    </div>
    <div id="login-form" style="display: none;">
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
    delete globalThis.pywebview;
    renderLoginDom();
  });

  it("shows the returning-user view when an Apple ID is remembered", async () => {
    globalThis.pywebview = {
      api: {
        get_auth_state: vi.fn().mockResolvedValue({
          success: true,
          has_remembered_apple_id: true,
          remembered_apple_id: "user@icloud.com",
        }),
      },
    };

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.initializeLogin();

    expect(document.getElementById("returning-user").style.display).toBe("block");
    expect(document.getElementById("rememberedAppleId").innerText).toBe("user@icloud.com");
    expect(document.getElementById("login-form").style.display).toBe("none");
  });

  it("shows the first-login form when no Apple ID is remembered", async () => {
    globalThis.pywebview = {
      api: {
        get_auth_state: vi.fn().mockResolvedValue({
          success: true,
          has_remembered_apple_id: false,
          remembered_apple_id: null,
        }),
      },
    };

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.initializeLogin();

    expect(document.getElementById("returning-user").style.display).toBe("none");
    expect(document.getElementById("login-form").style.display).toBe("block");
  });

  it("keeps the first-login form hidden while auth state is loading", async () => {
    let resolveAuthState;
    const authStatePromise = new Promise((resolve) => {
      resolveAuthState = resolve;
    });
    globalThis.pywebview = {
      api: {
        get_auth_state: vi.fn().mockReturnValue(authStatePromise),
      },
    };

    const loginModule = await import("../../app/ui/js/login.js");
    const initializePromise = loginModule.initializeLogin();

    expect(document.getElementById("login-form").style.display).toBe("none");

    resolveAuthState({
      success: true,
      has_remembered_apple_id: false,
      remembered_apple_id: null,
    });
    await initializePromise;

    expect(document.getElementById("login-form").style.display).toBe("block");
  });

  it("waits for pywebview readiness before checking auth state", async () => {
    const getAuthState = vi.fn().mockResolvedValue({
      success: true,
      has_remembered_apple_id: true,
      remembered_apple_id: "user@icloud.com",
    });

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.initializeLogin();

    expect(getAuthState).not.toHaveBeenCalled();

    globalThis.pywebview = {
      api: { get_auth_state: getAuthState },
    };
    document.dispatchEvent(new Event("pywebviewready"));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(getAuthState).toHaveBeenCalledTimes(1);
    expect(document.getElementById("returning-user").style.display).toBe("block");
    expect(document.getElementById("rememberedAppleId").innerText).toBe("user@icloud.com");
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
    document.getElementById("login-form").style.display = "block";

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
    document.getElementById("login-form").style.display = "block";

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

  it("loads albums after continuing a valid remembered session", async () => {
    const continueSession = vi.fn().mockResolvedValue({ success: true });
    const getAlbums = vi.fn().mockResolvedValue({
      success: true,
      albums: [{ id: "album-1", name: "Trips", item_count: 3, is_system_album: false }],
      error: null,
    });
    globalThis.pywebview = {
      api: {
        continue_session: continueSession,
        get_albums: getAlbums,
      },
    };

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.continueSession();

    expect(continueSession).toHaveBeenCalledTimes(1);
    expect(getAlbums).toHaveBeenCalledTimes(1);
    expect(document.getElementById("albums-view").style.display).toBe("block");
  });

  it("clears the saved session and shows first login when Not you is selected", async () => {
    const logout = vi.fn().mockResolvedValue({ success: true });
    globalThis.pywebview = {
      api: { logout },
    };
    document.getElementById("returning-user").style.display = "block";
    document.getElementById("login-form").style.display = "none";

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.notYou();

    expect(logout).toHaveBeenCalledTimes(1);
    expect(document.getElementById("returning-user").style.display).toBe("none");
    expect(document.getElementById("login-form").style.display).toBe("block");
    expect(document.getElementById("status").innerText).toBe("Please sign in with your Apple ID.");
  });

  it("shows sign-in-required copy when remembered session resume fails", async () => {
    globalThis.pywebview = {
      api: {
        continue_session: vi.fn().mockResolvedValue({
          success: false,
          requires_login: true,
          message: "Session expired. Please sign in again.",
        }),
      },
    };
    document.getElementById("returning-user").style.display = "block";
    document.getElementById("login-form").style.display = "none";

    const loginModule = await import("../../app/ui/js/login.js");
    await loginModule.continueSession();

    expect(document.getElementById("returning-user").style.display).toBe("none");
    expect(document.getElementById("login-form").style.display).toBe("block");
    expect(document.getElementById("status").innerText).toBe("Session expired. Please sign in again.");
  });
});
