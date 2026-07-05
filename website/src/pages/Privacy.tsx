import { Link } from 'react-router-dom';

export default function Privacy() {
  return (
    <main style={{ paddingBottom: '0' }}>
      <div className="ambient-orb dark"></div>

      <header className="manifesto-header animate-fade-in delay-1" style={{ padding: '8rem 1.5rem 4rem', maxWidth: '900px' }}>
        <p className="eyebrow" style={{ color: '#a1a1aa', letterSpacing: '0.25em', marginBottom: '1.5rem', fontWeight: 500 }}>
          LEGAL
        </p>
        <h1 className="font-serif">
          <span className="text-gradient">Privacy Policy</span>
        </h1>
        <p className="lede" style={{ fontSize: '1.1rem', color: '#71717a', marginTop: '1rem' }}>Last updated: May 7, 2026</p>
      </header>

      <section className="story-section animate-fade-in delay-2" style={{ paddingTop: '0', maxWidth: '800px' }}>
        <div className="glass-panel" style={{ padding: '3rem 4rem', borderRadius: '24px' }}>
          
          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Overview</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem', marginBottom: '1rem' }}>
              Hilda (“the Software”) runs primarily on your computer. This policy describes what typically stays on your device, what may be sent to third-party services when you enable optional features, and how you can control that behavior.
            </p>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              If you distribute your own build or fork of Hilda, you are responsible for updating this policy to match your product and jurisdiction.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Information Processed Locally</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              Microphone input, wake detection, and speech recognition can stay on your device depending on settings. Actions you ask for—opening files, running allowed commands—are handled locally within the Software’s safeguards.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Optional Cloud Integrations</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              If you add API keys or turn on integrations, data those services need may be sent per their terms—only for features you enable. Check each provider’s policy before connecting.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Logs and Diagnostics</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              The Software may write logs on disk for troubleshooting. Those logs are under your control. Unless you separately configure telemetry, we do not operate a central service that collects those logs automatically.
            </p>
          </div>

          <div style={{ marginTop: '4rem', paddingTop: '2rem', borderTop: '1px solid var(--line-strong)', display: 'flex', gap: '1rem' }}>
            <Link className="btn secondary" to="/" style={{ padding: '0.8rem 1.5rem', fontSize: '0.9rem', borderRadius: '999px', border: '1px solid var(--line)', color: '#a1a1aa', textDecoration: 'none' }}>← Return Home</Link>
            <Link className="btn secondary" to="/terms" style={{ padding: '0.8rem 1.5rem', fontSize: '0.9rem', borderRadius: '999px', border: '1px solid var(--line)', color: '#a1a1aa', textDecoration: 'none' }}>View Terms of Use</Link>
          </div>
          
        </div>
      </section>
    </main>
  );
}
