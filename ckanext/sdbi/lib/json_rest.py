# -*- coding: utf-8 -*-
"""Pure mapping helpers for the JSON REST harvester."""
import json
import re
import uuid

try:
    from urllib.parse import parse_qs, quote, urlparse
except ImportError:
    from urllib import quote
    from urlparse import parse_qs, urlparse


class JSONRestConfigError(ValueError):
    pass


_NAME_RE = re.compile(r'[^a-z0-9\-]+')
_LIST_NAME_KEYS = ('name', 'url', 'slug', 'id', 'kode', 'kode_dataset', 'identifier')
_LIST_TITLE_KEYS = ('title', 'nama', 'judul', 'name', 'label')
_LIST_CONTAINER_KEYS = ('data', 'datasets', 'results', 'items', 'records')
_QUERY_NAME_KEYS = ('url', 'name', 'id', 'slug', 'dataset')
_GENERIC_PATH_SEGMENTS = frozenset((
    'satudata', 'api', 'dataset', 'datasets', 'data', 'list', 'detail',
    '1.0', 'gateway',
))

DEFAULT_HARVEST_SOURCE_URL = (
    'https://ws.jakarta.go.id/gateway/DataPortalSatuDataJakarta/1.0/'
    'satudata?kategori=dataset&tipe=detail&url='
    'kerusakan-pada-infrastruktur-vital-dan-jumlah-gangguan-'
    'pada-layanan-dasar-akibat-bencana'
)
DEFAULT_HARVEST_CONFIG = {
    'title': (
        'Kerusakan infrastruktur vital dan gangguan layanan dasar '
        'akibat bencana'
    ),
    'source_portal': 'satudata.jakarta.go.id',
    'default_tags': [
        {'name': 'harvested'},
        {'name': 'satudata-jakarta'},
    ],
    'default_extras': {},
}


def default_harvest_config_json():
    return json.dumps(DEFAULT_HARVEST_CONFIG, indent=2, ensure_ascii=False)


def json_harvest_form_defaults():
    return {
        'config': default_harvest_config_json(),
        'url': DEFAULT_HARVEST_SOURCE_URL,
        'source_type': 'sdbi_json_harvester',
    }


def _normalize_tags(tags):
    normalized = []
    seen = set()
    for tag in tags or []:
        if isinstance(tag, dict):
            name = tag.get('name')
        else:
            name = tag
        if not name:
            continue
        name = str(name).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append({'name': name})
    if not normalized:
        normalized.append({'name': 'harvested'})
    return normalized


def _normalize_extras(extras):
    if not extras:
        return {}
    if isinstance(extras, dict):
        return extras
    raise JSONRestConfigError('default_extras must be a JSON object')


def parse_harvest_config(config_str):
    if config_str is None or not str(config_str).strip():
        config = {}
    else:
        try:
            config = json.loads(config_str)
        except ValueError as exc:
            raise JSONRestConfigError('Harvest config must be valid JSON') from exc
        if not isinstance(config, dict):
            raise JSONRestConfigError('Harvest config must be a JSON object')
    template = config.get('detail_url_template') or ''
    datasets = config.get('datasets')
    if datasets is None:
        datasets = []
    if not isinstance(datasets, list):
        raise JSONRestConfigError('datasets must be a list when provided')
    for item in datasets:
        if not isinstance(item, dict) or not item.get('name'):
            raise JSONRestConfigError('each dataset needs a name')
        if not item.get('title'):
            item['title'] = item['name']
    include = config.get('datasets_filter_include') or []
    exclude = config.get('datasets_filter_exclude') or []
    if include and exclude:
        raise JSONRestConfigError(
            'cannot set both datasets_filter_include and datasets_filter_exclude'
        )
    if not isinstance(include, list) or not isinstance(exclude, list):
        raise JSONRestConfigError('dataset filters must be lists of names')
    list_url = config.get('list_url') or ''
    needs_template = bool(datasets) or bool(list_url)
    if template and '{name}' not in str(template):
        raise JSONRestConfigError(
            'detail_url_template must include {name}'
        )
    if needs_template and '{name}' not in str(template):
        raise JSONRestConfigError(
            'detail_url_template must include {name}'
        )
    config['datasets'] = datasets
    config['datasets_filter_include'] = [str(item) for item in include]
    config['datasets_filter_exclude'] = [str(item) for item in exclude]
    config['detail_url_template'] = template
    config.setdefault('title', '')
    config.setdefault('source_portal', '')
    config['list_url'] = list_url
    config['default_tags'] = _normalize_tags(config.get('default_tags'))
    config['default_extras'] = _normalize_extras(config.get('default_extras'))
    return config


def build_detail_url(config, name):
    template = config['detail_url_template']
    return template.replace('{name}', quote(str(name), safe='-._~'))


def dataset_from_source_url(source_url, config=None):
    if not source_url or not str(source_url).strip():
        raise JSONRestConfigError('Harvest URL is required')
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query)
    name = None
    for key in _QUERY_NAME_KEYS:
        values = query.get(key)
        if values and str(values[0]).strip():
            name = str(values[0]).strip()
            break
    if not name:
        segment = (parsed.path or '').rstrip('/').split('/')[-1]
        if segment and segment.lower() not in _GENERIC_PATH_SEGMENTS:
            name = segment
    if not name:
        raise JSONRestConfigError(
            'Cannot derive dataset name from harvest URL. '
            'Use a detail URL with url= (or name=), or add datasets[] plus '
            'detail_url_template.'
        )
    title = (config or {}).get('title') or name.replace('-', ' ')
    return {
        'name': name,
        'title': title,
        'detail_url': source_url,
    }


