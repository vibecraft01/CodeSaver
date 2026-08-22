# CodeSaver Website

This directory contains the complete CodeSaver landing page in a single file: `index.html`. CSS, JavaScript, and the SVG logo are embedded in the page, so no build step or package manager is required.

## Preview locally

From the repository root:

```bash
cd website
python -m http.server 8080
```

Open <http://localhost:8080> in a browser and stop the server with `Ctrl+C`.

## Deploy to Vercel

Install and authenticate the Vercel CLI once:

```bash
npm install --global vercel
vercel login
```

Deploy the site:

```bash
cd website
vercel --prod
```

On the first deployment, Vercel asks for the account/team and project name. Use the default settings: this is a static site with no build command and no output directory. Future deployments from this directory can use the same `vercel --prod` command.

The page links to the current stable CodeSaver CLI `v1.1.7` and Desktop `v1.0.4` GitHub releases. Update those URLs in `index.html` when new release assets are published.
