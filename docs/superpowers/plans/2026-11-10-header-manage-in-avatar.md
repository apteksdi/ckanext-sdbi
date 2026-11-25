# Header Manage-in-Avatar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move logged-in Manage nav links into the avatar dropdown so Manage no longer overlaps the search icon.

**Architecture:** Template-only IA change. Remove Manage from `header_navigation_items.html`; append the same destinations (with existing sysadmin gating) into `header_account_menu.html` between Profile settings and Log out. Trim unused Manage CSS if present.

**Tech Stack:** CKAN Jinja templates (`ckanext-sdbi`), Bootstrap 3 dropdowns, `header_nav.css`.

## Global Constraints

- Avatar menu order: Profile → Profile settings → divider → Dashboard/Pages/Blog/Analytics → (sysadmin) Harvest/Admin/Google Forms → divider → Log out
- Same URLs and sysadmin gating as current Manage menu
- Guest header unchanged
- No full header redesign

## File map

| File | Role |
|------|------|
| `ckanext/sdbi/templates/snippets/header_navigation_items.html` | Remove Manage dropdown block |
| `ckanext/sdbi/templates/snippets/header_account_menu.html` | Add Manage links to avatar menu |
| `ckanext/sdbi/public/css/header_nav.css` | Remove unused `.site-header__manage` rules if any |
| `ckanext/sdbi/templates/header.html` | Bump CSS `?v=` if CSS changes |

---

### Task 1: Move Manage links into avatar menu

**Files:**
- Modify: `ckanext/sdbi/templates/snippets/header_navigation_items.html`
- Modify: `ckanext/sdbi/templates/snippets/header_account_menu.html`

- [ ] Step 1: Delete the `{% if c.userobj %}` Manage `<li class="dropdown site-header__manage">…` block from `header_navigation_items.html` (keep public nav + Tanggap as-is).
- [ ] Step 2: In `header_account_menu.html`, after Profile settings and before the logout divider, insert: divider; Dashboard, Pages, Blog, Analytics; if sysadmin: divider + Harvest, Admin, Google Forms; then existing logout divider + Log out.
- [ ] Step 3: Hard-refresh `/` logged in — main nav has no Manage; avatar menu lists the links; search icon is not overlapped.
- [ ] Step 4: Commit `SCOL-1234 move manage links into avatar dropdown`

### Task 2: Clean unused Manage CSS (if any)

**Files:**
- Modify: `ckanext/sdbi/public/css/header_nav.css` (only if `.site-header__manage` rules exist and are unused)
- Modify: `ckanext/sdbi/templates/header.html` (cache bust)

- [ ] Step 1: Grep for `site-header__manage`; remove dead rules only.
- [ ] Step 2: Bump `header_nav.css?v=` if CSS changed.
- [ ] Step 3: Commit only if files changed: `SCOL-1234 remove unused manage nav css`
