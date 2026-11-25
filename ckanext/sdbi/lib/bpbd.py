# -*- coding: utf-8 -*-
"""BPBD CSV import, Postgres persistence, and Google Maps URL helpers."""
import csv
import io
import logging
import re

from sqlalchemy import text

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus


log = logging.getLogger(__name__)

BPBD_CSV_FIELDS = [
    'kode_wilayah',
    'tingkat',
    'nama_instansi',
    'alamat',
    'lat',
    'lng',
    'telepon',
    'email',
    'jumlah_sdm',
    'catatan_sdm',
]

BPBD_EXTRA_FIELDS = [
    'status_bpbd',
    'keterangan_status',
    'nama_kepala',
    'nama_staf',
    'website',
    'id_prov',
]

BPBD_DB_FIELDS = BPBD_CSV_FIELDS + BPBD_EXTRA_FIELDS

VALID_TINGKAT = ('provinsi', 'kabupaten')

_TABLE_ENSURED = False

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sdbi_bpbd (
    id SERIAL PRIMARY KEY,
    kode_wilayah TEXT NOT NULL,
    tingkat TEXT NOT NULL CHECK (tingkat IN ('provinsi', 'kabupaten')),
    nama_instansi TEXT NOT NULL,
    alamat TEXT DEFAULT '',
    telepon TEXT DEFAULT '',
    email TEXT DEFAULT '',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    jumlah_sdm INTEGER DEFAULT 0,
    catatan_sdm TEXT DEFAULT '',
    status_bpbd TEXT DEFAULT '',
    keterangan_status TEXT DEFAULT '',
    nama_kepala TEXT DEFAULT '',
    nama_staf TEXT DEFAULT '',
    website TEXT DEFAULT '',
    id_prov TEXT DEFAULT '',
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
)
"""

_CREATE_UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_sdbi_bpbd_kode_wilayah
    ON sdbi_bpbd (kode_wilayah)
"""

_CREATE_TINGKAT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_sdbi_bpbd_tingkat
    ON sdbi_bpbd (tingkat)
