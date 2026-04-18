# Vercel Node.js version (clear “Node.js Version Override”)

## Where to set it in the dashboard

Node.js is **not** under **General**. Use:

1. [Vercel Dashboard](https://vercel.com/dashboard) → select the **llmhive** project  
2. **Settings** (left sidebar)  
3. **Build and Deployment**  
4. **Node.js Version** → choose **22.x** → **Save**

Official steps: [Setting the Node.js version in project settings](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions#setting-the-node.js-version-in-project-settings).

## What this repo already does

- `package.json` has `"engines": { "node": "22.x" }`, which Vercel uses and can **override** the dropdown (see [Version overrides in package.json](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions#version-overrides-in-package.json)).
- `.nvmrc` is `22` for local tooling.

Set the dashboard to **22.x** as well so the UI matches `engines`.

## Yellow banner: “Production Overrides” vs “Project Settings”

On **Build and Deployment → Node.js Version** you may see two rows:

| Row | Meaning |
| --- | --- |
| **Project Settings** | The Node major Vercel will use for **new** builds (set this to **22.x**). |
| **Production Overrides** | The Node major that **the currently promoted Production deployment** was built with. You do not pick this separately—it reflects that deployment. |

If Production shows **24.x** and Project Settings show **22.x**, the live site was built with Node 24 (e.g. an older deploy or before `engines` was pinned). **Redeploy Production** from a commit that has `"engines": { "node": "22.x" }` (this repo). After the new deployment is live, Production Overrides should show **22.x** and the warning typically goes away.

**Redeploy:** **Deployments** tab → open the latest deployment from `main` → **⋯** → **Redeploy** (or push a commit to `main`).
