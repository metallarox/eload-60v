"""Generatore progetto KiCad 7 gerarchico a partire da una netlist descritta in Python."""
import uuid, os, re, json, math
from sexp import q, uq, find, find1, dump
from lib import get_symbol, pins as sym_pins, prop, n_units

G = 1.27
PROJECT = 'carico_attivo'
POWER_NETS = {'GND': 'power:GND', 'GND1': 'power:GND1', '+12V': 'power:+12V', '+5V': 'power:+5V',
              '+3V3': 'power:+3V3', 'VBUS': 'power:VBUS'}


def U():
    return str(uuid.uuid4())


def snap(v, g=2.54):
    return round(v / g) * g


def f(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


class Part:
    def __init__(self, sheet, group, lib_id, value, fp, pins, ref_prefix, unit=1, mpn='', note='', nc=(), ref=None, pos=None, rot=0, wired=()):
        self.sheet, self.group, self.lib_id, self.value, self.fp = sheet, group, lib_id, value, fp
        self.pins = {str(k): v for k, v in pins.items()}
        self.prefix, self.unit, self.mpn, self.note, self.nc = ref_prefix, unit, mpn, note, set(map(str, nc))
        self.ref = ref
        self.pos, self.rot, self.wired = pos, rot, set(map(str, wired))
        self.sym = get_symbol(lib_id)


class Design:
    def __init__(self):
        self.parts = []
        self.sheets = []  # (file, title, description)
        self.counters = {}
        self.flags = {}
        self.draw = {}
        self.origins = {}

    def sheet(self, file, title, desc):
        self.sheets.append((file, title, desc))

    def add(self, *a, **k):
        p = Part(*a, **k)
        if p.ref is None:
            n = self.counters.get(p.prefix, 0) + 1
            self.counters[p.prefix] = n
            p.ref = '%s%d' % (p.prefix, n)
        self.parts.append(p)
        return p


# ----------------------------------------------------------------------------------------
def unit_pins(p):
    return [x for x in sym_pins(p.sym) if x['unit'] in (0, p.unit)]


def bbox(p):
    xs, ys = [], []
    for sub in find(p.sym, 'symbol'):
        m = re.match(r'.*_(\d+)_(\d+)$', uq(sub[1]))
        if int(m.group(1)) not in (0, p.unit) or int(m.group(2)) == 2:
            continue
        for r in find(sub, 'rectangle'):
            for k in ('start', 'end'):
                e = find1(r, k); xs.append(float(e[1])); ys.append(float(e[2]))
        for pl in find(sub, 'polyline'):
            for xy in find(find1(pl, 'pts'), 'xy'):
                xs.append(float(xy[1])); ys.append(float(xy[2]))
        for c in find(sub, 'circle'):
            ce = find1(c, 'center'); r = float(find1(c, 'radius')[1])
            xs += [float(ce[1]) - r, float(ce[1]) + r]; ys += [float(ce[2]) - r, float(ce[2]) + r]
    for pn in unit_pins(p):
        xs.append(pn['x']); ys.append(pn['y'])
    if not xs:
        xs, ys = [0], [0]
    return min(xs), max(xs), min(ys), max(ys)   # symbol coords (y up)


def outward(a):
    a = a % 360
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]   # schematic coords


def rot(v, r):
    x, y = v
    r = r % 360
    if r == 0: return (x, y)
    if r == 90: return (y, -x)
    if r == 180: return (-x, -y)
    if r == 270: return (-y, x)


def label_len(name):
    return len(name) * 1.05 + 4.5


