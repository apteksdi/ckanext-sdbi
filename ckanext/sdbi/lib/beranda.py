# -*- coding: utf-8 -*-
"""Data for the beranda (homepage) category cards.

Counts are cached in-process for a few minutes: the homepage is the most
visited page and these numbers do not need to be live to the second.
"""
import time

CACHE_SECONDS = 300
FASE_KEYS = ('prabencana', 'saatbencana', 'pascabencana')
KEYWORD_KEYS = ('kejadian', 'dampak')

_cache = {'at': None, 'value': None}


def _ckan_search(data_dict):
    import ckan.plugins.toolkit as toolkit
    return toolkit.get_action('package_search')({}, data_dict)


def _compute(search):
    counts = {key: 0 for key in FASE_KEYS + KEYWORD_KEYS}
    counts['total'] = 0

    result = search({'rows': 0, 'facet.field': ['fase'], 'facet.limit': -1})
    counts['total'] = result.get('count') or 0
    fase = (result.get('search_facets') or {}).get('fase') or {}
    for item in fase.get('items') or []:
        if item.get('name') in FASE_KEYS:
            counts[item['name']] = item.get('count') or 0

    for keyword in KEYWORD_KEYS:
        counts[keyword] = search({'rows': 0, 'q': keyword}).get('count') or 0
    return counts


def kategori_counts(search=None, now=None):
    """Return dataset counts per beranda category.

    Keys: kejadian, dampak, prabencana, saatbencana, pascabencana, total.
    On a search failure returns None so the template can hide the counts
    instead of showing misleading zeros.
    """
    now = time.time() if now is None else now
    if _cache['at'] is not None and now - _cache['at'] < CACHE_SECONDS:
        return _cache['value']
    try:
        value = _compute(search or _ckan_search)
    except Exception:
        return _cache['value']  # last good value (or None) on failure
    _cache['at'] = now
    _cache['value'] = value
    return value


def _reset_cache():
    _cache['at'] = None
    _cache['value'] = None


def waktu_relatif(iso_value, now=None):
    """'hari ini' / 'kemarin' / '3 hari lalu' / '2 bulan lalu' / '1 tahun lalu'.

    iso_value: CKAN metadata timestamp string (UTC, e.g. '2026-11-20T08:15:00.123456').
    Returns '' when the value can't be parsed.
    """
    import datetime
    if not iso_value:
        return ''
    try:
        then = datetime.datetime.fromisoformat(str(iso_value).replace('Z', '')[:26])
    except ValueError:
        return ''
    now = now or datetime.datetime.utcnow()
    days = (now.date() - then.date()).days
    if days <= 0:
        return 'hari ini'
    if days == 1:
        return 'kemarin'
    if days < 7:
        return '%d hari lalu' % days
    if days < 30:
        return '%d minggu lalu' % (days // 7)
    if days < 365:
        return '%d bulan lalu' % (days // 30)
    return '%d tahun lalu' % (days // 365)
