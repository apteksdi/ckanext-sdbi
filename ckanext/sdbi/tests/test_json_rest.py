# -*- coding: utf-8 -*-
"""Unit tests for JSON REST harvest mapping (no CKAN harvest runtime)."""
import json
import pytest

from ckanext.sdbi.lib.json_rest import (
    DEFAULT_HARVEST_SOURCE_URL,
    JSONRestConfigError,
    apply_dataset_filters,
    build_detail_url,
    build_package_dict,
    dataset_from_source_url,
    default_harvest_config_json,
    extract_datasets_from_list_payload,
    parse_harvest_config,
    resolve_detail_url,
    tabular_records_from_payload,
)

JAKARTA_DETAIL_URL = (
    'https://ws.jakarta.go.id/gateway/DataPortalSatuDataJakarta/1.0/'
    'satudata?kategori=dataset&tipe=detail&url='
    'kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-'
    'pada-layanan-dasar-akibat-bencana'
)


VALID_CONFIG = {
    'datasets': [
        {
            'name': 'kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-pada-layanan-dasar-akibat-bencana',
            'title': 'Kerusakan infrastruktur vital dan gangguan layanan dasar akibat bencana',
            'owner_org': 'bpbd-dki-jakarta',
        }
    ],
    'detail_url_template': (
        'https://ws.jakarta.go.id/gateway/DataPortalSatuDataJakarta/1.0/'
        'satudata?kategori=dataset&tipe=detail&url={name}'
    ),
    'source_portal': 'satudata.jakarta.go.id',
    'default_tags': [
        {'name': 'harvested'},
        {'name': 'satudata-jakarta'},
    ],
    'default_extras': {'license': 'open'},
}


def test_parse_harvest_config_accepts_valid_json():
    parsed = parse_harvest_config(json.dumps(VALID_CONFIG))
    assert len(parsed['datasets']) == 1
    assert parsed['source_portal'] == 'satudata.jakarta.go.id'
    assert parsed['default_tags'][0] == {'name': 'harvested'}


def test_parse_harvest_config_allows_catalog_mode_without_datasets():
    parsed = parse_harvest_config(json.dumps({
        'detail_url_template': 'https://example.com/{name}',
        'default_tags': ['geo'],
    }))
    assert parsed['datasets'] == []
    assert parsed['default_tags'] == [{'name': 'geo'}]


def test_parse_harvest_config_allows_empty_config_for_single_url():
    parsed = parse_harvest_config('')
    assert parsed['datasets'] == []
    assert parsed['detail_url_template'] == ''


def test_parse_harvest_config_allows_single_url_without_template():
    parsed = parse_harvest_config(json.dumps({
        'title': 'Kerusakan infrastruktur vital',
        'default_tags': ['geo'],
    }))
    assert parsed['datasets'] == []
    assert parsed['title'] == 'Kerusakan infrastruktur vital'
    assert parsed['default_tags'] == [{'name': 'geo'}]


def test_parse_harvest_config_rejects_missing_template():
    with pytest.raises(JSONRestConfigError):
        parse_harvest_config(json.dumps({
            'datasets': [{'name': 'a', 'title': 'A'}],
        }))


def test_parse_harvest_config_rejects_list_url_without_template():
    with pytest.raises(JSONRestConfigError):
        parse_harvest_config(json.dumps({
            'list_url': 'https://example.com/datasets',
        }))


def test_parse_harvest_config_rejects_invalid_json():
    with pytest.raises(JSONRestConfigError):
        parse_harvest_config('{not json')


def test_parse_harvest_config_rejects_both_include_and_exclude():
    payload = dict(VALID_CONFIG)
    payload['datasets_filter_include'] = ['a']
    payload['datasets_filter_exclude'] = ['b']
    with pytest.raises(JSONRestConfigError):
        parse_harvest_config(json.dumps(payload))


def test_default_harvest_config_json_is_valid():
    parsed = parse_harvest_config(default_harvest_config_json())
    assert parsed['datasets'] == []
    assert parsed['detail_url_template'] == ''
    assert parsed['source_portal'] == 'satudata.jakarta.go.id'
    assert 'tipe=detail' in DEFAULT_HARVEST_SOURCE_URL
    assert parsed['title']


def test_dataset_from_source_url_reads_jakarta_query():
    remote = dataset_from_source_url(
        JAKARTA_DETAIL_URL,
        {'title': 'Kerusakan infrastruktur vital'},
    )
    assert remote['name'] == (
        'kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-'
        'pada-layanan-dasar-akibat-bencana'
    )
    assert remote['title'] == 'Kerusakan infrastruktur vital'
    assert remote['detail_url'] == JAKARTA_DETAIL_URL


def test_dataset_from_source_url_rejects_unusable_url():
    with pytest.raises(JSONRestConfigError):
        dataset_from_source_url('https://satudata.jakarta.go.id/', {})


def test_resolve_detail_url_prefers_remote():
    url = resolve_detail_url(
        {'name': 'other', 'detail_url': JAKARTA_DETAIL_URL},
        VALID_CONFIG,
    )
    assert url == JAKARTA_DETAIL_URL


