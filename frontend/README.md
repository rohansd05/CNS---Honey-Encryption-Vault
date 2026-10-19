# HoneyVault Frontend

> **Owner:** Krrish (T3)  
> **Stack:** Vite · React 18 · TypeScript · Tailwind CSS v3 · shadcn/ui · TanStack Query · MSW

---

## Prerequisites

- Node.js ≥ 20
- The repo-root `.env` file must exist with at minimum:
  ```
  VITE_API_BASE_URL=http://localhost:8000
  VITE_USE_MOCKS=false          # set true only for offline UI work
  ```

---

## Getting Started

```bash
# From the repo root
cd frontend
npm install

# Dev server (reads .env from repo root via vite envDir: '..')
npm run dev          # → http://localhost:5173

# With real backend
VITE_USE_MOCKS=false npm run dev
```

---

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Type-check and build for production |
| `npm run lint` | ESLint with strict TS rules (zero warnings) |
| `npm run preview` | Preview the production build |
| `npm run format` | Prettier auto-format |

---

## Project Structure

```
src/
├── api/           # Typed API client, endpoints, TanStack Query hooks (K1.2)
├── components/    # Reusable UI components
│   └── layout/    # AppShell, Navbar, Footer
├── features/      # Page-level feature modules
│   ├── landing/   # LandingPage            (Chetan)
│   ├── auth/      # LoginPage, RegisterPage (Krrish)
│   ├── vault/     # VaultPage              (Krrish)
│   ├── share/     # SharePage              (Krrish)
│   ├── attack/    # AttackLabPage          (Chetan)
│   ├── evaluation/# EvaluationPage         (Chetan)
│   ├── admin/     # AdminPage              (Chetan)
│   └── about/     # AboutPage              (Chetan)
├── lib/
│   ├── auth.tsx   # AuthProvider, ProtectedRoute, AdminRoute
│   ├── theme.tsx  # ThemeProvider (dark/light, localStorage)
│   └── utils.ts   # cn() class merge utility
├── mocks/         # MSW browser worker + handlers (K1.2)
└── index.css      # Design system: ocean/honey theme, CSS variables
```

---

## Design System

- **Dark theme default:** `--bg #0B1220`, ocean slate surfaces
- **Honey accent:** `#F5A524`
- **Fonts:** Inter (UI), JetBrains Mono (code/sigil display)
- **Light mode:** toggle via top-right sun/moon button; preference in `localStorage` (UI pref only)
- CSS custom properties in `src/index.css` — no hardcoded colors anywhere

---

## Mock API (MSW) — optional, offline only

MSW mocks are **opt-in**: set `VITE_USE_MOCKS=true` in the repo-root `.env` only when
you need to develop the UI without a running backend. The default is `false` (real API).  
Full mock handlers (auth, vault, shares, admin) are added in **K1.2** (`feat/t3-api-auth`).  
The **mock-only** master password (`correct horse`) returns fake entries + sigil in the
offline mock; it has no effect on the real API.

---

## Branch Plan

| Branch | Owner | Status |
|---|---|---|
| `feat/t3-scaffold` | Krrish | ✅ K1.1 scaffold, design system, app shell |
| `feat/t3-api-auth` | Krrish | 🔜 K1.2 API client + MSW + auth context; K1.3 login/register |

---

## Key Rules (from AGENTS.md)

- **Master passwords are NEVER stored** anywhere (not localStorage, not sessionStorage, not Redux).
- The vault unlock screen must show the **sigil before any write** so users can spot a typo.
- `/vault/unlock` always returns 200 — the frontend must never infer correctness from the status code.
- Tokens live **in memory** (sessionStorage is allowed for tab reload only).
