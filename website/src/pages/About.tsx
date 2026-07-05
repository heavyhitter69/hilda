import { Link } from 'react-router-dom';

export default function About() {
  return (
    <main style={{ paddingBottom: '0' }}>
      <div className="ambient-orb dark"></div>

      <header className="manifesto-header animate-fade-in delay-1">
        <p className="eyebrow" style={{ color: '#a1a1aa', letterSpacing: '0.25em', marginBottom: '2rem', fontWeight: 500 }}>
          OUR MANIFESTO
        </p>
        <h1 className="font-serif">
          The desktop assistant was fundamentally broken. <br/>
          <span className="text-gradient">So we engineered a better one.</span>
        </h1>
      </header>

      <div className="manifesto-body animate-fade-in delay-2">
        <p>
          For decades, "virtual assistants" have been nothing more than glorified web searchers. They interrupted our workflows with rigid voice commands, misunderstood our context, and sent our most private queries to remote servers to be harvested for data. They were tools, not companions.
        </p>
        <p>
          <strong>We believed true luxury in software means having an intelligence that is both profoundly capable and completely frictionless.</strong>
        </p>
        <p>
          Enter Hilda. Designed from the ground up for Windows, macOS, and Linux, she doesn't just passively wait for commands. She actively monitors your system state, reads your screen when needed, and learns the unique architecture of your digital life—all while remaining sovereign to your local hardware.
        </p>
      </div>

      <div className="luxury-divider animate-fade-in delay-3"></div>

      {/* The Core Pillars */}
      <section className="story-section centered animate-fade-in delay-3" style={{ padding: '4rem 1.5rem' }}>
        <h2 className="font-serif" style={{ color: 'var(--text)' }}>The Architecture of Intelligence</h2>
        <p className="lede">
          Hilda is built upon three distinct pillars of modern compute, designed to act as a seamless extension of your own thought process.
        </p>
      </section>

      <section className="story-section" style={{ paddingTop: '0' }}>
        <div className="staggered-grid">
          <div className="staggered-text">
            <h3 className="font-serif" style={{ fontSize: '2rem', fontWeight: 400, marginBottom: '1.25rem', color: 'var(--text)' }}>I. Semantic Understanding</h3>
            <p style={{ fontSize: '1.1rem', lineHeight: 1.8, color: '#a1a1aa' }}>
              At her core lies a state-of-the-art semantic memory engine. Instead of just storing files, she stores relationships. She knows that when you open your code editor, you likely want your terminal and documentation ready. She builds a living graph of your habits.
            </p>
          </div>
          <div className="staggered-visual" style={{ paddingLeft: '2rem' }}>
             <div className="glass-panel" style={{ padding: '2rem', height: '100%', minHeight: '250px' }}>
                {/* Abstract graphic */}
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '100px', height: '100px', border: '1px solid var(--line)', borderRadius: '50%' }}></div>
                <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '150px', height: '150px', border: '1px dashed var(--line)', borderRadius: '50%', animation: 'pulse-orb 10s infinite linear' }}></div>
             </div>
          </div>
        </div>

        <div className="staggered-grid reverse">
          <div className="staggered-text">
            <h3 className="font-serif" style={{ fontSize: '2rem', fontWeight: 400, marginBottom: '1.25rem', color: 'var(--text)' }}>II. Unbounded Autonomy</h3>
            <p style={{ fontSize: '1.1rem', lineHeight: 1.8, color: '#a1a1aa' }}>
              Her proactive sub-system operates autonomously in the background. It isn't just an app you launch; it's a daemon that constantly evaluates whether it can save you time. If you receive an invite, she schedules it. If space runs low, she clears the cache.
            </p>
          </div>
          <div className="staggered-visual" style={{ paddingRight: '2rem' }}>
             <div className="glass-panel" style={{ padding: '2rem', height: '100%', minHeight: '250px' }}>
                <div style={{ background: 'var(--accent-subtle)', height: '20%', borderRadius: '4px', marginBottom: '1rem' }}></div>
                <div style={{ background: 'var(--line)', height: '20%', width: '70%', borderRadius: '4px', marginBottom: '1rem' }}></div>
                <div style={{ background: 'var(--accent-subtle)', height: '20%', width: '40%', borderRadius: '4px' }}></div>
             </div>
          </div>
        </div>
      </section>

      <div className="luxury-divider"></div>

      <section className="vault-section" style={{ marginTop: '0', background: 'transparent', border: 'none' }}>
        <h2 className="font-serif" style={{ fontSize: 'clamp(2.5rem, 5vw, 4rem)', color: 'var(--text)', marginBottom: '1.5rem', fontWeight: 400 }}>
          Open Source Heritage.
        </h2>
        <p style={{ fontSize: '1.25rem', color: '#888', maxWidth: '60ch', margin: '0 auto 4rem', lineHeight: 1.8 }}>
          We believe the future of AI should not be locked behind corporate black boxes. Hilda is proudly open source. Inspect her core, modify her behavior, and contribute to the evolution of the desktop.
        </p>
        
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <a className="premium-btn" href="https://github.com/heavyhitter69/hilda" target="_blank" rel="noopener noreferrer">
            Explore the Source
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
          </a>
          <Link className="btn secondary" to="/download" style={{ padding: '1.1rem 2.5rem', fontSize: '1.05rem', borderRadius: '999px', border: '1px solid var(--line)' }}>
            Download Installer
          </Link>
        </div>
      </section>
      
      <section className="prose-block" style={{ margin: '4rem auto 0', textAlign: 'center', paddingBottom: '3rem' }}>
        <p style={{ fontSize: '0.85rem', color: '#71717a' }}>
          See our <Link to="/privacy" style={{ color: '#a1a1aa' }}>Privacy Policy</Link> and <Link to="/terms" style={{ color: '#a1a1aa' }}>Terms of Service</Link> for legal details.
        </p>
      </section>
    </main>
  );
}
