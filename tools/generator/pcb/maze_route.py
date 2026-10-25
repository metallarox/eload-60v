"""Instrada le connessioni mancanti con un A* su griglia a due layer (F.Cu/B.Cu)."""
import pcbnew, heapq, math, sys
sys.path.insert(0, '/home/claude/py311')
import numpy as np

PCB = '/home/claude/out/carico_attivo/carico_attivo.kicad_pcb'
G = 0.1                      # passo griglia mm
TW, CL, VD = 0.2, 0.21, 0.7  # pista, distanza, diametro via
OX, OY, W, H = 50.0, 40.0, 170.0, 125.0
NX, NY = int(W / G) + 1, int(H / G) + 1
HV = {'VLOAD', 'Net-(J1-Pin_1)', 'Net-(J3-Pin_1)'}

b = pcbnew.LoadBoard(PCB)
netname = sys.argv[1]
net = b.FindNet(netname)
code = net.GetNetCode()
L = [pcbnew.F_Cu, pcbnew.B_Cu]
blocked = np.zeros((2, NX, NY), dtype=bool)


def mark_disk(li, x, y, r):
    i0, i1 = max(0, int((x - r) / G)), min(NX - 1, int((x + r) / G) + 1)
    j0, j1 = max(0, int((y - r) / G)), min(NY - 1, int((y + r) / G) + 1)
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing='ij')
    m = (ii * G - x) ** 2 + (jj * G - y) ** 2 <= r * r
    blocked[li, i0:i1 + 1, j0:j1 + 1] |= m


def mark_seg(li, ax, ay, bx, by, r):
    n = max(1, int(math.hypot(bx - ax, by - ay) / (G / 2)))
    for k in range(n + 1):
        mark_disk(li, ax + (bx - ax) * k / n, ay + (by - ay) * k / n, r)


def mark_rect(li, x0, y0, x1, y1, m):
    i0, i1 = max(0, int((x0 - m) / G)), min(NX - 1, int((x1 + m) / G) + 1)
    j0, j1 = max(0, int((y0 - m) / G)), min(NY - 1, int((y1 + m) / G) + 1)
    blocked[li, i0:i1 + 1, j0:j1 + 1] = True


def loc(v):
    return v.x / 1e6 - OX, v.y / 1e6 - OY


r_track = TW / 2
for p in b.GetPads():
    if p.GetNetCode() == code:
        continue
    cl = (0.65 if p.GetNetname() in HV else CL) + r_track
    for li, lay in enumerate(L):
        if p.IsOnLayer(lay) or p.GetDrillSize().x > 0:
            sh = p.GetEffectivePolygon(lay)
            bb = sh.BBox()
            mark_rect(li, bb.GetLeft() / 1e6 - OX, bb.GetTop() / 1e6 - OY, bb.GetRight() / 1e6 - OX, bb.GetBottom() / 1e6 - OY, cl)
for t in b.GetTracks():
    if t.GetNetCode() == code:
        continue
    cl = (0.65 if t.GetNetname() in HV else CL) + r_track
    if t.GetClass() == 'PCB_VIA':
        x, y = loc(t.GetPosition())
        for li in (0, 1):
            mark_disk(li, x, y, t.GetWidth(pcbnew.F_Cu) / 2e6 + cl)
    else:
        li = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        ax, ay = loc(t.GetStart()); bx, by = loc(t.GetEnd())
        mark_seg(li, ax, ay, bx, by, t.GetWidth() / 2e6 + cl)
# zone di potenza sul top e bordo scheda
mark_rect(0, 16.8, 4.2, 98.3, 90.7, 0.4)
for li in (0, 1):
    blocked[li, :, :int(0.8 / G)] = blocked[li, :, -int(0.8 / G):] = True
    blocked[li, :int(0.8 / G), :] = blocked[li, -int(0.8 / G):, :] = True
# isola USB sul bottom (GND1) e fascia di isolamento
mark_rect(1, 131.0, 0, 170, 36.0, 0)

