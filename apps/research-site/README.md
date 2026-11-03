# MediVault project site

This is a static overview of MediVault's purpose, local capabilities, safety limits, and deployment status. It contains no patient data and has no form backend.

## Status

The informational project site is deployed at <https://medivault-project-site.vercel.app/>. The MediVault health-record application is not deployed and has no public app URL. This site does not connect to an API or database. Vercel Authentication protects the deployment; access requires the authorized Vercel team or a temporary share link.

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
