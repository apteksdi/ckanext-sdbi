# Unified BNPB-style header (account + main nav)

Date: 2026-11-07  
Repo focus: `ckanext-sdbi`  
Status: Approved for planning (brainstorm)

## Problem

Logged-in users see two stacked header bars:

1. `account-masthead` — Login / Admin / avatar / Dashboard / Settings / Logout (+ Pages/Blog from plugins)
2. `masthead` — Logo + Beranda / Dataset / Organisasi / … + search

That stack feels crowded (“bertumpuk”) and competes with the public nav. Goal: one header row, BNPB.go.id–like look, without losing account actions.

## Goals

- Single horizontal header for guest and authenticated users
- Visual language close to bnpb.go.id: navy bar, white logo lockup, light nav text, search on the right
- Account actions do not compete with main nav as a second full-width strip
- Role-gated links remain discoverable
- No duplicate Pages/Blog / Admin icons from plugin template chain

## Non-goals

- Renaming public menus to bnpb.go.id labels (Profil, Layanan, Berita, …)
- Changing homepage, MFA, or full-bleed pages that intentionally hide the site header (e.g. `/sebaran-bpbd`)
- Forking CKAN core templates beyond sdbi overrides

## Decisions (from brainstorm)

| Topic | Choice |
|--------|--------|
| Layout model | Approach 1: remove account strip; one masthead |
| Visual | BNPB-style navy single bar (reference screenshot) |
| Avatar dropdown | Profile, Settings, Logout only |
| Admin / Dashboard / Pages / Blog | Move into main nav (role-gated) |

## Information architecture

One row:

`[ BNPB logo ] … [ main nav ] … [ search ] [ Login | Avatar ▾ ]`

### Main nav (left → right, conceptual)

Public (always):

- Beranda
- Dataset
- Organisasi
- Aplikasi
- Peta BPBD
- Tanggap Darurat (dropdown when rooms exist / sysadmin)
- Bantuan

Role-gated:

- Dashboard — logged-in
- Analytics — logged-in (existing rule)
- Google Forms — sysadmin (existing rule)
- Admin — sysadmin
- Pages — sysadmin (or logged-in if product later widens; v1 = same audience as today’s pages icons, i.e. via sysadmin path unless pages plugin requires login-only — **v1: show Pages/Blog for any logged-in user** to match `ckanext-pages` account injection, which is not sysadmin-only)

Clarification locked in brainstorm Q3-A: Admin, Dashboard, Pages/Blog in main nav. Pages plugin injects for all logged-in users in `header_account_logged`; therefore **Pages/Blog = logged-in**, **Admin = sysadmin**.

### Account slot (far right)

- Guest: Login (Register only if `user_create` allowed)
- Logged-in: avatar (+ optional short display name) opening a dropdown:
  - Profile (`user.read`)
  - Settings (`user.edit`)
  - Logout

## Components (ckanext-sdbi only)

| Asset | Responsibility |
|--------|----------------|
| `templates/header.html` | Single `header.masthead`; no separate account-masthead strip |
| `templates/snippets/header_navigation_items.html` | Public + role-gated nav items |
| New snippet (e.g. `snippets/header_account_menu.html`) | Login vs avatar dropdown |
| `public/css/header_nav.css` | Navy bar, white links, dropdown, mobile collapse; bump `?v=` |
| Plugin block overrides | Neutralize `ckanext-pages` / `activity` account-bar injections so icons are not re-added into a removed strip / empty blocks |

### Plugin interaction

Template chain still resolves `header.html` via `activity → pages → showcase → sdbi`.

- Override / empty `header_account_logged` contributions from pages (Pages/Blog `<li>`s) by owning those links in main nav and ensuring pages’ `{{ super() }}` chain does not render a second account strip.
- Prefer: structure header so account UI is a dedicated block that pages does not wrap; keep `header_account_logged` empty or absent from the visible strip, and list Pages/Blog only in `header_navigation_items.html`.

## Visual / UX

- Background: navy aligned with current account strip / BNPB (`#044085` family)
- Logo: existing official white PNG URL (or local copy if hotlink fails); no dark plate needed on navy
- Nav: light text; Tanggap caret dropdown unchanged in behavior
- Search: icon-first or compact field; must not force a second row on desktop
- Optional thin gold/brown accent under the bar (subtle)
- Mobile: one hamburger panel containing main nav + account actions

## Edge cases

- Broken avatar → local placeholder; `alt=""` (avoid double username)
- Sysadmin vs user → Admin only for sysadmin; Pages/Blog for logged-in
- Full-bleed map/dashboard pages that `{% block header %}{% endblock %}` remain unchanged
- Keyboard: avatar dropdown open/close; Esc closes

## Test plan

- Guest / normal user / sysadmin on desktop and mobile
- Confirm single header height (no account-masthead)
- Pages/Blog appear once in main nav when logged in; not duplicated
- Admin visible only for sysadmin
- Avatar dropdown: Profile, Settings, Logout only
- Tanggap + avatar dropdowns do not fight for z-index
- Search still hits dataset search
- `/sebaran-bpbd` still hides site header as today

## Success criteria

- Logged-in header reads as one composition, not two stacked bars
- Visually recognizable as BNPB-style navy header
- Account actions reachable in ≤2 clicks via avatar menu
- No regression to public nav destinations

## Follow-ups (explicitly deferred)

- Group Pages/Blog/(Forms) under a “Konten” dropdown if nav length becomes an issue
- Bake BNPB logo into extension static files if Cloudflare blocks hotlink
- Match bnpb.go.id menu taxonomy (Profil / Layanan / …) — separate product decision
