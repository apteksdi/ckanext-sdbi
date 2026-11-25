# Laporan status — Upgrade Portal Data BNPB

**Dokumen paparan gabungan (status + screenshot + how-to + justifikasi embed):** [`DOC-2026-09-29.md`](DOC-2026-09-29.md).

Laporan kondisi terhadap [`PRD.md`](PRD.md). Cara implementasi detail: [`HOW-TO-IMPLEMENT.md`](HOW-TO-IMPLEMENT.md).

| Field | Nilai |
| --- | --- |
| Tanggal laporan | 29 September 2026 |
| Branch | `ckanext-sdbi` dan `ckan-compose`: `upgrade-ckan-security-etc` |
| URL lokal | http://localhost:8080 |
| Produksi | https://data.bnpb.go.id (masih CKAN 2.9.11) |

Update ringkas sejak laporan 9 Sep: titik BPBD Kab/Kota + Provinsi sudah di Postgres (`sdbi_bpbd`) dan tampil di `/sebaran-bpbd`; popup website; impor CSV kontak resmi; clustering Supercluster. Commit terkait: sdbi `faec4d2` / `c962097` / `2ed84c2` / `6199c61`, compose `65d2a3b`.

**Hasil visual (screenshot):** lihat [`DOC-2026-09-29.md`](DOC-2026-09-29.md) §3 dan folder [`screenshots/`](screenshots/).

---

## 1. Lingkungan

| Lingkungan | CKAN | Image / Solr |
| --- | --- | --- |
| Produksi | **2.9.11** | `ghcr.io/keitaroinc/ckan:2.9.11-focal` (rentang CVE `< 2.10.10`) |
| Compose lokal | **2.10.11** | `ckan/ckan-base:2.10.11-py3.10` + `ckan/ckan-solr:2.10-solr9` |

---

## 2. Status persyaratan

| ID | Persyaratan | Lokal | Produksi | Bukti / celah |
| --- | --- | --- | --- | --- |
| B0 | `CKAN__DATASTORE__SQLSEARCH__ENABLED=false` | **Selesai** | **Selesai** | Flag env. Tetap false setelah 2.10. |
| B2 | Auth SQL default tolak (`sdbi` terakhir) | **Selesai** | **Selesai** | `ckanext/sdbi/auth.py`; `sdbi` terakhir di plugins produksi |
| B1 | CKAN 2.10.11 | **Selesai** | **Belum dimulai** | Lokal `ckan --version` 2.10.11 |
| Fase 0 | 2FA TOTP | **Selesai** | Perlu rebuild image + `security migrate` | security 4.1.1, Redis DB 2, QR di login pertama |
| Fase 1 | Harvester JSON REST | **Selesai*** | Perlu image produksi + worker yang sama | Tipe **JSON REST**; *lihat catatan di bawah |
| Fase 2 | `/sebaran-bpbd` | **Selesai** | Belum di-deploy | Peta MapLibre; Kab/Kota + Provinsi di peta; cluster Supercluster |
| Fase 3 | `/bantuan` | **Selesai** | Belum di-deploy | Chip + cari; JSON `sdbi_settings.faq` (tanpa YAML) |
| Fase 4 | Kamar `/tanggap-darurat` | **Selesai** | Perlu cutover 2.10 | Dropdown **navbar**; JSON `tanggap_rooms`; `/kelola` sysadmin; iframe HTTPS |

### Catatan Fase 1 — Harvester JSON REST

- Bisa impor metadata dataset dari API JSON REST **bukan** CKAN Action API (contoh gateway kota).
- **Batasan:** impor mengasumsikan bentuk URL / payload yang **selaras dengan pola URL CKAN** (satu endpoint detail, atau daftar + template detail seperti yang didokumentasikan di PRD). Bukan harvester generik untuk sembarang skema JSON.
- Hasil harvest = paket katalog + resource tautan JSON ke API asal; **tidak** menyalin `data[]` ke DataStore.

### Catatan Fase 2 — `/sebaran-bpbd`

- Titik BPBD **Kabupaten/Kota** dan **Provinsi** sudah di `sdbi_bpbd` dan tampil di peta (~477 titik berkoordinat: ~443 kab + ~34 prov).
- Sumber Provinsi: CSV kontak resmi (~38 baris; 4 tanpa koordinat sehingga tidak di-plot).
- Marker clustering Supercluster: zoom-out grup berangka, zoom-in titik individual.
- Popup menampilkan telepon, email, website (jika ada), SDM, Maps.
- GeoJSON batas Kabupaten masih interim (boleh kosong / disederhanakan sesuai PRD rilis pertama).
- Skill impor ulang: `.cursor/skills/peta-sebaran` (`/peta-sebaran`).

