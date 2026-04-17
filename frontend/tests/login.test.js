import { beforeEach, describe, expect, it, vi } from "vitest";

const loadAlbums = vi.fn();

vi.mock("../../app/ui/js/albums.js", () => ({
  loadAlbums,
}));

const renderLoginDom = () => {
  document.body.innerHTML = `
    <div id="login-form" style="display: block;">
      <input id="appleId" type="text" />
      <input id="password" type="password" />
      <button id="loginBtn">Sign In</button>
    </div>
    <div id="2fa-form" style="display: none;">
      <input id="2faCode" type="text" />
      <button id="verifyBtn">Verify</button>
      <button id="restartBtn">Try Again</button>
    </div>
    <p id="status"></p>
  `;
};

describe("login.js", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    renderLoginDom();
  });

  it("calls the backend login API and loads albums after a successful login", async () => {
    const backendLogin = vi.fn().mockResolvedValue({ success: true });

    globalThis.pywebview = {
      api: {
        login: backendLogin,
        verify_2fa: vi.fn(),
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    const { login } = await import("../../app/ui/js/login.js");

    await login();

    expect(backendLogin).toHaveBeenCalledWith("user@example.com", "super-secret");
    expect(loadAlbums).toHaveBeenCalledTimes(1);
    expect(document.getElementById("password").value).toBe("");
    expect(document.getElementById("loginBtn").disabled).toBe(false);
  });

  it("shows invalid credentials message after entering incorrect credentials", async () => {
    const backendLogin = vi.fn().mockResolvedValue({
      success: false,
      message: "Invalid credentials",
    });

    globalThis.pywebview = {
      api: {
        login: backendLogin,
        verify_2fa: vi.fn(),
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    const { login } = await import("../../app/ui/js/login.js");

    await login();

    expect(backendLogin).toHaveBeenCalledWith("user@example.com", "super-secret");
    expect(loadAlbums).not.toHaveBeenCalled();
    expect(document.getElementById("login-form").style.display).toBe("block");
    expect(document.getElementById("status").innerText).toBe("Invalid credentials");
  });
});
