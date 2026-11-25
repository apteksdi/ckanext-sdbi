# -*- coding: utf-8 -*-
"""Unit tests for BPBD CSV import and Google Maps URL building."""
import io
import pytest

from ckanext.sdbi.lib.bpbd import (
    BPBD_CSV_FIELDS,
    BpbdImportError,
    build_google_maps_url,
    csv_to_records,
    geojson_to_csv,
    records_to_geojson,
)


SAMPLE_CSV = u"""kode_wilayah,tingkat,nama_instansi,alamat,lat,lng,telepon,email,jumlah_sdm,catatan_sdm
31,provinsi,BPBD DKI Jakarta,Jl. Medan Merdeka Selatan,-6.175392,106.827153,021-123,bpbd@jakarta.go.id,120,Personel TRC 40
3201,kabupaten,BPBD Kabupaten Bogor,Cibinong,-6.4817,106.8540,0251-123,bpbd@bogorkab.go.id,80,SAR 12
"""


def test_csv_to_records_parses_valid_rows():
    records = csv_to_records(io.StringIO(SAMPLE_CSV))
    assert len(records) == 2
    assert records[0]['nama_instansi'] == 'BPBD DKI Jakarta'
    assert records[0]['tingkat'] == 'provinsi'
    assert records[0]['lat'] == pytest.approx(-6.175392)
    assert records[0]['jumlah_sdm'] == 120


def test_csv_to_records_rejects_missing_columns():
    with pytest.raises(BpbdImportError):
        csv_to_records(io.StringIO('nama_instansi,lat\nBPBD,-6.1\n'))


def test_csv_to_records_rejects_invalid_tingkat():
    bad = SAMPLE_CSV.replace('provinsi', 'kecamatan', 1)
    with pytest.raises(BpbdImportError):
        csv_to_records(io.StringIO(bad))


def test_build_google_maps_url_prefers_coordinates():
    url = build_google_maps_url({'lat': -6.175392, 'lng': 106.827153, 'alamat': 'Monas'})
    assert url == 'https://www.google.com/maps?q=-6.175392,106.827153'


def test_build_google_maps_url_falls_back_to_address():
    url = build_google_maps_url({'lat': None, 'lng': None, 'alamat': 'Jl. Medan Merdeka Selatan'})
    assert url.startswith('https://www.google.com/maps?q=')
    assert 'Medan' in url


def test_records_to_geojson_skips_rows_without_coordinates():
    records = csv_to_records(io.StringIO(SAMPLE_CSV))
    records.append({
        'kode_wilayah': '99',
        'tingkat': 'provinsi',
        'nama_instansi': 'Tanpa koordinat',
        'alamat': 'Unknown',
        'lat': None,
        'lng': None,
        'telepon': '',
        'email': '',
        'jumlah_sdm': 0,
        'catatan_sdm': '',
    })
    geojson = records_to_geojson(records)
    assert geojson['type'] == 'FeatureCollection'
    assert len(geojson['features']) == 2
    assert BPBD_CSV_FIELDS


def test_kontak_csv_to_records_maps_official_columns():
    from ckanext.sdbi.lib.bpbd import kontak_csv_to_records
    sample = u"""id_prov,id_kab,Status BPBD,Keterangan Status,Provinsi,Kabupaten/Kota,Nama Kepala BPBD,Nama Staf,Kontak BPBD,Email,Alamat,Website,Facebook,Instagram,Twitter,koordinat latitude dan longitude
11,1101,Terbentuk,Terbentuk,Aceh,Kab. Aceh Selatan,Kepala,Staf,0811,a@b.com,Jl. Contoh,-,-,-,-,"3.26, 97.19"
31,3173,Belum Terbentuk,Belum Terbentuk,DKI Jakarta,Jakarta Barat,-,-,-,-,-,-,-,-,-,
"""
    records = kontak_csv_to_records(io.StringIO(sample))
    assert len(records) == 2
    assert records[0]['kode_wilayah'] == '1101'
    assert records[0]['tingkat'] == 'kabupaten'
    assert records[0]['nama_instansi'] == 'BPBD Aceh Selatan'
    assert records[0]['lat'] == pytest.approx(3.26)
    assert records[0]['lng'] == pytest.approx(97.19)
    assert records[0]['status_bpbd'] == 'Terbentuk'
    assert records[1]['lat'] is None
    assert records[1]['nama_instansi'] == 'BPBD Jakarta Barat'
    geojson = records_to_geojson(records)
    assert len(geojson['features']) == 1


def test_kontak_provinsi_csv_to_records():
    from ckanext.sdbi.lib.bpbd import (
        kontak_csv_to_records_auto,
        kontak_provinsi_csv_to_records,
    )
    sample = u"""id_prov,Provinsi,Status_BPBD,Alamat,Nama Kalaksa,Kontak BPBD,Website,Email,Facebook,Instagram,Twitter,Jumlah BPBD,koordinat latitude dan longitude
11,Aceh,Terbentuk,Jl. A,Kepala,0811,https://a.id/,a@b.com,-,-,-,23,"5.55, 95.32"
99,X,Belum Terbentuk,-,-,-,-,-,-,-,-,0,
"""
    records = kontak_provinsi_csv_to_records(io.StringIO(sample))
    assert len(records) == 2
    assert records[0]['tingkat'] == 'provinsi'
    assert records[0]['kode_wilayah'] == '11'
    assert records[0]['nama_instansi'] == 'BPBD Provinsi Aceh'
    assert records[0]['lat'] == pytest.approx(5.55)
    assert records[1]['lat'] is None
    kind, auto = kontak_csv_to_records_auto(io.StringIO(sample))
    assert kind == 'provinsi'
    assert len(auto) == 2
    assert len(records_to_geojson(records)['features']) == 1

