# Redesign Beranda Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Halaman `/` dirender oleh template beranda baru yang berdiri sendiri (header, isi, footer khusus) mengikuti gambar referensi, tanpa mengubah tampilan halaman lain.

**Architecture:** `templates/home/index.html` meng-extend CKAN `base.html` dan meng-override `{% block page %}` (jadi `page.html`/`header.html`/`footer.html` global tidak dirender). Markup dipecah ke `templates/home/beranda/*.html` per bagian. Gaya di `public/css/beranda.css` (semua selector di bawah `.sdbi-home`), perilaku di `public/js/beranda.js`, keduanya hanya di-link dari `home/index.html`.

**Tech Stack:** CKAN 2.10 Jinja2 templates, CSS polos, JS vanilla, Font Awesome bawaan CKAN (`/base/vendor/fontawesome-free/css/all.css`), Bootstrap 3 JS bawaan (dropdown/modal).

**Spec:** `docs/superpowers/specs/2026-11-25-beranda-redesign-design.md`

## Global Constraints

- Tidak mengubah file yang dirender halaman lain: `header.html`, `footer.html`, `page.html`, `public/css/header_nav.css`, snippet `snippets/header_*` — kecuali pemindahan survey modal di Task 5 (output HTML footer global harus identik).
- Setiap selector di `beranda.css` diawali `.sdbi-home` (termasuk di dalam `@media`); `@keyframes` dinamai `sdbi-home-*`. Semua class baru di template diawali `sdbi-home`.
- Logo: `h.url_for_static('/img/logo-bnpb-header.png')`. Hero: `/base/images/Dokumentasi-Erupsi-semeru.JPG`.
- Copy hero: judul "Satu Data untuk Indonesia Tangguh Bencana"; sub "Akses data, informasi, dan statistik kebencanaan Indonesia secara terintegrasi untuk mendukung pengambilan keputusan dan meningkatkan kesiapsiagaan."; placeholder cari "Cari dataset, dashboard, atau informasi bencana…".
- Iframe peta: `https://gis.bnpb.go.id/dev/map`. Tidak ada data bencana statis/palsu.
- Warna: biru utama `#0b4a8b`, biru gelap `#08305c`, oranye aksen `#f58220`.
- Breakpoint mobile: `max-width: 767px`; tablet `max-width: 991px`.

## Review Focus

- Halaman lain (`/dataset`, `/organization`, `/bantuan`, `/tanggap-darurat`) tidak memuat `beranda.css` dan tampil sama seperti sebelumnya → dicek di `scripts/check_beranda.py` (Task 1).
- `sdbi_tanggap_rooms()` kosong → panel menampilkan empty state, bukan kotak kosong (Task 3).
- `most_recent_datasets` mengembalikan dataset tanpa `notes`/organisasi atau list kosong → kartu tetap rapi / empty state (Task 4).
- Pengguna login vs anonim → header menampilkan dropdown avatar vs tombol "Masuk" (Task 2, dicek manual dengan login).
- Layar ≤767px → tidak ada scroll horizontal, menu jadi hamburger (Task 5).

---

### Task 1: Kerangka halaman + guard isolasi CSS

**Files:**
- Create: `ckanext/sdbi/templates/home/index.html`
- Create: `ckanext/sdbi/public/css/beranda.css`
- Create: `ckanext/sdbi/public/js/beranda.js` (kosong dulu, IIFE)
- Create: `ckanext/sdbi/tests/test_beranda_css.py`
- Create: `scripts/check_beranda.py`

**Interfaces:**
- Produces: `home/index.html` dengan `<div class="sdbi-home">` berisi, berurutan, `{% include 'home/beranda/header.html' %}`, `<main>` dengan include `hero.html`, `peta.html`, `kategori.html`, `konten.html`, `ekosistem.html`, lalu `footer.html` — semua di `templates/home/beranda/`. Task berikut membuat file-file itu; di Task 1 buat sebagai file kosong agar include tidak error.
- Produces: `scripts/check_beranda.py [base_url]` — dipakai verifikasi di semua task.

- [ ] **Step 1: Tulis test guard CSS (unittest stdlib, tanpa pytest)**

`test_beranda_css.py`: buang komentar `/* */`, ambil setiap prelude sebelum `{` yang bukan `@media`/`@supports`/`@keyframes`/`from`/`to`/persentase; split koma; assert tiap selector `.strip().startswith('.sdbi-home')`. Test kedua: setiap `@keyframes <name>` → `name.startswith('sdbi-home')`. Test ketiga: `beranda.css` tidak mengandung `!important` lebih dari 20 kali (rem pemaksaan).