# ----------------------------------------------------------------------------------------
def layout(parts, width=390.0, x0=20.0, y0=30.0, origins=None):
    """Shelf packing per gruppo; un gruppo puo avere un'origine/larghezza propria."""
    origins = origins or {}
    pos = {}
    groups = []
    for p in parts:
        if not groups or groups[-1][0] != p.group:
            groups.append((p.group, []))
        groups[-1][1].append(p)
    y = y0
    ymax = y0
    titles = []
    for gname, gp in groups:
        if gname in origins:
            gx0, gy, gw = origins[gname]
        else:
            gx0, gy, gw = x0, y, width
        titles.append((gname, gx0, gy))
        yy = gy + 6
        x = gx0
        row_h = 0
        row_items = []
        for p in gp:
            bx0, bx1, by0, by1 = bbox(p)
            ml = mr = mt = mb = 3.0
            for pn in unit_pins(p):
                net = p.pins.get(pn['number'])
                d = outward(pn['angle'])
                ln = 2.54 + (label_len(net) if net and net not in POWER_NETS else 5)
                if d == (-1, 0): ml = max(ml, ln)
                if d == (1, 0): mr = max(mr, ln)
                if d == (0, -1): mt = max(mt, 2.54 + (8 if net in POWER_NETS else label_len(net or '')))
                if d == (0, 1): mb = max(mb, 2.54 + (8 if net in POWER_NETS else label_len(net or '')))
            w = (bx1 - bx0) + ml + mr + 8
            h = (by1 - by0) + mt + mb + 4
            if x + w > gx0 + gw and row_items:
                yy += row_h + 4
                x = gx0
                row_h = 0
                row_items = []
            pos[p] = (snap(x + ml - bx0), snap(yy + mt + by1))
            row_items.append(p)
            x += w + 2
            row_h = max(row_h, h)
        yy += row_h
        ymax = max(ymax, yy)
        if gname not in origins:
            y = yy + 10
    return pos, max(ymax, y), titles


