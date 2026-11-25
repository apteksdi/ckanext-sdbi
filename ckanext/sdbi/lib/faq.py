# -*- coding: utf-8 -*-
"""FAQ JSON loader and client-side search helper."""
import os

import yaml

from ckanext.sdbi.lib.settings import KEY_FAQ, get_json, resolve_json


class FaqError(ValueError):
    pass


DEFAULT_FILE_LABEL = u'Referensi File'
MAX_CATEGORY_DEPTH = 8


def _empty_faq():
    return {'categories': []}


def _http_url(url, field='file_url'):
    raw = (url or '').strip()
    if not raw:
        return ''
    if not (raw.startswith('http://') or raw.startswith('https://')):
        raise FaqError('%s must be http or https' % field)
    return raw


def _parse_faq_item(item):
    if not isinstance(item, dict) or not item.get('q') or not item.get('a'):
        raise FaqError('Each FAQ item needs q and a')
    entry = {'q': item['q'], 'a': item['a']}
    file_url = _http_url(item.get('file_url') or '')
    if file_url:
        label = (item.get('file_label') or '').strip() or DEFAULT_FILE_LABEL
        entry['file_url'] = file_url
        entry['file_label'] = label
    return entry


def _parse_faq_category(category, depth=0):
    if depth > MAX_CATEGORY_DEPTH:
        raise FaqError('FAQ category nesting exceeds max depth (%s)' % MAX_CATEGORY_DEPTH)
    if not isinstance(category, dict):
        raise FaqError('Each FAQ category must be an object')
    if not category.get('id') or not category.get('title'):
        raise FaqError('Each FAQ category needs id and title')
    questions = category.get('questions') or category.get('items') or []
    if not isinstance(questions, list):
        raise FaqError('FAQ category questions must be a list')
    children = category.get('children') or []
    if not isinstance(children, list):
        raise FaqError('FAQ category children must be a list')
    entry = {
        'id': category['id'],
        'title': category['title'],
        'questions': [_parse_faq_item(item) for item in questions],
    }
    if children:
        entry['children'] = [
            _parse_faq_category(child, depth + 1) for child in children
        ]
    return entry


def parse_faq(data):
    if not isinstance(data, dict):
        raise FaqError('FAQ must be a JSON object')
    categories = data.get('categories')
    if not isinstance(categories, list):
        raise FaqError('FAQ must contain a categories list')
    cleaned = [_parse_faq_category(category) for category in categories]
    return {'categories': cleaned}


def _read_yaml(path):
    if not path or not os.path.isfile(path):
        raise FaqError('FAQ file not found: %s' % path)
    with open(path, 'r') as handle:
        return yaml.safe_load(handle) or {}


def load_faq(path=None):
    """Load FAQ from a YAML path (tests), or from sdbi_settings."""
    if path:
        return parse_faq(_read_yaml(path))
    return resolve_json(parse_faq, get_json(KEY_FAQ), _empty_faq)


def _search_category(category, needle, matches):
    for item in category.get('questions') or []:
        haystack = u' '.join([
            item.get('q') or '',
            item.get('a') or '',
            item.get('file_label') or '',
            item.get('file_url') or '',
            category.get('title') or '',
        ]).lower()
        if needle in haystack:
            match = {
                'category_id': category.get('id'),
                'category_title': category.get('title'),
                'q': item.get('q'),
                'a': item.get('a'),
            }
            if item.get('file_url'):
                match['file_url'] = item.get('file_url')
                match['file_label'] = item.get('file_label') or DEFAULT_FILE_LABEL
            matches.append(match)
    for child in category.get('children') or []:
        _search_category(child, needle, matches)


def search_faq(faq, query):
    needle = (query or '').strip().lower()
    if not needle:
        return []
    matches = []
    for category in faq.get('categories') or []:
        _search_category(category, needle, matches)
    return matches
