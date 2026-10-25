import copy, os, re
from sexp import parse, find, find1, uq, q

LIBDIR = '/home/claude/kicad10/squashfs-root/usr/share/kicad/symbols'
_cache = {}


def _lib(name):
    if name not in _cache:
        d = os.path.join(LIBDIR, name + '.kicad_symdir')
        if os.path.isdir(d):
            syms = {}
            for fn in os.listdir(d):
                tree = parse(open(os.path.join(d, fn)).read())[0]
                for s_ in find(tree, 'symbol'):
                    syms[uq(s_[1])] = s_
            _cache[name] = syms
        else:
            path = os.path.join(LIBDIR, name + '.kicad_sym')
            if not os.path.exists(path):
                path = os.path.join(os.path.dirname(__file__), 'custom', name + '.kicad_sym')
            tree = parse(open(path).read())[0]
            _cache[name] = {uq(s_[1]): s_ for s_ in find(tree, 'symbol')}
    return _cache[name]


def get_symbol(lib_id):
    """Return a flattened symbol tree named lib_id (Lib:Name)."""
    lib, name = lib_id.split(':')
    syms = _lib(lib)
    s = copy.deepcopy(syms[name])
    ext = find1(s, 'extends')
    if ext:
        parent = get_symbol(lib + ':' + uq(ext[1]))
        pname = uq(ext[1])
        props = find(s, 'property')
        base = [e for e in parent if not (isinstance(e, list) and e[0] == 'property')]
        # rename units
        new = []
        for e in base:
            if isinstance(e, list) and e[0] == 'symbol':
                e = copy.deepcopy(e)
                sub = uq(e[1]).split(':')[-1]
                e[1] = q(sub.replace(pname, name, 1))
            new.append(e)
        # insert props after header items
        out = [new[0], q(lib_id)]
        hdr = [e for e in new[2:] if not (isinstance(e, list) and e[0] == 'symbol')]
        units = [e for e in new[2:] if isinstance(e, list) and e[0] == 'symbol']
        out += hdr + props + units
        return out
    s[1] = q(lib_id)
    return s


def pins(sym):
    """List of dicts: unit, number, name, type, x, y, angle, length"""
    name = uq(sym[1]).split(':')[-1]
    res = []
    for sub in find(sym, 'symbol'):
        sn = uq(sub[1])
        m = re.match(r'.*_(\d+)_(\d+)$', sn)
        unit = int(m.group(1))
        conv = int(m.group(2))
        if conv == 2:
            continue
        for p in find(sub, 'pin'):
            at = find1(p, 'at')
            res.append(dict(unit=unit, type=p[1], x=float(at[1]), y=float(at[2]),
                            angle=int(float(at[3])) if len(at) > 3 else 0,
                            length=float(find1(p, 'length')[1]),
                            name=uq(find1(p, 'name')[1]), number=uq(find1(p, 'number')[1])))
    return res


def prop(sym, key):
    for p in find(sym, 'property'):
        if uq(p[1]) == key:
            return uq(p[2])
    return None


def n_units(sym):
    us = set()
    for sub in find(sym, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', uq(sub[1]))
        us.add(int(m.group(1)))
    us.discard(0)
    return max(us) if us else 1


if __name__ == '__main__':
    import sys
    for lid in sys.argv[1:]:
        s = get_symbol(lid)
        print('==', lid, 'units', n_units(s), 'fp', prop(s, 'Footprint'))
        for p in sorted(pins(s), key=lambda p: (p['unit'], p['number'].zfill(3))):
            print('  u%d %-4s %-14s %-14s (%g,%g) a%d' % (p['unit'], p['number'], p['name'], p['type'], p['x'], p['y'], p['angle']))
