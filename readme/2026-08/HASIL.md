# Hasil visual — Upgrade Portal Data BNPB (lokal)

**Dokumen paparan gabungan (status + screenshot + how-to + justifikasi embed):** [`DOC-2026-09-29.md`](DOC-2026-09-29.md).

Lampiran screenshot untuk paparan. Status teks: [`STATUS.md`](STATUS.md).

URL lokal: http://localhost:8080 — diambil 29 September 2026.  
Capture browser memakai **zoom ~80%** supaya konten tidak kepotong.

## Cara capture ulang (opsional)

1. Pastikan stack compose jalan (`ckan` healthy).
2. Buka halaman di browser; set zoom **80%** (`Cmd+-` sampai ~80%).
3. Screenshot (macOS: `Cmd+Shift+4` / `Cmd+Shift+5`).
4. Simpan ke `screenshots/` dengan nama yang sama agar tautan di bawah tetap valid.

---

## Checklist Status persyaratan

| ID | Persyaratan | Screenshot |
| --- | --- | --- |
| B0 | `CKAN__DATASTORE__SQLSEARCH__ENABLED=false` | [`07-b0-sqlsearch-disabled.png`](screenshots/07-b0-sqlsearch-disabled.png) |
| B1 | CKAN 2.10.11 | [`05-status-show.png`](screenshots/05-status-show.png) |
| B2 | Auth SQL / `sdbi` terakhir di plugins | terlihat di `extensions` pada `05-status-show.png` (plugin `sdbi` di akhir list) |
| Fase 0 | 2FA TOTP | [`06-fase0-2fa-login.png`](screenshots/06-fase0-2fa-login.png) |
| Fase 1 | Harvester JSON REST | [`04-harvest.png`](screenshots/04-harvest.png) |
| Fase 2 | `/sebaran-bpbd` | [`01-sebaran-bpbd-all.png`](screenshots/01-sebaran-bpbd-all.png) |
| Fase 3 | `/bantuan` | [`02-bantuan-hero.png`](screenshots/02-bantuan-hero.png) |
| Fase 3 | `/bantuan/kelola` | [`bantuan-kelola.png`](screenshots/bantuan-kelola.png) |
| Fase 4 | `/tanggap-darurat` | [`03-tanggap-darurat.png`](screenshots/03-tanggap-darurat.png) |
| Fase 4 | `/tanggap-darurat/kelola` | [`tanggap-darurat-kelola.png`](screenshots/tanggap-darurat-kelola.png) |

Narasi lengkap + justifikasi embed: [`DOC-2026-09-29.md`](DOC-2026-09-29.md) §2–3.

---

## Ringkas untuk slide

| Slide | Gambar | Poin bicara |
| --- | --- | --- |
| B0 SQLSEARCH | `07-b0-sqlsearch-disabled.png` | Env false; aksi SQL tidak dikenal |
| B1 versi | `05-status-show.png` | Lokal 2.10.11; produksi 2.9.11 |
| Fase 0 2FA | `06-fase0-2fa-login.png` | TOTP / QR di login |
| Peta BPBD | `01-sebaran-bpbd-all.png` | Kab + Provinsi (~477); cluster |
| Bantuan | `02-bantuan-hero.png` + `bantuan-kelola.png` | FAQ DB + kelola sysadmin |
| Tanggap | `03-tanggap-darurat.png` + `tanggap-darurat-kelola.png` | Navbar + embed dinamis |
| Harvest | `04-harvest.png` | JSON REST; batasan format URL |
