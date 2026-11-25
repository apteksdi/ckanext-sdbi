# -*- coding: utf-8 -*-
"""Unit tests for beranda category counts (stdlib unittest, no CKAN needed)."""
import unittest

from ckanext.sdbi.lib import beranda


def fake_search(data_dict):
    if 'facet.field' in data_dict:
        return {'count': 184, 'search_facets': {'fase': {'items': [
            {'name': 'saatbencana', 'count': 11},
            {'name': 'prabencana', 'count': 1},
            {'name': 'pascabencana', 'count': 28},
            {'name': 'lain', 'count': 99},
        ]}}}
    return {'count': {'kejadian': 41, 'dampak': 30}[data_dict['q']]}


class KategoriCountsTest(unittest.TestCase):
    def setUp(self):
        beranda._reset_cache()

    def test_counts_from_facets_and_keywords(self):
        self.assertEqual(beranda.kategori_counts(fake_search, now=0), {
            'total': 184, 'prabencana': 1, 'saatbencana': 11,
            'pascabencana': 28, 'kejadian': 41, 'dampak': 30,
        })

    def test_missing_facet_gives_zero(self):
        def search(d):
            return {'count': 5} if 'facet.field' in d else {'count': 2}
        counts = beranda.kategori_counts(search, now=0)
        self.assertEqual(counts['prabencana'], 0)
        self.assertEqual(counts['total'], 5)

    def test_cached_within_ttl(self):
        calls = []

        def search(d):
            calls.append(d)
            return fake_search(d)
        beranda.kategori_counts(search, now=0)
        n = len(calls)
        beranda.kategori_counts(search, now=beranda.CACHE_SECONDS - 1)
        self.assertEqual(len(calls), n)
        beranda.kategori_counts(search, now=beranda.CACHE_SECONDS + 1)
        self.assertGreater(len(calls), n)

    def test_failure_returns_none_without_cache(self):
        def boom(d):
            raise RuntimeError('solr down')
        self.assertIsNone(beranda.kategori_counts(boom, now=0))

    def test_failure_keeps_last_good_value(self):
        good = beranda.kategori_counts(fake_search, now=0)

        def boom(d):
            raise RuntimeError('solr down')
        self.assertEqual(beranda.kategori_counts(boom, now=beranda.CACHE_SECONDS + 1), good)


class WaktuRelatifTest(unittest.TestCase):
    def test_ranges(self):
        import datetime
        now = datetime.datetime(2026, 11, 25, 12, 0)
        cases = {
            '2026-11-25T01:00:00.000000': 'hari ini',
            '2026-11-24T23:59:00': 'kemarin',
            '2026-11-20T08:15:00.123456': '5 hari lalu',
            '2026-11-04T00:00:00': '3 minggu lalu',
            '2026-08-25T00:00:00': '3 bulan lalu',
            '2023-11-01T00:00:00Z': '3 tahun lalu',
            '': '',
            'bukan tanggal': '',
        }
        for value, expected in cases.items():
            self.assertEqual(beranda.waktu_relatif(value, now=now), expected, value)



def extras_search(data_dict):
    if data_dict.get('q') == 'banjir':
        return {'count': 24, 'results': [{
            'name': 'banjir-aceh', 'title': 'Rekapitulasi Banjir Aceh',
            'organization': {'title': 'BPBD Provinsi Aceh'},
            'notes': 'Data   kejadian\nbanjir ' + 'x' * 300,
            'resources': [{'name': 'Tabel', 'format': 'csv'}, {'name': 'Peta', 'format': 'GeoJSON'},
                          {'name': 'Tabel 2', 'format': 'CSV'}],
            'tags': [{'name': 'sdbi'}, {'name': 'banjir', 'display_name': 'banjir'}],
        }]}
    return {'count': 184, 'search_facets': {
        'tags': {'items': [
            {'name': 'sdbi', 'count': 100}, {'name': 'bencana', 'count': 128},
            {'name': 'kejadian', 'count': 34}, {'name': '2026', 'count': 50},
        ]},
        'res_format': {'items': [
            {'name': 'CSV', 'count': 100}, {'name': 'GeoJSON', 'count': 100},
            {'name': 'XLSX', 'count': 17},
        ]},
    }}


