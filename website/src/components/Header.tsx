import { Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { detectOS } from '../utils/hildaInstaller';

export default function Header() {
  const location = useLocation();
  const [downloadUrl, setDownloadUrl] = useState('/download');

  useEffect(() => {
    if (location.pathname === '/download') {
      const os = detectOS();
      if (os === 'Mac') {
        setDownloadUrl('https://github.com/heavyhitter69/hilda/releases/latest/download/Hilda-Setup-mac-x64.dmg');
      } else if (os === 'Linux') {
        setDownloadUrl('https://github.com/heavyhitter69/hilda/releases/latest/download/Hilda-Setup-linux-x86_64.AppImage');
      } else {
        setDownloadUrl('https://github.com/heavyhitter69/hilda/releases/latest/download/Hilda-Setup-win-x64.exe');
      }
    } else {
      setDownloadUrl('/download');
    }
  }, [location.pathname]);

  const buttonStyle = {
    background: 'var(--bg-elevated)',
    color: 'var(--text)',
    padding: '0.5rem 1.25rem',
    borderRadius: '999px',
    fontSize: '0.85rem',
    fontWeight: 500 as const,
    textDecoration: 'none',
    transition: 'all 0.3s ease',
    boxShadow: '0 0 0 1px var(--line)'
  };

  return (
    <header className="top" style={{ 
      background: 'var(--bg-elevated)', 
      backdropFilter: 'blur(20px)', 
      WebkitBackdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--line-strong)',
      boxShadow: '0 4px 30px var(--line)'
    }}>
      <div className="top-inner">
        <Link className="brand" to="/" style={{ gap: '0.75rem' }}>
          <img
            className="brand-logo"
            src="/hilda-ai.png"
            width="28"
            height="28"
            alt="Hilda"
            decoding="async"
            style={{ borderRadius: '8px', border: '1px solid var(--line)' }}
          />
          <span className="brand-word font-serif" style={{ letterSpacing: '0.08em', fontSize: '1.1rem', textTransform: 'none' }}>Hilda</span>
        </Link>
        <nav className="nav" aria-label="Primary" style={{ gap: '1rem' }}>
          <Link
            className={`nav-link ${location.pathname === '/' ? 'is-active' : ''}`}
            to="/"
            style={location.pathname === '/' ? { color: 'var(--text)' } : {}}
          >
            Overview
          </Link>
          <Link
            className={`nav-link ${location.pathname === '/about' ? 'is-active' : ''}`}
            to="/about"
            style={location.pathname === '/about' ? { color: 'var(--text)' } : {}}
          >
            Manifesto
          </Link>
        </nav>
        <div className="top-actions">
          {location.pathname === '/download' ? (
            <a href={downloadUrl} style={buttonStyle}>Download</a>
          ) : (
            <Link to="/download" style={buttonStyle}>Download</Link>
          )}
        </div>
      </div>
    </header>
  );
}