- [ ] **Step 2: Jalankan — harus FAIL karena file belum ada**

Run: `cd ckanext-sdbi && python3 -m unittest ckanext.sdbi.tests.test_beranda_css -v`
Expected: FAIL / error file tidak ditemukan.

- [ ] **Step 3: Buat `home/index.html`, `beranda.css`, `beranda.js`, dan 7 partial kosong**

`index.html`: `{% extends "base.html" %}`; `{% block subtitle %}Beranda{% endblock %}`; di `{% block custom_styles %}{{ super() }}` link `/base/vendor/fontawesome-free/css/all.css` dan `/css/beranda.css?v=1`; di `{% block page %}` markup wrapper di atas + `<script src="/js/beranda.js?v=1" defer>`. Jangan override `block scripts` (JS CKAN tetap dimuat). `beranda.css` berisi reset terbatas di bawah `.sdbi-home` (font Inter/system, `box-sizing`, `a` color, `.sdbi-home-container{max-width:1200px;margin:0 auto;padding:0 24px}`).

- [ ] **Step 4: Tulis `scripts/check_beranda.py`**

Stdlib `urllib`. Default base `http://localhost:8080`. Cek: GET `/` status 200, berisi `class="sdbi-home"` dan `/css/beranda.css`, TIDAK berisi `site-header__logo-lockup` (header global). Untuk `/dataset`, `/organization`, `/bantuan`, `/tanggap-darurat`: status 200 dan TIDAK berisi `beranda.css` maupun `sdbi-home`. Argumen opsional `--expect TEXT` (bisa berulang) untuk memastikan teks muncul di `/`. Exit 1 dengan daftar kegagalan.

- [ ] **Step 5: Jalankan test + check**

Run: `python3 -m unittest ckanext.sdbi.tests.test_beranda_css -v && docker restart ckan && sleep 15 && python3 scripts/check_beranda.py`
Expected: semua OK. (CKAN cache template; restart diperlukan saat file template baru dibuat.)

- [ ] **Step 6: Commit**

```bash
git add ckanext/sdbi/templates/home/index.html ckanext/sdbi/templates/home/beranda ckanext/sdbi/public/css/beranda.css ckanext/sdbi/public/js/beranda.js ckanext/sdbi/tests/test_beranda_css.py scripts/check_beranda.py
git commit -m "SCOL-1234 add standalone beranda skeleton with css isolation guard"
```

### Task 2: Header beranda

**Files:**
- Modify: `ckanext/sdbi/templates/home/beranda/header.html`
- Modify: `ckanext/sdbi/public/css/beranda.css`, `ckanext/sdbi/public/js/beranda.js`

**Interfaces:**
- Produces: class `sdbi-home-header`, `sdbi-home-nav`, `sdbi-home-burger` (button, `aria-expanded`), `sdbi-home-nav.is-open`.

- [ ] **Step 1: Tulis markup header**

Putih, sticky, tinggi ~72px. Kiri: logo (`h.url_for('home.index')`). Tengah: menu dengan link yang sama persis seperti `snippets/header_navigation_items.html` (Beranda aktif dengan garis bawah biru; Tanggap Darurat dropdown berisi `h.sdbi_tanggap_rooms()` → `/tanggap-darurat?jenis={{ room.slug }}` label `room.label`, divider, Kelola Dashboard, Panduan hosting — tampilkan dua link terakhir hanya jika sebelumnya juga tanpa syarat). Kanan: tombol ikon cari (link ke `h.url_for('dataset.search')`), lalu jika `c.userobj` dropdown avatar dengan item & kondisi sysadmin persis seperti `snippets/header_account_menu.html`; jika anonim tombol oranye pill "Masuk" → `user.login`. Dropdown memakai `data-toggle="dropdown"` Bootstrap dengan class `dropdown-menu` dibungkus elemen `.sdbi-home-dropdown`.

- [ ] **Step 2: CSS header + hamburger ≤991px; JS toggle `is-open` dan `aria-expanded` di `beranda.js`**

- [ ] **Step 3: Verifikasi**

Run: `python3 -m unittest ckanext.sdbi.tests.test_beranda_css && python3 scripts/check_beranda.py --expect "Sebaran BPBD" --expect "Masuk"`
Expected: OK. Manual: login sebagai sysadmin, buka `/`, dropdown avatar memuat Harvest & Admin.

