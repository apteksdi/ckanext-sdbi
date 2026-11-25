# -*- coding: utf-8 -*-
"""Unit tests for remote CSV/Excel → DataStore helpers."""
from ckanext.sdbi.lib.datastore_table import (
    fetch_tabular_records,
    is_remote_tabular_resource,
    records_from_csv_bytes,
    records_from_dicts,
)


def test_records_from_csv_bytes():
    raw = b'periode_data,wilayah,jumlah\n2025,Jakarta,1\n2025,Bogor,2\n'
    rows = records_from_csv_bytes(raw)
    assert len(rows) == 2
    assert rows[0]['wilayah'] == 'Jakarta'
    assert rows[1]['jumlah'] == '2'


def test_records_from_dicts_stringifies_nested():
    rows = records_from_dicts([{'a': 1, 'meta': {'x': True}}])
    assert rows[0]['a'] == 1
    assert rows[0]['meta'] == '{"x": true}'


def test_is_remote_tabular_resource_csv_link():
    assert is_remote_tabular_resource({
        'id': 'r1',
        'url': 'https://example.com/data.csv',
        'format': 'CSV',
        'url_type': None,
    })


def test_is_remote_tabular_resource_skips_upload():
    assert not is_remote_tabular_resource({
        'id': 'r1',
        'url': 'https://example.com/data.csv',
        'format': 'CSV',
        'url_type': 'upload',
    })


def test_is_remote_tabular_resource_detects_ext_without_format():
    assert is_remote_tabular_resource({
        'id': 'r1',
        'url': 'https://example.com/files/report.XLSX',
        'format': '',
        'url_type': '',
    })


def test_fetch_tabular_records_csv(monkeypatch):
    class _Resp(object):
        content = b'a,b\n1,2\n'

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        'ckanext.sdbi.lib.datastore_table.requests.get',
        lambda *a, **k: _Resp(),
    )
    rows = fetch_tabular_records('https://example.com/x.csv', 'csv')
    assert rows == [{'a': '1', 'b': '2'}]
