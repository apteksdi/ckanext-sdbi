# -*- coding: utf-8 -*-
import json
import logging

from flask import Blueprint, abort, redirect, request, jsonify

import ckan.authz as authz
from ckan.plugins import toolkit

from ckanext.sdbi.lib.faq import FaqError, load_faq, parse_faq, search_faq
from ckanext.sdbi.lib.settings import KEY_FAQ, set_json

log = logging.getLogger(__name__)

bantuan_blueprint = Blueprint('bantuan', __name__)


def _current_username():
    return getattr(toolkit.current_user, 'name', None) or ''


def _require_sysadmin():
    if not authz.is_sysadmin(_current_username()):
        abort(403, description='Access denied. Admin privileges required.')


def _is_sysadmin():
    return authz.is_sysadmin(_current_username())


def _faq():
    return load_faq()


def _pretty(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def _map_category(category):
    return {
        'id': category.get('id'),
        'title': category.get('title'),
        'entries': list(category.get('questions') or []),
        'children': [
            _map_category(child) for child in (category.get('children') or [])
        ],
    }


@bantuan_blueprint.route('/bantuan', methods=['GET'])
def index():
    try:
        faq = _faq()
    except FaqError:
        faq = {'categories': []}
    faq_categories = [
        _map_category(category) for category in (faq.get('categories') or [])
    ]
    return toolkit.render(
        'bantuan/index.html',
        extra_vars={
            'faq_categories': faq_categories,
            'is_sysadmin': _is_sysadmin(),
        },
    )


@bantuan_blueprint.route('/bantuan/search', methods=['GET'])
def search():
    query = request.args.get('q') or ''
    try:
        faq = _faq()
    except FaqError:
        return jsonify({'results': []})
    return jsonify({'results': search_faq(faq, query)})


@bantuan_blueprint.route('/bantuan/kelola', methods=['GET', 'POST'])
def kelola():
    _require_sysadmin()
    error = None
    saved = request.args.get('saved') == '1'
    payload = ''
    if request.method == 'POST':
        payload = request.form.get('payload') or ''
        try:
            parsed = parse_faq(json.loads(payload))
            set_json(KEY_FAQ, parsed, _current_username())
            return redirect('/bantuan/kelola?saved=1')
        except (ValueError, TypeError, FaqError) as exc:
            error = str(exc)
            saved = False
    if not payload:
        try:
            payload = _pretty(_faq())
        except FaqError as exc:
            error = error or str(exc)
            payload = '{\n  "categories": []\n}'
    return toolkit.render(
        'bantuan/kelola.html',
        extra_vars={
            'payload': payload,
            'error': error,
            'saved': saved,
        },
    )
