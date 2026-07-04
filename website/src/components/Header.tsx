import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  return (
    <header className="top">
      <div className="top-inner">
        <Link className="brand" to="/">
          <img
            className="brand-logo"
            src="/hilda-ai.png"
            width="28"
            height="28"
            alt="Hilda"
            decoding="async"
          />
          <span className="brand-word">Hilda</span>
        </Link>
        <nav className="nav" aria-label="Primary">
          <Link
            className={`nav-link ${location.pathname === '/' ? 'is-active' : ''}`}
            to="/"
          >
            Home
          </Link>
          <Link
            className={`nav-link ${location.pathname === '/about' ? 'is-active' : ''}`}
            to="/about"
          >
            About
          </Link>
          <Link
            className={`nav-link ${location.pathname === '/download' ? 'is-active' : ''}`}
            to="/download"
          >
            Download
          </Link>
        </nav>
        <div className="top-actions">
          <Link className="btn-header-primary" to="/download">
            Download
          </Link>
        </div>
      </div>
    </header>
  );
}
