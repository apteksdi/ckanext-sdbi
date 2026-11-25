# How to implement — Portal Data BNPB

**Dokumen paparan gabungan (status + screenshot + how-to ringkas + justifikasi embed):** [`DOC-2026-09-29.md`](DOC-2026-09-29.md).

Cara menjalankan stack di [`PRD.md`](PRD.md) secara lokal, lalu memindahkan produksi dari CKAN **2.9.11** ke **2.10.11**. Progres: [`STATUS.md`](STATUS.md).

**Belum dijalankan di produksi.** Kerjakan staging dulu. Jaga `CKAN__DATASTORE__SQLSEARCH__ENABLED=false` sepanjang proses.

CLI compose: `docker-compose` (tanda hubung). Image resmi 2.10: `CKAN_INI=/srv/app/ckan.ini` (`production.ini` harus symlink). Context Docker lokal: `colima-ckan`.

---

## Lokal vs produksi — cara baca status

Bandingkan dua endpoint, lalu cocokkan dengan tabel di [`STATUS.md`](STATUS.md).

| | Lokal | Produksi |
| --- | --- | --- |
| Situs | http://localhost:8080 | https://data.bnpb.go.id |
| Status API | http://localhost:8080/api/3/action/status_show | https://data.bnpb.go.id/api/3/action/status_show |
| CKAN | **2.10.11** | **2.9.11** |
| Image | `ckan/ckan-base:2.10.11-py3.10` | `ghcr.io/keitaroinc/ckan:2.9.11-focal` |
| SQL search (B0) | Mati | Mati |
| 2FA / peta / FAQ / tanggap / JSON REST | Ada di tree ini | Belum cutover 2.10 (kecuali B0) |

Cara cek versi dan plugin:

```
curl -sS http://localhost:8080/api/3/action/status_show
curl -sS https://data.bnpb.go.id/api/3/action/status_show
```

Dari `result`:

- `ckan_version` — 2.10.11 lokal vs 2.9.11 produksi
- `extensions` — lokal harus punya `activity` dan `sdbi_json_harvester`; `sdbi` di **akhir** daftar
- produksi 2.9 punya `resourceauthorizer` dan `dcat*` yang **sengaja tidak** di lokal 2.10

| Field `extensions` | Lokal 2.10 | Produksi 2.9 | Artinya |
| --- | --- | --- | --- |
| `activity` | Ada | Tidak (inti 2.9) | Wajib di 2.10 |
| `sdbi_json_harvester` | Ada | Tidak | Harvest JSON REST |
| `resourceauthorizer` | Tidak | Ada | Jangan di 2.10 |
| `dcat`, `dcat_*`, `structured_data` | Tidak | Ada | Katalog RDF; bukan harvest Jakarta |
| `sdbi` | Terakhir | **Terakhir** (B2 deploy) | Auth SQL override |

Laporan lengkap (Fase 0–4, risiko, langkah produksi): [`STATUS.md`](STATUS.md).

### Hasil `status_show` (9 Sep 2026)

| | Lokal | Produksi |
| --- | --- | --- |
| `ckan_version` | **2.10.11** | **2.9.11** |
| `site_title` | CKAN | Portal Satu Data Bencana Indonesia |
| `site_url` | http://localhost:8080 | https://data.bnpb.go.id |
| `sdbi` | **Terakhir** (benar untuk 2.10) | **Terakhir** (B2 sudah deploy) |

**Hanya lokal:** `activity`, `sdbi_json_harvester`  
**Hanya produksi:** `resourceauthorizer`, `structured_data` (terdaftar **dua kali**), `dcat`, `dcat_rdf_harvester`, `dcat_json_harvester`, `dcat_json_interface`  
**Sama:** `envvars`, `stats`, views, `usertracking`, `security`, `collaborator_orgs`, `resource_proxy`, `geo_view`, `harvest`, `ckan_harvester`, `csw_harvester`, `spatial_*`, `datastore`, `datapusher`, `pages`, `showcase`, `sdbi`

---

