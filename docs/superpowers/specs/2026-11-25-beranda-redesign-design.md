# Redesign Beranda (halaman `/`) — Design

Tanggal: 2026-11-25 · Referensi visual: `../revamp/BNPB Badan Penaggulangan Bencana Nasional Redesign.png`

## Intent

Beranda `localhost:8080/` dibuat mengikuti gambar referensi. Revamp sebelumnya mengubah
CSS/HTML yang reusable sehingga ikut mengubah halaman lain. Karena itu beranda dibangun
sebagai **satu halaman baru yang berdiri sendiri**: tidak ada file atau class yang dipakai
halaman lain yang diubah.

## Goals / Non-goals / Anti-goals

- **Goals:** tampilan mirip referensi (desktop + mobile) dengan isi dari data dan aset asli.
- **Non-goals:** mengubah header/footer global, halaman lain, atau logo (logo tetap
  `logo-bnpb-header.png`); membuat bottom tab bar mobile.
- **Anti-goals:** CSS beranda bocor ke halaman lain; data palsu/statis yang terlihat live.

## Approaches

- A. Halaman baru + include header/footer global — risiko paling kecil, tetapi header tidak
  mirip referensi.
- **B. Halaman baru + header/footer khusus beranda (dipilih)** — paling mirip referensi.
  Konsekuensinya, menu ada dua salinan: kalau menu global berubah, beranda harus ikut diubah.
- C. HTML lepas dari CKAN `base.html` — isolasi total, tetapi flash message, JS CKAN dan
  login harus dibangun ulang. Ditolak.

## Desain

- `templates/home/index.html` (baru) meng-extend `base.html` dan meng-override
  `{% block page %}`, sehingga `page.html`, header dan footer global tidak dirender.
  Route `home.index` otomatis memakai template ini; `layout1.html` dan snippet `home/…`
  dibiarkan (tidak dipakai lagi oleh `/`).
- CSS di `public/css/beranda.css`, hanya di-link dari template ini. Semua selector diawali
  `.sdbi-home`; tidak ada selector global/tag polos. JS kecil (menu mobile + dropdown) di
  `public/js/beranda.js`, juga hanya untuk halaman ini.
- **Header:** logo existing; menu sama dengan `snippets/header_navigation_items.html`
  (Beranda, Dataset, Organisasi, Showcase, Sebaran BPBD, Tanggap Darurat▾ dari
  `h.sdbi_tanggap_rooms()`, Bantuan); tombol cari; "Masuk" untuk anonim, dropdown avatar
  dengan link sama seperti `snippets/header_account_menu.html` untuk yang login.
- **Hero:** foto `/base/images/Dokumentasi-Erupsi-semeru.JPG` (sudah di-serve container)
  + overlay biru, judul "Satu Data untuk Indonesia Tangguh Bencana", form cari ke
  `dataset.search`, tombol "Lihat Peta Bencana" (`#peta`) dan "Jelajahi Dataset".
- **Strip statistik:** Total Dataset (`sdbi_theme_dataset_count`), Provinsi, Kabupaten/Kota,
  Instansi (= kementerian/lembaga + NGO) dari `sdbi_theme_connected_statistics`.
- **Peta + Tanggap Darurat Aktif:** iframe `https://gis.bnpb.go.id/dev/map` dalam kartu
  dengan tombol "Buka Peta Lengkap"; panel kanan berisi daftar `sdbi_tanggap_rooms()`
  (link `/tanggap-darurat?jenis=<slug>`), dengan empty state bila kosong.
- **Kategori Dataset (6):** Kejadian Bencana `?q=kejadian`, Dampak Bencana `?q=dampak`,
  Mitigasi & Kesiapsiagaan `?fase=prabencana`, Penanganan Darurat `?fase=saatbencana`,
  Pemulihan Pascabencana `?fase=pascabencana`, Data Lainnya `/dataset`.
- **Dataset Terbaru:** 3 dataset dari `sdbi_theme_most_recent_datasets`, dengan views/downloads
  dari helper yang sudah ada.
- **Layanan & Dashboard:** 6 dashboard dari beranda lama beserta gambar `/base/images/…`.
- **Banner Ekosistem:** teks + statistik provinsi/kab-kota/instansi + "Pelajari Integrasi Data"
  (→ `/bantuan`).
- **Footer khusus beranda:** navy, logo, link (Tentang, Layanan, Dokumentasi, Bantuan, Kontak)
  mengikuti link yang ada di footer global, ikon sosial media, copyright.
- **Responsif:** satu kolom di mobile, menu jadi hamburger, statistik 2×2.

## Diserahkan ke builder

Detail spacing/warna mengikuti gambar (biru `#0b4a8b`-an, aksen oranye); ikon memakai
Font Awesome yang sudah dimuat.

## Revisi 2026-11-25 (setelah review pengguna)

- Header dan footer kembali memakai yang existing: `home/index.html` sekarang meng-extend
  `page.html` dan hanya meng-override `{% block content %}`. Partial header/footer beranda dan
  `beranda.js` dihapus. Script, tracking dan popup survey datang dari `page.html`/`footer.html`.
- Hero: foto diganti gradien biru + siluet peta Indonesia (`public/img/peta-indonesia-hero.svg`).
- Kartu peta: iframe diganti screenshot peta kejadian bencana per provinsi
  (`public/img/peta-sebaran-bencana.jpg`, dari `revamp/BNPB LOGO Indonesia.png`) yang bila
  diklik membuka `https://gis.bnpb.go.id/dev/map`. SVG hero dibuat dari
  `public/data/boundaries/provinsi.geojson` (32 provinsi, disederhanakan), tanpa titik bencana.
