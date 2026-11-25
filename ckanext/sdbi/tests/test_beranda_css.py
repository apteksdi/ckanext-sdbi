"""Guard isolasi CSS beranda (unittest stdlib)."""
import os
import re
import unittest

CSS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'public', 'css', 'beranda.css')

SKIP_AT = ('@media', '@supports', '@keyframes', '@-webkit-keyframes')


def _load():
    with open(CSS_PATH, encoding='utf-8') as f:
        return re.sub(r'/\*.*?\*/', '', f.read(), flags=re.S)


class BerandaCssGuard(unittest.TestCase):
    def test_all_selectors_scoped(self):
        css = _load()
        bad = []
        for prelude in re.findall(r'([^{}]+)\{', css):
            p = prelude.strip()
            if not p or p.startswith(SKIP_AT):
                continue
            if p in ('from', 'to') or re.fullmatch(r'[\d.]+%(\s*,\s*[\d.]+%)*', p):
                continue
            for sel in p.split(','):
                if not sel.strip().startswith('.sdbi-home'):
                    bad.append(sel.strip())
        self.assertEqual(bad, [])

    def test_keyframes_prefixed(self):
        css = _load()
        for name in re.findall(r'@(?:-webkit-)?keyframes\s+([\w-]+)', css):
            self.assertTrue(name.startswith('sdbi-home'), name)

    def test_important_limited(self):
        self.assertLessEqual(_load().count('!important'), 20)


if __name__ == '__main__':
    unittest.main()
