# -*- coding: utf-8 -*-
"""Push tabular rows into DataStore and ensure a DataTables view."""
from __future__ import absolute_import

import csv
import io
import json
import logging
import threading
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

_SYNCING = threading.local()

TABULAR_FORMATS = frozenset({
    'csv', 'tsv', 'xls', 'xlsx',
    'application/csv', 'text/csv', 'text/tab-separated-values',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})


def syncing_datastore():
    return bool(getattr(_SYNCING, 'active', False))


def _cell_value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return json.dumps(value, ensure_ascii=False)


def records_from_dicts(rows):
    records = []
    for item in rows or []:
        if not isinstance(item, dict) or not item:
            continue
        records.append({
            str(key): _cell_value(value) for key, value in item.items()
        })
    return records


def _format_token(format_name, url=''):
    token = (format_name or '').strip().lower()
    if token in TABULAR_FORMATS or token in ('csv', 'tsv', 'xls', 'xlsx'):
        if '/' in token:
            if 'spreadsheetml' in token or token.endswith('xlsx'):
                return 'xlsx'
            if 'ms-excel' in token or token.endswith('xls'):
                return 'xls'
            if 'tab-separated' in token or token.endswith('tsv'):
                return 'tsv'
            return 'csv'
        return token
    path = (urlparse(url or '').path or '').lower()
    for ext in ('xlsx', 'xls', 'tsv', 'csv'):
        if path.endswith('.' + ext):
            return ext
    return ''


def is_remote_tabular_resource(resource):
    """True for http(s) link resources that look like CSV/Excel."""
    if not resource or syncing_datastore():
        return False
    if (resource.get('url_type') or '') == 'upload':
        return False
    url = (resource.get('url') or '').strip()
    if not url.startswith(('http://', 'https://')):
        return False
    return bool(_format_token(resource.get('format'), url))


def records_from_csv_bytes(raw, dialect_hint='excel'):
    text = raw.decode('utf-8-sig', errors='replace')
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel_tab if dialect_hint == 'tsv' else csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return records_from_dicts(list(reader))


def records_from_excel_bytes(raw):
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError('pandas is required to read Excel resources') from exc
    try:
        frame = pd.read_excel(io.BytesIO(raw), dtype=object)
    except ImportError as exc:
        # Missing openpyxl/xlrd
        raise RuntimeError(
            'Excel support needs openpyxl (xlsx) or xlrd (xls) installed'
        ) from exc
    frame = frame.where(frame.notnull(), None)
    return records_from_dicts(frame.to_dict(orient='records'))


def fetch_tabular_records(url, format_name='', timeout=60):
    kind = _format_token(format_name, url)
    if not kind:
        return []
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    raw = response.content
    if kind in ('csv', 'tsv'):
        return records_from_csv_bytes(raw, dialect_hint=kind)
    if kind in ('xls', 'xlsx'):
        return records_from_excel_bytes(raw)
    return []


def ensure_datatables_view(resource_id, context=None):
    from ckan.plugins import toolkit
    ctx = dict(context or {'ignore_auth': True})
    views = toolkit.get_action('resource_view_list')(ctx, {'id': resource_id})
    if any(v.get('view_type') == 'datatables_view' for v in views):
        return
    toolkit.get_action('resource_view_create')(
        ctx,
        {
            'resource_id': resource_id,
            'title': 'Table',
            'view_type': 'datatables_view',
        },
    )


def sync_records_to_resource(resource_id, records, context=None):
    """Replace DataStore rows for resource_id and ensure DataTables view."""
    if not resource_id or not records:
        return False
    from ckan.plugins import toolkit
    ctx = dict(context or {'ignore_auth': True})
    _SYNCING.active = True
    try:
        try:
            toolkit.get_action('datastore_delete')(
                ctx,
                {'resource_id': resource_id, 'force': True, 'filters': {}},
            )
        except Exception:
            pass
        toolkit.get_action('datastore_create')(
            ctx,
            {
                'resource_id': resource_id,
                'force': True,
                'records': records,
            },
        )
        ensure_datatables_view(resource_id, ctx)
        return True
    finally:
        _SYNCING.active = False


def sync_remote_tabular_resource(resource, context=None):
    """Fetch CSV/Excel link resource into DataStore when applicable."""
    if not is_remote_tabular_resource(resource):
        return False
    resource_id = resource.get('id')
    url = resource.get('url')
    try:
        records = fetch_tabular_records(url, resource.get('format') or '')
    except Exception as exc:
        log.warning(
            'Tabular fetch failed for resource %s: %s', resource_id, exc
        )
        return False
    if not records:
        log.info('No tabular rows for resource %s', resource_id)
        return False
    try:
        return sync_records_to_resource(resource_id, records, context=context)
    except Exception as exc:
        log.warning(
            'DataStore sync failed for resource %s: %s', resource_id, exc
        )
        return False
