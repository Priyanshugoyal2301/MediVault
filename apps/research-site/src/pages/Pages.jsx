import { Link, useParams } from 'react-router-dom';
import { PageHeader, Reveal, Seo } from '../components/ui';
import {
  anomalyAblation,
  benchmarks,
  blogPosts,
  datasets,
  downloads,
  faq,
  features,
  gallery,
  legal,
  methodology,
  narrative,
  navMega,
  news,
  partners,
  pipelineSteps,
  press,
  publications,
  site,
  team,
  techDepth,
  techStack,
  timeline,
} from '../content/site';

function Paras({ text }) {
  return text.split(/\n\n+/).map((p) => (
    <p key={p.slice(0, 48)}>{p}</p>
  ));
}

export function AboutPage() {
  return (
    <>
      <Seo
        title="About"
        path="/about"
        description="Mission, vision, and research philosophy of MediVault Research."
      />
      <PageHeader
        title="About the initiative"
        lede="Why MediVault exists, who it is for, and the principles that constrain every system decision."
        crumbs={[{ label: 'About', href: '/about' }]}
      />
      <section className="section section-tight">
        <div className="shell two-col">
          <Reveal>
            <div className="prose" style={{ maxWidth: 'none' }}>
              <h2>Mission</h2>
              <p>{narrative.mission}</p>
              <h2>Vision</h2>
              <p>{narrative.vision}</p>
              <h2>Research philosophy</h2>
              <p>{narrative.philosophy}</p>
              <h2>Why this project exists</h2>
              <p>{narrative.problem}</p>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="panel stack-md">
              <p className="eyebrow">Innovation principles</p>
              <ul className="stack-sm" style={{ paddingLeft: '1.1rem', color: 'var(--ink-muted)', margin: 0 }}>
                <li>Ship narrow, ship real—not a seven-module fantasy product</li>
                <li>Citations and owner data over fluent hallucinations</li>
                <li>Privacy structural, not ornamental</li>
                <li>Publish failures with the same care as wins</li>
                <li>Never let ML override emergency safety rules</li>
              </ul>
              <Link className="btn btn-primary" to="/team">
                Meet the team
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function ResearchPage() {
  return (
    <>
      <Seo
        title="Research"
        path="/research"
        description="Abstract, contributions, limits, and future work for MediVault Research."
      />
      <PageHeader
        title="Research overview"
        lede="A unified program for longitudinal, cited, non-diagnostic personal laboratory intelligence."
        crumbs={[{ label: 'Research', href: '/research' }]}
      />
      <section className="section section-tight">
        <div className="shell prose">
          <Reveal>
            <h2>Abstract</h2>
            <p>{narrative.abstract}</p>
            <h2>Scientific contribution</h2>
            <p>{narrative.contribution}</p>
            <h2>Problem framing</h2>
            <p>{narrative.problem}</p>
            <h2>Limitations</h2>
            <p>{narrative.limitations}</p>
            <h2>Future work</h2>
            <p>{narrative.future}</p>
            <p>
              Continue to <Link to="/methodology">methodology</Link>,{' '}
              <Link to="/datasets">datasets</Link>, and <Link to="/benchmarks">benchmarks</Link>.
            </p>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function TechnologyPage() {
  return (
    <>
      <Seo
        title="Technology"
        path="/technology"
        description="OCR, IE, statistical monitoring, BM25 retrieval, and safety stack."
      />
      <PageHeader
        title="Technology"
        lede="The medical intelligence stack—perception, statistics, retrieval, and safety—assembled for auditability."
        crumbs={[{ label: 'Technology', href: '/technology' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide">
          <div className="two-col">
            <Reveal>
              <div className="prose" style={{ maxWidth: 'none' }}>
                <h2>Intelligence layers</h2>
                <p>{techDepth.intro}</p>
                <h3>OCR & parsing</h3>
                <p>{techDepth.ocr}</p>
                <p>{techDepth.ie}</p>
                <h3>Personal-series monitoring</h3>
                <p>{techDepth.anomaly}</p>
                <h3>Retrieval & synthesis</h3>
                <p>{techDepth.rag}</p>
                <h3>Safety</h3>
                <p>{techDepth.safety}</p>
                <h2>Pipeline</h2>
                <div className="pipeline" style={{ marginTop: '1.5rem' }}>
                  {pipelineSteps.map((s) => (
                    <div key={s.id} className="pipeline-step">
                      <div className="idx">{s.id}</div>
                      <h3>{s.title}</h3>
                      <p>{s.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
            <Reveal delay={0.08}>
              <div className="panel">
                <p className="eyebrow">Stack map</p>
                <div className="stack-md" style={{ marginTop: '1rem' }}>
                  {techStack.map((row) => (
                    <div key={row.layer} style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                      <div className="mono" style={{ color: 'var(--color-primary-600)', marginBottom: '0.35rem' }}>
                        {row.layer}
                      </div>
                      <div style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-sm)' }}>{row.items}</div>
                    </div>
                  ))}
                </div>
                <p style={{ marginTop: '1.5rem' }}>
                  <Link className="btn btn-secondary" to="/architecture">
                    Architecture
                  </Link>
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>
    </>
  );
}

export function MethodologyPage() {
  return (
    <>
      <Seo
        title="Methodology"
        path="/methodology"
        description="Experiment design, algorithms, validation, and Guardian gates."
      />
      <PageHeader
        title="Research methodology"
        lede="How we design experiments, evaluate systems, and refuse claims the evidence cannot support."
        crumbs={[{ label: 'Methodology', href: '/methodology' }]}
      />
      <section className="section section-tight">
        <div className="shell prose">
          <Reveal>
            <h2>Workflow</h2>
            <p>{methodology.workflow}</p>
            <h2>Algorithms (summary)</h2>
            <p>
              Information extraction via multi-alias regex; trend via normalized slope and series z-score; anomaly via
              leave-last-out z (threshold 2) or CUSUM (k = 0.5σ, h = 4σ); retrieval via BM25 (k1 = 1.5, b = 0.75) with
              intent boosts capped at 0.35; answers via bilingual templates with tone sanitization.
            </p>
            <h2>Validation & experiment design</h2>
            <p>{methodology.validation}</p>
            <h2>Performance evaluation</h2>
            <p>{methodology.metrics}</p>
            <h2>Limitations</h2>
            <p>{narrative.limitations}</p>
            <h2>Future improvements</h2>
            <p>{narrative.future}</p>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function ArchitecturePage() {
  return (
    <>
      <Seo
        title="Architecture"
        path="/architecture"
        description="BFF microservices topology for MediVault auth, health, and internal AI."
      />
      <PageHeader
        title="System architecture"
        lede="A BFF-fronted microservice topology that keeps identity, health data, and intelligence separable."
        crumbs={[{ label: 'Architecture', href: '/architecture' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide">
          <Reveal>
            <div className="arch-diagram" aria-label="Architecture diagram">
              <div className="arch-node arch-node--ink">Client · research portal / product web</div>
              <div className="arch-node">API Gateway BFF · JWT verification · trusted owner injection</div>
              <div className="arch-row">
                <div className="arch-node arch-node--muted">Auth service · JWT & users</div>
                <div className="arch-node arch-node--muted">Health service · reports & timeline</div>
                <div className="arch-node arch-node--muted">AI service · parse · anomaly · Q&A</div>
              </div>
              <div className="arch-row">
                <div className="arch-node">PostgreSQL · owner_id FKs</div>
                <div className="arch-node">ScopedRepository</div>
                <div className="arch-node">Local OCR storage root</div>
              </div>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="prose" style={{ marginTop: '3rem', maxWidth: '42rem' }}>
              <h2>Boundaries</h2>
              <p>
                Browser traffic never addresses AI endpoints. The gateway strips client identity headers and reinjects{' '}
                <span className="mono">X-User-ID</span> from the JWT subject. Service-to-service parse and anomaly calls
                may require an internal key; file reads are restricted to the storage root. Compose binds health and AI
                ports to localhost so LAN spoofing cannot hit trusted headers.
              </p>
              <h2>Data lifecycle (reports)</h2>
              <p>
                Upload → magic-byte MIME validation → owner-scoped file save → report row → background{' '}
                <span className="mono">POST /parse</span> → structured values with bilingual explanations → timeline
                events when dates exist → status complete or failed.
              </p>
              <h2>Q&A lifecycle</h2>
              <p>
                Health loads recent owner report values, then calls AI <span className="mono">/qa</span>. Safety
                patterns run first; BM25 retrieval merges knowledge chunks with personal values; templates emit answers
                and citations.
              </p>
              <Link className="btn btn-primary" to="/documentation">
                Documentation
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function DatasetsPage() {
  return (
    <>
      <Seo
        title="Datasets"
        path="/datasets"
        description="Evaluation fixtures, knowledge base, and data pipelines for MediVault."
      />
      <PageHeader
        title="Data & statistical analysis"
        lede="Sources, pipelines, quality posture, and evaluation assets used by the research program."
        crumbs={[{ label: 'Datasets', href: '/datasets' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide two-col">
          <Reveal>
            <div className="prose" style={{ maxWidth: 'none' }}>
              <h2>Dataset overview</h2>
              <p>{datasets.overview}</p>
              <h2>Data sources</h2>
              <p>{datasets.sources}</p>
              <h2>Processing pipeline</h2>
              <p>{datasets.pipeline}</p>
              <h2>Data quality</h2>
              <p>{datasets.quality}</p>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="panel">
              <p className="eyebrow">Exploratory snapshot</p>
              <div className="chart-bars" style={{ marginTop: '1.25rem' }} aria-hidden="true">
                {[
                  { label: 'IE field F1', v: 97 },
                  { label: 'Anomaly F1', v: 87 },
                  { label: 'Hit@5', v: 100 },
                  { label: 'Tone clean', v: 100 },
                ].map((row) => (
                  <div className="chart-bar-row" key={row.label}>
                    <span>{row.label}</span>
                    <div className="chart-bar-track">
                      <div className="chart-bar-fill" style={{ width: `${row.v}%` }} />
                    </div>
                    <span className="mono">{row.v}%</span>
                  </div>
                ))}
              </div>
              <p className="metric-note" style={{ marginTop: '1rem' }}>
                Bars mirror the published evaluation table. Full confidence statements live on the Benchmarks page.
              </p>
              <p style={{ marginTop: '1.25rem' }}>
                <Link to="/benchmarks">Open benchmarks →</Link>
              </p>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function BenchmarksPage() {
  return (
    <>
      <Seo
        title="Benchmarks"
        path="/benchmarks"
        description="Plan B and Plan C metrics with protocol caveats for MediVault."
      />
      <PageHeader
        title="Benchmarks"
        lede="Performance metrics with protocol notes. Prefer honest synthetic evidence over inflated claims."
        crumbs={[{ label: 'Benchmarks', href: '/benchmarks' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide">
          <Reveal>
            <h2 className="display" style={{ fontSize: 'var(--text-xl)', marginBottom: '1rem' }}>
              Headline results
            </h2>
            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>System</th>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Reference</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarks.map((b) => (
                    <tr key={b.name}>
                      <td>{b.name}</td>
                      <td className="mono">{b.metric}</td>
                      <td className="mono">{b.value}</td>
                      <td className="mono">{b.baseline}</td>
                      <td>{b.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
          <Reveal delay={0.06}>
            <h2 className="display" style={{ fontSize: 'var(--text-xl)', margin: '3rem 0 1rem' }}>
              Anomaly ablation (Plan B, spike synthetic Hb)
            </h2>
            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>FAR</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalyAblation.map((r) => (
                    <tr key={r.method}>
                      <td>{r.method}</td>
                      <td className="mono">{r.precision.toFixed(3)}</td>
                      <td className="mono">{r.recall.toFixed(3)}</td>
                      <td className="mono">{r.f1.toFixed(3)}</td>
                      <td className="mono">{r.far.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="prose" style={{ marginTop: '3rem' }}>
              <h2>Evaluation methodology</h2>
              <p>
                Anomaly seed 42; 200 synthetic patients; 20% last-point spikes for the pitch baseline. Retrieval
                uses 50 labeled FAQ questions. IE uses eight layout fixtures with 29 gold fields. Dense hybrid bake-off
                reported ΔMRR ≈ +0.036 with Hit@5 already saturated—kept optional due to cold-start download risk.
              </p>
              <h2>Interpretation</h2>
              <p>
                Numbers are research measurements under disclosed protocols. Mixed-regime anomaly evaluation shows
                gradual drift is harder (overall recall ≈ 0.57). These results support engineering decisions; they are
                not clinical sensitivity claims and do not replace clinician judgment.
              </p>
              <p>
                Primary reports:{' '}
                <a href={publications[0].href} target="_blank" rel="noreferrer">
                  Plan B
                </a>
                {' · '}
                <a href={publications[1].href} target="_blank" rel="noreferrer">
                  Plan C
                </a>
                .
              </p>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function FeaturesPage() {
  return (
    <>
      <Seo title="Features" path="/features" description="MediVault platform capabilities." />
      <PageHeader
        title="Features"
        lede="Product surfaces aligned to the research system—without overclaiming clinical authority."
        crumbs={[{ label: 'Features', href: '/features' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide feature-grid">
          {features.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.04}>
              <article className="feature-item" tabIndex={0}>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function TimelinePage() {
  return (
    <>
      <Seo title="Timeline" path="/timeline" description="MediVault research milestones and roadmap." />
      <PageHeader
        title="Project timeline"
        lede="Milestones from scope freeze through Plan C—and what comes next."
        crumbs={[{ label: 'Timeline', href: '/timeline' }]}
      />
      <section className="section section-tight">
        <div className="shell">
          <div className="timeline">
            {timeline.map((t, i) => (
              <Reveal key={t.date + t.title} delay={i * 0.05}>
                <div className="timeline-item">
                  <div className="timeline-date">{t.date}</div>
                  <h3>{t.title}</h3>
                  <p>{t.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

export function PublicationsPage() {
  return (
    <>
      <Seo
        title="Publications"
        path="/publications"
        description="Technical reports and architecture literature from MediVault Research."
      />
      <PageHeader
        title="Publications"
        lede="Technical reports, evaluation documents, and citable project literature."
        crumbs={[{ label: 'Publications', href: '/publications' }]}
      />
      <section className="section section-tight">
        <div className="shell">
          <div className="pub-list">
            {publications.map((p) => (
              <Reveal key={p.title}>
                <article className="pub-item">
                  <div className="pub-type">
                    {p.type} · {p.year}
                  </div>
                  <h3>{p.title}</h3>
                  <p style={{ color: 'var(--ink-muted)', margin: 0 }}>
                    {p.authors} — {p.venue}
                  </p>
                  <p className="cite">{p.cite}</p>
                  <p style={{ marginTop: '1rem' }}>
                    <a className="btn btn-secondary" href={p.href} target="_blank" rel="noreferrer">
                      Open document
                    </a>
                  </p>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

export function GalleryPage() {
  return (
    <>
      <Seo title="Gallery" path="/gallery" description="Architecture and science visuals for MediVault." />
      <PageHeader
        title="Gallery"
        lede="Architecture studies, pipeline views, and scientific framing graphics."
        crumbs={[{ label: 'Gallery', href: '/gallery' }]}
      />
      <section className="section section-tight">
        <div className="shell-wide gallery-grid">
          {gallery.map((g, i) => (
            <Reveal key={g.title} delay={i * 0.04}>
              <figure className="gallery-tile">
                <div
                  className="tile-art"
                  role="img"
                  aria-label={g.note}
                  style={{
                    background: `linear-gradient(${120 + i * 18}deg,
                      color-mix(in srgb, var(--color-primary-200) ${30 + i * 5}%, transparent),
                      color-mix(in srgb, var(--color-secondary-200) 40%, transparent) 50%,
                      color-mix(in srgb, var(--color-primary-100) 60%, white))`,
                  }}
                />
                <figcaption>
                  <div
                    style={{
                      opacity: 0.75,
                      fontSize: '0.7rem',
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {g.category}
                  </div>
                  {g.title}
                  <div style={{ opacity: 0.8, fontWeight: 400, marginTop: '0.25rem' }}>{g.note}</div>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function FaqPage() {
  return (
    <>
      <Seo title="FAQ" path="/faq" description="FAQ on privacy, accuracy limits, ML methods, and use of MediVault." />
      <PageHeader
        title="Frequently asked questions"
        lede="Privacy, accuracy limits, technology, deployment, and clinical posture."
        crumbs={[{ label: 'FAQ', href: '/faq' }]}
      />
      <section className="section section-tight">
        <div className="shell">
          <div className="faq-list">
            {faq.map((item) => (
              <details key={item.q} className="faq-item">
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

export function ContactPage() {
  return (
    <>
      <Seo title="Contact" path="/contact" description="Contact MediVault Research for collaboration." />
      <PageHeader
        title="Contact"
        lede="Research inquiries, evaluation partnerships, and institutional collaboration."
        crumbs={[{ label: 'Contact', href: '/contact' }]}
      />
      <section className="section section-tight">
        <div className="shell two-col">
          <Reveal>
            <form
              className="form-grid"
              action={`mailto:${site.email}`}
              method="get"
              encType="text/plain"
            >
              <div className="field">
                <label htmlFor="name">Name</label>
                <input id="name" name="name" autoComplete="name" required />
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input id="email" name="email" type="email" autoComplete="email" required />
              </div>
              <div className="field">
                <label htmlFor="org">Organization</label>
                <input id="org" name="org" autoComplete="organization" />
              </div>
              <div className="field">
                <label htmlFor="topic">Topic</label>
                <select id="topic" name="subject" defaultValue="Research inquiry">
                  <option value="Research inquiry">Research inquiry</option>
                  <option value="Collaboration">Collaboration</option>
                  <option value="Press">Press</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="message">Message</label>
                <textarea id="message" name="body" rows={5} required />
              </div>
              <button type="submit" className="btn btn-primary">
                Open email client
              </button>
              <p className="metric-note">Opens your mail client with a draft to {site.email}.</p>
            </form>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="panel stack-md">
              <div>
                <p className="eyebrow">Email</p>
                <a href={`mailto:${site.email}`}>{site.email}</a>
              </div>
              <div>
                <p className="eyebrow">GitHub</p>
                <a href={site.github} target="_blank" rel="noreferrer">
                  {site.github.replace('https://', '')}
                </a>
              </div>
              <div>
                <p className="eyebrow">Location</p>
                <p style={{ margin: 0, color: 'var(--ink-muted)' }}>{site.location}</p>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}

export function DocsPage() {
  return (
    <>
      <Seo title="Documentation" path="/documentation" description="Technical documentation index for MediVault." />
      <PageHeader
        title="Documentation"
        lede="Operator and developer documentation for the research stack."
        crumbs={[{ label: 'Documentation', href: '/documentation' }]}
      />
      <section className="section section-tight">
        <div className="shell feature-grid">
          {[
            {
              t: 'Project Bible',
              d: 'Institutional technical encyclopedia—APIs, ML math, ops, security.',
              h: 'https://github.com/Priyanshugoyal2301/MediVault/blob/main/BIBLE.md',
            },
            {
              t: 'Architecture notes',
              d: 'Service boundaries and privacy model.',
              h: '/architecture',
            },
            {
              t: 'Technology surface',
              d: 'OCR, IE, anomaly, retrieval, and safety.',
              h: '/technology',
            },
            {
              t: 'Evaluation reports',
              d: 'Plan B and Plan C methods and tables.',
              h: '/benchmarks',
            },
            {
              t: 'Contributors',
              d: 'Author and maintainer — Deepansh Khanna.',
              h: 'https://github.com/Priyanshugoyal2301/MediVault/blob/main/CONTRIBUTORS.md',
            },
            {
              t: 'Developer rules',
              d: 'Conventions and privacy rules for maintainers.',
              h: 'https://github.com/Priyanshugoyal2301/MediVault/blob/main/docs/DEVELOPER_RULES.md',
            },
          ].map((item) => (
            <Reveal key={item.t}>
              {item.h.startsWith('http') ? (
                <a
                  className="feature-item"
                  href={item.h}
                  target="_blank"
                  rel="noreferrer"
                  style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}
                >
                  <h3>{item.t}</h3>
                  <p>{item.d}</p>
                </a>
              ) : (
                <Link className="feature-item" to={item.h} style={{ textDecoration: 'none', color: 'inherit' }}>
                  <h3>{item.t}</h3>
                  <p>{item.d}</p>
                </Link>
              )}
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function DownloadsPage() {
  return (
    <>
      <Seo title="Downloads" path="/downloads" description="Reports and source links for MediVault Research." />
      <PageHeader
        title="Downloads"
        lede="Technical reports, evaluation documents, and source access."
        crumbs={[{ label: 'Downloads', href: '/downloads' }]}
      />
      <section className="section section-tight">
        <div className="shell stack-md">
          {downloads.map((item) => (
            <Reveal key={item.label}>
              <div
                className="panel"
                style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}
              >
                <div>
                  <strong className="display" style={{ fontSize: 'var(--text-base)' }}>
                    {item.label}
                  </strong>
                  <p className="metric-note" style={{ margin: '0.35rem 0 0' }}>
                    {item.meta}
                  </p>
                </div>
                <a className="btn btn-secondary" href={item.href} target="_blank" rel="noreferrer">
                  Open
                </a>
              </div>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function TeamPage() {
  return (
    <>
      <Seo title="Team" path="/team" description="People and roles behind MediVault Research." />
      <PageHeader title="Team" lede="People steering the research initiative." crumbs={[{ label: 'Team' }]} />
      <section className="section section-tight">
        <div className="shell-wide team-grid">
          {team.map((m) => (
            <Reveal key={m.role + m.name}>
              <article className="team-card">
                <div className="team-avatar" aria-hidden="true" />
                <h3>{m.name}</h3>
                <div className="role">{m.role}</div>
                <p>{m.bio}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function PartnersPage() {
  return (
    <>
      <Seo title="Partners" path="/partners" description="Collaborators and ecosystem around MediVault." />
      <PageHeader
        title="Partners & ecosystem"
        lede={partners.intro}
        crumbs={[{ label: 'Partners' }]}
      />
      <section className="section section-tight">
        <div className="shell feature-grid">
          {partners.list.map((p) => (
            <Reveal key={p.name}>
              <article className="panel">
                <h3 className="display" style={{ fontSize: 'var(--text-lg)', margin: '0 0 0.75rem' }}>
                  {p.name}
                </h3>
                <p style={{ margin: 0, color: 'var(--ink-muted)', lineHeight: 1.65 }}>{p.blurb}</p>
              </article>
            </Reveal>
          ))}
        </div>
        <p className="shell" style={{ marginTop: '2rem' }}>
          <Link className="btn btn-primary" to="/contact">
            Propose a partnership
          </Link>
        </p>
      </section>
    </>
  );
}

export function BlogPage() {
  return (
    <>
      <Seo title="Blog" path="/blog" description="Research notes from MediVault Research." />
      <PageHeader title="Blog" lede="Research notes from the lab." crumbs={[{ label: 'Blog' }]} />
      <section className="section section-tight">
        <div className="shell pub-list">
          {blogPosts.map((p) => (
            <Reveal key={p.slug}>
              <article className="pub-item">
                <div className="pub-type">{p.date}</div>
                <h3>
                  <Link to={`/blog/${p.slug}`}>{p.title}</Link>
                </h3>
                <p style={{ color: 'var(--ink-muted)' }}>{p.excerpt}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function BlogPostPage() {
  const { slug } = useParams();
  const post = blogPosts.find((p) => p.slug === slug) || blogPosts[0];
  return (
    <>
      <Seo title={post.title} path={`/blog/${post.slug}`} description={post.excerpt} />
      <PageHeader
        title={post.title}
        lede={`${post.date} · Research note`}
        crumbs={[{ label: 'Blog', href: '/blog' }, { label: post.title }]}
      />
      <section className="section section-tight">
        <div className="shell prose">
          <Paras text={post.body} />
          <p>
            <Link to="/blog">← All notes</Link>
          </p>
        </div>
      </section>
    </>
  );
}

export function NewsPage() {
  return (
    <>
      <Seo title="News" path="/news" description="News and announcements from MediVault Research." />
      <PageHeader title="News" lede="Announcements from the research program." crumbs={[{ label: 'News' }]} />
      <section className="section section-tight">
        <div className="shell pub-list">
          {news.map((n) => (
            <Reveal key={n.title}>
              <article className="pub-item">
                <div className="pub-type">{n.date}</div>
                <h3>{n.title}</h3>
                <p style={{ color: 'var(--ink-muted)' }}>{n.body}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  );
}

export function LegalPage({ kind }) {
  const map = {
    privacy: { title: 'Privacy Policy', path: '/privacy', body: legal.privacy },
    terms: { title: 'Terms of Service', path: '/terms', body: legal.terms },
    accessibility: { title: 'Accessibility', path: '/accessibility', body: legal.accessibility },
    acknowledgements: { title: 'Acknowledgements', path: '/acknowledgements', body: legal.acknowledgements },
    licenses: { title: 'Licenses', path: '/licenses', body: legal.licenses },
    credits: { title: 'Credits', path: '/credits', body: legal.credits },
  };
  const page = map[kind];
  return (
    <>
      <Seo title={page.title} path={page.path} description={`${page.title} for MediVault Research.`} />
      <PageHeader title={page.title} crumbs={[{ label: page.title }]} />
      <section className="section section-tight">
        <div className="shell prose">
          <Paras text={page.body} />
          <p className="metric-note">
            Version {site.version} · Last review {site.lastReview}
          </p>
        </div>
      </section>
    </>
  );
}

export function PressPage() {
  return (
    <>
      <Seo title="Press Kit" path="/press" description="Press boilerplate and facts for MediVault Research." />
      <PageHeader
        title="Press kit"
        lede="Boilerplate and factual statements for accurate reporting."
        crumbs={[{ label: 'Press kit' }]}
      />
      <section className="section section-tight">
        <div className="shell prose">
          <h2>Boilerplate</h2>
          <p>{press.boilerplate}</p>
          <h2>Facts</h2>
          <ul>
            {press.facts.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          <h2>Media contact</h2>
          <p>
            <a href={`mailto:${site.email}`}>{site.email}</a>
          </p>
          <Link className="btn btn-primary" to="/media">
            Media resources
          </Link>
        </div>
      </section>
    </>
  );
}

export function MediaPage() {
  return (
    <>
      <Seo title="Media Resources" path="/media" description="Brand and visual resources for MediVault." />
      <PageHeader
        title="Media resources"
        lede="Brand language, colour cues, and link-out assets for presentations."
        crumbs={[{ label: 'Media resources' }]}
      />
      <section className="section section-tight">
        <div className="shell">
          <div className="prose" style={{ maxWidth: '40rem' }}>
            <h2>Usage</h2>
            <p>
              Prefer the research site’s lagoon-ink palette and Space Grotesk / Source Serif typography. Do not imply
              hospital certification, HIPAA clearance, or diagnostic capability in headlines or captions.
            </p>
            <h2>Recommended links</h2>
            <ul>
              <li>
                <a href={site.github} target="_blank" rel="noreferrer">
                  Source repository
                </a>
              </li>
              <li>
                <Link to="/benchmarks">Benchmarks</Link>
              </li>
              <li>
                <Link to="/press">Press kit</Link>
              </li>
            </ul>
          </div>
          <div className="gallery-grid" style={{ marginTop: '2rem' }}>
            {gallery.slice(0, 3).map((g, i) => (
              <figure key={g.title} className="gallery-tile">
                <div
                  className="tile-art"
                  aria-hidden="true"
                  style={{
                    background: `linear-gradient(${140 + i * 20}deg, var(--color-primary-200), var(--color-secondary-100))`,
                  }}
                />
                <figcaption>
                  {g.title}
                  <div style={{ opacity: 0.85, fontWeight: 400 }}>{g.note}</div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}

export function SitemapPage() {
  return (
    <>
      <Seo title="Sitemap" path="/sitemap" description="All public routes on MediVault Research." />
      <PageHeader title="Sitemap" lede="All public research site routes." crumbs={[{ label: 'Sitemap' }]} />
      <section className="section section-tight">
        <div className="shell-wide site-map-columns">
          {navMega.map((col) => (
            <div key={col.title}>
              <h2>{col.title}</h2>
              <ul>
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link to={l.href}>{l.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div>
            <h2>Utility</h2>
            <ul>
              <li>
                <Link to="/faq">FAQ</Link>
              </li>
              <li>
                <Link to="/privacy">Privacy</Link>
              </li>
              <li>
                <Link to="/terms">Terms</Link>
              </li>
              <li>
                <Link to="/accessibility">Accessibility</Link>
              </li>
              <li>
                <Link to="/acknowledgements">Acknowledgements</Link>
              </li>
              <li>
                <Link to="/credits">Credits</Link>
              </li>
              <li>
                <Link to="/search">Search</Link>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}

export function SearchPage() {
  return (
    <>
      <Seo title="Search" path="/search" description="Search MediVault Research pages." />
      <PageHeader
        title="Search"
        lede="Use the magnifying glass in the navigation bar for instant filtering across the site index."
        crumbs={[{ label: 'Search' }]}
      />
      <section className="section section-tight">
        <div className="shell">
          <p className="lede">
            Keyboard users can open the navigator menu, then tab to Search. Results cover research, systems,
            institute, legal, and media routes.
          </p>
          <Link className="btn btn-primary" to="/">
            Return home
          </Link>
        </div>
      </section>
    </>
  );
}

export function StatusPage({ code = 404 }) {
  const map = {
    404: {
      title: '404',
      message: 'This page is not in the research archive. Check the sitemap or return home.',
    },
    500: {
      title: '500',
      message: `Something failed on our side. Retry shortly or contact ${site.email}.`,
    },
    maintenance: {
      title: 'Maintenance',
      message: 'We are performing scheduled updates. Thank you for your patience.',
    },
    soon: {
      title: 'Coming soon',
      message: 'This surface is reserved for a future release of MediVault Research.',
    },
  };
  const page = map[code] || map[404];
  return (
    <div className="status-page">
      <Seo title={page.title} description={page.message} />
      <div>
        <p className="eyebrow">{site.institution}</p>
        <h1>{page.title}</h1>
        <p>{page.message}</p>
        <Link className="btn btn-primary" to="/">
          Back to home
        </Link>
      </div>
    </div>
  );
}
