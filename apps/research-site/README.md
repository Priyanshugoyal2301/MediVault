# MediVault project site

This is a static overview of MediVault's purpose, local capabilities, safety limits, and deployment status. It contains no patient data and has no form backend.

## Status

The site and the MediVault application are not deployed. The canonical domain is intentionally unset; do not invent or publish a deployment URL. After deployment, set `site.domain`, add absolute canonical URLs to the sitemap, and update the deployment section in the root README and project About page with verified links.

## Local development

Requirements: Node.js 20.19+ or 22.12+.

```bash
npm ci
npm run dev
npm run build
npm run preview
```

The production build is emitted to `dist/`. All narrative content lives in `src/content/site.js`; the About page is in `src/pages/Pages.jsx`.

## Hosting configuration

`vercel.json` configures a Vite static build for a future Vercel project. The expected root directory is `apps/research-site`; the build command is `npm run build`, and the output directory is `dist`. No Vercel project is currently linked. The site is informational only and does not deploy the product API or database.

Do not add credentials, real patient examples, private contact details, fabricated service links, or unverified clinical claims to this site.
