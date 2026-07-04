import { Link } from 'react-router-dom';

export default function About() {
  return (
    <main>
      <header className="page-hero compact">
        <p className="eyebrow">About</p>
        <h1>A personal assistant that keeps pace</h1>
        <p className="lede tight-bottom">
          Hilda is built for Windows—a companion that handles quick jobs fast and deeper questions when you ask, without crowding your workspace.
        </p>
      </header>

      <section className="prose-block">
        <h2>Why Hilda</h2>
        <p>
          Simple tasks should feel immediate. Hilda is meant to cut the gap between what you want and what your PC does—whether you speak or click—while leaving you in control of privacy and optional online features.
        </p>
      </section>

      <section className="prose-block" id="source">
        <h2>From source</h2>
        <p>
          If you’re building Hilda yourself, follow the README in your repository.
        </p>
      </section>

      <section className="prose-block">
        <h2>Legal</h2>
        <p>
          See <Link to="/privacy">Privacy</Link> and <Link to="/terms">Terms</Link> for policies that apply to this software.
        </p>
      </section>

      <p className="back-row">
        <Link className="btn secondary" to="/">← Home</Link>
        <Link className="btn primary" to="/download">Download</Link>
      </p>
    </main>
  );
}
