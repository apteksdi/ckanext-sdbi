#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Import official BPBD contact CSV (Kab/Kota or Provinsi) into sdbi_bpbd.

Run inside the CKAN container, e.g.:

  docker exec -i ckan python /srv/app/src/ckanext-sdbi/scripts/import_bpbd_kontak_csv.py \\
    --csv /srv/app/src/ckanext-sdbi/data/kontak_bpbd_provinsi.csv

By default only the matching tingkat is replaced (kabupaten CSV does not wipe
provinsi rows, and vice versa). Pass --replace-all to wipe the whole table.
"""
from __future__ import print_function

import argparse
import io
import os
import sys
from collections import Counter


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Import BPBD contact CSV (Kab/Kota or Provinsi) into sdbi_bpbd'
    )
    parser.add_argument(
        '--csv',
        required=True,
        help='Path to official contact CSV',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and summarize only; do not write to the database',
    )
    parser.add_argument(
        '--replace-all',
        action='store_true',
        help='Wipe entire sdbi_bpbd table before insert (default: only matching tingkat)',
    )
    parser.add_argument(
        '--db-url',
        default=os.environ.get('CKAN_SQLALCHEMY_URL', ''),
        help='SQLAlchemy URL (default: CKAN_SQLALCHEMY_URL env)',
    )
    args = parser.parse_args(argv)

    csv_path = os.path.abspath(args.csv)
    if not os.path.isfile(csv_path):
        raise SystemExit('CSV not found: %s' % csv_path)

    with io.open(csv_path, 'r', encoding='utf-8-sig') as handle:
        content = handle.read()

    from ckanext.sdbi.lib.bpbd import (
        kontak_csv_to_records_auto,
        records_to_geojson,
        replace_records_via_url,
    )

    kind, records = kontak_csv_to_records_auto(io.StringIO(content))
    with_coords = sum(
        1 for r in records if r.get('lat') is not None and r.get('lng') is not None
    )
    without_coords = len(records) - with_coords
    status_counts = Counter(r.get('status_bpbd') or '(empty)' for r in records)
    mapped = len(records_to_geojson(records).get('features') or [])

    print('CSV: %s' % csv_path)
    print('Detected kind: %s' % kind)
    print('Total rows: %s' % len(records))
    print('With coordinates: %s' % with_coords)
    print('Without coordinates: %s' % without_coords)
    print('GeoJSON features (would map): %s' % mapped)
    print('Status breakdown:')
    for key, count in sorted(status_counts.items()):
        print('  %s: %s' % (key, count))

    if args.dry_run:
        print('Dry run only — database not modified.')
        return 0

    if not args.db_url:
        raise SystemExit(
            'Database URL missing. Pass --db-url or set CKAN_SQLALCHEMY_URL.'
        )

    tingkat = None if args.replace_all else kind
    stored = replace_records_via_url(args.db_url, records, tingkat=tingkat)
    scope = 'entire table' if tingkat is None else ('tingkat=%s only' % tingkat)
    print('Inserted into sdbi_bpbd (%s): %s' % (scope, len(stored)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