- [ ] **Step 4: Commit** — `SCOL-1234 beranda header`

### Task 3: Hero, strip statistik, peta + Tanggap Darurat Aktif

**Files:**
- Modify: `templates/home/beranda/hero.html`, `templates/home/beranda/peta.html`, `beranda.css`

- [ ] **Step 1: Hero** — background `/base/images/Dokumentasi-Erupsi-semeru.JPG` cover + gradient kiri `rgba(8,48,92,.92)`→transparan; copy dari Global Constraints; form GET ke `h.url_for('dataset.search')` field `q` dengan tombol oranye "Cari"; tombol outline putih "Lihat Peta Bencana" (`#peta`, ikon `fa-map`) dan "Jelajahi Dataset" (`dataset.search`, ikon `fa-chart-bar`).

- [ ] **Step 2: Strip statistik** — kartu putih overlap hero (margin-top negatif), 4 item: `h.sdbi_theme_dataset_count()` "Total Dataset" (`fa-database`), `stats.provinsi_terhubung` "Provinsi Terhubung" (`fa-map-marker-alt`), `stats.kabupaten_kota_terhubung` "Kabupaten/Kota" (`fa-city`), `stats.kementerian_lembaga_terhubung + stats.ngo_terhubung` "Instansi Terintegrasi" (`fa-users`), di mana `stats = h.sdbi_theme_connected_statistics()`. Angka diformat ribuan dengan titik (`'{:,}'.format(n).replace(',', '.')`).

- [ ] **Step 3: Peta** — `<section id="peta">` grid 2 kolom (≈ 2.4fr / 1fr). Kiri: judul "Peta Sebaran Bencana di Indonesia", deskripsi "Pantau kejadian bencana terkini di seluruh wilayah Indonesia.", iframe `https://gis.bnpb.go.id/dev/map` tinggi 420px (`loading="lazy"`, `title`), tombol biru "Buka Peta Lengkap" → URL iframe `target="_blank" rel="noopener"`. Kanan: kartu "Tanggap Darurat Aktif" dengan badge oranye "Aktif"; loop `h.sdbi_tanggap_rooms()` → item ikon `fa-exclamation-triangle`, label, link. Kosong → "Belum ada tanggap darurat aktif." + link "Kelola Dashboard" hanya jika `c.userobj and c.userobj.sysadmin`. Footer kartu: link "Lihat Semua" → `/tanggap-darurat`.

- [ ] **Step 4: Verifikasi**

Run: `python3 -m unittest ckanext.sdbi.tests.test_beranda_css && python3 scripts/check_beranda.py --expect "Indonesia Tangguh Bencana" --expect "Total Dataset" --expect "gis.bnpb.go.id/dev/map" --expect "Tanggap Darurat Aktif"`
Expected: OK. Manual: kosongkan rooms (atau cek lokal yang kosong) → empty state tampil.

- [ ] **Step 5: Commit** — `SCOL-1234 beranda hero, stats, map`

### Task 4: Kategori, Dataset Terbaru, Layanan & Dashboard

**Files:**
- Modify: `templates/home/beranda/kategori.html`, `templates/home/beranda/konten.html`, `beranda.css`

- [ ] **Step 1: Kategori** — judul "Kategori Dataset" dengan aksen garis oranye, link kanan "Lihat Semua" → `dataset.search`. 6 kartu (grid 6 kolom → 3 → 2), masing-masing dengan warna latar pastel berbeda:

| Label | URL | Ikon |
|---|---|---|
| Kejadian Bencana | `/dataset/?q=kejadian` | `fa-wave-square` |
| Dampak Bencana | `/dataset/?q=dampak` | `fa-users` |
| Mitigasi & Kesiapsiagaan | `/dataset/?fase=prabencana` | `fa-shield-alt` |
| Penanganan Darurat | `/dataset/?fase=saatbencana` | `fa-truck` |
| Pemulihan Pascabencana | `/dataset/?fase=pascabencana` | `fa-hands-helping` |
| Data Lainnya | `/dataset/` | `fa-database` |

- [ ] **Step 2: Dataset Terbaru** (kolom kiri ~45%) — `h.sdbi_theme_most_recent_datasets(3)`; tiap item: thumbnail (`/base/images/placeholder-image.png` bila tak ada gambar), badge "Dataset Terbaru" pada item pertama, judul → `h.url_for('dataset.read', id=pkg.name)`, nama organisasi (`pkg.organization.title` bila ada), `h.get_dataset_views_by_name(pkg.name)` views dan `h.get_dataset_downloads_by_name(pkg.name)` downloads (cek bentuk return kedua helper di `plugin.py` dan ambil angka totalnya). List kosong → "Belum ada dataset."

