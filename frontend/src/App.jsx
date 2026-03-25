import { useEffect, useState } from "react";

function getDesktopApi() {
  return globalThis.window?.pywebview?.api ?? null;
}

function getErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Unexpected error. Check the Python process output for details.";
}

function StatusBanner({ tone, children }) {
  if (!children) {
    return null;
  }

  return <div className={`status-banner ${tone}`}>{children}</div>;
}

export default function App() {
  const [desktopApi, setDesktopApi] = useState(() => getDesktopApi());
  const [appleId, setAppleId] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [statusTone, setStatusTone] = useState("info");

  useEffect(() => {
    if (getDesktopApi()) {
      setDesktopApi(getDesktopApi());
      return undefined;
    }

    function handleReady() {
      setDesktopApi(getDesktopApi());
    }

    window.addEventListener("pywebviewready", handleReady);

    return () => {
      window.removeEventListener("pywebviewready", handleReady);
    };
  }, []);

  async function handleCredentialsSubmit(event) {
    event.preventDefault();

    if (!desktopApi) {
      setStatusTone("warning");
      setStatusMessage("Desktop bridge unavailable. Open this screen via `python3 -m app.main`.");
      return;
    }

    setIsSubmitting(true);
    setStatusMessage("");

    try {
      const result = await desktopApi.login(appleId.trim(), password);

      setRequiresTwoFactor(Boolean(result.requires_2fa));
      setIsLoggedIn(Boolean(result.ok));
      setStatusTone(result.ok ? "success" : result.requires_2fa ? "info" : "danger");
      setStatusMessage(result.message);

      if (result.ok) {
        setPassword("");
      }
    } catch (error) {
      setStatusTone("danger");
      setStatusMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleTwoFactorSubmit(event) {
    event.preventDefault();

    if (!desktopApi) {
      setStatusTone("warning");
      setStatusMessage("Desktop bridge unavailable. Open this screen via `python3 -m app.main`.");
      return;
    }

    setIsSubmitting(true);
    setStatusMessage("");

    try {
      const result = await desktopApi.submit_2fa_code(code.trim());

      setRequiresTwoFactor(Boolean(result.requires_2fa));
      setIsLoggedIn(Boolean(result.ok));
      setStatusTone(result.ok ? "success" : result.requires_2fa ? "info" : "danger");
      setStatusMessage(result.message);

      if (result.ok) {
        setCode("");
      }
    } catch (error) {
      setStatusTone("danger");
      setStatusMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">iCloud Sorter</p>
        <h1>Sign in to iCloud from the desktop app.</h1>
        <p className="lede">
          The Python process handles authentication. This React screen runs inside
          the native <code>pywebview</code> window and talks to Python through the
          desktop bridge.
        </p>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="section-label">Desktop bridge</p>
            <h2>{desktopApi ? "Connected" : "Browser preview mode"}</h2>
          </div>
          <span className={`pill ${desktopApi ? "live" : "offline"}`}>
            {desktopApi ? "pywebview" : "browser only"}
          </span>
        </div>

        <StatusBanner tone={desktopApi ? "info" : "warning"}>
          {desktopApi
            ? "Python API available. You can sign in from this window."
            : "Open this UI through `python3 -m app.main` to use the native auth bridge."}
        </StatusBanner>

        <StatusBanner tone={statusTone}>{statusMessage}</StatusBanner>

        {isLoggedIn ? (
          <div className="success-state">
            <p className="section-label">Session</p>
            <h3>Authentication complete</h3>
            <p>
              The iCloud session is active in the Python process. The next step is
              to replace this placeholder with the actual sorting workflow.
            </p>
          </div>
        ) : (
          <>
            <form className="form-grid" onSubmit={handleCredentialsSubmit}>
              <div className="field">
                <label htmlFor="apple-id">Apple ID</label>
                <input
                  id="apple-id"
                  type="email"
                  autoComplete="username"
                  placeholder="name@example.com"
                  value={appleId}
                  onChange={(event) => setAppleId(event.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="Apple ID password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              <button
                className="primary-button"
                type="submit"
                disabled={!appleId || !password || isSubmitting}
              >
                {isSubmitting ? "Signing in..." : "Sign in"}
              </button>
            </form>

            {requiresTwoFactor ? (
              <form className="two-factor-card" onSubmit={handleTwoFactorSubmit}>
                <div>
                  <p className="section-label">Two-factor authentication</p>
                  <h3>Enter the verification code</h3>
                  <p>
                    Apple requested a 2FA code for this session. Enter the latest
                    verification code from your trusted device.
                  </p>
                </div>

                <div className="field">
                  <label htmlFor="two-factor-code">Verification code</label>
                  <input
                    id="two-factor-code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="123456"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                  />
                </div>

                <button
                  className="secondary-button"
                  type="submit"
                  disabled={!code || isSubmitting}
                >
                  {isSubmitting ? "Verifying..." : "Verify code"}
                </button>
              </form>
            ) : null}
          </>
        )}
      </section>
    </main>
  );
}