def extras_orgs(data_dict):
    return [
        {'name': 'pusdatinkom', 'title': 'Pusat Data Informasi dan Komunikasi Kebencanaan',
         'package_count': 78, 'image_display_url': 'http://x/logo.png'},
        {'name': 'pvmbg', 'title': 'Badan Geologi PVMBG', 'package_count': 5},
        {'name': 'kosong', 'title': 'Org Kosong', 'package_count': 0},
    ]


class BerandaExtrasTest(unittest.TestCase):
    def setUp(self):
        beranda._reset_cache()

    def test_tags_hide_internal_and_sort_by_count(self):
        extras = beranda.beranda_extras(extras_search, extras_orgs, now=0, tag_limit=2)
        self.assertEqual([t['name'] for t in extras['tags']], ['bencana', '2026'])

    def test_formats_tie_broken_by_name(self):
        extras = beranda.beranda_extras(extras_search, extras_orgs, now=0)
        self.assertEqual([f['name'] for f in extras['formats']], ['CSV', 'GeoJSON', 'XLSX'])

    def test_providers_skip_empty_and_build_initials(self):
        providers = beranda.beranda_extras(extras_search, extras_orgs, now=0)['providers']
        self.assertEqual([p['name'] for p in providers], ['pusdatinkom', 'pvmbg'])
        self.assertEqual(providers[0]['image'], 'http://x/logo.png')
        self.assertEqual(providers[1]['image'], '')
        self.assertEqual(providers[1]['initials'], 'BG')

    def test_extras_and_kategori_cached_independently(self):
        beranda.kategori_counts(fake_search, now=0)
        extras = beranda.beranda_extras(extras_search, extras_orgs, now=1)
        self.assertEqual(extras['formats'][0]['name'], 'CSV')

    def test_extras_failure_returns_none(self):
        def boom(d):
            raise RuntimeError('down')
        self.assertIsNone(beranda.beranda_extras(boom, extras_orgs, now=0))


class ProviderTypeTest(unittest.TestCase):
    def test_types(self):
        cases = {
            'Pusat Data Informasi dan Komunikasi Kebencanaan': 'bnpb',
            'BPBD Kabupaten Lumajang': 'bnpb',
            'Badan Nasional Penanggulangan Bencana': 'bnpb',
            'Badan Geologi PVMBG': 'kl',
            'Badan Meteorologi Klimatologi dan Geofisika': 'kl',
            'NGO World Vision Indonesia': 'ngo',
            'NGO Habitat for Humanity Indonesia': 'ngo',
            'Universitas Gadjah Mada': 'lain',
        }
        for title, expected in cases.items():
            self.assertEqual(beranda.provider_type(title), expected, title)


class ExtrasTourAndShareTest(unittest.TestCase):
    def setUp(self):
        beranda._reset_cache()

    def test_provider_share_and_type_counts(self):
        extras = beranda.beranda_extras(extras_search, extras_orgs, now=0)
        self.assertEqual([p['share'] for p in extras['providers']], [100, 6])
        self.assertEqual([p['type'] for p in extras['providers']], ['bnpb', 'kl'])
        self.assertEqual(extras['provider_types'], [
            {'key': 'bnpb', 'label': 'BNPB & BPBD', 'count': 1},
            {'key': 'kl', 'label': 'Kementerian/Lembaga', 'count': 1},
        ])

    def test_example_datasets_trimmed(self):
        example = beranda.beranda_extras(extras_search, extras_orgs, now=0)['example']
        self.assertEqual(example['query'], 'banjir')
        self.assertEqual(example['count'], 24)
        item = example['results'][0]
        self.assertEqual(item['formats'], ['CSV', 'GEOJSON'])
        self.assertTrue(item['notes'].startswith('Data kejadian banjir'))
        self.assertTrue(item['notes'].endswith('…'))
        self.assertEqual(item['tags'], ['banjir'])
        self.assertEqual(len(item['resources']), 3)

    def test_example_failure_keeps_rest(self):
        def search(d):
            if d.get('q') == 'banjir':
                raise RuntimeError('boom')
            return extras_search(d)
        extras = beranda.beranda_extras(search, extras_orgs, now=0)
        self.assertIsNone(extras['example'])
        self.assertEqual(extras['formats'][0]['name'], 'CSV')


if __name__ == '__main__':
    unittest.main()