## A. Lokal (sudah jalan)

Kerjakan di `ckan-compose` dengan overlay dev agar `ckanext-sdbi` di-bind-mount.

```
cd ckan-compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

| Layanan | Peran |
| --- | --- |
| `ckan` | Web, http://localhost:8080 |
| `ckan-harvest-gather` / `fetch` / `run` | Job harvest (image **sama** dengan web: `ckan-compose-ckan`) |
| `solr` | `ckan/ckan-solr:2.10-solr9`, volume `solr_data_210` |
| `db`, `redis` | PostgreSQL + Redis |

Worker harvest **harus** memakai daftar plugin dari `CKAN__PLUGINS` (overlay dev menuliskannya ke `ckan.ini` saat start). Tanpa itu gather gagal: `No harvester could be found for source type sdbi_json_harvester`.

Healthcheck web memakai `wget` ke `/api/3/action/status_show` (image tidak punya `curl`). Worker harvest tidak di-healthcheck HTTP.

Login lokal sysadmin: akun seed + TOTP. Jangan commit `.ckan-env`.

### Plugin: lokal 2.10 vs produksi 2.9

Lokal **sengaja berbeda** dari https://data.bnpb.go.id/api/3/action/status_show.

| Hanya lokal | Alasan |
| --- | --- |
| `activity` | Wajib di CKAN 2.10 (di 2.9 sudah inti) |
| `sdbi_json_harvester` | Harvest JSON REST |

| Hanya produksi | Alasan |
| --- | --- |
| `resourceauthorizer` | Jangan di 2.10 (Pylons) |
| `dcat`, `dcat_rdf_harvester`, `dcat_json_harvester`, `dcat_json_interface`, `structured_data` | Belum dipasang di target 2.10; bukan pengganti JSON REST Jakarta |

`sdbi` **terakhir**. Harvest: `harvest`, `ckan_harvester`, `csw_harvester`, `sdbi_json_harvester`.

### Harvest JSON REST

Tipe sumber: **JSON REST** (`sdbi_json_harvester`). Form sama dengan CKAN/CSW.

**Satu dataset (paling mudah):** URL = endpoint JSON detail. Configuration opsional, contoh Satu Data Jakarta:

URL:

```
https://ws.jakarta.go.id/gateway/DataPortalSatuDataJakarta/1.0/satudata?kategori=dataset&tipe=detail&url=kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-pada-layanan-dasar-akibat-bencana
```

Configuration:

```json
{
  "title": "Kerusakan infrastruktur vital dan gangguan layanan dasar akibat bencana",
  "source_portal": "satudata.jakarta.go.id",
  "default_tags": [
    {
      "name": "harvested"
    },
    {
      "name": "satudata-jakarta"
    }
  ],
  "default_extras": {}
}
```

**Banyak dataset dalam satu sumber:** `datasets[]` plus `detail_url_template` yang mengandung `{name}`. Jangan sisakan slug contoh (`another-jakarta-slug`).

Frequency **MANUAL** tidak memanen sampai:

- tombol **Reharvest** di `/harvest/<nama-sumber>`, atau
- `docker exec ckan ckan -c /srv/app/ckan.ini harvester job <nama-sumber>`

Hasil: paket CKAN `sdbi-<slug>` dengan resource **JSON** yang menunjuk ke API asal. Baris `data[]` **tidak** disalin ke DataStore.

### Peta, FAQ, tanggap

Konten FAQ dan kamar **hanya** di Postgres (`sdbi_settings` key `faq` dan `tanggap_rooms`). Tidak ada `faq.yaml` / `dashboard_rooms.yaml`. Baris kosong → `/bantuan` tanpa pertanyaan; Tanggap Darurat di navbar menjadi tautan biasa sampai JSON disimpan di Kelola.

| Rute | Isi |
| --- | --- |
| `/sebaran-bpbd` | Peta MapLibre layar penuh; unduh CSV; unggah CSV (sysadmin, mengganti semua titik) |
| `/bantuan` | FAQ (DB `sdbi_settings.faq`); chip kategori + cari |
| `/bantuan/kelola` | Sysadmin: edit JSON FAQ, tanpa rebuild |
| Navbar **Tanggap Darurat** | Dropdown kamar (Gempa Bumi, Banjir, …). Sysadmin: Kelola Dashboard + Panduan hosting |
| `/tanggap-darurat?jenis=<slug>` | Iframe HTTPS kamar itu, atau pesan kamar kosong. Tidak ada dropdown di halaman |
| `/tanggap-darurat/kelola` | Sysadmin: edit JSON kamar / iframe HTTPS |
| `/tanggap-darurat/panduan` | Hanya sysadmin |
| `/gempantt2026` | Dashboard GIS; **tidak** di navbar |

Dropdown navbar harus di atas iframe (masthead `z-index` lebih tinggi dari frame).

Contoh SQL (opsional; UI kelola lebih aman karena divalidasi):

```
-- setelah tabel ada (otomatis saat halaman dibuka, atau 40_sdbi_settings.sql)
UPDATE sdbi_settings SET value = '{"categories":[]}'::jsonb, updated_at = NOW() WHERE key = 'faq';
```

### Ubah template / CSS / Python (lokal)

`ckanext-sdbi` di-bind-mount lewat `docker-compose.dev.yml`. Tidak perlu `docker-compose build` untuk edit halaman.

Jinja di-cache jika `debug = false`. Setelah ubah HTML/Python:

```
cd ckan-compose
docker-compose restart ckan
```

Lebih cepat (hanya bust cache):

```
docker exec ckan touch /srv/app/src/ckanext-sdbi/ckanext/sdbi/plugin.py
```

Lalu hard-refresh browser. CSS/JS memakai `?v=`; naikkan angka itu jika stylesheet lama masih ter-cache.

Jangan `docker-compose up --build` kecuali Dockerfile atau layer image berubah. Worker harvest (`gather` / `fetch` / `run`) hanya perlu restart jika Python harvester berubah, bukan untuk HTML/CSS.

---

## B. Staging / produksi (cutover 2.10)

### Cabut API key produksi (sekarang, 2.9.11)

2FA web **tidak** melindungi API key. Setelah kebocoran kredensial, cabut **semua** API key pengguna di https://data.bnpb.go.id. Jangan tunda sampai cutover 2.10.

CKAN 2.9 memakai satu `apikey` per user. Integrasi yang mengirim `Authorization` ke portal ini akan putus sampai diberi key baru.

**Cabut**

- Semua API key pengguna, termasuk sysadmin dan key yang pernah ada di tiket, skrip, atau dump.

**Putar, jangan dihapus tanpa pengganti**

- Token DataPusher (`CKAN__DATAPUSHER__API_TOKEN` atau setara di env 2.9). Buat token sysadmin **baru**, tulis ke env, **recreate** container `ckan` (dan datapusher), lalu cabut token lama. Nilai kosong mematikan unggah resource.

**Tidak terpengaruh**

- Harvester JSON REST yang *menarik* API Jakarta tidak memakai API key CKAN produksi.

**Urutan**

1. Umumin ke editor/integrator bahwa API akan putus sebentar.
2. Reset password akun yang terdampak (atau semua akun).
3. Cycle semua API key pengguna (UI pengguna / aksi `user_generate_apikey`).
4. Putar token DataPusher; uji unggah resource ke DataStore masih jalan.
5. Terbitkan key baru hanya ke pihak yang masih butuh API; jangan kirim key lewat email biasa.

Setelah cutover **2.10.11**, cabut lagi. 2.10 memakai banyak JWT per user (`api_token`); key 2.9 tidak boleh tetap valid.

Jangan commit API key di skrip seed (`ckan-compose/seed_dummy_datasets.py`). Jika key itu pernah dipakai di produksi, cabut UUID itu bersama key lain.

### Sumber harvest produksi (sekarang, 2.9.11)

Harvest `ckan_harvester` / DCAT **bisa** menerbitkan dataset tanpa API key pengguna: job berjalan sebagai user harvest.

Temuan 9 Sep 2026 (katalog publik): `package_search` dengan `harvest_source_title:*` ≈ **372** paket. Sumber **Data Integrasi-Kota Malang** menarik seluruh CKAN Malang, termasuk data **bukan** kebencanaan (BPJS/DTKS desil, data penduduk kelurahan). `sdbi_json_harvester` **tidak** ada di produksi 2.9; ini bukan harvest JSON REST Jakarta.

**Tindakan**

1. Di `/harvest`, jeda atau hapus sumber yang menelan **seluruh** katalog kota/CKAN lain.
2. Hapus atau purge paket harvested yang bukan data bencana.
3. Setelah 2.10, jangan harvest katalog remote tanpa daftar izinan. JSON REST memakai URL dataset eksplisit; `ckan_harvester` tidak.

### 0. Prasyarat

- B0 sudah hidup: SQL search dimatikan dan container **ckan** sudah **di-recreate**.
- Backup PostgreSQL (`ckan` dan `datastore`), Solr, dan volume berkas CKAN.
- Kode rilis: branch `upgrade-ckan-security-etc` (`ckanext-sdbi` + `ckan-compose`), termasuk Fase 0–4.
- Reset TOTP: `ckan -c /srv/app/ckan.ini security reset-totp <username>`.

Konfirmasi B0:

```
docker exec ckan env | grep SQLSEARCH
curl -sS 'https://data.bnpb.go.id/api/action/help_show?name=datastore_search_sql'
```

Harapkan `CKAN__DATASTORE__SQLSEARCH__ENABLED=false` dan aksi SQL **tidak dikenal**.

Jika B0 belum dikerjakan (hanya penahanan, tanpa rebuild image):

```
# di .ckan-env
CKAN__DATASTORE__SQLSEARCH__ENABLED=false