def resolve_detail_url(remote, config):
    if remote.get('detail_url'):
        return remote['detail_url']
    template = (config or {}).get('detail_url_template') or ''
    if template and '{name}' in str(template) and remote.get('name'):
        return build_detail_url(config, remote['name'])
    raise JSONRestConfigError(
        'No detail URL for dataset %s' % remote.get('name')
    )


def attach_detail_urls(datasets, config):
    attached = []
    for item in datasets:
        remote = dict(item)
        remote['detail_url'] = resolve_detail_url(remote, config)
        attached.append(remote)
    return attached


def _first_value(item, keys):
    for key in keys:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _find_list_container(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in _LIST_CONTAINER_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    result = payload.get('result')
    if isinstance(result, dict):
        results = result.get('results')
        if isinstance(results, list):
            return results
    return []


def extract_datasets_from_list_payload(payload):
    datasets = []
    for item in _find_list_container(payload):
        if isinstance(item, str) and item.strip():
            datasets.append({'name': item.strip(), 'title': item.strip()})
            continue
        if not isinstance(item, dict):
            continue
        name = _first_value(item, _LIST_NAME_KEYS)
        if not name:
            continue
        title = _first_value(item, _LIST_TITLE_KEYS) or name
        datasets.append({'name': name, 'title': title})
    return datasets


def apply_dataset_filters(datasets, config):
    include = config.get('datasets_filter_include') or []
    exclude = config.get('datasets_filter_exclude') or []
    if include:
        allowed = set(include)
        datasets = [item for item in datasets if item['name'] in allowed]
    if exclude:
        blocked = set(exclude)
        datasets = [item for item in datasets if item['name'] not in blocked]
    return datasets


def _munge_name(value):
    slug = str(value or '').strip().lower().replace('_', '-')
    slug = _NAME_RE.sub('-', slug).strip('-')
    slug = re.sub(r'-{2,}', '-', slug)
    return slug or 'dataset'


def _stable_id(source_portal, remote_name):
    seed = u'%s:%s' % (source_portal or 'json-rest', remote_name)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _cell_value(value):
    """Coerce nested JSON values to DataStore-friendly scalars."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return json.dumps(value, ensure_ascii=False)


def tabular_records_from_payload(payload):
    """
    Extract a flat table from a JSON REST payload for DataStore.

    Supports Jakarta-style ``{"data": [ {...}, ... ]}`` and a bare list of
    objects. Returns [] when the payload is not tabular (so harvest still
    succeeds as a JSON link only).
    """
    if not payload:
        return []
    rows = None
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        data = payload.get('data')
        if isinstance(data, list):
            rows = data
    if not rows:
        return []
    records = []
    for item in rows:
        if not isinstance(item, dict) or not item:
            continue
        records.append({
            str(key): _cell_value(value) for key, value in item.items()
        })
    return records


def _record_count(payload):
    if not payload:
        return 0
    tabular = tabular_records_from_payload(payload)
    if tabular:
        return len(tabular)
    if isinstance(payload, dict) and payload.get('total_file') is not None:
        try:
            return int(payload['total_file'])
        except (TypeError, ValueError):
            return 0
    if isinstance(payload, list):
        return len(payload)
    return 0


def _notes_from_payload(remote, payload, source_portal):
    parts = [
        remote.get('notes') or remote.get('title') or '',
        'Sumber: %s' % (source_portal or 'JSON REST'),
    ]
    count = _record_count(payload)
    if count:
        parts.append('Jumlah rekaman pada harvest terakhir: %s.' % count)
    return '\n\n'.join([part for part in parts if part])


def build_package_dict(remote, config, payload, harvest_source_title=''):
    source_portal = config.get('source_portal') or ''
    remote_name = remote['name']
    title = remote.get('title') or remote_name
    name = ('sdbi-' + _munge_name(remote_name))[:100]
    tags = list(config.get('default_tags') or [{'name': 'harvested'}])
    extras = [
        {'key': 'source_portal', 'value': source_portal},
        {'key': 'remote_name', 'value': remote_name},
        {'key': 'harvest_source', 'value': harvest_source_title or source_portal},
        {'key': 'record_count', 'value': str(_record_count(payload))},
    ]
    for key, value in (config.get('default_extras') or {}).items():
        extras.append({'key': str(key), 'value': str(value)})
    package = {
        'id': _stable_id(source_portal, remote_name),
        'name': name,
        'title': title,
        'notes': _notes_from_payload(remote, payload, source_portal),
        'owner_org': remote.get('owner_org'),
        'tags': tags,
        'extras': extras,
        'resources': [{
            'url': resolve_detail_url(remote, config),
            'name': title,
            'format': 'JSON',
            'description': 'API sumber dari %s' % (source_portal or 'portal asal'),
        }],
    }
    return package
