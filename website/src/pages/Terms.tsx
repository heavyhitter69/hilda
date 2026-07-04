import { Link } from 'react-router-dom';

export default function Terms() {
  return (
    <main className="legal">
      <header className="page-hero compact">
        <p className="eyebrow">Legal</p>
        <h1>Terms of Use</h1>
        <p className="meta-line">Last updated: May 7, 2026</p>
      </header>

      <section className="legal-section">
        <h2>Agreement</h2>
        <p>
          By downloading, installing, or using Hilda (the “Software”), you agree to these terms. If you do not agree, do not use the Software.
        </p>
      </section>

      <section className="legal-section">
        <h2>License</h2>
        <p>
          Use of the Software is governed by the license file shipped with your copy or repository (for example an MIT or other open-source license).
          If no license is specified in your distribution, contact the distributor for terms.
        </p>
      </section>

      <section className="legal-section">
        <h2>Acceptable use</h2>
        <p>
          You are responsible for complying with applicable laws and for how you use speech input, automation, and optional cloud APIs.
          Do not use the Software to harm systems you do not own or lack permission to operate, or to violate others’ privacy.
        </p>
      </section>

      <section className="legal-section">
        <h2>Interpretation &amp; automation</h2>
        <p>
          Speech and automation can misinterpret intent. Review sensitive actions before relying on them. API keys, models, and permissions are your responsibility.
        </p>
      </section>

      <section className="legal-section">
        <h2>Disclaimer</h2>
        <p>
          THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
          FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
          LIABILITY ARISING FROM THE USE OF THE SOFTWARE.
        </p>
      </section>

      <section className="legal-section">
        <h2>Third-party services</h2>
        <p>
          Optional integrations are subject to their providers’ terms. You are responsible for fees, usage limits, and compliance when you enable those integrations.
        </p>
      </section>

      <section className="legal-section">
        <h2>Changes</h2>
        <p>
          These terms may be updated. Continued use after changes constitutes acceptance of the revised terms for your deployment.
        </p>
      </section>

      <p className="back-row">
        <Link className="btn secondary" to="/">← Home</Link>
        <Link className="btn secondary" to="/privacy">Privacy Policy</Link>
      </p>
    </main>
  );
}
