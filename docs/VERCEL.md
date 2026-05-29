# Vercel Web Dashboard — Making Changes

The public dashboard is the **`flood-webapp/`** folder. It's a plain static site
(`index.html` + `app.js` + `style.css` + `img/`) — there is no build step. Vercel
serves those files exactly as they are.

## How deployment works

```
You edit flood-webapp/  ──►  git push to GitHub  ──►  Vercel auto-builds & deploys
        (local)              (paopao-GG/FloodSense)        (your-site.vercel.app)
```

Vercel is connected to the GitHub repo **`paopao-GG/FloodSense`** and redeploys
**automatically every time you push to `main`**. You do not click anything on
Vercel for a normal update — pushing is the deploy.

> 🔑 **Critical Vercel setting — the Root Directory.**
> This repo keeps the website in a *subfolder* (`flood-webapp/`), not at the repo
> root. So in Vercel the project's **Root Directory must be set to `flood-webapp`**
> (Vercel → Project → **Settings → Build & Deployment → Root Directory**).
> If that's ever blank or wrong, the site deploys empty / 404s.
> **Do not rename or move the `flood-webapp/` folder** — that's the path Vercel
> builds from. See the root [README](../README.md#do-not-move-these--server-critical-paths).

---

## The everyday workflow — change something on the site

```bash
cd /home/ralphazanza/flood_project

# 1. edit the files in flood-webapp/  (index.html / app.js / style.css / img/)

# 2. preview locally before pushing (optional but recommended)
cd flood-webapp
python3 -m http.server 8080
#   open http://localhost:8080  → check it looks right → Ctrl+C to stop
cd ..

# 3. commit and push — this triggers the Vercel deploy
git add flood-webapp/
git commit -m "tweak: <what you changed>"
git push origin main
```

Within ~30–60 seconds Vercel builds and the live URL updates. Watch progress at
[vercel.com](https://vercel.com) → your project → **Deployments**.

---

## What lives where in `flood-webapp/`

| File | What to edit it for |
|------|---------------------|
| `index.html` | Page structure, text, titles, authors, the three nav tabs (Dashboard / Data Analysis / Rationale). |
| `style.css`  | Colors, fonts, layout, spacing. |
| `app.js`     | Live data logic: the Firebase config, which fields are read, the charts, the snapshot gallery, the stale-data detector. |
| `img/`       | Logos (`iiee.png`, `buceng.png`) and the favicon. Referenced by **relative** paths from `index.html` — keep them inside `flood-webapp/img/`. |

> The `img/` folder at the **repo root** is just the original/source logos. The site
> only serves `flood-webapp/img/`. If you swap a logo, replace the copy **inside
> `flood-webapp/img/`**.

---

## Changing the data source (Firebase)

The dashboard reads from Firebase. The connection lives at the top of
[`flood-webapp/app.js`](../flood-webapp/app.js):

```js
const firebaseConfig = {
  apiKey:      "…",
  databaseURL: "https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app",
  …
};
```

- The webapp listens to two nodes: **`flood_telemetry`** (live readings) and
  **`snapshots`** (the 6-hour image history).
- These field names must match what the Pi writes in
  [`Flood_system_final.py`](../Flood_system_final.py) (`send_firebase_payload`):
  `status`, `water_depth_gap_cm`, `temperature_c`, `humidity_percent`,
  `cnn_confidence`, `epoch_timestamp`, `location`, `live_snapshot_url`,
  `flood_snapshot_url`. **If you rename a field on the Pi, rename it here too**, or
  that card/chart shows `—`.
- If you point the webapp at a different Firebase project, update **both**
  `app.js` (here) **and** `FIREBASE_BASE` in `Flood_system_final.py`.

---

## First-time Vercel setup (only if it isn't connected yet)

1. Go to [vercel.com](https://vercel.com) and sign in **with GitHub**.
2. **Add New → Project** → import the **`paopao-GG/FloodSense`** repo.
3. **Root Directory → `flood-webapp`** (this is the important one — see the box above).
4. Framework Preset: **Other** / Static. No build command, no output directory.
5. **Deploy.** Vercel gives you a `…vercel.app` URL.

Custom domain (optional): Project → **Settings → Domains → Add**, then follow the DNS
instructions. SSL is automatic.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Deploy succeeds but site is blank / 404 | Root Directory not set to `flood-webapp`. Fix it in Settings → Build & Deployment, then redeploy. |
| Push didn't trigger a deploy | You pushed to a branch other than the one Vercel watches (`main`), or the GitHub↔Vercel link broke. Check Vercel → Settings → Git. |
| Cards/charts show `—` forever | Field-name mismatch between `app.js` and the Pi payload, or the wrong `databaseURL`. |
| Banner stuck on `CONNECTING…` | Wrong `databaseURL` in `app.js`, or Firebase read rules blocking the browser. See [DEPLOYMENT.md](DEPLOYMENT.md) Step 11. |
| Logo/image broken | Image isn't in `flood-webapp/img/`, or the `src` path in `index.html` is wrong. |
| Old version still showing | Hard-refresh (Ctrl+Shift+R); confirm the latest deploy is "Ready" in Vercel → Deployments. |

For full first-time deployment (Firebase + Cloudinary + Vercel together), see
[DEPLOYMENT.md](DEPLOYMENT.md).
