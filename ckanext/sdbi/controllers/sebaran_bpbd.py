# -*- coding: utf-8 -*-
from flask import Blueprint, Response, request, abort, jsonify
import io

from ckan.plugins import toolkit
import ckan.authz as authz

from ckanext.sdbi.lib.bpbd import (
    BpbdImportError,
    csv_to_records,
    geojson_to_csv,
    load_geojson,
    load_records,
    records_to_geojson,
    replace_records,
)

sebaran_bpbd_blueprint = Blueprint('sebaran_bpbd', __name__)


def _require_sysadmin():
    user = getattr(toolkit.current_user, 'name', None) or ''
    if not authz.is_sysadmin(user):
        abort(403, description='Access denied. Admin privileges required.')


def _load_bpbd_geojson():
    return load_geojson()


@sebaran_bpbd_blueprint.route('/sebaran-bpbd', methods=['GET'])
def index():
    geojson = _load_bpbd_geojson()
    return toolkit.render(
        'sebaran_bpbd/index.html',
        extra_vars={
            'bpbd_count': len(geojson.get('features') or []),
        },
    )


@sebaran_bpbd_blueprint.route('/sebaran-bpbd/data.geojson', methods=['GET'])
def data_geojson():
    return jsonify(_load_bpbd_geojson())


@sebaran_bpbd_blueprint.route('/sebaran-bpbd/data.csv', methods=['GET'])
def data_csv():
    csv_text = geojson_to_csv(_load_bpbd_geojson())
    return Response(
        csv_text.encode('utf-8-sig'),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="sebaran-bpbd.csv"',
        },
    )


@sebaran_bpbd_blueprint.route('/sebaran-bpbd/import', methods=['POST'])
def import_csv():
    _require_sysadmin()
    uploaded = request.files.get('csv')
    if not uploaded:
        return _import_error('Berkas CSV wajib diunggah.')
    try:
        content = uploaded.read().decode('utf-8-sig')
        records = csv_to_records(io.StringIO(content))
        stored = replace_records(records)
        geojson = records_to_geojson(stored)
    except BpbdImportError as exc:
        return _import_error(str(exc))
    except Exception as exc:
        return _import_error('Impor gagal: %s' % exc)
    return jsonify({
        'success': True,
        'imported': len(stored),
        'mapped': len(geojson.get('features') or []),
        'total_db': len(load_records()),
    })


def _import_error(message, status=400):
    return jsonify({'success': False, 'error': message}), status