docker-compose up -d --no-build ckan
docker-compose up -d --no-build ckan-harvest-gather ckan-harvest-fetch ckan-harvest-run
```

### 1. Image dan env (staging)

Kerjakan di `ckan-compose`.

#### 1.1 `.ckan-env`

| Key | Nilai / aturan |
| --- | --- |
| `CKAN__DATASTORE__SQLSEARCH__ENABLED` | `false` |
| `CKAN__PLUGINS` | `activity`, `sdbi_json_harvester` setelah plugin harvest, **`sdbi` terakhir**. Tanpa `resourceauthorizer`. |
| `CKAN__DATAPUSHER__API_TOKEN` | Token sungguhan (bukan placeholder lokal) |
| `CKANEXT__SECURITY__REDIS__HOST` | `redis` |
| `CKANEXT__SECURITY__REDIS__PORT` | `6379` |
| `CKANEXT__SECURITY__REDIS__DB` | **2** (CKAN memakai Redis DB 1) |
| `CKAN__WEBASSETS__PATH` | `/var/lib/ckan/webassets` |

#### 1.2 Dockerfile / Solr (harus sama dengan lokal)

- Base: `ckan/ckan-base:2.10.11-py3.10` (bukan Keitaro 2.9)
- Solr: `ckan/ckan-solr:2.10-solr9`, volume **baru**
- Harvest `v1.4.2`, spatial `v2.3.2`, geoview `v0.2.2`
- Security: `data-govt-nz/ckanext-security@4.1.1`; salin `fanstatic/` ke dalam image
- Setelah pip tambahan, kembalikan pin `requirements.txt` inti CKAN
- Layanan harvest memakai `image: ckan-compose-ckan` (bukan image worker 2.9 terpisah)

#### 1.3 Build dan boot

```
docker-compose build
docker-compose up -d
```

Lalu:

```
docker exec ckan ckan -c /srv/app/ckan.ini db upgrade
docker exec ckan ckan -c /srv/app/ckan.ini security migrate
docker exec ckan ckan -c /srv/app/ckan.ini search-index rebuild
```

Konfirmasi: CKAN **2.10.11**, SQLSEARCH **false**, `status_show` memuat `sdbi_json_harvester` dan `activity`.

Produksi **jangan** andalkan `pip install -e`. Plugin harvester harus ter-bake di image; `ckan.ini` worker harus berisi `CKAN__PLUGINS` yang sama.

### 2. Pemeriksaan staging

- [ ] Login + 2FA (login pertama menampilkan QR)
- [ ] Beranda, `/dataset`, satu detail dataset, pratinjau resource
- [ ] `/sebaran-bpbd` layar penuh, unduh CSV
- [ ] `/bantuan`, dropdown navbar Tanggap Darurat, satu kamar kosong
- [ ] `/tanggap-darurat/panduan` 403 kecuali sysadmin
- [ ] `/gempantt2026` 200 lewat URL; **tidak** ada di navbar
- [ ] `/harvest`: tipe **JSON REST**; Reharvest membuat paket `sdbi-*`
- [ ] `ckan harvester harvesters_info` di **worker gather** memuat JSON REST
- [ ] `datastore_search` tetap jalan
- [ ] Jangan mengaktifkan kembali SQL search
- [ ] API key pengguna sudah di-cycle; token DataPusher di env adalah token **baru**
- [ ] Sumber harvest katalog penuh (contoh Integrasi Kota Malang) dijeda; paket non-bencana dihapus

### 3. Cutover produksi

Image dan env sama dengan staging. Butuh jendela maintenance.

1. Bekukan penulisan / halaman maintenance jika diperlukan.
2. Arahkan aplikasi baru ke DB produksi; jalankan `ckan db upgrade`.
3. Naikkan Solr 9 di volume baru; lalu `search-index rebuild`.
4. Jalankan `security migrate` **sebelum** pengguna login.
5. Recreate `ckan` **dan** worker harvest dari image yang sama.
6. Cabut semua JWT API token 2.10 (key 2.9 tidak boleh tersisa); putar token DataPusher di env 2.10.
7. Ulangi bagian 2 terhadap `https://data.bnpb.go.id`.
8. Tahan **job** harvest sampai worker memakai image baru dan konfigurasi sumber disepakati.

