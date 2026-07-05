import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';

export default function Footer() {
  const [theme, setTheme] = useState<'system' | 'light' | 'dark'>('system');

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      root.setAttribute('data-theme', theme);
    }
  }, [theme]);

  return (
    <footer className="site-footer" style={{ 
      background: 'var(--bg)', 
      borderTop: '1px solid var(--line)',
      padding: '5rem 1.5rem 3rem'
    }}>
      <div className="footer-inner" style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div className="footer-grid" style={{ gap: '3rem 2rem' }}>
          <div className="footer-col">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
              <img src="/hilda-ai.png" width="24" height="24" alt="Hilda" style={{ borderRadius: '6px', opacity: 0.8 }} />
              <span className="font-serif" style={{ fontSize: '1.1rem', color: 'var(--text)' }}>Hilda</span>
            </div>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: 1.6, margin: 0, maxWidth: '200px' }}>
              A sovereign intelligence, crafted for the modern desktop.
            </p>
          </div>
          <div className="footer-col">
            <h4 style={{ color: 'var(--text)', letterSpacing: '0.1em' }}>Platform</h4>
            <Link to="/">Overview</Link>
            <Link to="/download">Downloads</Link>
            <Link to="/about">Manifesto</Link>
          </div>
          <div className="footer-col">
            <h4 style={{ color: 'var(--text)', letterSpacing: '0.1em' }}>Developers</h4>
            <a href="https://github.com/heavyhitter69/hilda" target="_blank" rel="noopener noreferrer">Source Code</a>
            <Link to="/download">Build Guide</Link>
          </div>
          <div className="footer-col">
            <h4 style={{ color: 'var(--text)', letterSpacing: '0.1em' }}>Legal</h4>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
          </div>
        </div>
        
        <div className="luxury-divider horizontal" style={{ margin: '4rem auto 2rem', width: '100%', background: 'linear-gradient(to right, transparent, var(--line-strong), transparent)' }}></div>
        
        <div className="footer-bottom" style={{ borderTop: 'none', paddingTop: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '2rem' }}>
          <span style={{ color: 'var(--text-dim)' }}>© {new Date().getFullYear()} Hilda AI. All rights reserved.</span>
          
          <div className="theme-switcher" role="radiogroup" aria-label="Theme selection">
            <button 
              className={`theme-btn ${theme === 'system' ? 'active' : ''}`} 
              onClick={() => setTheme('system')}
              aria-label="System theme"
              aria-checked={theme === 'system'}
              role="radio"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
            </button>
            <button 
              className={`theme-btn ${theme === 'light' ? 'active' : ''}`} 
              onClick={() => setTheme('light')}
              aria-label="Light theme"
              aria-checked={theme === 'light'}
              role="radio"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
            </button>
            <button 
              className={`theme-btn ${theme === 'dark' ? 'active' : ''}`} 
              onClick={() => setTheme('dark')}
              aria-label="Dark theme"
              aria-checked={theme === 'dark'}
              role="radio"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            </button>
          </div>

          <span className="font-serif" style={{ fontStyle: 'italic', opacity: 0.7, color: 'var(--text-dim)' }}>Intelligence, refined.</span>
        </div>
      </div>
    </footer>
  );
}
