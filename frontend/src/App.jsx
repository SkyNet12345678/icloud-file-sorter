export default function App() {
  return (
    <main
      style={{
        fontFamily: "system-ui, sans-serif",
        margin: "0 auto",
        maxWidth: "720px",
        padding: "48px 24px",
      }}
    >
      <p style={{ fontSize: "12px", letterSpacing: "0.12em", textTransform: "uppercase" }}>
        iCloud Sorter
      </p>
      <h1 style={{ fontSize: "40px", marginBottom: "12px" }}>
        React UI running in Docker, native shell running on the host.
      </h1>
      <p style={{ fontSize: "18px", lineHeight: 1.5 }}>
        This is the recommended development split for a pywebview desktop app.
        Run the Vite server in Docker, then point the local Python shell at
        http://localhost:5173 during development.
      </p>
    </main>
  );
}
