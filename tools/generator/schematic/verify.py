"""Confronta la netlist esportata da KiCad con quella prevista e fa controlli tipo ERC."""
import sys
from sexp import parse, find, find1, uq
from design import d
from lib import pins as sym_pins

net = parse(open(sys.argv[1]).read())[0]
# netlist kicad
kic = {}
for n in find(find1(net, 'nets'), 'net'):
    name = uq(find1(n, 'name')[1]).split('/')[-1]
    nodes = frozenset((uq(find1(x, 'ref')[1]), uq(find1(x, 'pin')[1])) for x in find(n, 'node'))
    kic[nodes] = name
comps = {uq(find1(c, 'ref')[1]): uq(find1(c, 'footprint')[1]) if find1(c, 'footprint') else ''
         for c in find(find1(net, 'components'), 'comp')}

# netlist prevista
exp = {}
ptype = {}
for p in d.parts:
    for pn in sym_pins(p.sym):
        if pn['unit'] in (0, p.unit):
            ptype[(p.ref, pn['number'])] = pn['type']
    for num, n in p.pins.items():
        exp.setdefault(n, set()).add((p.ref, num))
expset = {frozenset(v): k for k, v in exp.items()}

ok = True
for nodes, name in expset.items():
    if nodes not in kic:
        ok = False
        # trova rete kicad che contiene questi nodi
        found = [(kn, kic[kn]) for kn in kic if nodes & kn]
        print('MISMATCH rete', name, sorted(nodes)[:6], '->', [(v, len(k)) for k, v in found])
extra = [kic[k] for k in kic if k not in expset and len(k) > 1]
if extra:
    ok = False
    print('Reti KiCad non previste:', extra)
print('reti previste', len(expset), 'reti kicad', len(kic), 'componenti', len(comps))

# controlli tipo ERC
drivers = {'power_out'}
for nodes, name in kic.items():
    types = [ptype.get(nd, '?') for nd in nodes]
    if len(nodes) == 1 and types[0] not in ('no_connect',):
        print('ERC: rete con un solo pin', name, list(nodes))
    if 'power_in' in types and not any(t == 'power_out' for t in types) and name not in ('GND', '+12V'):
        print('ERC: power_in non pilotato su', name)
    if types.count('output') + types.count('power_out') > 1:
        print('ERC: piu uscite su', name, [nd for nd in nodes if ptype.get(nd) in ('output', 'power_out')])
missing_fp = [r for r, fp in comps.items() if not fp and not r.startswith('#')]
print('componenti senza footprint:', missing_fp)
print('OK' if ok else 'ERRORI')
