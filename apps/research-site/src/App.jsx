import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { HelmetProvider } from 'react-helmet-async';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ReadProgress, SiteFooter, TopNav } from './components/layout/Chrome';
import HomePage from './pages/Home';
import {
  AboutPage,
  ArchitecturePage,
  BenchmarksPage,
  BlogPage,
  BlogPostPage,
  ContactPage,
  DatasetsPage,
  DocsPage,
  DownloadsPage,
  FaqPage,
  FeaturesPage,
  GalleryPage,
  LegalPage,
  MediaPage,
  MethodologyPage,
  NewsPage,
  PartnersPage,
  PressPage,
  PublicationsPage,
  ResearchPage,
  SearchPage,
  SitemapPage,
  StatusPage,
  TeamPage,
  TechnologyPage,
  TimelinePage,
} from './pages/Pages';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

function AnimatedRoutes() {
  const location = useLocation();
  const reduce = useReducedMotion();
  const bare = ['/404', '/500', '/maintenance', '/coming-soon'].includes(location.pathname);

  const routes = (
    <Routes location={location} key={location.pathname}>
      <Route path="/" element={<HomePage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/research" element={<ResearchPage />} />
      <Route path="/technology" element={<TechnologyPage />} />
      <Route path="/methodology" element={<MethodologyPage />} />
      <Route path="/architecture" element={<ArchitecturePage />} />
      <Route path="/datasets" element={<DatasetsPage />} />
      <Route path="/benchmarks" element={<BenchmarksPage />} />
      <Route path="/features" element={<FeaturesPage />} />
      <Route path="/timeline" element={<TimelinePage />} />
      <Route path="/publications" element={<PublicationsPage />} />
      <Route path="/gallery" element={<GalleryPage />} />
      <Route path="/faq" element={<FaqPage />} />
      <Route path="/contact" element={<ContactPage />} />
      <Route path="/documentation" element={<DocsPage />} />
      <Route path="/downloads" element={<DownloadsPage />} />
      <Route path="/team" element={<TeamPage />} />
      <Route path="/partners" element={<PartnersPage />} />
      <Route path="/blog" element={<BlogPage />} />
      <Route path="/blog/:slug" element={<BlogPostPage />} />
      <Route path="/news" element={<NewsPage />} />
      <Route path="/privacy" element={<LegalPage kind="privacy" />} />
      <Route path="/terms" element={<LegalPage kind="terms" />} />
      <Route path="/accessibility" element={<LegalPage kind="accessibility" />} />
      <Route path="/acknowledgements" element={<LegalPage kind="acknowledgements" />} />
      <Route path="/licenses" element={<LegalPage kind="licenses" />} />
      <Route path="/credits" element={<LegalPage kind="credits" />} />
      <Route path="/press" element={<PressPage />} />
      <Route path="/media" element={<MediaPage />} />
      <Route path="/sitemap" element={<SitemapPage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/404" element={<StatusPage code={404} />} />
      <Route path="/500" element={<StatusPage code={500} />} />
      <Route path="/maintenance" element={<StatusPage code="maintenance" />} />
      <Route path="/coming-soon" element={<StatusPage code="soon" />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );

  const staged = reduce ? (
    routes
  ) : (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: bare ? 0 : 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: bare ? 0 : -6 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        {routes}
      </motion.div>
    </AnimatePresence>
  );

  return (
    <ShellChrome bare={bare}>
      {bare ? (
        staged
      ) : (
        <>
          <ReadProgress />
          <a className="skip-link" href="#main">
            Skip to content
          </a>
          <main id="main" className="page-main">
            {staged}
          </main>
          <SiteFooter />
        </>
      )}
    </ShellChrome>
  );
}

function ShellChrome({ children, bare = false }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'light';
    return localStorage.getItem('mv-theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('mv-theme', theme);
  }, [theme]);

  return (
    <>
      {!bare && (
        <TopNav
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        />
      )}
      {children}
    </>
  );
}

export default function App() {
  return (
    <HelmetProvider>
      <BrowserRouter>
        <ScrollToTop />
        <AnimatedRoutes />
      </BrowserRouter>
    </HelmetProvider>
  );
}