"""


class BpbdImportError(ValueError):
    pass


def _parse_float(value):
    if value is None:
        return None
    text_value = str(value).strip()
    if text_value == '':
        return None
    try:
        return float(text_value)
    except ValueError:
        raise BpbdImportError('lat/lng must be numeric: %s' % value)


def _parse_int(value, default=0):
    if value is None or str(value).strip() == '':
        return default
    try:
        return int(float(str(value).strip()))
    except ValueError:
        raise BpbdImportError('jumlah_sdm must be numeric: %s' % value)


def _blank_to_empty(value):
    text_value = (value or '').strip()
    if text_value in ('-', '–', '—'):
        return ''
    return text_value


def csv_to_records(handle):
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        raise BpbdImportError('CSV is empty')
    missing = [field for field in BPBD_CSV_FIELDS if field not in reader.fieldnames]
    if missing:
        raise BpbdImportError('CSV missing columns: %s' % ', '.join(missing))
    records = []
    for index, row in enumerate(reader, start=2):
        tingkat = (row.get('tingkat') or '').strip().lower()
        if tingkat not in VALID_TINGKAT:
            raise BpbdImportError(
                'Row %s: tingkat must be provinsi or kabupaten' % index
            )
        nama = (row.get('nama_instansi') or '').strip()
        if not nama:
            raise BpbdImportError('Row %s: nama_instansi is required' % index)
        records.append({
            'kode_wilayah': (row.get('kode_wilayah') or '').strip(),
            'tingkat': tingkat,
            'nama_instansi': nama,
            'alamat': (row.get('alamat') or '').strip(),
            'lat': _parse_float(row.get('lat')),
            'lng': _parse_float(row.get('lng')),
            'telepon': (row.get('telepon') or '').strip(),
            'email': (row.get('email') or '').strip(),
            'jumlah_sdm': _parse_int(row.get('jumlah_sdm')),
            'catatan_sdm': (row.get('catatan_sdm') or '').strip(),
            'status_bpbd': _blank_to_empty(row.get('status_bpbd')),
            'keterangan_status': _blank_to_empty(row.get('keterangan_status')),
            'nama_kepala': _blank_to_empty(row.get('nama_kepala')),
            'nama_staf': _blank_to_empty(row.get('nama_staf')),
            'website': _blank_to_empty(row.get('website')),
            'id_prov': _blank_to_empty(row.get('id_prov')),
        })
    return records


def parse_lat_lng(value):
    """Parse 'lat, lng' string. Returns (lat, lng) or (None, None)."""
    text_value = _blank_to_empty(value)
    if not text_value:
        return None, None
    parts = re.split(r'\s*,\s*', text_value, maxsplit=1)
    if len(parts) != 2:
        return None, None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None, None


def normalize_kabupaten_name(name):
    text_value = _blank_to_empty(name)
    text_value = re.sub(r'^(Kab\.?|Kota)\s+', '', text_value, flags=re.IGNORECASE)
    return text_value.strip()


def _squash_whitespace(value):
    text_value = _blank_to_empty(value)
    return re.sub(r'\s+', ' ', text_value).strip()


def detect_kontak_csv_kind(fieldnames):
    """Return 'provinsi', 'kabupaten', or raise."""
    names = set(fieldnames or [])
    if 'id_kab' in names and 'Kabupaten/Kota' in names:
        return 'kabupaten'
    if 'id_prov' in names and 'Provinsi' in names and 'id_kab' not in names:
        return 'provinsi'
    if 'id_prov' in names and 'Provinsi' in names and 'Status_BPBD' in names:
        return 'provinsi'
    raise BpbdImportError(
        'Unrecognized contact CSV columns. Need Kab/Kota (id_kab, Kabupaten/Kota) '
        'or Provinsi (id_prov, Provinsi).'
    )


def kontak_csv_to_records(handle):
    """Map official Kab/Kota contact CSV into sdbi_bpbd records."""
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        raise BpbdImportError('CSV is empty')
    required = ['id_kab', 'Kabupaten/Kota']
    missing = [field for field in required if field not in reader.fieldnames]
    if missing:
        raise BpbdImportError('CSV missing columns: %s' % ', '.join(missing))

    records = []
    for index, row in enumerate(reader, start=2):
        kode = str(row.get('id_kab') or '').strip()
        if not kode:
            raise BpbdImportError('Row %s: id_kab is required' % index)
        wilayah = normalize_kabupaten_name(row.get('Kabupaten/Kota'))
        if not wilayah:
            raise BpbdImportError('Row %s: Kabupaten/Kota is required' % index)

        status = _blank_to_empty(row.get('Status BPBD'))
        keterangan = _blank_to_empty(row.get('Keterangan Status'))
        catatan = status
        if status == 'Lainnya' and keterangan:
            catatan = '%s: %s' % (status, keterangan)
        elif keterangan and keterangan != status:
            catatan = '%s (%s)' % (status, keterangan) if status else keterangan

        lat, lng = parse_lat_lng(row.get('koordinat latitude dan longitude'))
        records.append({
            'kode_wilayah': kode,
            'tingkat': 'kabupaten',
            'nama_instansi': 'BPBD %s' % wilayah,
            'alamat': _blank_to_empty(row.get('Alamat')),
            'lat': lat,
            'lng': lng,
            'telepon': _squash_whitespace(row.get('Kontak BPBD')),
            'email': _blank_to_empty(row.get('Email')),
            'jumlah_sdm': 0,
            'catatan_sdm': catatan,
            'status_bpbd': status,
            'keterangan_status': keterangan,
            'nama_kepala': _blank_to_empty(row.get('Nama Kepala BPBD')),
            'nama_staf': _blank_to_empty(row.get('Nama Staf')),
            'website': _blank_to_empty(row.get('Website')),
            'id_prov': str(row.get('id_prov') or '').strip(),
        })
    return records


def kontak_provinsi_csv_to_records(handle):
    """Map official Provinsi contact CSV into sdbi_bpbd records."""
    reader = csv.DictReader(handle)
    if not reader.fieldnames:
        raise BpbdImportError('CSV is empty')
    required = ['id_prov', 'Provinsi']
    missing = [field for field in required if field not in reader.fieldnames]
    if missing:
        raise BpbdImportError('CSV missing columns: %s' % ', '.join(missing))

    records = []
    for index, row in enumerate(reader, start=2):
        kode = str(row.get('id_prov') or '').strip()
        if not kode:
            raise BpbdImportError('Row %s: id_prov is required' % index)
        wilayah = _blank_to_empty(row.get('Provinsi'))
        if not wilayah:
            raise BpbdImportError('Row %s: Provinsi is required' % index)

        status = _blank_to_empty(row.get('Status_BPBD') or row.get('Status BPBD'))
        jumlah_bpbd = _blank_to_empty(row.get('Jumlah BPBD'))
        catatan = status
        if jumlah_bpbd:
            catatan = (
                '%s; Jumlah BPBD kab/kota: %s' % (status, jumlah_bpbd)
                if status else 'Jumlah BPBD kab/kota: %s' % jumlah_bpbd
            )

        lat, lng = parse_lat_lng(row.get('koordinat latitude dan longitude'))
        records.append({
            'kode_wilayah': kode,
            'tingkat': 'provinsi',
            'nama_instansi': 'BPBD Provinsi %s' % wilayah,
            'alamat': _blank_to_empty(row.get('Alamat')),
            'lat': lat,
            'lng': lng,
            'telepon': _squash_whitespace(row.get('Kontak BPBD')),
            'email': _blank_to_empty(row.get('Email')),
            'jumlah_sdm': 0,
            'catatan_sdm': catatan,
            'status_bpbd': status,
            'keterangan_status': '',
            'nama_kepala': _blank_to_empty(row.get('Nama Kalaksa') or row.get('Nama Kepala BPBD')),
            'nama_staf': '',
            'website': _blank_to_empty(row.get('Website')),
            'id_prov': kode,
        })
    return records


def kontak_csv_to_records_auto(handle):
    """Detect Kab/Kota vs Provinsi CSV and map to records."""
    sample = handle.read()
    if hasattr(sample, 'decode'):
        sample = sample.decode('utf-8-sig')
    buffer = io.StringIO(sample)
    reader = csv.DictReader(buffer)
    kind = detect_kontak_csv_kind(reader.fieldnames)
    buffer.seek(0)
    if kind == 'provinsi':
        return kind, kontak_provinsi_csv_to_records(buffer)
    return kind, kontak_csv_to_records(buffer)


def build_google_maps_url(record):
    lat = record.get('lat')
    lng = record.get('lng')
    if lat is not None and lng is not None:
        return 'https://www.google.com/maps?q=%s,%s' % (lat, lng)
    alamat = (record.get('alamat') or record.get('nama_instansi') or '').strip()
    return 'https://www.google.com/maps?q=' + quote_plus(alamat)


def records_to_geojson(records):
    features = []
    for record in records:
        if record.get('lat') is None or record.get('lng') is None:
            continue
        properties = {}
        for field in BPBD_CSV_FIELDS:
            properties[field] = record.get(field)
        website = (record.get('website') or '').strip()
        if website:
            properties['website'] = website
        properties['maps_url'] = build_google_maps_url(record)
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [record['lng'], record['lat']],
            },
            'properties': properties,
        })
    return {'type': 'FeatureCollection', 'features': features}


def geojson_to_csv(geojson):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=BPBD_CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()
    for feature in geojson.get('features') or []:
        props = feature.get('properties') or {}
        row = {}
        for field in BPBD_CSV_FIELDS:
            value = props.get(field, '')
            row[field] = '' if value is None else value
        writer.writerow(row)
    return output.getvalue()


def ensure_table():
    global _TABLE_ENSURED
    if _TABLE_ENSURED:
        return
    import ckan.model as model
    model.Session.execute(text(_CREATE_TABLE))
    model.Session.execute(text(_CREATE_UNIQUE_INDEX))
    model.Session.execute(text(_CREATE_TINGKAT_INDEX))
    model.Session.commit()
    _TABLE_ENSURED = True


def _normalize_record(record):
    tingkat = (record.get('tingkat') or '').strip().lower()
    if tingkat not in VALID_TINGKAT:
        raise BpbdImportError('tingkat must be provinsi or kabupaten')
    nama = (record.get('nama_instansi') or '').strip()
    if not nama:
        raise BpbdImportError('nama_instansi is required')
    normalized = {
        'kode_wilayah': (record.get('kode_wilayah') or '').strip(),
        'tingkat': tingkat,
        'nama_instansi': nama,
        'alamat': (record.get('alamat') or '').strip(),
        'lat': record.get('lat'),
        'lng': record.get('lng'),
        'telepon': (record.get('telepon') or '').strip(),
        'email': (record.get('email') or '').strip(),
        'jumlah_sdm': _parse_int(record.get('jumlah_sdm')),
        'catatan_sdm': (record.get('catatan_sdm') or '').strip(),
        'status_bpbd': _blank_to_empty(record.get('status_bpbd')),
        'keterangan_status': _blank_to_empty(record.get('keterangan_status')),
        'nama_kepala': _blank_to_empty(record.get('nama_kepala')),
        'nama_staf': _blank_to_empty(record.get('nama_staf')),
        'website': _blank_to_empty(record.get('website')),
        'id_prov': _blank_to_empty(record.get('id_prov')),
    }
    if not normalized['kode_wilayah']:
        raise BpbdImportError('kode_wilayah is required')
    return normalized


_INSERT_SQL = """
    INSERT INTO sdbi_bpbd (
        kode_wilayah, tingkat, nama_instansi, alamat, telepon, email,
        lat, lng, jumlah_sdm, catatan_sdm,
        status_bpbd, keterangan_status, nama_kepala, nama_staf, website, id_prov,
        updated_at
    ) VALUES (
        :kode_wilayah, :tingkat, :nama_instansi, :alamat, :telepon, :email,
        :lat, :lng, :jumlah_sdm, :catatan_sdm,
        :status_bpbd, :keterangan_status, :nama_kepala, :nama_staf, :website, :id_prov,
        CURRENT_TIMESTAMP
    )
