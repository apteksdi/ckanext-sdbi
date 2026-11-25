# -*- coding: utf-8 -*-
"""Unit tests for FAQ JSON/YAML loader."""
import os
import tempfile

import pytest

from ckanext.sdbi.lib.faq import FaqError, load_faq, search_faq


SAMPLE_YAML = u"""
categories:
  - id: akun
    title: Akun dan login
    items:
      - q: Bagaimana cara mengaktifkan 2FA?
        a: Setelah username dan password, pindai QR code dengan aplikasi authenticator.
      - q: Saya terkunci dari akun.
        a: Hubungi sysadmin untuk reset TOTP.
  - id: dataset
    title: Dataset
    items:
      - q: Bagaimana cara mengunduh dataset?
        a: Buka halaman dataset lalu pilih sumber daya yang ingin diunduh.
"""


def test_load_faq_reads_categories_and_items():
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as handle:
        handle.write(SAMPLE_YAML)
        path = handle.name
    try:
        data = load_faq(path)
    finally:
        os.unlink(path)
    assert len(data['categories']) == 2
    assert data['categories'][0]['id'] == 'akun'
    assert data['categories'][0]['questions'][0]['q'].startswith('Bagaimana')


def test_load_faq_rejects_missing_file():
    with pytest.raises(FaqError):
        load_faq('/tmp/does-not-exist-sdbi-faq.yaml')


def test_load_faq_without_path_falls_back_to_empty(monkeypatch):
    from ckanext.sdbi.lib import faq as faq_mod

    monkeypatch.setattr(faq_mod, 'get_json', lambda key: None)
    assert load_faq() == {'categories': []}


def test_parse_faq_from_dict():
    from ckanext.sdbi.lib.faq import parse_faq
    parsed = parse_faq({
        'categories': [{
            'id': 'akun',
            'title': 'Akun',
            'questions': [{'q': 'Apa itu 2FA?', 'a': 'Kode sekali pakai.'}],
        }],
    })
    assert parsed['categories'][0]['questions'][0]['q'] == 'Apa itu 2FA?'


def test_parse_faq_keeps_optional_file_url():
    from ckanext.sdbi.lib.faq import parse_faq
    parsed = parse_faq({
        'categories': [{
            'id': 'prinsip',
            'title': 'Prinsip',
            'questions': [{
                'q': 'Standar Data',
                'a': 'Kepala BPS Nomor 850 Tahun 2023.',
                'file_url': 'https://example.com/standar.pdf',
            }],
        }],
    })
    item = parsed['categories'][0]['questions'][0]
    assert item['file_url'] == 'https://example.com/standar.pdf'
    assert item['file_label'] == 'Referensi File'


def test_parse_faq_rejects_non_http_file_url():
    from ckanext.sdbi.lib.faq import parse_faq
    with pytest.raises(FaqError):
        parse_faq({
            'categories': [{
                'id': 'prinsip',
                'title': 'Prinsip',
                'questions': [{
                    'q': 'Standar Data',
                    'a': 'Teks',
                    'file_url': 'javascript:alert(1)',
                }],
            }],
        })


def test_search_faq_matches_file_label():
    faq = {
        'categories': [
            {
                'id': 'prinsip',
                'title': 'Prinsip',
                'questions': [
                    {
                        'q': 'Standar Data',
                        'a': 'Kepala BPS.',
                        'file_url': 'https://example.com/a.pdf',
                        'file_label': 'Referensi File',
                    },
                ],
            }
        ]
    }
    matches = search_faq(faq, 'referensi')
    assert len(matches) == 1
    assert matches[0]['file_url'] == 'https://example.com/a.pdf'


def test_resolve_json_falls_back_when_db_invalid():
    from ckanext.sdbi.lib.faq import parse_faq
    from ckanext.sdbi.lib.settings import resolve_json
    called = []

    def fallback():
        called.append(True)
        return parse_faq({
            'categories': [{
                'id': 'x',
                'title': 'X',
                'questions': [{'q': 'Q', 'a': 'A'}],
            }],
        })

    result = resolve_json(parse_faq, {'not': 'faq'}, fallback)
    assert called == [True]
    assert result['categories'][0]['id'] == 'x'


def test_search_faq_filters_by_query():
    faq = {
        'categories': [
            {
                'id': 'akun',
                'title': 'Akun',
                'questions': [
                    {'q': 'Apa itu 2FA?', 'a': 'Kode sekali pakai.'},
                    {'q': 'Lupa password?', 'a': 'Gunakan reset password.'},
                ],
            }
        ]
    }
    matches = search_faq(faq, '2fa')
    assert len(matches) == 1
    assert matches[0]['q'] == 'Apa itu 2FA?'


def test_parse_faq_keeps_nested_children():
    from ckanext.sdbi.lib.faq import parse_faq
    parsed = parse_faq({
        'categories': [{
            'id': 'prinsip-satudata',
            'title': 'Prinsip Satudata',
            'children': [
                {
                    'id': 'metadata',
                    'title': 'Metadata',
                    'questions': [],
                },
                {
                    'id': 'kode-referensi',
                    'title': 'Kode Referensi',
                    'children': [
                        {
                            'id': 'penduduk',
                            'title': 'Penduduk',
                            'questions': [
                                {'q': 'Apa kode penduduk?', 'a': 'Kode referensi penduduk.'},
                            ],
                        },
                    ],
                },
            ],
        }],
    })
    root = parsed['categories'][0]
    assert root['children'][0]['id'] == 'metadata'
    assert root['children'][1]['children'][0]['questions'][0]['q'] == 'Apa kode penduduk?'


def test_search_faq_matches_nested_children():
    faq = {
        'categories': [{
            'id': 'prinsip-satudata',
            'title': 'Prinsip Satudata',
            'children': [{
                'id': 'kode-referensi',
                'title': 'Kode Referensi',
                'children': [{
                    'id': 'penduduk',
                    'title': 'Penduduk',
                    'questions': [
                        {'q': 'Apa kode penduduk?', 'a': 'Kode referensi penduduk.'},
                    ],
                }],
            }],
        }]
    }
    matches = search_faq(faq, 'penduduk')
    assert len(matches) == 1
    assert matches[0]['category_id'] == 'penduduk'
    assert matches[0]['q'] == 'Apa kode penduduk?'


def test_parse_faq_rejects_excessive_nesting():
    from ckanext.sdbi.lib.faq import MAX_CATEGORY_DEPTH, parse_faq

    node = {'id': 'leaf', 'title': 'Leaf', 'questions': [{'q': 'Q', 'a': 'A'}]}
    for index in range(MAX_CATEGORY_DEPTH + 1):
        node = {
            'id': 'n%s' % index,
            'title': 'N%s' % index,
            'children': [node],
        }
    with pytest.raises(FaqError):
        parse_faq({'categories': [node]})
