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


if __name__ == '__main__':
    unittest.main()
