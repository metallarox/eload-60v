"""Importa le piste di Freerouting (/tmp/out.ses) aggiungendo solo quelle nuove."""
import pcbnew, re, sys
sys.path.insert(0, '/home/claude/gen')
from sexp import parse, find, find1, uq

PCB = '/home/claude/out/eload_4ch/eload_4ch.kicad_pcb'
ses = parse(open([x for x in sys.argv[1:] if not x.startswith('--')][0]).read())[0]
routes = find1(ses, 'routes')
res = find1(routes, 'resolution')
unit, div = res[1], float(res[2])
to_nm = {'um': 1000.0, 'mm': 1e6, 'mil': 25400.0}[unit] / div

b = pcbnew.LoadBoard(PCB)
nets = {n.GetNetname(): n for n in b.GetNetsByName().values()} if hasattr(b, 'GetNetsByName') else None
netmap = {}
for code, ni in b.GetNetInfo().NetsByNetcode().items():
    netmap[ni.GetNetname()] = ni

PROT = ('GND', 'GND1', 'VLOAD', 'Net-(J1-Pin_1)')
def is_prot(n):
    return n in PROT or n.startswith('Net-(Q') or '/SHP' in n or '/SHN' in n
if '--replace' in sys.argv:
    ses_nets = {uq(n[1]) for n in find(find1(routes, 'network_out'), 'net')}
    rm = [t for t in b.GetTracks() if t.GetNetname() in ses_nets and not is_prot(t.GetNetname())]
    for t in rm:
        b.Remove(t)
    print('rimosse piste di segnale', len(rm))
existing = set()
vias = set()
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        q = t.GetPosition(); vias.add((round(q.x / 1e4), round(q.y / 1e4)))
    else:
        a, e = t.GetStart(), t.GetEnd()
        k1 = (round(a.x / 1e4), round(a.y / 1e4)); k2 = (round(e.x / 1e4), round(e.y / 1e4))
        existing.add((t.GetLayerName(), min(k1, k2), max(k1, k2)))

layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
nt = nv = 0
for n in find(find1(routes, 'network_out'), 'net'):
    name = uq(n[1])
    ni = netmap.get(name)
    if ni is None:
        print('rete sconosciuta', name); continue
    for w in find(n, 'wire'):
        path = find1(w, 'path')
        layer = uq(path[1]); width = float(path[2]) * to_nm
        xy = [float(v) * to_nm for v in path[3:] if not isinstance(v, list)]
        pts = [(int(xy[i]), int(-xy[i + 1])) for i in range(0, len(xy), 2)]
        for a, e in zip(pts, pts[1:]):
            k1 = (round(a[0] / 1e4), round(a[1] / 1e4)); k2 = (round(e[0] / 1e4), round(e[1] / 1e4))
            if (layer, min(k1, k2), max(k1, k2)) in existing or k1 == k2:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(*a)); t.SetEnd(pcbnew.VECTOR2I(*e))
            t.SetWidth(int(width)); t.SetLayer(layers[layer]); t.SetNet(ni)
            b.Add(t); nt += 1
    for v in find(n, 'via'):
        ps = uq(v[1]); x = float(v[2]) * to_nm; y = -float(v[3]) * to_nm
        if (round(x / 1e4), round(y / 1e4)) in vias:
            continue
        m = re.search(r'_(\d+):(\d+)_um', ps)
        d, dr = (int(m.group(1)) * 1000, int(m.group(2)) * 1000) if m else (800000, 400000)
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pcbnew.VECTOR2I(int(x), int(y))); via.SetWidth(pcbnew.F_Cu, d); via.SetDrill(dr)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni)
        b.Add(via); nv += 1
b.Save(PCB)
print('piste aggiunte', nt, 'vias aggiunte', nv)