"""


def _replace_on_connection(conn, records, tingkat=None):
    """Replace rows. If tingkat is set, only delete that tingkat; else wipe all."""
    normalized = [_normalize_record(record) for record in records]
    if tingkat is not None:
        tingkat = tingkat.strip().lower()
        if tingkat not in VALID_TINGKAT:
            raise BpbdImportError('tingkat must be provinsi or kabupaten')
        for record in normalized:
            if record['tingkat'] != tingkat:
                raise BpbdImportError(
                    'Record kode_wilayah=%s has tingkat=%s, expected %s'
                    % (record['kode_wilayah'], record['tingkat'], tingkat)
                )
    conn.execute(text(_CREATE_TABLE))
    conn.execute(text(_CREATE_UNIQUE_INDEX))
    conn.execute(text(_CREATE_TINGKAT_INDEX))
    if tingkat is None:
        conn.execute(text('DELETE FROM sdbi_bpbd'))
    else:
        conn.execute(
            text('DELETE FROM sdbi_bpbd WHERE tingkat = :tingkat'),
            {'tingkat': tingkat},
        )
    insert_sql = text(_INSERT_SQL)
    for record in normalized:
        conn.execute(insert_sql, record)
    return normalized


def replace_records(records):
    """Replace all rows in sdbi_bpbd with the given records (CKAN Session)."""
    ensure_table()
    import ckan.model as model
    normalized = _replace_on_connection(model.Session, records)
    model.Session.commit()
    return normalized


def replace_records_by_tingkat(records, tingkat):
    """Replace only rows for one tingkat; leave the other tingkat intact."""
    ensure_table()
    import ckan.model as model
    normalized = _replace_on_connection(model.Session, records, tingkat=tingkat)
    model.Session.commit()
    return normalized


def replace_records_via_url(sqlalchemy_url, records, tingkat=None):
    """Replace rows using a SQLAlchemy URL (CLI / scripts).

    tingkat=None → replace entire table
    tingkat='provinsi'|'kabupaten' → replace only that tingkat
    """
    from sqlalchemy import create_engine
    engine = create_engine(sqlalchemy_url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        stored = _replace_on_connection(connection, records, tingkat=tingkat)
        transaction.commit()
        return stored
    except Exception:
        transaction.rollback()
        raise
    finally:
        connection.close()


def load_records():
    ensure_table()
    import ckan.model as model
    result = model.Session.execute(text("""
        SELECT
            kode_wilayah, tingkat, nama_instansi, alamat, lat, lng,
            telepon, email, jumlah_sdm, catatan_sdm,
            status_bpbd, keterangan_status, nama_kepala, nama_staf, website, id_prov
        FROM sdbi_bpbd
        ORDER BY tingkat, kode_wilayah
    """))
    records = []
    for row in result:
        records.append({
            'kode_wilayah': row[0] or '',
            'tingkat': row[1] or '',
            'nama_instansi': row[2] or '',
            'alamat': row[3] or '',
            'lat': row[4],
            'lng': row[5],
            'telepon': row[6] or '',
            'email': row[7] or '',
            'jumlah_sdm': int(row[8] or 0),
            'catatan_sdm': row[9] or '',
            'status_bpbd': row[10] or '',
            'keterangan_status': row[11] or '',
            'nama_kepala': row[12] or '',
            'nama_staf': row[13] or '',
            'website': row[14] or '',
            'id_prov': row[15] or '',
        })
    return records


def load_geojson():
    return records_to_geojson(load_records())
