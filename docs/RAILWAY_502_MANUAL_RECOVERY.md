# Railway HTTP 502 — remaining blocker (logs only)

**Status:** GitHub→Railway auto-deploy is **connected and working**.  
**Canonical backend:** `https://web-production-ad6a36.up.railway.app` → still **502**.  
**Main tip:** `df7e4e9e83ff134bd6bbc2daa9cc849ac23f5a9f`

---

## Proven facts (no token required)

| Fact | Evidence |
|---|---|
| Repo watched | `dialloao494-design/plateforme-sante-guinee` |
| Branch watched | `main` |
| Railway project | `sunny-illumination` (`1ae125c3-84d4-4503-adf8-7b4b0eaf691e`) |
| Service | `web` (`c4350189-ecd8-4291-bbf2-60ae517f0894`) |
| Public URL | `web-production-ad6a36.up.railway.app` |
| Auto-deploy | GitHub commit status `sunny-illumination - web` goes pending → success → failure on every `main` push |
| Latest deploy | `df7e4e9` — success at `21:56:38Z`, failure at `21:56:48Z` (~10s crash after start) |
| Code on main | Migration `20260730_0025_ensure_session_version`, entrypoint migrate-then-serve, `railway.json` clears stale `startCommand` |

Agent can trigger deploys by pushing `main`. Agent **cannot read Railway build/runtime logs** without dashboard access.

---

## Single action required (no coding, no token)

1. Open this exact failed deployment:  
   https://railway.com/project/1ae125c3-84d4-4503-adf8-7b4b0eaf691e/service/c4350189-ecd8-4291-bbf2-60ae517f0894?id=79b93981-98ea-4d7d-acea-f8d66cedfc8b&environmentId=00e222de-cf54-4d1d-a813-457eac4839cc
2. Click **Deploy Logs** (or **HTTP Logs** / **Build Logs** if Deploy is empty — use the panel that shows the red error).
3. Copy the **last 80 lines** (redact secrets if any) and paste them into the Cursor agent chat.

That is the only step. Do **not** recreate the database. Do **not** delete users. After the log paste, the agent will fix the next root cause and push to `main` again (auto-deploy will pick it up).
