export function initLoginForm({
  doc = globalThis.document,
  api = globalThis.pywebview?.api,
} = {}) {
  const loginBtn = doc.getElementById("loginBtn");
  const verifyBtn = doc.getElementById("verifyBtn");
  const status = doc.getElementById("status");
  const loginForm = doc.getElementById("login-form");
  const twoFactorForm = doc.getElementById("2fa-form");

  if (!loginBtn || !verifyBtn || !status || !loginForm || !twoFactorForm) {
    return;
  }

  const setStatus = (message) => {
    status.textContent = message ?? "";
  };

  loginBtn.addEventListener("click", async () => {
    if (!api?.login) return;

    const appleId = doc.getElementById("appleId")?.value ?? "";
    const password = doc.getElementById("password")?.value ?? "";

    const result = await api.login(appleId, password);
    console.log(result);

    if (result.success) {
      setStatus("Logged in!");
      loginForm.style.display = "none";
    } else if (result["2fa_required"]) {
      loginForm.style.display = "none";
      twoFactorForm.style.display = "block";
      setStatus(result.message);
    } else {
      setStatus(result.message);
    }
  });

  verifyBtn.addEventListener("click", async () => {
    if (!api?.verify_2fa) return;

    const code = doc.getElementById("2faCode")?.value ?? "";
    const result = await api.verify_2fa(code);
    console.log(result);

    if (result.success) {
      setStatus(result.message || "Logged in!");
      twoFactorForm.style.display = "none";
    } else {
      setStatus(result.message);
    }
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    initLoginForm();
  });
}
