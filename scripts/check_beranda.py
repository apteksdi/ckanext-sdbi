#!/usr/bin/env python3
"""Verifikasi beranda SDBI. Usage: check_beranda.py [base_url] [--expect TEXT ...]"""
import argparse
import re
import sys
import urllib.error
import urllib.request


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:  # noqa
        return 0, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base_url', nargs='?', default='http://localhost:8080')
    ap.add_argument('--expect', action='append', default=[])
    a = ap.parse_args()
    base = a.base_url.rstrip('/')
    fails = []

    st, body = fetch(base + '/')
    if st != 200:
        fails.append('/ status %s' % st)
    for needle in ['class="sdbi-home"', '/css/beranda.css'] + a.expect:
        if needle not in body:
            fails.append('/ missing: %s' % needle)
    if not re.search(r'<script[^>]+src="[^"]*jquery[^"]*"', body, re.I):
        fails.append('/ missing jQuery script tag')
    if 'tracking.js' not in body:
        fails.append('/ missing tracking script')
    for needle in ('site-header__logo-lockup', 'surveyModal'):
        if needle not in body:
            fails.append('/ missing global header/footer marker: %s' % needle)

    for path in ['/dataset', '/organization', '/bantuan', '/tanggap-darurat']:
        st, body = fetch(base + path)
        if st != 200:
            fails.append('%s status %s' % (path, st))
        for bad in ('beranda.css', 'sdbi-home'):
            if bad in body:
                fails.append('%s leaks: %s' % (path, bad))

    if fails:
        print('FAIL')
        for f in fails:
            print(' - ' + f)
        return 1
    print('OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