# ----------------------------------------------------------------------------------------
class SheetWriter:
    def __init__(self, design, root_uuid, sheet_uuid, file, title, page, globals_):
        self.d, self.root, self.su, self.file, self.title, self.page = design, root_uuid, sheet_uuid, file, title, page
        self.globals = globals_
        self.items = []
        self.libs = {}
        self.pwr = 0

    def path(self):
        return '/%s/%s' % (self.root, self.su)

    def add_lib(self, lid):
        if lid not in self.libs:
            self.libs[lid] = get_symbol(lid)

    def sym_inst(self, lid, x, y, ref, value, unit=1, fp='', extra=(), hide_ref=False, pin_numbers=(), refpos=None, valpos=None, power=False, r=0, fa=0, just=''):
        self.add_lib(lid)
        rx, ry = refpos or (x, y - 3)
        vx, vy = valpos or (x, y + 3)
        hide = ' hide' if hide_ref else ''
        props = [
            '(property "Reference" %s (at %s %s %d) (effects (font (size 1.27 1.27))%s%s))' % (q(ref), f(rx), f(ry), fa, just, hide),
            '(property "Value" %s (at %s %s %d) (effects (font (size 1.27 1.27))%s))' % (q(value), f(vx), f(vy), fa, just),
            '(property "Footprint" %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (q(fp), f(x), f(y)),
            '(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (f(x), f(y)),
        ]
        for k, v in extra:
            props.append('(property %s %s (at %s %s 0) (effects (font (size 1.27 1.27)) hide))' % (q(k), q(v), f(x), f(y)))
        pins = ''.join('(pin %s (uuid %s))' % (q(n), U()) for n in pin_numbers)
        s = ('(symbol (lib_id %s) (at %s %s ' + str(r) + ') (unit %d) (in_bom %s) (on_board %s) (dnp no) (uuid %s)\n  %s\n  %s\n'
             '  (instances (project %s (path %s (reference %s) (unit %d)))))') % (
            q(lid), f(x), f(y), unit, 'no' if power else 'yes', 'no' if power else 'yes', U(), '\n  '.join(props), pins,
            q(PROJECT), q(self.path()), q(ref), unit)
        self.items.append(s)

    def power(self, net, x, y, d=None):
        self.pwr += 1
        gnd = net.startswith('GND')
        if d is None:
            d = (0, 1) if gnd else (0, -1)
        body = (0, 1) if gnd else (0, -1)
        r = [rr for rr in (0, 90, 180, 270) if tuple(round(v) for v in rot(body, rr)) == tuple(d)][0]
        dist = 5.08 if gnd else 3.81
        if d[0]:
            vp = (x + d[0] * (4.2 if gnd else 2.2), y)
            just = ' (justify left)' if d[0] > 0 else ' (justify right)'
            if not gnd:
                vp = (x + d[0] * 1.0, y - 2.6)
        else:
            vp = (x, y + d[1] * dist)
            just = ''
        self.sym_inst(POWER_NETS[net], x, y, '#PWR%03d' % (self.page * 100 + self.pwr), net, hide_ref=True,
                      pin_numbers=['1'], power=True, valpos=vp, r=r, fa=r, just=just)

    def flag(self, x, y):
        self.pwr += 1
        self.sym_inst('power:PWR_FLAG', x, y, '#FLG%03d' % (self.page * 100 + self.pwr), 'PWR_FLAG', hide_ref=True,
                      pin_numbers=['1'], power=True, valpos=(x, y - 3.81))

    def wire(self, x1, y1, x2, y2):
        self.items.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))' % (
            f(x1), f(y1), f(x2), f(y2), U()))

    def label(self, net, x, y, d):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
        just = 'left' if ang in (0, 90) else 'right'
        if net in self.globals:
            self.items.append(
                '(global_label %s (shape passive) (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s)) (uuid %s)'
                ' (property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) (effects (font (size 1.27 1.27)) hide)))' % (
                    q(net), f(x), f(y), ang, just, U(), f(x), f(y)))
        else:
            self.items.append('(label %s (at %s %s %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))' % (
                q(net), f(x), f(y), ang, just, U()))

    def nc(self, x, y):
        self.items.append('(no_connect (at %s %s) (uuid %s))' % (f(x), f(y), U()))

    def text(self, s, x, y, size=1.27, bold=False):
        b = ' bold' if bold else ''
        self.items.append('(text %s (at %s %s 0) (effects (font (size %s %s)%s) (justify left bottom)) (uuid %s))' % (
            q(s), f(x), f(y), f(size), f(size), b, U()))

    def junction(self, x, y):
        self.items.append('(junction (at %s %s) (diameter 0) (color 0 0 0 0) (uuid %s))' % (f(x), f(y), U()))

    def place_part(self, p, x, y):
        r = p.rot
        bx0, bx1, by0, by1 = bbox(p)
        extra = []
        if p.mpn: extra.append(('MPN', p.mpn))
        if p.note: extra.append(('Note', p.note))
        upins = unit_pins(p)
        two_pole = (bx1 - bx0) <= 6 and len(upins) <= 2 and all(pn['x'] == 0 for pn in upins)
        pinxy = [rot((pn['x'], -pn['y']), r) for pn in upins]
        npos = len(set((round(a, 2), round(b, 2)) for a, b in pinxy))
        if r and npos == 2 and pinxy[0][1] == pinxy[-1][1] or (two_pole and r in (90, 270)):
            # bipolo orizzontale: testo sopra/sotto, centrato
            self.sym_inst(p.lib_id, x, y, p.ref, p.value, p.unit, p.fp, extra,
                          pin_numbers=[pn['number'] for pn in upins], refpos=(x, y - 2.8), valpos=(x, y + 2.8), r=r, fa=0 if r == 180 else (-r) % 360)
        elif r or (two_pole and getattr(p, 'textleft', False)) or two_pole:
            left = getattr(p, 'textleft', False)
            dx = -3.0 if left else 3.0
            self.sym_inst(p.lib_id, x, y, p.ref, p.value, p.unit, p.fp, extra,
                          pin_numbers=[pn['number'] for pn in upins], refpos=(x + dx, y - 1.27), valpos=(x + dx, y + 1.27),
                          r=r, fa=0 if r == 180 else (-r) % 360, just=' (justify right)' if (left != (r == 180)) else ' (justify left)')
        elif p.lib_id.endswith('Q_NMOS_GDS'):
            self.sym_inst(p.lib_id, x, y, p.ref, p.value, p.unit, p.fp, extra,
                          pin_numbers=[pn['number'] for pn in upins], refpos=(x + 4.5, y - 6.35), valpos=(x + 4.5, y - 3.81),
                          just=' (justify left)')
        else:
            refpos = (x + (bx0 + bx1) / 2, y - by1 - 1.6)
            valpos = (x + (bx0 + bx1) / 2, y - by0 + 1.9)
            just = ''
            if p.lib_id == 'Device:R_Shunt':
                refpos = (x + 2.5, y + 6.35); valpos = (x + 2.5, y + 8.89); just = ' (justify left)'
            if p.lib_id.startswith(('Amplifier_Operational', 'Comparator')) and p.unit in (1, 2):
                refpos = (x - 0.5, y - by1 - 1.6); valpos = (x + 0.5, y - by1 - 1.6)
            self.sym_inst(p.lib_id, x, y, p.ref, p.value, p.unit, p.fp, extra,
                          pin_numbers=[pn['number'] for pn in upins], refpos=refpos, valpos=valpos, r=r, just=just)
            if p.lib_id.startswith(('Amplifier_Operational', 'Comparator')) and p.unit in (1, 2):
                it = self.items[-1]
                it = it.replace('(at %s %s 0) (effects (font (size 1.27 1.27))))' % (f(refpos[0]), f(refpos[1])),
                                '(at %s %s 0) (effects (font (size 1.27 1.27)) (justify right)))' % (f(refpos[0]), f(refpos[1])), 1)
                it = it.replace('(at %s %s 0) (effects (font (size 1.27 1.27))))' % (f(valpos[0]), f(valpos[1])),
                                '(at %s %s 0) (effects (font (size 1.27 1.27)) (justify left)))' % (f(valpos[0]), f(valpos[1])), 1)
                self.items[-1] = it
        done = set()
        for pn in upins:
            ox, oy = rot((pn['x'], -pn['y']), r)
            px, py = x + ox, y + oy
            key = (round(px, 2), round(py, 2))
            num = pn['number']
            group = num.strip('[]').split(',') if num.startswith('[') else [num]
            net = next((p.pins[k] for k in group if k in p.pins), None)
            if any(k in p.wired for k in group):
                continue
            if net is None:
                if pn['type'] == 'no_connect' or num in p.nc:
                    if key not in done:
                        self.nc(px, py)
                    done.add(key)
                    continue
                raise SystemExit('Pin %s.%s (%s) non assegnato' % (p.ref, num, pn['name']))
            if key in done:
                continue
            done.add(key)
            d = rot(outward(pn['angle']), r)
            d = (round(d[0]), round(d[1]))
            ex, ey = px + d[0] * 2.54, py + d[1] * 2.54
            self.wire(px, py, ex, ey)
            if net in POWER_NETS:
                self.power(net, ex, ey, d)
            else:
                self.label(net, ex, ey, d)

    def write(self, outdir, paper, title_block):
        libs = '\n'.join(dump_symbol(s) for s in self.libs.values())
        body = '\n'.join(self.items)
        txt = ('(kicad_sch (version 20230121) (generator eeschema)\n(uuid %s)\n(paper %s)\n%s\n(lib_symbols\n%s\n)\n%s\n)\n') % (
            self.su, q(paper), title_block, libs, body)
        open(os.path.join(outdir, self.file), 'w').write(txt)


