# -*- coding: utf-8 -*-
"""Data for the beranda (homepage): category counts, search suggestions,
format summary and top data providers.

Counts are cached in-process for a few minutes: the homepage is the most
visited page and these numbers do not need to be live to the second.
"""
import time

CACHE_SECONDS = 300
FASE_KEYS = ('prabencana', 'saatbencana', 'pascabencana')
KEYWORD_KEYS = ('kejadian', 'dampak')

_caches = {}

# Internal/housekeeping tags that mean nothing to a visitor.
HIDDEN_TAGS = ('sdbi',)


def _cached(key, compute, now):
    """Run compute() at most once per CACHE_SECONDS per key.

    On failure returns the last good value (or None if there never was one).
    """
    now = time.time() if now is None else now
    entry = _caches.get(key)
    if entry and now - entry[0] < CACHE_SECONDS:
        return entry[1]
    try:
        value = compute()
    except Exception:
        return entry[1] if entry else None
    _caches[key] = (now, value)
    return value


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
    return _cached('kategori', lambda: _compute(search or _ckan_search), now)


def _ckan_orgs(data_dict):
    import ckan.plugins.toolkit as toolkit
    return toolkit.get_action('organization_list')({}, data_dict)


def _facet_items(result, field, limit, hidden=()):
    facet = (result.get('search_facets') or {}).get(field) or {}
    items = [
        {'name': i.get('name'), 'count': i.get('count') or 0}
        for i in facet.get('items') or []
        if i.get('name') and i.get('name').lower() not in hidden
    ]
    items.sort(key=lambda i: (-i['count'], i['name'].lower()))
    return items[:limit]


EXAMPLE_QUERY = 'banjir'

# Provider type, matched on the lower-cased organisation title (first match wins).
PROVIDER_TYPES = (
    ('bnpb', ('bpbd', 'bnpb', 'penanggulangan bencana', 'pusat data informasi dan komunikasi kebencanaan')),
    ('ngo', ('ngo', 'yayasan', 'habitat for humanity', 'world vision', 'palang merah')),
    ('kl', ('kementerian', 'lembaga', 'badan')),
)
PROVIDER_TYPE_LABELS = {
    'bnpb': 'BNPB & BPBD',
    'kl': 'Kementerian/Lembaga',
    'ngo': 'NGO',
    'lain': 'Lainnya',
}


def provider_type(title):
    lowered = (title or '').lower()
    for key, words in PROVIDER_TYPES:
        if any(w in lowered for w in words):
            return key
    return 'lain'


def _initials(title):
    return ''.join(w[0] for w in title.split() if w[:1].isalnum())[:2].upper() or '?'


def _example_datasets(search, rows=3):
    result = search({'q': EXAMPLE_QUERY, 'rows': rows})
    items = []
    for pkg in result.get('results') or []:
        formats = []
        for res in pkg.get('resources') or []:
            fmt = (res.get('format') or '').upper()
            if fmt and fmt not in formats:
                formats.append(fmt)
        notes = ' '.join((pkg.get('notes') or '').split())
        items.append({
            'name': pkg.get('name'),
            'title': pkg.get('title') or pkg.get('name'),
            'org': (pkg.get('organization') or {}).get('title') or '',
            'notes': notes[:180] + ('…' if len(notes) > 180 else ''),
            'formats': formats[:4],
            'resources': [
                {'name': r.get('name') or 'Tanpa nama', 'format': (r.get('format') or '').upper()}
                for r in (pkg.get('resources') or [])[:3]
            ],
            'tags': [t.get('display_name') or t.get('name') for t in (pkg.get('tags') or [])
                     if (t.get('name') or '').lower() not in HIDDEN_TAGS][:4],
        })
    return {'query': EXAMPLE_QUERY, 'count': result.get('count') or 0, 'results': items}


def _compute_extras(search, orgs, tag_limit, format_limit, org_limit):
    result = search({
        'rows': 0,
        'facet.field': ['tags', 'res_format'],
        'facet.limit': max(tag_limit, format_limit) + len(HIDDEN_TAGS),
    })
    providers = []
    for org in orgs({'all_fields': True, 'sort': 'package_count desc', 'limit': org_limit}) or []:
        count = org.get('package_count') or 0
        if not count:
            continue
        title = org.get('title') or org.get('name') or ''
        kind = provider_type(title)
        providers.append({
            'name': org.get('name'),
            'title': title,
            'count': count,
            'image': org.get('image_display_url') or '',
            'initials': _initials(title),
            'type': kind,
            'type_label': PROVIDER_TYPE_LABELS[kind],
        })
    top = max([p['count'] for p in providers] or [0])
    for p in providers:
        p['share'] = int(round(p['count'] * 100.0 / top)) if top else 0
    type_counts = []
    for key in ('bnpb', 'kl', 'ngo', 'lain'):
        n = sum(1 for p in providers if p['type'] == key)
        if n:
            type_counts.append({'key': key, 'label': PROVIDER_TYPE_LABELS[key], 'count': n})
    try:
        example = _example_datasets(search)
    except Exception:
        example = None  # the tour still works without live examples
    return {
        'tags': _facet_items(result, 'tags', tag_limit, HIDDEN_TAGS),
        'formats': _facet_items(result, 'res_format', format_limit),
        'providers': providers,
        'provider_types': type_counts,
        'example': example,
    }


def beranda_extras(search=None, orgs=None, now=None, tag_limit=5, format_limit=6, org_limit=8):
    """Popular tags, resource formats and top data providers for the beranda.

    Returns {'tags': [...], 'formats': [...], 'providers': [...]} or None if
    it could never be computed.
    """
    return _cached('extras', lambda: _compute_extras(
        search or _ckan_search, orgs or _ckan_orgs, tag_limit, format_limit, org_limit), now)


def _reset_cache():
    _caches.clear()


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
