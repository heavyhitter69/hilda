import { Link } from 'react-router-dom';

export default function Privacy() {
  return (
    <main className="legal">
      <header className="page-hero compact">
        <p className="eyebrow">Legal</p>
        <h1>Privacy Policy</h1>
        <p className="meta-line">Last updated: May 7, 2026</p>
      </header>

      <section className="legal-section">
        <h2>Overview</h2>
        <p>
          Hilda (“the Software”) runs primarily on your computer. This policy describes what typically stays on your device,
          what may be sent to third-party services when you enable optional features, and how you can control that behavior.
        </p>
        <p>
          If you distribute your own build or fork of Hilda, you are responsible for updating this policy to match your product and jurisdiction.
        </p>
      </section>

      <section className="legal-section">
        <h2>Information processed locally</h2>
        <p>
          Microphone input, wake detection, and speech recognition can stay on your device depending on settings.
          Actions you ask for—opening files, running allowed commands—are handled locally within the Software’s safeguards.
        </p>
      </section>

      <section className="legal-section">
        <h2>Optional cloud and third-party services</h2>
        <p>
          If you add API keys or turn on integrations, data those services need may be sent per their terms—only for features you enable. Check each provider’s policy before connecting.
        </p>
      </section>

      <section className="legal-section">
        <h2>Logs and diagnostics</h2>
        <p>
          The Software may write logs on disk for troubleshooting (for example under your user application data directory). Those logs are under your control.
          Unless you separately configure telemetry or crash reporting, we do not operate a central service that collects those logs automatically.
        </p>
      </section>

      <section className="legal-section">
        <h2>Changes</h2>
        <p>
          We may update this policy when the Software or hosting practices change. The “Last updated” date at the top reflects the latest revision for this page.
        </p>
      </section>

      <section className="legal-section">
        <h2>Contact</h2>
        <p>
          For privacy questions related to your deployment of Hilda, contact the maintainer of your build or repository using the channels listed there.
        </p>
      </section>

      <p className="back-row">
        <Link className="btn secondary" to="/">← Home</Link>
        <Link className="btn secondary" to="/terms">Terms of Use</Link>
      </p>
    </main>
  );
}
