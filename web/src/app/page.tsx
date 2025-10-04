import Link from 'next/link';

export default function Home() {
  return (
    <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>GIF Distributor</h1>
      <p>Upload once, distribute everywhere.</p>

      <Link
        href="/publish"
        style={{
          display: 'inline-block',
          marginTop: '1.5rem',
          padding: '0.75rem 2rem',
          backgroundColor: '#0070f3',
          color: 'white',
          textDecoration: 'none',
          borderRadius: '6px',
          fontWeight: '500',
        }}
      >
        Start Publishing →
      </Link>

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
