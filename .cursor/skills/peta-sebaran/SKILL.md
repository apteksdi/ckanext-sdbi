---
name: peta-sebaran
description: >-
  Import BPBD contact CSV (Kab/Kota or Provinsi) into Postgres sdbi_bpbd for
  /sebaran-bpbd map. Use when user asks to import kontak BPBD, update peta
  sebaran points, load province/kabupaten CSV into sdbi_bpbd, or mentions
  /peta-sebaran / /sebaran-bpbd data import.
disable-model-invocation: true
---

# Peta Sebaran BPBD — import kontak CSV

## Goal

Load official BPBD contact CSV into table `sdbi_bpbd` so `/sebaran-bpbd` map points update. Supports **Kab/Kota** and **Provinsi** CSVs.

## Source files (examples)

- Kab/Kota: `Data Kontak BPBD Kab_Kota.xlsx - Data Kontak BPBD Kabkot.csv`
- Provinsi: `Data Kontak BPBD Provinsi.xlsx - Data Kontak BPBD Provinsi.csv`

Copy into mounted path before import:

```bash
cp "<source.csv>" ckanext-sdbi/data/kontak_bpbd_<kabkot|provinsi>.csv
```

## Import command (inside `ckan` container)

```bash
docker context use colima-ckan

# Provinsi — replaces only tingkat=provinsi (keeps kabupaten)
docker exec -i ckan python /srv/app/src/ckanext-sdbi/scripts/import_bpbd_kontak_csv.py \
  --csv /srv/app/src/ckanext-sdbi/data/kontak_bpbd_provinsi.csv

# Kab/Kota — replaces only tingkat=kabupaten (keeps provinsi)
docker exec -i ckan python /srv/app/src/ckanext-sdbi/scripts/import_bpbd_kontak_csv.py \
  --csv /srv/app/src/ckanext-sdbi/data/kontak_bpbd_kabkot.csv

# Optional dry-run
docker exec -i ckan python /srv/app/src/ckanext-sdbi/scripts/import_bpbd_kontak_csv.py \
  --csv /srv/app/src/ckanext-sdbi/data/kontak_bpbd_provinsi.csv --dry-run
```

Default: **replace matching tingkat only**. Use `--replace-all` only when intentionally wiping the whole table.

## Mapping

### Kab/Kota CSV

| CSV | DB |
|-----|-----|
| `id_kab` | `kode_wilayah` |
| (fixed) | `tingkat=kabupaten` |
| `Kabupaten/Kota` | `nama_instansi` = `BPBD {name}` (strip Kab./Kota) |
| `Alamat`, `Kontak BPBD`, `Email`, `Website` | same |
| `koordinat latitude dan longitude` | `lat`,`lng` |
| `Status BPBD` | `status_bpbd` / `catatan_sdm` |

### Provinsi CSV

| CSV | DB |
|-----|-----|
| `id_prov` | `kode_wilayah` + `id_prov` |
| (fixed) | `tingkat=provinsi` |
| `Provinsi` | `nama_instansi` = `BPBD Provinsi {name}` |
| `Nama Kalaksa` | `nama_kepala` |
| `Status_BPBD`, `Jumlah BPBD` | `status_bpbd` / `catatan_sdm` |
| coords / kontak / email / website / alamat | same |

Rows without coordinates are stored but **omitted from GeoJSON** (map).

## Code touchpoints

- Lib: [`ckanext-sdbi/ckanext/sdbi/lib/bpbd.py`](ckanext-sdbi/ckanext/sdbi/lib/bpbd.py) — `kontak_csv_to_records_auto`, `replace_records_via_url(..., tingkat=)`
- Script: [`ckanext-sdbi/scripts/import_bpbd_kontak_csv.py`](ckanext-sdbi/scripts/import_bpbd_kontak_csv.py)
- API map: `GET /sebaran-bpbd/data.geojson` (reads DB)
- SQL init: [`ckan-compose/postgresql/docker-entrypoint-initdb.d/50_sdbi_bpbd.sql`](ckan-compose/postgresql/docker-entrypoint-initdb.d/50_sdbi_bpbd.sql)
- Host Postgres (DBeaver): `127.0.0.1:5433`, db/user `ckan`, password from `ckan-compose/.env`

## Verify

```bash
docker exec db psql -U ckan -d ckan -c \
  "SELECT tingkat, count(*) FROM sdbi_bpbd GROUP BY 1 ORDER BY 1;"

curl -s http://localhost:8080/sebaran-bpbd/data.geojson | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(len(d['features']))"
```

Restart `ckan` if Python lib changes are not picked up:

```bash
cd ckan-compose && docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart ckan
```

## Agent checklist

When user asks to import BPBD contacts / update peta sebaran:

1. Identify CSV kind (provinsi vs kabkot) from headers
2. Copy into `ckanext-sdbi/data/`
3. Dry-run, then import with tingkat-scoped replace
4. Verify DB counts + geojson feature count
5. Do **not** use `--replace-all` unless user explicitly wants a full wipe
