import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-grid">
          <div className="footer-col">
            <h4>Product</h4>
            <Link to="/">Overview</Link>
            <Link to="/download">Download</Link>
            <Link to="/about">About</Link>
          </div>
          <div className="footer-col">
            <h4>Developers</h4>
            <Link to="/about#source">From source</Link>
            <Link to="/download">Platforms</Link>
          </div>
          <div className="footer-col">
            <h4>Legal</h4>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Use</Link>
          </div>
          <div className="footer-col">
            <h4>Resources</h4>
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2026 Hilda · Personal assistant for Windows, macOS, and Linux</span>
          <span>Made for focus, not noise.</span>
        </div>
      </div>
    </footer>
  );
}
