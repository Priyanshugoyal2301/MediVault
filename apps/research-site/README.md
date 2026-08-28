# MediVault Research Site

Production research website for **MediVault** — the institutional face of the project.

> Not the product demo SPA (`apps/web`). This site is for faculty review, competitions, and portfolio publication.

## Quick start

```bash
cd apps/research-site
npm install
npm run dev      # http://localhost:5173
npm run build    # → dist/ static export
npm run preview  # preview production build
```

## Content source of truth

`src/content/site.js` holds all narrative copy, metrics, publications, FAQ, legal text, and navigation.  
Claims stay aligned with `docs/PRESENTATION_CLAIMS.md` and Plan B/C reports.

## Structure

```
src/
  content/site.js       # All page content
  components/           # Layout chrome, SEO, hero canvases
  pages/                # Route views
  styles/               # Tokens + global + layout
public/                 # favicon, robots, sitemap
dist/                   # Production build output
```

## Deploy (static)

`npm run build` emits static assets in `dist/`. Host with any static CDN (Vercel, Netlify, GitHub Pages, Nginx).

Set a real canonical domain by updating `site.domain` in `src/content/site.js` and matching entries in `public/sitemap.xml` / `index.html`.

## Accessibility & SEO

- Skip link, semantic landmarks, focus styles, reduced-motion canvas gates
- react-helmet-async titles/descriptions, Open Graph, JSON-LD ResearchProject
- `public/sitemap.xml` + `robots.txt`
