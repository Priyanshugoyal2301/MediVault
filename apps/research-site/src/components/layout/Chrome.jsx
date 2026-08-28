import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { Menu, Moon, Search, Sun, X } from 'lucide-react';
import { footerColumns, navMega, navPrimary, site } from '../../content/site';

const SEARCH_INDEX = [
  { label: 'Research overview', href: '/research' },
  { label: 'Technology', href: '/technology' },
  { label: 'Methodology', href: '/methodology' },
  { label: 'Architecture', href: '/architecture' },
  { label: 'Datasets', href: '/datasets' },
  { label: 'Benchmarks', href: '/benchmarks' },
  { label: 'Documentation', href: '/documentation' },
  { label: 'Downloads', href: '/downloads' },
  { label: 'Publications', href: '/publications' },
  { label: 'Features', href: '/features' },
  { label: 'Timeline', href: '/timeline' },
  { label: 'Gallery', href: '/gallery' },
  { label: 'Team', href: '/team' },
  { label: 'Partners', href: '/partners' },
  { label: 'Blog', href: '/blog' },
  { label: 'News', href: '/news' },
  { label: 'FAQ', href: '/faq' },
  { label: 'Contact', href: '/contact' },
  { label: 'Privacy Policy', href: '/privacy' },
  { label: 'Accessibility', href: '/accessibility' },
  { label: 'Press kit', href: '/press' },
  { label: 'About', href: '/about' },
];

function BrandMark() {
  return (
    <span className="topnav__mark" aria-hidden="true">
      <svg viewBox="0 0 16 16" fill="none">
        <path
          d="M2.5 10c1.5-3.5 3-5 5.5-5s4 1.5 5.5 5"
          stroke="#D4E8E4"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
        <circle cx="8" cy="11.2" r="1.4" fill="#3D9B8F" />
      </svg>
    </span>
  );
}

export function ReadProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const onScroll = () => {
      const el = document.documentElement;
      const max = el.scrollHeight - el.clientHeight;
      setP(max > 0 ? el.scrollTop / max : 0);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  return (
    <div
      className="read-progress"
      style={{ transform: `scaleX(${p})` }}
      aria-hidden="true"
    />
  );
}

