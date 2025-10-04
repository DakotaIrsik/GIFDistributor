export default function Home() {
  return (
    <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>GIF Distributor</h1>
      <p>Upload once, distribute everywhere.</p>
      <div style={{ marginTop: '2rem' }}>
        <h2>Features</h2>
        <ul>
          <li>Upload GIFs and videos</li>
          <li>Distribute to GIPHY, Tenor, Slack, Discord, Teams</li>
          <li>Platform-specific optimizations</li>
          <li>Content moderation</li>
        </ul>
      </div>
    </main>
  );
}
