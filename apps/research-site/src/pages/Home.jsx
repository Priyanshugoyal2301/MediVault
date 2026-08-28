import { motion, useReducedMotion } from 'framer-motion';
import { Link } from 'react-router-dom';
import HeroField from '../components/HeroField';
import SignalPanel from '../components/SignalPanel';
import { Reveal, SectionHead, Seo } from '../components/ui';
import {
  benchmarks,
  features,
  hero,
  narrative,
  pillars,
  pipelineSteps,
  problemStats,
  site,
} from '../content/site';

export default function HomePage() {
  const reduce = useReducedMotion();

  return (
    <>
      <Seo
        path="/"
        title="Home"
        description="MediVault Research — owner-scoped lab intelligence with personal-series monitoring and citation-backed Q&A, engineered never to diagnose."
      />

      <section className="home-hero" aria-label="Introduction">
        <HeroField />
        <div className="home-hero__content">
          <div>
            <motion.p
              className="home-hero__brand"
              initial={reduce ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            >
              {hero.brand}
            </motion.p>
            <motion.h1
              className="text-balance"
              initial={reduce ? false : { opacity: 0, y: 28 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.85, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            >
              {hero.headline}
            </motion.h1>
            <motion.p
              className="home-hero__support"
              initial={reduce ? false : { opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.16, ease: [0.22, 1, 0.36, 1] }}
            >
              {hero.support}
            </motion.p>
            <motion.div
              className="home-hero__actions"
              initial={reduce ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.24, ease: [0.22, 1, 0.36, 1] }}
            >
              <Link className="btn btn-primary" to={hero.primaryCta.href}>
                {hero.primaryCta.label}
              </Link>
              <Link className="btn btn-secondary" to={hero.secondaryCta.href}>
                {hero.secondaryCta.label}
              </Link>
            </motion.div>
          </div>
          <motion.div
            className="home-hero__visual"
            initial={reduce ? false : { opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
            role="img"
            aria-label="Illustration of a rising personal laboratory series monitored for anomalous change"
          >
            <SignalPanel />
          </motion.div>
        </div>
      </section>

      <section className="section-tight" aria-label="Scientific posture">
        <div className="shell-wide">
          <div className="trust-row">
            <span>Non-diagnostic by design</span>
            <span>Owner-scoped privacy</span>
            <span>Deterministic safety layer</span>
            <span>Published evaluation protocol</span>
            <span>Rejected approaches documented</span>
          </div>
        </div>
      </section>

      <section className="section" id="problem">
        <div className="shell-wide">
          <Reveal>
            <SectionHead
              eyebrow="The problem"
              title="Between “I feel fine” and “I need a clinician,” people are alone with their labs."
              lede={narrative.problem}
            />
          </Reveal>
          <div className="metric-row">
            {problemStats.map((m, i) => (
              <Reveal key={m.label} delay={i * 0.06}>
                <div className="metric">
                  <div className="metric-value mono">{m.value}</div>
                  <div className="metric-label">{m.label}</div>
                  <div className="metric-note">{m.note}</div>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.1}>
            <p className="lede" style={{ marginTop: '2.5rem' }}>
              Existing tools often solve one slice in isolation: a chat answer without memory, a chart without
              citations, or a parser without a safety posture.{' '}
              <Link to="/research">Read the research framing →</Link>
            </p>
          </Reveal>
        </div>
      </section>

      <section className="section" style={{ background: 'var(--bg-muted)' }} id="solution">
        <div className="shell-wide">
          <Reveal>
            <SectionHead
              eyebrow="Our approach"
              title="Three capabilities, one coherent system."
              lede={narrative.contribution}
            />
          </Reveal>
          <div className="feature-grid">
            {pillars.map((p, i) => (
              <Reveal key={p.title} delay={i * 0.05}>
                <article className="panel stack-sm">
                  <p className="eyebrow">0{i + 1}</p>
                  <h3 className="display" style={{ fontSize: 'var(--text-xl)', margin: 0 }}>
                    {p.title}
                  </h3>
                  <p style={{ margin: 0, color: 'var(--ink-muted)', lineHeight: 1.65 }}>{p.body}</p>
                </article>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="pipeline">
        <div className="shell-wide">
          <Reveal>
            <SectionHead
              eyebrow="Intelligence pipeline"
              title="From report bytes to evidence-bound answers."
              lede="A deliberate path—validate, perceive, explain, monitor, retrieve—with deterministic safety as a hard gate before any synthesis."
            />
          </Reveal>
          <div className="pipeline">
            {pipelineSteps.map((s, i) => (
              <Reveal key={s.id} delay={i * 0.05}>
                <div className="pipeline-step">
                  <div className="idx">{s.id}</div>
                  <h3>{s.title}</h3>
                  <p>{s.detail}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.1}>
            <p style={{ marginTop: '2rem' }}>
              <Link className="btn btn-secondary" to="/technology">
                Explore technology
              </Link>
            </p>
          </Reveal>
        </div>
      </section>

      <section className="section section-ink" id="benchmarks-preview">
        <div className="shell-wide">
          <Reveal>
            <p className="eyebrow">Evaluation</p>
            <h2
              className="display text-balance"
              style={{
                fontSize: 'var(--text-3xl)',
                margin: '0.75rem 0 1rem',
                maxWidth: '18ch',
                color: '#f7faf9',
                opacity: 1,
              }}
            >
              Measured where it matters. Honest where it does not.
            </h2>
            <p className="lede">
              Headline results from the open evaluation suite—research signals under disclosed synthetic protocols,
              not clinical validation.
            </p>
          </Reveal>
          <div className="metric-row" style={{ marginTop: '2.5rem' }}>
            {benchmarks.map((b, i) => (
              <Reveal key={b.name} delay={i * 0.05}>
                <div className="metric">
                  <div className="metric-value mono">{b.value}</div>
                  <div className="metric-label">
                    {b.name} · {b.metric}
                  </div>
                  <div className="metric-note">vs {b.baseline}</div>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.1}>
            <p style={{ marginTop: '2.5rem' }}>
              <Link className="btn btn-on-ink" to="/benchmarks">
                Full benchmarks
              </Link>
            </p>
          </Reveal>
        </div>
      </section>

      <section className="section" id="features">
        <div className="shell-wide">
          <Reveal>
            <SectionHead
              eyebrow="Capabilities"
              title="What the platform surfaces — with scientific restraint."
              lede="Designed for clarity under clinical-trust constraints: no scare language, no invented diagnoses, no unsourced claims."
            />
          </Reveal>
          <div className="feature-grid">
            {features.map((f, i) => (
              <Reveal key={f.title} delay={i * 0.04}>
                <div className="feature-item" tabIndex={0}>
                  <h3>{f.title}</h3>
                  <p>{f.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section" style={{ background: 'var(--bg-muted)' }}>
        <div className="shell-wide two-col">
          <Reveal>
            <SectionHead
              eyebrow="Principles"
              title="Safety is not a model feature."
              lede={narrative.philosophy}
            />
            <ul className="stack-md" style={{ paddingLeft: '1.1rem', color: 'var(--ink-muted)' }}>
              <li>Red-flag emergency logic is deterministic and pre-empts all generation.</li>
              <li>Identity is gateway-verified; owner scope is structural at query time.</li>
              <li>Evaluation claims distinguish Hit@5, F1, tone heuristics, and clinical proof.</li>
              <li>Rejected approaches are published—not quietly abandoned in code.</li>
            </ul>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="panel">
              <p className="eyebrow">Research posture</p>
              <h3
                className="display"
                style={{ fontSize: 'var(--text-2xl)', margin: '0.5rem 0 1rem' }}
              >
                Transparent limits. Stronger trust.
              </h3>
              <p style={{ color: 'var(--ink-muted)', lineHeight: 1.7, margin: '0 0 1.5rem' }}>
                {narrative.limitations}
              </p>
              <Link className="btn btn-primary" to="/methodology">
                Methodology
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      <section className="section">
        <div className="shell-wide">
          <Reveal>
            <div className="panel cta-band" style={{ padding: 'clamp(2rem, 5vw, 3rem)' }}>
              <div>
                <p className="eyebrow">Collaborate</p>
                <h2 className="text-balance">Partner with MediVault Research</h2>
                <p className="lede" style={{ margin: 0 }}>
                  Evaluation partnerships, corpus collaboration, and research inquiries. {site.location}.
                </p>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                <Link className="btn btn-primary" to="/contact">
                  Contact
                </Link>
                <Link className="btn btn-secondary" to="/publications">
                  Publications
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