def test_build_detail_url_substitutes_name():
    url = build_detail_url(VALID_CONFIG, VALID_CONFIG['datasets'][0]['name'])
    assert url.endswith(
        'url=kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-pada-layanan-dasar-akibat-bencana'
    )


def test_extract_datasets_from_jakarta_style_list():
    payload = {
        'data': [
            {'url': 'banjir-2024', 'nama': 'Banjir 2024'},
            {'name': 'gempa', 'title': 'Gempa'},
        ]
    }
    datasets = extract_datasets_from_list_payload(payload)
    assert datasets[0] == {'name': 'banjir-2024', 'title': 'Banjir 2024'}
    assert datasets[1]['name'] == 'gempa'


def test_extract_datasets_from_ckan_style_list():
    payload = {
        'result': {
            'results': [
                {'name': 'floods', 'title': 'Flood events'},
            ]
        }
    }
    datasets = extract_datasets_from_list_payload(payload)
    assert datasets == [{'name': 'floods', 'title': 'Flood events'}]


def test_apply_dataset_filters_include():
    datasets = [
        {'name': 'keep', 'title': 'Keep'},
        {'name': 'drop', 'title': 'Drop'},
    ]
    filtered = apply_dataset_filters(
        datasets,
        {'datasets_filter_include': ['keep'], 'datasets_filter_exclude': []},
    )
    assert [item['name'] for item in filtered] == ['keep']


def test_tabular_records_from_jakarta_payload():
    payload = {
        'data': [
            {'periode_data': '2025', 'wilayah': 'JAKARTA BARAT', 'jumlah': '1'},
            {'periode_data': '2025', 'wilayah': 'JAKARTA TIMUR', 'meta': {'x': 1}},
        ],
        'total_file': 2,
        'message': 'success',
    }
    records = tabular_records_from_payload(payload)
    assert len(records) == 2
    assert records[0]['wilayah'] == 'JAKARTA BARAT'
    assert records[1]['meta'] == '{"x": 1}'


def test_tabular_records_from_list_payload():
    records = tabular_records_from_payload([{'a': 1}, {'a': 2}])
    assert records == [{'a': 1}, {'a': 2}]


def test_tabular_records_empty_for_non_tabular():
    assert tabular_records_from_payload({'message': 'ok'}) == []
    assert tabular_records_from_payload(None) == []
    assert tabular_records_from_payload({'data': 'not-a-list'}) == []


def test_build_package_dict_maps_jakarta_payload_to_ckan_dataset():
    remote = VALID_CONFIG['datasets'][0]
    payload = {
        'data': [{'periode_data': '2025', 'wilayah': 'KOTA ADM. JAKARTA BARAT'}],
        'total_file': 1,
        'message': 'success',
    }
    package = build_package_dict(
        remote=remote,
        config=parse_harvest_config(json.dumps(VALID_CONFIG)),
        payload=payload,
        harvest_source_title='Satu Data Jakarta',
    )

    assert package['name'].startswith('sdbi-')
    assert package['title'] == remote['title']
    assert package['owner_org'] == 'bpbd-dki-jakarta'
    assert {'name': 'harvested'} in package['tags']
    assert {'name': 'satudata-jakarta'} in package['tags']
    extras = {item['key']: item['value'] for item in package['extras']}
    assert extras['source_portal'] == 'satudata.jakarta.go.id'
    assert extras['remote_name'] == remote['name']
    assert extras['record_count'] == '1'
    assert extras['license'] == 'open'
    assert package['resources'][0]['format'] == 'JSON'
    assert remote['name'] in package['resources'][0]['url']


def test_build_package_dict_handles_empty_payload():
    remote = VALID_CONFIG['datasets'][0]
    package = build_package_dict(
        remote=remote,
        config=parse_harvest_config(json.dumps(VALID_CONFIG)),
        payload=None,
        harvest_source_title='Satu Data Jakarta',
    )
    extras = {item['key']: item['value'] for item in package['extras']}
    assert extras['record_count'] == '0'
    assert package['resources']


def test_build_package_dict_uses_remote_detail_url():
    remote = {
        'name': 'kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-pada-layanan-dasar-akibat-bencana',
        'title': 'Kerusakan infrastruktur vital',
        'detail_url': JAKARTA_DETAIL_URL,
    }
    config = parse_harvest_config(json.dumps({
        'title': 'Kerusakan infrastruktur vital',
        'source_portal': 'satudata.jakarta.go.id',
        'default_tags': [{'name': 'harvested'}],
    }))
    package = build_package_dict(
        remote=remote,
        config=config,
        payload={'data': [{'wilayah': 'KOTA ADM. JAKARTA BARAT'}], 'total_file': 1},
        harvest_source_title='Satu Data Jakarta',
    )
    assert package['resources'][0]['url'] == JAKARTA_DETAIL_URL
    extras = {item['key']: item['value'] for item in package['extras']}
    assert extras['record_count'] == '1'
