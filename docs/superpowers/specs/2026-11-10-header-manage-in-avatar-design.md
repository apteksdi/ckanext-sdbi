# Header: Move Manage into avatar dropdown

Date: 2026-11-10  
Status: Approved (brainstorm)  
Related: `2026-11-07-unified-bnpb-header-design.md`

## Problem

After login, the masthead adds a **Manage** dropdown in the main nav plus search and the user chip (`avatar + display name`). On typical desktop widths those items collide: **Manage** overlaps the search icon.

## Goal

Keep one BNPB-style masthead row with no overlap when logged in, without shrinking public nav labels.

## Decision

**Option B — Move Manage into the avatar dropdown.**

- Public nav stays: Beranda, Dataset, Organisasi, Aplikasi, Peta BPBD, Tanggap Darurat, Bantuan.
- Right tools stay: search toggle + account slot.
- Manage links live under the avatar menu only.

## Avatar menu order

1. Profile  
2. Profile settings  
3. divider  
4. Dashboard, Pages, Blog, Analytics  
5. If sysadmin: divider, then Harvest, Admin, Google Forms  
6. divider  
7. Log out  

URLs and sysadmin gating match the current Manage menu in `header_navigation_items.html`.

## Out of scope

- Guest header changes  
- Mobile hamburger IA redesign (beyond removing Manage from the pill list so it also disappears from the collapse drawer)  
- Renaming “Manage” as a visible section label in the dropdown  
- Full header visual redesign  

## Implementation sketch

1. Remove the Manage `<li class="dropdown site-header__manage">` block from `snippets/header_navigation_items.html`.  
2. Add the same links (and `manage_active` path logic only if needed for styling — optional) into `snippets/header_account_menu.html` between profile settings and logout.  
3. Drop unused `.site-header__manage` CSS if nothing else depends on it; bump `header_nav.css` cache query if any related rule changes.  
4. Manual check: logged-in non-sysadmin and sysadmin at ~1280px and ~992px — no overlap; search opens; avatar menu items work.

## Success criteria

- Logged-in header: no Manage in main nav; no overlap with search.  
- All former Manage destinations reachable from the avatar menu.  
- Sysadmin-only links still sysadmin-only.  
- Logged-out header unchanged.
