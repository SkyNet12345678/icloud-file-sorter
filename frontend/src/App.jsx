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

function formatBytes(bytes) {
  if (typeof bytes !== "number") {
    return "Unavailable";
  }

  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
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
  const [sessionSummary, setSessionSummary] = useState(null);

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
      setSessionSummary(result.session_summary ?? null);
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
      setSessionSummary(result.session_summary ?? null);
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
            <h3>{sessionSummary?.display_name ?? "Authentication complete"}</h3>
            <p>The iCloud session is active in the Python process.</p>

            <div className="summary-grid">
              <article className="summary-card">
                <p className="section-label">Apple ID</p>
                <strong>{sessionSummary?.account_name ?? "Unavailable"}</strong>
              </article>

              <article className="summary-card">
                <p className="section-label">Trusted session</p>
                <strong>{sessionSummary?.trusted_session ? "Yes" : "No"}</strong>
              </article>

              <article className="summary-card">
                <p className="section-label">Storage used</p>
                <strong>
                  {sessionSummary?.storage
                    ? `${formatBytes(sessionSummary.storage.used_bytes)} / ${formatBytes(sessionSummary.storage.total_bytes)}`
                    : "Unavailable"}
                </strong>
                <span>
                  {sessionSummary?.storage
                    ? `${sessionSummary.storage.used_percent}% used`
                    : "Storage information not available"}
                </span>
              </article>

              <article className="summary-card">
                <p className="section-label">Storage free</p>
                <strong>
                  {sessionSummary?.storage
                    ? formatBytes(sessionSummary.storage.available_bytes)
                    : "Unavailable"}
                </strong>
              </article>

              <article className="summary-card">
                <p className="section-label">Paired devices</p>
                <strong>
                  {sessionSummary?.paired_device_count ?? "Unavailable"}
                </strong>
              </article>

              <article className="summary-card">
                <p className="section-label">Family members</p>
                <strong>
                  {sessionSummary?.family_member_count ?? "Unavailable"}
                </strong>
              </article>
            </div>

            <div className="service-list">
              <p className="section-label">Available services</p>
              <div className="service-pills">
                {(sessionSummary?.available_services ?? []).map((service) => (
                  <span key={service} className="service-pill">
                    {service}
                  </span>
                ))}
              </div>
            </div>
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
