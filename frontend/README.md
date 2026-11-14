# Wedding Attendance — Frontend SPA (`wa-amplify`)

This directory contains the Single Page Application (SPA) frontend for the Wedding Attendance & RSVP Guestbook, using the HTML5 History API (`/`, `/rsvp`, `/guestbook`, and `/ticket/<guestId>`).

---

## 🧭 Client-Side SPA Routes

| Route | View | Description |
|---|---|---|
| `/` | Overview | Full portal with Stats HUD, RSVP Form, and Guestbook Feed |
| `/rsvp` | RSVP Form | Focused view for submitting guest attendance |
| `/guestbook` | Digital Guestbook | Focused guestbook feed with clickable **Pass** links |
| `/ticket/<guestId>` | Digital Pass | Direct URL to a guest attendance pass (e.g. `/ticket/WA-9B41FA`) |

> Static assets in `index.html` use root-relative paths (`/style.css`, `/app.js`) so refreshing nested routes such as `/ticket/WA-9B41FA` resolves from the site root.

---

## 🔀 SPA Rewrite Rule Setup (AWS Amplify)

Without a rewrite rule, refreshing a client-side route like `/rsvp` or `/ticket/WA-9B41FA` on CloudFront/Amplify returns `404 Not Found` because those paths do not exist as static HTML files.

### Setup via AWS Amplify Console

1. Open **AWS Amplify** → select app **`wa-amplify`**.
2. In the left sidebar, go to **Hosting** → **Rewrites and redirects**.
3. Click **Manage redirects** to open the **`redirects`** JSON editor.
4. Replace or save the JSON rules with one of the following valid SPA rewrite configurations:

   - **Option A — True SPA `200 (Rewrite)` (Excludes static assets so CSS/JS still load):**
     ```json
     [
       {
         "source": "</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|ttf|map|json)$)([^.]+$)/>",
         "status": "200",
         "target": "/index.html"
       }
     ]
     ```

   - **Option B — Amplify Default `404 (Rewrite)` (`404-200`, serves existing files directly and falls back to `/index.html`):**
     ```json
     [
       {
         "source": "/<*>",
         "status": "404-200",
         "target": "/index.html"
       }
     ]
     ```

5. Click **Save**.

> **Important:** Do **not** combine `"source": "/<*>"` with `"status": "200"`, as that rewrites `/style.css` and `/app.js` requests into `index.html`. Use the asset-exclusion regex with `"200"`, or use `"404-200"` with `"/<*>"`.

### Setup via AWS CLI (Optional)

```powershell
aws amplify update-app `
  --app-id <YOUR_APP_ID> `
  --region us-east-1 `
  --custom-rules '[{"source":"</^[^.]+$|\\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|ttf|map|json)$)([^.]+$)/>","target":"/index.html","status":"200"}]'
```

---

## ✅ Verify SPA Rewrite Behavior

1. Open your Amplify app URL and click **Configure API** (gear icon) to connect your `prod` API Gateway Invoke URL (`API Gateway Live`).
2. Click **Guestbook** (`/guestbook`) or open a guest **Pass** (`/ticket/WA-...`).
3. Press **Refresh (`F5`)** in the browser — the page must render `/index.html` cleanly with `/style.css` and `/app.js` loaded (no `404` page).
