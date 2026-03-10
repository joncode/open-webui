# Jaco to Agent1 / Agent1 (QA) Rename

Plan for renaming the app display name from "Jaco" to "Agent1" and staging from "Jaco (QA)" to "Agent1 (QA)", plus optional production URL and staging infra changes. Use this when you're ready to do the rename.

---

## Where the app name comes from

At runtime the visible name is **$WEBUI_NAME** from the store, which is set from the backend config when available; otherwise it falls back to **APP_NAME** from [src/lib/constants.ts](src/lib/constants.ts). So changing the default name and the deployed name requires edits in both app code and k8s config.

---

## 1. Display name – must change (4 places)

| Location | Current | New |
|----------|---------|-----|
| [src/lib/constants.ts](src/lib/constants.ts) | `APP_NAME = 'Jaco'` | `'Agent1'` |
| [src/app.html](src/app.html) | `<title>Jaco</title>` | `<title>Agent1</title>` |
| [k8s/base/jaco-configmap.yaml](k8s/base/jaco-configmap.yaml) | `WEBUI_NAME: "Jaco"` | `"Agent1"` |
| [k8s/staging/jaco-configmap.yaml](k8s/staging/jaco-configmap.yaml) | `WEBUI_NAME: "Jaco (QA)"` | `"Agent1 (QA)"` |

These four edits are enough for production UI/tab title "Agent1" and staging "Agent1 (QA)". All other UI (auth, error, admin, workspace titles, shared chat) uses `$WEBUI_NAME` or i18n `{{WEBUI_NAME}}`, so they update automatically once the backend sends the new name (or default from constants).

---

## 2. UI copy that says "Jaco" (2 strings in 1 file)

[src/lib/components/chat/TopicSplitAlert.svelte](src/lib/components/chat/TopicSplitAlert.svelte):

- Line 75: **"Jaco's about to split"** → "Agent1's about to split"
- Line 87: **"Don't do it, Jaco →"** → "Don't do it, Agent1 →"

---

## 3. Docs / README (optional)

- [README.md](../README.md) line 183: "Let's make Jaco amazing" → "Agent1"
- [docs/performance-optimizations.md](performance-optimizations.md): title/references "Jaco" → "Agent1" if desired

---

## 4. Staging hostname / namespace ("Jaco-stg" → "Agent1-stg")

Display name is covered in section 1. For full staging rename (URL and k8s identity):

- Host: `jaco-stg.manifest.network` → `agent1-stg.manifest.network` in [k8s/staging/jaco-configmap.yaml](../k8s/staging/jaco-configmap.yaml) and [k8s/staging/jaco-ingress.yaml](../k8s/staging/jaco-ingress.yaml)
- Namespace: `jaco-stg` → `agent1-stg` across staging deployments, services, ingress, PVC, secrets, backup scripts
- DB/user names in examples: `jaco_stg`, `jaco-stg-backups` → equivalent agent1-stg names

Larger change; do as a separate pass if needed.

---

## 5. Production URL: agent1.manifest.network → app on current server

To have **https://agent1.manifest.network** serve the app on the current server (same box/cluster as jaco today):

### 5a. DNS (outside this repo)

- In DNS for **manifest.network**, add an **A record** (or CNAME) for **agent1.manifest.network** pointing to the **current server box IP** (same as jaco.manifest.network or cluster ingress IP).
- Both hostnames can point to the same IP during transition.

### 5b. Kubernetes (in this repo)

| Location | Change |
|----------|--------|
| [k8s/base/jaco-ingress.yaml](../k8s/base/jaco-ingress.yaml) | `host: jaco.manifest.network` → `host: agent1.manifest.network` |
| [k8s/base/jaco-configmap.yaml](../k8s/base/jaco-configmap.yaml) | Replace all **jaco.manifest.network** with **agent1.manifest.network** in: `WEBUI_URL`, `CORS_ALLOW_ORIGIN`, and inside `CONTENT_SECURITY_POLICY` (the `connect-src` / `wss://` URL). |

Total: 2 files, 4 string replacements (1 in ingress, 3 in configmap).

After applying k8s and DNS propagation, https://agent1.manifest.network will hit the same app. If using Cloudflare, add the new hostname there and keep TLS (Full or Full strict).

---

## 6. What not to change (by default)

- **Tailwind theme** `jaco: { red, denim, sunflower, ... }` in [tailwind.config.js](../tailwind.config.js) and classes like `jaco-sunflower`, `jaco-red` in Svelte: design tokens, not product name; leave unless doing a full theme rename.
- **K8s resource names** in production (namespace `jaco`, `app: jaco`, image `jaco:latest`, etc.): only change if you want internal identity to match "Agent1".
- **Comments** ("Jaco Step Mode API", "jaco-step"): optional; no impact on user-facing name.

---

## Summary

| Category | Places to change |
|----------|------------------|
| **Display name (required)** | 4 (constants.ts, app.html, base configmap, staging configmap) |
| **UI copy (TopicSplitAlert)** | 1 file, 2 strings |
| **README / docs** | 1–2 files (optional) |
| **Staging hostname/namespace** | Many k8s + scripts (optional; separate pass) |
| **Production URL → agent1.manifest.network** | 1 DNS record (external) + 2 files (ingress + configmap) |

Minimum for "app name Agent1, staging name Agent1 (QA)": **4 edits**. Add TopicSplitAlert and/or URL/DNS when ready.
