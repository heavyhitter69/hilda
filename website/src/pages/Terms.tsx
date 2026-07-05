import { Link } from 'react-router-dom';

export default function Terms() {
  return (
    <main style={{ paddingBottom: '0' }}>
      <div className="ambient-orb dark"></div>

      <header className="manifesto-header animate-fade-in delay-1" style={{ padding: '8rem 1.5rem 4rem', maxWidth: '900px' }}>
        <p className="eyebrow" style={{ color: '#a1a1aa', letterSpacing: '0.25em', marginBottom: '1.5rem', fontWeight: 500 }}>
          LEGAL
        </p>
        <h1 className="font-serif">
          <span className="text-gradient">Terms of Use</span>
        </h1>
        <p className="lede" style={{ fontSize: '1.1rem', color: '#71717a', marginTop: '1rem' }}>Last updated: May 7, 2026</p>
      </header>

      <section className="story-section animate-fade-in delay-2" style={{ paddingTop: '0', maxWidth: '800px' }}>
        <div className="glass-panel" style={{ padding: '3rem 4rem', borderRadius: '24px' }}>
          
          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Agreement</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              By downloading, installing, or using Hilda (the “Software”), you agree to these terms. If you do not agree, do not use the Software.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>License</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              Use of the Software is governed by the license file shipped with your copy or repository (for example an MIT or other open-source license). If no license is specified in your distribution, contact the distributor for terms.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Acceptable Use</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              You are responsible for complying with applicable laws and for how you use speech input, automation, and optional cloud APIs. Do not use the Software to harm systems you do not own or lack permission to operate, or to violate others’ privacy.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Interpretation & Automation</h2>
            <p style={{ color: '#a1a1aa', lineHeight: 1.8, fontSize: '1.05rem' }}>
              Speech and automation can misinterpret intent. Review sensitive actions before relying on them. API keys, models, and permissions are your responsibility.
            </p>
          </div>

          <div style={{ marginBottom: '3rem' }}>
            <h2 className="font-serif" style={{ fontSize: '1.5rem', fontWeight: 400, color: 'var(--text)', marginBottom: '1rem' }}>Disclaimer</h2>
            <p style={{ color: '#71717a', lineHeight: 1.8, fontSize: '0.95rem', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
              The software is provided “as is”, without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability arising from the use of the software.
            </p>
          </div>

          <div style={{ marginTop: '4rem', paddingTop: '2rem', borderTop: '1px solid var(--line-strong)', display: 'flex', gap: '1rem' }}>
            <Link className="btn secondary" to="/" style={{ padding: '0.8rem 1.5rem', fontSize: '0.9rem', borderRadius: '999px', border: '1px solid var(--line)', color: '#a1a1aa', textDecoration: 'none' }}>← Return Home</Link>
            <Link className="btn secondary" to="/privacy" style={{ padding: '0.8rem 1.5rem', fontSize: '0.9rem', borderRadius: '999px', border: '1px solid var(--line)', color: '#a1a1aa', textDecoration: 'none' }}>View Privacy Policy</Link>
          </div>
          
        </div>
      </section>
    </main>
  );
}
