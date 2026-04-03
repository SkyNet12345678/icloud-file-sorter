import { beforeEach, describe, expect, it, vi } from "vitest";

import { initLoginForm } from "../../app/ui/js/login.js";

function renderLoginForm() {
  document.body.innerHTML = `
    <div id="login-form">
      <input id="appleId" type="text" />
      <input id="password" type="password" />
      <button id="loginBtn">Sign In</button>
    </div>
    <div id="2fa-form" style="display: none;">
      <input id="2faCode" type="text" />
      <button id="verifyBtn">Verify 2FA</button>
    </div>
    <p id="status"></p>
  `;
}

async function flushPromises() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("initLoginForm", () => {
  beforeEach(() => {
    renderLoginForm();
  });

  it("submits credentials and hides the login form after a successful login", async () => {
    const api = {
      login: vi.fn().mockResolvedValue({ success: true }),
      verify_2fa: vi.fn(),
    };

    initLoginForm({ doc: document, api });

    document.getElementById("appleId").value = "person@example.com";
    document.getElementById("password").value = "topsecret";
    document.getElementById("loginBtn").click();
    await flushPromises();

    expect(api.login).toHaveBeenCalledWith("person@example.com", "topsecret");
    expect(document.getElementById("status").textContent).toBe("Logged in!");
    expect(document.getElementById("login-form").style.display).toBe("none");
  });

  it("shows the 2FA form when the backend requests verification", async () => {
    const api = {
      login: vi.fn().mockResolvedValue({
        success: false,
        "2fa_required": true,
        message: "Enter the six-digit code.",
      }),
      verify_2fa: vi.fn(),
    };

    initLoginForm({ doc: document, api });

    document.getElementById("loginBtn").click();
    await flushPromises();

    expect(document.getElementById("login-form").style.display).toBe("none");
    expect(document.getElementById("2fa-form").style.display).toBe("block");
    expect(document.getElementById("status").textContent).toBe(
      "Enter the six-digit code.",
    );
  });
});