# terminali: pad della rete
pads = [p for p in b.GetPads() if p.GetNetCode() == code]
b.BuildConnectivity()
src, dst = pads[0], pads[-1]
# usa i due pad indicati dal DRC se passati
if len(sys.argv) > 3:
    find = lambda s: [p for p in pads if p.GetParentFootprint().GetReference() + '.' + p.GetNumber() == s][0]
    src, dst = find(sys.argv[2]), find(sys.argv[3])


def cells_of(p):
    x, y = loc(p.GetPosition())
    i, j = int(round(x / G)), int(round(y / G))
    out = []
    for li, lay in enumerate(L):
        if p.IsOnLayer(lay):
            out.append((li, i, j))
    return out, (x, y)


S, sxy = cells_of(src)
T, txy = cells_of(dst)
for li, i, j in S + T:
    blocked[li, max(0, i - 4):i + 5, max(0, j - 2):j + 3] = False   # uscita dal pad
tset = set(T)
via_r = int(math.ceil((VD / 2 + CL - r_track) / G))


def via_ok(i, j):
    for li in (0, 1):
        if blocked[li, max(0, i - via_r):i + via_r + 1, max(0, j - via_r):j + via_r + 1].any():
            return False
    return True


def h(c):
    return math.hypot(c[1] - T[0][1], c[2] - T[0][2])


openq = [(h(s), 0.0, s, None) for s in S]
heapq.heapify(openq)
came, gbest = {}, {s: 0.0 for s in S}
moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
found = None
while openq:
    f, g, c, par = heapq.heappop(openq)
    if c in came:
        continue
    came[c] = par
    if c in tset:
        found = c; break
    li, i, j = c
    for di, dj, cost in moves:
        n = (li, i + di, j + dj)
        if not (0 <= n[1] < NX and 0 <= n[2] < NY) or blocked[n]:
            continue
        ng = g + cost + (0.3 if li == 1 else 0)
        if ng < gbest.get(n, 1e18):
            gbest[n] = ng; heapq.heappush(openq, (ng + h(n), ng, n, c))
    n = (1 - li, i, j)
    if via_ok(i, j):
        ng = g + 25
        if ng < gbest.get(n, 1e18):
            gbest[n] = ng; heapq.heappush(openq, (ng + h(n), ng, n, c))
if not found:
    print('visitati da sorgente', len(came), 'S', S, 'T', T, 'T bloccati', [bool(blocked[t]) for t in T])
    raise SystemExit('nessun percorso')
path = []
c = found
while c:
    path.append(c); c = came[c]
path.reverse()
# semplifica e crea piste/vias
def P(c):
    return pcbnew.VECTOR2I(int((c[1] * G + OX) * 1e6), int((c[2] * G + OY) * 1e6))
segs = []
start = path[0]
prev = path[0]
dirn = None
for c in path[1:]:
    if c[0] != prev[0]:
        segs.append(('seg', start, prev)); segs.append(('via', prev)); start = c; dirn = None
    else:
        d = (c[1] - prev[1], c[2] - prev[2])
        if dirn is not None and d != dirn:
            segs.append(('seg', start, prev)); start = prev
        dirn = d
    prev = c
segs.append(('seg', start, prev))
nt = nv = 0
for s in segs:
    if s[0] == 'seg' and s[1] != s[2]:
        t = pcbnew.PCB_TRACK(b); t.SetStart(P(s[1])); t.SetEnd(P(s[2])); t.SetWidth(int(TW * 1e6))
        t.SetLayer(L[s[1][0]]); t.SetNet(net); b.Add(t); nt += 1
    elif s[0] == 'via':
        v = pcbnew.PCB_VIA(b); v.SetPosition(P(s[1])); v.SetWidth(pcbnew.F_Cu, int(VD * 1e6)); v.SetDrill(int(0.35e6))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); b.Add(v); nv += 1
# raccordi pad -> primo/ultimo punto griglia
for (li, i, j), (x, y) in ((path[0], sxy), (path[-1], txy)):
    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(int((x + OX) * 1e6), int((y + OY) * 1e6))); t.SetEnd(P((li, i, j)))
    t.SetWidth(int(TW * 1e6)); t.SetLayer(L[li]); t.SetNet(net); b.Add(t)
b.Save(PCB)
print('instradato', netname, 'segmenti', nt, 'vias', nv, 'lunghezza celle', len(path))