### 4. Setelah go-live (mode gagal 2.10 yang sudah diketahui)

| Gejala | Penyebab yang mungkin |
| --- | --- |
| Login HTTP 500 | `ckanext.security.redis.host` (serta port/db) belum diisi |
| `$ is not defined` / jQuery hilang | `CKAN__WEBASSETS__PATH` salah |
| Detail dataset 500 | Plugin `activity` mati |
| QR MFA tanpa JS | Wheel security tanpa `fanstatic/` |
| `/google-forms` 500 | Masih memakai `ckan.lib.base.c` Pylons |
| Harvest JSON REST: `No harvester could be found for source type sdbi_json_harvester` | Worker tidak memuat `CKAN__PLUGINS` / image lama |
| Sumber harvest tanpa dataset | Frequency MANUAL tanpa Reharvest |
| Container `unhealthy` tetapi situs 200 | Healthcheck `curl` di image tanpa curl — pakai `wget` |

Reset TOTP:

```
docker exec ckan ckan -c /srv/app/ckan.ini security reset-totp <username>
```

### 5. Urutan penerapan

1. B0 di produksi (env + recreate, tanpa build) — **selesai**
2. B2 produksi (`sdbi` terakhir / auth SQL tolak) — **selesai**
3. B1 staging, lalu image produksi ke **2.10.11**
4. Fase 0/1 di image itu (`security migrate`, plugin harvester di web **dan** worker)
5. Fase 2–4 ikut image yang sama

### 6. Di luar lingkup sampai diminta

- Penolakan WAF/nginx untuk `/api/action/datastore_search_sql`
- Lompat ke CKAN 2.11.5
- Mengaktifkan kembali SQL search
- Keycloak / 2FA kustom di sdbi
- Overlay `pip install -e` pada worker harvest di produksi
- Menyalin baris JSON `data[]` ke DataStore
- Memasang plugin DCAT produksi di 2.10