---

## 3. Verifikasi lokal (29 Sep 2026)

| Pemeriksaan | Hasil |
| --- | --- |
| Beranda, `/dataset`, detail dataset | 200 |
| `status_show` | 2.10.11; plugin termasuk `activity`, `sdbi_json_harvester`; `sdbi` terakhir |
| `/sebaran-bpbd` | 200; peta layar penuh; Kab + Provinsi di peta (~477 titik); cluster zoom; unduh CSV |
| `/sebaran-bpbd` popup | Telepon / email / website (bila ada) |
| `/bantuan` | 200; chip kategori; cari |
| `/bantuan/kelola` | 403 anonim; sysadmin menyimpan JSON `faq` |
| `/tanggap-darurat` | 200, kamar dari dropdown navbar |
| `/tanggap-darurat/kelola` | 403 anonim; iframe harus HTTPS |
| `/harvest` | Tipe JSON REST tersedia; batasan format URL seperti catatan Fase 1 |
| `datastore_search_sql` | Tidak terdaftar / tertahan |
| Healthcheck | `ckan` healthy; worker harvest tanpa probe HTTP |

Plugin produksi 2.9 yang **belum** di lokal: `dcat*`, `structured_data`, `resourceauthorizer` (sengaja).

---

## 4. Risiko dan sisa pekerjaan

| Item | Dampak | Catatan |
| --- | --- | --- |
| Produksi masih 2.9.11 | CVE sampai cutover B1 | B0 adalah kunci produksi saat ini |
| Image produksi belum di-bake 2.10 | Worker/web bisa beda plugin | Lokal sudah: image compose + `CKAN__PLUGINS` di start worker |
| **4 BPBD Provinsi tanpa koordinat** | Minor: 4 baris tidak di-plot | Provinsi berkoordinat sudah di peta; lengkapi lat/lng via SQL bila sumber resmi ada |
| **JSON REST bukan harvester generik** | Hanya API dengan pola URL mirip CKAN | Integrasi portal kota lain perlu sesuaikan config / template URL |
| Harvest MANUAL tanpa Reharvest | Sumber ada, `job_count=0`, tidak ada dataset | Harus Reharvest atau `ckan harvester job` |
| Harvest hanya metadata + tautan JSON | Tabel `data[]` tidak di DataStore | Sesuai Fase 1; salin ke DataStore belum diminta |
| GeoJSON Kabupaten kosong / interim | Layer kabupaten terbatas | Tambah ADM2 yang disederhanakan nanti |
| Kamar Tanggap kosong | Sesuai desain | Isi iframe di `/tanggap-darurat/kelola` |
| API key produksi masih yang lama | Token lolos 2FA | Cabut semua key 2.9 sekarang; putar DataPusher; cabut JWT lagi setelah 2.10 |
| Harvest katalog kota tanpa saring | Dataset tidak pantas / data pribadi di portal | Jeda sumber katalog penuh; hapus paket non-bencana |
| Fase 0–4 belum di produksi | Celah fitur | Kirim bersama image 2.10 |
| DCAT produksi tidak di 2.10 | RDF/JSON-LD katalog | Bukan pengganti `sdbi_json_harvester` |

---

## 5. Langkah berikutnya (produksi)

1. Cabut semua API key pengguna produksi 2.9; putar token DataPusher (lihat [`HOW-TO-IMPLEMENT.md`](HOW-TO-IMPLEMENT.md))
2. Jeda harvest katalog penuh; hapus paket non-bencana harvested (lihat HOW-TO *Sumber harvest produksi*)
3. Rebuild staging ke 2.10.11 memakai [`HOW-TO-IMPLEMENT.md`](HOW-TO-IMPLEMENT.md)
4. Ulangi pemeriksaan lokal di staging (termasuk `harvesters_info` di **gather**)
5. Jendela maintenance produksi: `db upgrade`, Solr 9, `security migrate`, reindex
6. Recreate web **dan** worker harvest dari image yang sama; cabut JWT 2.10
7. Jangan mengaktifkan kembali SQL search
8. **(Lokal / data, opsional)** Lengkapi 4 BPBD Provinsi tanpa koordinat bila lat/lng resmi tersedia
9. **(Lokal / harvest)** Dokumentasikan contoh URL yang didukung JSON REST saat onboarding sumber baru

Urutan: B0 (selesai) → B2 produksi (selesai) → B1 staging/produksi → Fase 0/1 di image web+worker → Fase 2–4 ikut image yang sama.
