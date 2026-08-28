import { motion, useReducedMotion } from 'framer-motion';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { site } from '../content/site';

export function Seo({
  title,
  description = 'MediVault Research — owner-scoped lab intelligence with personal-series monitoring and citation-backed Q&A, engineered never to diagnose.',
  path = '/',
}) {
  const full =
    title && title !== 'Home'
      ? `${title} · ${site.institution}`
      : `${site.institution} — ${site.tagline}`;
  const url = `${site.domain}${path === '/' ? '' : path}`;
  return (
    <Helmet>
      <title>{full}</title>
      <meta name="description" content={description} />
      <meta name="author" content={site.institution} />
      <meta
        name="keywords"
        content="MediVault, medical AI research, lab report intelligence, BM25 RAG, personal series anomaly, non-diagnostic AI, health privacy"
      />
      <link rel="canonical" href={url || site.domain} />
      <meta property="og:type" content="website" />
      <meta property="og:title" content={full} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={url || site.domain} />
      <meta property="og:site_name" content={site.institution} />
      <meta property="og:locale" content="en_IN" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={full} />
      <meta name="twitter:description" content={description} />
      <script type="application/ld+json">
        {JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'ResearchProject',
          name: site.institution,
          description,
          url: site.domain,
          keywords:
            'laboratory literacy, personal-series monitoring, BM25 retrieval, medical safety AI',
          parentOrganization: {
            '@type': 'Organization',
            name: site.brand,
            url: site.github,
          },
          founder: {
            '@type': 'Person',
            name: 'Priyanshu Goyal',
          },
        })}
      </script>
    </Helmet>
  );
}

export function Reveal({ children, delay = 0, className, y = 22 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-8% 0px' }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function PageHeader({ title, lede, crumbs = [] }) {
  return (
    <header className="page-hero">
      <div className="shell">
        <nav aria-label="Breadcrumb">
          <ol className="breadcrumbs">
            <li>
              <Link to="/">Home</Link>
            </li>
            {crumbs.map((c, i) => (
              <li key={c.href || c.label} style={{ display: 'contents' }}>
                <span aria-hidden="true">/</span>
                <span aria-current={i === crumbs.length - 1 ? 'page' : undefined}>
                  {c.href && i < crumbs.length - 1 ? (
                    <Link to={c.href}>{c.label}</Link>
                  ) : (
                    c.label
                  )}
                </span>
              </li>
            ))}
          </ol>
        </nav>
        <Reveal>
          <p className="eyebrow">{site.institution}</p>
          <h1 className="text-balance">{title}</h1>
          {lede && <p className="lede">{lede}</p>}
        </Reveal>
      </div>
    </header>
  );
}

export function SectionHead({ eyebrow, title, lede }) {
  return (
    <div className="section-header">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h2 className="text-balance">{title}</h2>
      {lede && <p className="lede">{lede}</p>}
    </div>
  );
}

export function LegalBody({ children }) {
  return (
    <div className="section section-tight">
      <div className="shell prose">{children}</div>
    </div>
  );
}