export function TopNav({ theme, onToggleTheme }) {
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const [megaOpen, setMegaOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const searchRef = useRef(null);
  const megaId = useId();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    setMegaOpen(false);
    setDrawerOpen(false);
    setSearchOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (searchOpen) {
      searchRef.current?.focus();
      const onKey = (e) => {
        if (e.key === 'Escape') setSearchOpen(false);
      };
      window.addEventListener('keydown', onKey);
      return () => window.removeEventListener('keydown', onKey);
    }
  }, [searchOpen]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return SEARCH_INDEX.slice(0, 8);
    return SEARCH_INDEX.filter((item) => item.label.toLowerCase().includes(q)).slice(0, 12);
  }, [query]);

  return (
    <>
      <header
        className={`topnav${scrolled || megaOpen || drawerOpen ? ' is-scrolled' : ''}${
          megaOpen || drawerOpen ? ' is-open' : ''
        }`}
      >
        <div className="topnav__inner">
          <Link to="/" className="topnav__brand">
            <BrandMark />
            <span>{site.institution}</span>
          </Link>

          <nav aria-label="Primary">
            <ul className="topnav__primary">
              {navPrimary.map((item) => (
                <li key={item.href}>
                  <NavLink
                    to={item.href}
                    className={({ isActive }) => (isActive ? undefined : undefined)}
                    aria-current={location.pathname === item.href ? 'page' : undefined}
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ minHeight: '2.2rem', paddingInline: '0.75rem' }}
                  aria-expanded={megaOpen}
                  aria-controls={megaId}
                  onClick={() => {
                    setMegaOpen((v) => !v);
                    setDrawerOpen(false);
                  }}
                >
                  Explore
                </button>
              </li>
            </ul>
          </nav>

          <div className="topnav__actions">
            <button
              type="button"
              className="icon-btn"
              aria-label="Search site"
              onClick={() => setSearchOpen(true)}
            >
              <Search size={18} strokeWidth={1.75} />
            </button>
            <button
              type="button"
              className="icon-btn"
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              onClick={onToggleTheme}
            >
              {theme === 'dark' ? (
                <Sun size={18} strokeWidth={1.75} />
              ) : (
                <Moon size={18} strokeWidth={1.75} />
              )}
            </button>
            <Link to="/contact" className="btn btn-primary" style={{ display: 'none' }} id="nav-contact-lg">
              Contact
            </Link>
            <style>{`@media(min-width:1024px){#nav-contact-lg{display:inline-flex!important}}`}</style>
            <button
              type="button"
              className="icon-btn topnav__menu-btn"
              aria-label={drawerOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={drawerOpen}
              onClick={() => {
                setDrawerOpen((v) => !v);
                setMegaOpen(false);
              }}
            >
              {drawerOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
      </header>

      {megaOpen && (
        <>
          <button
            type="button"
            className="mega-backdrop"
            aria-label="Close explore menu"
            onClick={() => setMegaOpen(false)}
          />
          <div className="mega" id={megaId} role="region" aria-label="Explore menu">
            <div className="mega__inner">
              {navMega.map((col) => (
                <div key={col.title}>
                  <h3>{col.title}</h3>
                  <ul>
                    {col.links.map((link) => (
                      <li key={link.href}>
                        <Link to={link.href}>{link.label}</Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <div className={`drawer${drawerOpen ? ' is-open' : ''}`} aria-hidden={!drawerOpen}>
        {navMega.map((col) => (
          <div key={col.title}>
            <div className="group-title">{col.title}</div>
            {col.links.map((link) => (
              <Link key={link.href} to={link.href}>
                {link.label}
              </Link>
            ))}
          </div>
        ))}
        <Link to="/contact" style={{ marginTop: '1.5rem', fontWeight: 600 }}>
          Contact research
        </Link>
      </div>

      {searchOpen && (
        <div
          className="search-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Site search"
          onClick={(e) => {
            if (e.target === e.currentTarget) setSearchOpen(false);
          }}
        >
          <div className="search-overlay__panel">
            <label className="sr-only" htmlFor="site-search">
              Search
            </label>
            <input
              id="site-search"
              ref={searchRef}
              type="search"
              placeholder="Search research pages…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <ul className="search-results">
              {results.map((item) => (
                <li key={item.href}>
                  <Link to={item.href} onClick={() => setSearchOpen(false)}>
                    {item.label}
                  </Link>
                </li>
              ))}
              {results.length === 0 && (
                <li style={{ padding: '0.75rem 0', color: 'var(--ink-subtle)' }}>No matches</li>
              )}
            </ul>
            <p style={{ margin: '1rem 0 0', fontSize: 'var(--text-xs)', color: 'var(--ink-subtle)' }}>
              Press Esc to close
            </p>
          </div>
        </div>
      )}
    </>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell-wide">
        <div className="site-footer__grid">
          <div>
            <p className="site-footer__brand">{site.institution}</p>
            <p className="site-footer__blurb">
              Evidence-grounded medical intelligence research — longitudinal, cited, and
              non-diagnostic by design.
            </p>
          </div>
          {footerColumns.map((col) => (
            <div key={col.title}>
              <h3>{col.title}</h3>
              <ul>
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link to={link.href}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="site-footer__meta">
          <span>
            © {new Date().getFullYear()} {site.institution}. Not a medical device.
          </span>
          <div className="site-footer__legal">
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
            <Link to="/accessibility">Accessibility</Link>
            <Link to="/sitemap">Sitemap</Link>
            <span>
              v{site.version} · {site.build}
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