- [ ] **Step 3: Layanan & Dashboard** (kolom kanan) — grid 3 kartu yang bisa digeser horizontal (scroll-snap, tanpa JS carousel) berisi 6 item dari `layout1.html` lama (judul, deskripsi singkat, URL, gambar `/base/images/{NTT.png,Karhutla.png,sumatera.png,dashboard-cianjur.png,Lewotobi.PNG,heli.JPG}`), `<a target="_blank" rel="noopener">`. Link "Lihat Semua" → `h.url_for('showcase_blueprint.index')`.

- [ ] **Step 4: Verifikasi**

Run: `python3 -m unittest ckanext.sdbi.tests.test_beranda_css && python3 scripts/check_beranda.py --expect "Kategori Dataset" --expect "fase=prabencana" --expect "Dataset Terbaru" --expect "Layanan &amp; Dashboard"`
Expected: OK.

- [ ] **Step 5: Commit** — `SCOL-1234 beranda categories, latest datasets, services`

### Task 5: Ekosistem, footer, survey, responsif

**Files:**
- Modify: `templates/home/beranda/ekosistem.html`, `templates/home/beranda/footer.html`, `beranda.css`
- Create: `ckanext/sdbi/templates/snippets/survey_modal.html`
- Modify: `ckanext/sdbi/templates/footer.html` (pindahkan modal survey + `<script>` `showSurveyPopup` ke snippet, ganti dengan `{% include 'snippets/survey_modal.html' %}`)

- [ ] **Step 1: Snapshot footer global sebelum refactor**

Run: `curl -s http://localhost:8080/dataset | sed -n '/<footer/,$p' > $SCRATCH/footer_before.html` (`$SCRATCH` = scratchpad session)

- [ ] **Step 2: Pindahkan survey ke snippet, restart, bandingkan**

Run: `docker restart ckan && sleep 15 && curl -s http://localhost:8080/dataset | sed -n '/<footer/,$p' | diff - $SCRATCH/footer_before.html`
Expected: tidak ada perbedaan (selain whitespace; pakai `diff -w`).

- [ ] **Step 3: Banner ekosistem** — band biru `#0b4a8b` lebar penuh: ikon `fa-handshake`, "Ekosistem Data Kebencanaan Nasional", "Bersama instansi dan pemerintah daerah, BNPB berkomitmen membangun ekosistem data kebencanaan yang terintegrasi.", 3 angka (provinsi, kab/kota, instansi — sumber sama dengan Task 3), tombol putih "Pelajari Integrasi Data" → `/bantuan`.

- [ ] **Step 4: Footer beranda** — band `#08305c`: logo (`/img/logo-footer.png`), link Tentang (`https://bnpb.go.id/`), Layanan (`showcase_blueprint.index`), Dokumentasi (`/bantuan`), Bantuan (`/bantuan`), Kontak (`/sebaran-bpbd`), "Isi Survey" (`onclick="showSurveyPopup(); return false;"`); ikon sosial (Instagram, X/Twitter, YouTube, Facebook, Telegram dengan URL dari footer global); "© {{ now year }} BNPB. Semua Hak Dilindungi." (tahun via `h.render_datetime` atau literal 2026). `{% include 'snippets/survey_modal.html' %}` di akhir.

- [ ] **Step 5: Responsif** — ≤991px: peta 1 kolom, konten 1 kolom, kategori 3 kolom; ≤767px: hero judul 32px, tombol hero 2 kolom sama lebar, statistik 2×2, kategori 2 kolom, ekosistem bertumpuk, footer bertumpuk; `.sdbi-home{overflow-x:hidden}`.

- [ ] **Step 6: Verifikasi akhir**

Run: `python3 -m unittest ckanext.sdbi.tests.test_beranda_css && python3 scripts/check_beranda.py --expect "Ekosistem Data Kebencanaan Nasional" --expect "showSurveyPopup" --expect "surveyModal"`
Expected: OK. Manual di browser: `/` lebar 1440px dan 390px dibandingkan dengan gambar referensi; klik "Isi Survey" di beranda dan di `/dataset` → modal muncul; `/dataset` tampil seperti sebelumnya.

- [ ] **Step 7: Commit** — `SCOL-1234 beranda ecosystem band, footer, responsive`
