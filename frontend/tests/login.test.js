import { beforeEach, describe, expect, it, vi } from "vitest";

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
    </div>
    <p id="status"></p>
  `;
};

describe("login.js", () => {
  beforeEach(() => {
    vi.resetModules();
    renderLoginDom();
  });

  it("shows a success message and hides the login form after a successful login", async () => {
    const login = vi.fn().mockResolvedValue({ success: true });

    globalThis.pywebview = {
      api: {
        login,
        verify_2fa: vi.fn(),
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    await import("../../app/ui/js/login.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    document.getElementById("loginBtn").click();
    await vi.waitFor(() => expect(login).toHaveBeenCalledWith("user@example.com", "super-secret"));

    expect(document.getElementById("status").innerText).toBe("Logged in!");
    expect(document.getElementById("login-form").style.display).toBe("none");
  });
  it("shows invalid credentials message after entering incorrect credentials", async () => {
    const login = vi.fn().mockResolvedValue({ 
      success: false,
      message: "Invalid credentials",
     });

    globalThis.pywebview = {
      api: {
        login,
      },
    };

    document.getElementById("appleId").value = "user@example.com";
    document.getElementById("password").value = "super-secret";

    await import("../../app/ui/js/login.js");
    document.dispatchEvent(new Event("DOMContentLoaded"));

    document.getElementById("loginBtn").click();
    await vi.waitFor(() => expect(login).toHaveBeenCalledWith("user@example.com", "super-secret"));

    expect(document.getElementById("login-form").style.display).toBe("block");
  });
});
