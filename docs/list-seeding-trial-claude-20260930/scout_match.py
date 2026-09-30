#!/usr/bin/env python3
"""Match seed names against Scout's complete Mesa delivery.

    python3 scout_match.py <category-id> "Name one" "Name two" ...
    python3 scout_match.py <category-id> --file seeds.json   # [{"name":..., "website":..., "address":...}]

Prints, per seed, the best Scout match: in this category, in another category, or none.
Matching: website host+path, then name tokens (words of 3+ letters, ignoring common words).
"""
import gzip, json, re, sys
from urllib.parse import urlparse

FILE = '/Users/michaelbendio/resource-scout-pairwise/deliveries/mesa-complete-20260927-r2/prepared-resources.json.gz'
STOP = set('the and for inc llc of in at a an services service program programs center centre mesa arizona az phoenix valley east county maricopa community city'.split())
resources = json.load(gzip.open(FILE))['resources']

def toks(s):
    return {w for w in re.findall(r'[a-z0-9]+', (s or '').lower()) if len(w) >= 3 and w not in STOP}

def host(u):
    u = (u or '').lower().strip()
    if not u: return ''
    if '://' not in u: u = 'https://' + u
    p = urlparse(u); return (p.netloc.removeprefix('www.') + p.path.rstrip('/'))

def score(seed_tokens, seed_host, r):
    value = 0.0
    rh = host(r.get('website'))
    if seed_host and rh and (rh == seed_host or rh.startswith(seed_host) or seed_host.startswith(rh)):
        value += 1.0
    if seed_tokens:
        in_name = len(seed_tokens & toks(r['name'])) / len(seed_tokens)
        in_text = len(seed_tokens & toks(r['name'] + ' ' + r.get('description', ''))) / len(seed_tokens)
        value += max(in_name, 0.9 * in_text)
    return value


def match(seed, category):
    """Prefer the agency's entry in this category when Scout has one (agencies often
    have several programmes, filed under different categories)."""
    st, sh = toks(seed.get('name')), host(seed.get('website'))
    scored = [(score(st, sh, r), r) for r in resources]
    good = [(v, r) for v, r in scored if v >= 0.6]
    if not good: return {'match': 'none'}
    here = [(v, r) for v, r in good if category in r['categories']]
    v, r = max(here or good, key=lambda x: x[0])
    where = 'this-category' if here else 'other-category'
    return {'match': where, 'scoutId': r['id'], 'scoutName': r['name'], 'scoutCategories': r['categories'], 'state': r['state'], 'score': round(v, 2)}


if __name__ == '__main__':
    cat = sys.argv[1]
    if sys.argv[2] == '--file':
        seeds = json.load(open(sys.argv[3]))
    else:
        seeds = [{'name': n} for n in sys.argv[2:]]
    for s in seeds:
        print(json.dumps({'seed': s.get('name'), **match(s, cat)}, ensure_ascii=False))