def dump_symbol(s):
    return dump(s)


def title_block(title, page_title, rev, date, comments):
    c = ''.join('(comment %d %s)' % (i + 1, q(t)) for i, t in enumerate(comments))
    return '(title_block (title %s) (date %s) (rev %s) (company "IV3HGA") %s)' % (q(title + ' — ' + page_title), q(date), q(rev), c)


def build(design, outdir, title, rev, date, notes):
    os.makedirs(outdir, exist_ok=True)
    root = U()
    # reti globali = usate in piu' fogli
    use = {}
    for p in design.parts:
        for n in p.pins.values():
            use.setdefault(n, set()).add(p.sheet)
    globals_ = {n for n, s in use.items() if len(s) > 1 and n not in POWER_NETS}
    # reti con un solo pin -> errore
    cnt = {}
    for p in design.parts:
        for n in set(p.pins.values()):
            cnt[n] = cnt.get(n, 0) + 1
    singles = [n for n, c in cnt.items() if c == 1 and n not in POWER_NETS]
    if singles:
        print('ATTENZIONE reti con un solo componente:', singles)

    sheet_entries = []
    for i, (file, stitle, desc) in enumerate(design.sheets):
        su = U()
        page = i + 2
        sw = SheetWriter(design, root, su, file, stitle, page, globals_)
        parts = [p for p in design.parts if p.sheet == file]
        man = [p for p in parts if p.pos]
        auto = [p for p in parts if not p.pos]
        draw = design.draw.get(file, [])
        ymax = max([p.pos[1] for p in man] + [it[-1] if it[0] == 'title' else 0 for it in draw] + [0])
        pos, h, titles = layout(auto, y0=(ymax + 25) if man else 30.0, origins=design.origins.get(file, {}))
        h = max(h, ymax)
        for p in man:
            pos[p] = p.pos
        for it in draw:
            k = it[0]
            if k == 'wire':
                pts = it[1]
                for a_, b_ in zip(pts, pts[1:]):
                    sw.wire(a_[0], a_[1], b_[0], b_[1])
            elif k == 'junc':
                sw.junction(it[1], it[2])
            elif k == 'label':
                sw.label(it[1], it[2], it[3], it[4])
            elif k == 'title':
                sw.text(it[1], it[2], it[3], 2.0, True)
            elif k == 'text':
                sw.text(it[1], it[2], it[3])
            elif k == 'pwr':
                sw.power(it[1], it[2], it[3])
            elif k == 'flag':
                sw.flag(it[1], it[2])
        for gname, gx, gy in titles:
            sw.text(gname, gx, gy + 3, 2.0, True)
        for p in parts:
            sw.place_part(p, *pos[p])
        # PWR_FLAG
        flags = design.flags.get(file, [])
        fx = 30.48
        fy = snap(h + 10)
        for net in flags:
            sw.flag(fx, fy)
            sw.wire(fx, fy, fx, fy + 2.54)
            sw.power(net, fx, fy + 2.54)
            fx += 15.24
        paper = 'A3' if h < 272 else ('A2' if h + 25 < 400 else 'A1')
        sw.write(outdir, paper, title_block(title, stitle, rev, date, [desc]))
        sheet_entries.append((su, file, stitle, page))

    # foglio radice
    items = []
    x, y = 30, 60
    for k, (su, file, stitle, page) in enumerate(sheet_entries):
        sx = 30 + (k % 3) * 120
        sy = 50 + (k // 3) * 60
        items.append(('(sheet (at %s %s) (size 90 35) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid %s)\n'
                      ' (property "Sheetname" %s (at %s %s 0) (effects (font (size 1.524 1.524)) (justify left bottom)))\n'
                      ' (property "Sheetfile" %s (at %s %s 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
                      ' (instances (project %s (path %s (page %s)))))') % (
            f(sx), f(sy), su, q(stitle), f(sx), f(sy - 0.7), q(file), f(sx), f(sy + 35.6), q(PROJECT), q('/' + root), q(str(page))))
    ty = 185
    for line in notes:
        items.append('(text %s (at 30 %s 0) (effects (font (size 1.524 1.524)%s) (justify left bottom)) (uuid %s))' % (
            q(line.lstrip('#')), f(ty), ' bold' if line.startswith('#') else '', U()))
        ty += 5.08 if not line.startswith('#') else 7
    txt = ('(kicad_sch (version 20230121) (generator eeschema)\n(uuid %s)\n(paper "A3")\n%s\n(lib_symbols)\n%s\n'
           '(sheet_instances (path "/" (page "1")))\n)\n') % (
        root, title_block(title, 'Indice', rev, date, ['Schema gerarchico: un foglio per blocco funzionale']), '\n'.join(items))
    open(os.path.join(outdir, PROJECT + '.kicad_sch'), 'w').write(txt)
    pro = {"meta": {"filename": PROJECT + ".kicad_pro", "version": 1},
           "sheets": [[root, "Root"]] + [[su, t] for su, _, t, _ in sheet_entries],
           "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []}, "boards": [], "text_variables": {}}
    json.dump(pro, open(os.path.join(outdir, PROJECT + '.kicad_pro'), 'w'), indent=2)
    return globals_
