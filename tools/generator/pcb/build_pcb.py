"""Builds eload_4ch.kicad_pcb: piazzamento completo + potenza e Kelvin tracciati."""
import sys, os, json, math
sys.path.insert(0, '/home/claude/gen')
import pcbnew
from sexp import parse, find, find1, uq

PRJ = '/home/claude/out/eload_4ch'
FPDIR = '/home/claude/kicad10/squashfs-root/usr/share/kicad/footprints'
OX, OY = 50.0, 40.0          # origine scheda nel foglio
W, H = 170.0, 125.0
HV_NETS = ['VLOAD', 'VSENSE', 'Net-(J1-Pin_1)', 'Net-(J3-Pin_1)']


def V(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))


def mm(v):
    return pcbnew.ToMM(v)


# ------------------------------------------------------------------ netlist
net = parse(open(os.path.join(PRJ, 'eload_4ch.net')).read())[0]
comps = {}
for c in find(find1(net, 'components'), 'comp'):
    ref = uq(find1(c, 'ref')[1])
    flds = {}
    fl = find1(c, 'fields')
    if fl:
        for f_ in find(fl, 'field'):
            nm = uq(find1(f_, 'name')[1]); val = uq(f_[-1]) if not isinstance(f_[-1], list) else ''
            if nm in ('MPN', 'Note') and val:
                flds[nm] = val
    comps[ref] = dict(value=uq(find1(c, 'value')[1]), fp=uq(find1(c, 'footprint')[1]), fields=flds)
pinnet = {}
for n in find(find1(net, 'nets'), 'net'):
    name = uq(find1(n, 'name')[1])
    for nd in find(n, 'node'):
        pinnet[(uq(find1(nd, 'ref')[1]), uq(find1(nd, 'pin')[1]))] = name

board = pcbnew.NewBoard(os.path.join(PRJ, 'eload_4ch.kicad_pcb'))
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
nets = {}
for name in sorted(set(pinnet.values())):
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni

fps = {}
problems = []
for ref, c in comps.items():
    lib, name = c['fp'].split(':')
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    if fp is None:
        raise SystemExit('footprint mancante ' + c['fp'])
    fp.SetReference(ref)
    fp.SetValue(c['value'])
    fp.SetFPIDAsString(c['fp'])
    for k_, v_ in c['fields'].items():
        fp.SetField(k_, v_)
        fp.GetField(k_).SetVisible(False)
    if ref in ('J1', 'J2'):
        fp.SetExcludedFromBOM(False)
    board.Add(fp)
    padnums = {p.GetNumber() for p in fp.Pads()}
    for (r, pin), n in pinnet.items():
        if r != ref:
            continue
        if pin not in padnums:
            problems.append('%s pin %s non esiste nel footprint %s' % (ref, pin, c['fp']))
        for p in fp.Pads():
            if p.GetNumber() == pin:
                p.SetNet(nets[n])
    used = {pin for (r, pin) in pinnet if r == ref}
    for pn in padnums - used - {''}:
        problems.append('%s pad %s senza pin nel simbolo' % (ref, pn))
    fps[ref] = fp
for ref, fp in fps.items():
    r = fp.Reference()
    if ref[0] in 'RCDF' and fp.GetFPIDAsString().split(':')[1].startswith(('R_1206', 'C_1206', 'LED_1206', 'Fuse_1206', 'D_SMA')):
        r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
        r.SetTextThickness(pcbnew.FromMM(0.12))
    fp.Value().SetVisible(False)
print('componenti', len(fps), 'reti', len(nets))
for p in problems:
    print('PINOUT:', p)

# MOSFET: foro di accesso vite 7 mm al posto del foro da 3,6
for ref in ('Q1', 'Q2', 'Q3', 'Q4'):
    for p in fps[ref].Pads():
        if p.GetNumber() == '':
            p.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(7.0), pcbnew.FromMM(7.0)))
            p.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(pcbnew.FromMM(7.0), pcbnew.FromMM(7.0)))


def place(ref, x, y, rot=0, bottom=False):
    fp = fps[ref]
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)
    if bottom and not fp.IsFlipped():
        fp.Flip(V(x, y), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    fp.SetLocked(False)
    return fp


def pad(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == str(num):
            q = p.GetPosition()
            return (mm(q.x) - OX, mm(q.y) - OY)
    raise KeyError((ref, num))


def crtyd(fp):
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox()
    else:
        bb = fp.GetBoundingBox(False, False)
    return (mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY)


placed_rects = []


def pack(refs, x0, y0, x1, y1, gap=0.8, rot=0, gy=1.5):
    """Impacchetta i footprint (lato top) nella regione, evitando i rettangoli gia occupati."""
    x, y, row_h = x0, y0, 0
    for ref in refs:
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(0, 0))
        l, t, r, b = crtyd(fp)
        w, h = r - l, b - t
        for _ in range(400):
            if x + w > x1:
                x, y, row_h = x0, y + row_h + gy, 0
            if y + h > y1:
                raise SystemExit('regione piena per %s in %s' % (ref, (x0, y0, x1, y1)))
            cand = (x, y, x + w, y + h)
            hit = [rr for rr in placed_rects if not (cand[2] + gap <= rr[0] or cand[0] >= rr[2] + gap or cand[3] + gy <= rr[1] or cand[1] >= rr[3] + gy)]
            if not hit:
                break
            x = max(rr[2] for rr in hit) + gap
        fp.SetPosition(V(x - l, y - t))
        placed_rects.append(cand)
        x += w + gap
        row_h = max(row_h, h)


def reserve(ref):
    placed_rects.append(crtyd(fps[ref]))


# ------------------------------------------------------------------ potenza
CX = [50.0, 74.0]           # centri corpo MOSFET
YT, YB = 34.0, 90.0         # file dei terminali (riga alta / bassa)
# riga alta (corpo verso il basso): rot 180 sul lato bottom -> G=x0, D=x0-5.45, S=x0-10.9
place('Q1', CX[0] + 5.45, YT, 180, True)
place('Q2', CX[1] + 5.45, YT, 180, True)
# riga bassa (corpo verso l'alto): rot 0 sul lato bottom -> G=x0, D=x0+5.45, S=x0+10.9
place('Q3', CX[0] - 5.45, YB, 0, True)
place('Q4', CX[1] - 5.45, YB, 0, True)

SH = {'Q1': 'R17', 'Q2': 'R23', 'Q3': 'R29', 'Q4': 'R35'}
RG = {'Q1': 'R15', 'Q2': 'R21', 'Q3': 'R27', 'Q4': 'R33'}
INA = {'Q1': 'U4', 'Q2': 'U5', 'Q3': 'U7', 'Q4': 'U8'}
for q in ('Q1', 'Q2'):
    sx, sy = pad(q, 3)
    place(SH[q], sx + 0.64, 24.0, 90)            # pad1 in basso verso il source
    gx, gy = pad(q, 1)
    place(RG[q], gx, 26.5, 270)                  # pad2 (GATE) in basso
for q in ('Q3', 'Q4'):
    sx, sy = pad(q, 3)
    place(SH[q], sx - 0.64, 100.0, 270)          # pad1 in alto verso il source
    gx, gy = pad(q, 1)
    place(RG[q], gx, 97.5, 90)                   # pad2 (GATE) in alto

# morsetti, fusibile, diodo, TVS
place('J1', 9.0, 12.0)
place('J2', 9.0, 113.0)
place('F1', 20.0, 14.0, 270)
place('D1', 21.0, 45.0, 0)
place('D2', 20.0, 58.0, 180)
place('C1', 20.6, 66.0, 180)
place('J3', 8.5, 61.0, 90)

for ref in ('Q1', 'Q2', 'Q3', 'Q4', 'J1', 'J2', 'F1', 'D1', 'D2', 'C1', 'J3') + tuple(SH.values()) + tuple(RG.values()):
    reserve(ref)
# area corpo MOSFET / zona VLOAD: nessun componente piccolo
placed_rects.append((24, 30, 98, 94))

# INA228 vicino agli shunt (pin Vin verso lo shunt) + corridoi Kelvin riservati
# INA228 ruotati: fila pin 6..10 verso lo shunt, pin 9 (Vin-) allineato al pad di sense SHN
KEL = {}
for q in ('Q1', 'Q2'):
    sx, _ = pad(q, 3); KEL[q] = sx
    place(INA[q], sx - 1.13, 12.0, 270)
for q in ('Q3', 'Q4'):
    sx, _ = pad(q, 3); KEL[q] = sx
    place(INA[q], sx + 1.13, 112.0, 90)
for q in ('Q1', 'Q2', 'Q3', 'Q4'):
    x9, _ = pad(INA[q], 9)
    p3 = pad(SH[q], 3)
    if abs(x9 - p3[0]) > 0.02:
        fp = fps[INA[q]]; c = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(c.x + pcbnew.FromMM(p3[0] - x9), c.y))
place('U3', 57.0, 5.5, 0)
place('U6', 67.0, 120.0, 0)
for ref in ('U4', 'U5', 'U7', 'U8', 'U3', 'U6'):
    reserve(ref)
for q in ('Q1', 'Q2'):
    sx = KEL[q]; placed_rects.append((sx - 0.9, 14.6, sx + 5.4, 20.0))
for q in ('Q3', 'Q4'):
    sx = KEL[q]; placed_rects.append((sx - 5.4, 104.0, sx + 0.9, 109.4))

# ---------------------------------------------------------------- piazzatore ad ancore
USB_BOX = (131.0, 0.0, 170.0, 36.0)     # lato isolato + fascia di isolamento
GND1_BOX = (138.0, 0.5, 169.5, 33.0)


def rect_hit(r, rects, m=0.25):
    return [q for q in rects if not (r[2] + m <= q[0] or r[0] >= q[2] + m or r[3] + m <= q[1] or r[1] >= q[3] + m)]


placed_refs = set()
FIXED = set()


def same_net_points(netname, exclude):
    pts = []
    for r in placed_refs | FIXED:
        if r == exclude:
            continue
        for p in fps[r].Pads():
            if p.GetNetname() == netname:
                q = p.GetPosition()
                pts.append((mm(q.x) - OX, mm(q.y) - OY))
    return pts


def near(ref, aref, apin, own, extra=()):
    """Piazza ref vicino al pad (aref, apin) con il proprio pad 'own' rivolto verso l'ancora."""
    fp = fps[ref]
    ax, ay = pad(aref, apin)
    gnd1 = any(p.GetNetname() == 'GND1' for p in fp.Pads())
    others = {}
    for p in fp.Pads():
        if p.GetNumber() != str(own) and p.GetNetname() not in ('GND', 'GND1', ''):
            others[p.GetNumber()] = same_net_points(p.GetNetname(), ref)
    best = None
    for rad in [1.5 + 0.5 * i for i in range(40)]:
        steps = max(8, int(2 * math.pi * rad / 0.6))
        for k in range(steps):
            th = 2 * math.pi * k / steps
            cx, cy = ax + rad * math.cos(th), ay + rad * math.sin(th)
            for rot in (0, 90, 180, 270):
                fp.SetOrientationDegrees(rot)
                fp.SetPosition(V(cx, cy))
                l, t, r_, b_ = crtyd(fp)
                if l < 0.6 or t < 0.6 or r_ > W - 0.6 or b_ > H - 0.6:
                    continue
                if rect_hit((l, t, r_, b_), placed_rects):
                    continue
                if gnd1:
                    if not (l >= GND1_BOX[0] and t >= GND1_BOX[1] and r_ <= GND1_BOX[2] and b_ <= GND1_BOX[3]):
                        continue
                elif rect_hit((l, t, r_, b_), [USB_BOX], 0):
                    continue
                ox, oy = pad(ref, own)
                cost = math.hypot(ox - ax, oy - ay)
                for num, pts in others.items():
                    if pts:
                        px, py = pad(ref, num)
                        cost += 0.35 * min(math.hypot(px - qx, py - qy) for qx, qy in pts)
                for xr, xp in extra:
                    ex, ey = pad(xr, xp)
                    cost += 0.5 * math.hypot(cx - ex, cy - ey)
                if best is None or cost < best[0]:
                    best = (cost, cx, cy, rot)
        if best and rad > best[0] + 3:
            break
    if best is None:
        raise SystemExit('nessuna posizione per ' + ref)
    _, cx, cy, rot = best
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(V(cx, cy))
    placed_rects.append(crtyd(fp))
    placed_refs.add(ref)


# canali: (Rtop, Rbot, Cset, Rfb, Cfb, Rpd, Cina, Rg, opamp, +, -, out, Q, INA)
CH = [('R12', 'R13', 'C5', 'R14', 'C6', 'R16', 'C7', 'R15', 'U3', 3, 2, 1, 'Q1', 'U4'),
      ('R18', 'R19', 'C8', 'R20', 'C9', 'R22', 'C10', 'R21', 'U3', 5, 6, 7, 'Q2', 'U5'),
      ('R24', 'R25', 'C11', 'R26', 'C12', 'R28', 'C13', 'R27', 'U6', 3, 2, 1, 'Q3', 'U7'),
      ('R30', 'R31', 'C14', 'R32', 'C15', 'R34', 'C16', 'R33', 'U6', 5, 6, 7, 'Q4', 'U8')]

# --- IC e connettori della sezione di controllo (posizioni scelte a mano)
# Wemos D1 mini Pro su due strip 1x8: pin 1 (RST / TX) verso il bordo destro,
# cosi l'antenna ceramica e l'U.FL sporgono oltre il bordo, lontano da cooler e spreader.
WX1, WY0 = 166.5, 9.5
place('J4', WX1, WY0, 270)
place('J5', WX1, WY0 + 22.86, 270)
place('U12', 140.0, 33.0, 0)
place('L1', 140.0, 26.5, 0)
place('U10', 112.0, 74.0, 0)
place('U9', 122.0, 47.0, 0)
place('J6', 110.0, 11.0, 90)
place('Q5', 132.0, 66.0, 0)
place('Q6', 141.0, 66.0, 0)
place('Q7', 150.0, 66.0, 0)
place('J7', 157.0, 80.0, 0)
place('J8', 157.0, 90.0, 0)
place('U1', 109.0, 92.0, 0)
place('U2', 121.0, 92.0, 0)
place('J9', 153.0, 107.0, 180)
place('D4', 143.0, 112.0, 180)
place('F2', 136.0, 112.0, 0)
place('U11', 127.0, 112.0, 0)
place('D5', 107.0, 120.0, 0)
for r in ('J4', 'J5', 'U12', 'L1', 'U10', 'U9', 'J6', 'Q5', 'Q6', 'Q7', 'J7', 'J8', 'U1', 'U2',
          'J9', 'D4', 'F2', 'U11', 'D5'):
    reserve(r)
# area occupata dal corpo del modulo (niente componenti sotto)
placed_rects.append((147.0, 7.0, 170.0, 35.0))
place('R7', 101.0, 62.0, 0)          # 249k OVP: pad1 (VLOAD) verso la zona
place('R2', 15.5, 76.0, 180)         # 10k fallback sense: pad1 (VLOAD) verso la zona
reserve('R7'); reserve('R2')
FIXED = {r for r in fps if not (r[0] in 'RC' and r not in ('R17', 'R23', 'R29', 'R35', 'R15', 'R21', 'R27', 'R33', 'C1', 'R7', 'R2'))}

# --- reti dei canali, attorno all'op-amp e al gate
for rt, rb, cs, rf, cf, rpd, cina, rg, op, pin_p, pin_m, pin_o, q, ina in CH:
    near(cina, ina, 6, 1)
    near(rpd, rg, 2, 1)
    near(rb, op, pin_p, 1)
    near(cs, op, pin_p, 1)
    near(rt, op, pin_p, 2)
    near(cf, op, pin_m, 1, extra=[(op, pin_o)])
    near(rf, op, pin_m, 2)
near('C17', 'U3', 8, 1); near('C19', 'U3', 8, 1); near('C18', 'U6', 8, 1)

# --- rete di sense (bordo sinistro): prima riservo le vias di massa di D1/D2/C1
placed_rects += [(9.0, 39.5, 14.2, 50.5), (13.4, 56.6, 17.8, 59.4), (14.8, 64.8, 20.0, 67.2)]
near('R1', 'J3', 1, 1); near('R3', 'J3', 2, 2); near('D3', 'R1', 2, 1); near('C2', 'R1', 2, 1)

# --- Wemos: disaccoppiamento 3V3, pull-up I2C, tach su RX
near('C20', 'J4', 8, 1); near('C21', 'J4', 8, 1)
near('R37', 'J5', 4, 2); near('R38', 'J5', 3, 2); near('R36', 'J5', 2, 1)
near('C33', 'J8', 1, 1)
# --- pannello frontale: espansore, antirimbalzo, disaccoppiamento OLED
near('C22', 'U9', 16, 1); near('R43', 'U9', 9, 1)
near('R39', 'J6', 6, 2); near('C23', 'J6', 6, 1); near('R40', 'J6', 7, 2); near('C24', 'J6', 7, 1)
near('R41', 'J6', 8, 2); near('C25', 'J6', 8, 1); near('R42', 'J6', 9, 2); near('C26', 'J6', 9, 1)
near('C27', 'J6', 1, 1); near('C28', 'J6', 1, 1)
# --- buck 12 V -> 5 V
near('C39', 'U12', 3, 1); near('C40', 'U12', 3, 1); near('R55', 'U12', 2, 2); near('C41', 'U12', 6, 1)
near('C42', 'L1', 2, 1); near('C43', 'L1', 2, 1)
# --- DAC
near('C29', 'U10', 3, 1); near('C30', 'U10', 4, 1); near('C31', 'U10', 4, 1); near('C32', 'U10', 12, 1); near('R44', 'U10', 13, 2)
# --- NTC
near('R52', 'J8', 1, 2); near('R53', 'J8', 3, 2); near('C34', 'J8', 3, 1)
# --- logica ARM/CLAMP e ventola
near('R46', 'Q5', 2, 1); near('R45', 'Q5', 2, 2); near('R47', 'Q5', 2, 1); near('R48', 'Q5', 7, 2)
near('R49', 'Q7', 4, 2); near('R50', 'Q7', 4, 1); near('R51', 'J7', 3, 2)
# --- riferimento e comparatori
near('R4', 'U1', 1, 2); near('C4', 'U2', 8, 1)
near('R5', 'U2', 3, 2); near('R6', 'U2', 3, 1); near('R8', 'U2', 2, 1); near('C3', 'U2', 2, 1)
near('R10', 'U2', 6, 1); near('R9', 'U2', 6, 2); near('R11', 'U2', 5, 1)
# --- alimentazioni
near('C35', 'U11', 8, 1); near('C36', 'U11', 8, 1); near('C37', 'U11', 1, 1); near('C38', 'D5', 2, 1); near('R54', 'D5', 2, 2)

# fori di montaggio: angoli + distanziali verso lo spreader
holes = [(4, 4), (W - 4, 4), (4, H - 4), (W - 4, H - 4), (35, 47), (89, 47), (35, 77), (89, 77)]
for i, (hx, hy) in enumerate(holes):
    hfp = pcbnew.FootprintLoad(os.path.join(FPDIR, 'MountingHole.pretty'), 'MountingHole_3.2mm_M3')
    hfp.SetReference('H%d' % (i + 1))
    hfp.SetValue('M3' if i < 4 else 'M3 nylon (spreader)')
    board.Add(hfp)
    hfp.SetPosition(V(hx, hy))
    hfp.Reference().SetVisible(False)
    hfp.SetBoardOnly(True); hfp.SetExcludedFromBOM(True)

# ------------------------------------------------------------------ contorno e disegni
def seg(layer, a, b, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b))
    s.SetLayer(layer); s.SetWidth(pcbnew.FromMM(w))
    board.Add(s)


def rect(layer, x0, y0, x1, y1, w=0.1):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        seg(layer, a, b, w)


def text(layer, s, x, y, size=1.5, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(V(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


rect(pcbnew.Edge_Cuts, 0, 0, W, H, 0.15)
rect(pcbnew.Dwgs_User, 22, 27, 102, 97, 0.2)             # spreader rame 80x70
rect(pcbnew.Cmts_User, 27, 22, 97, 102, 0.2)             # base cooler SP3/TR4 (indicativa)
text(pcbnew.Dwgs_User, 'Cu SPREADER 80x70x6 (at VLOAD potential) - insulate from the cooler', 62, 99, 1.2)
text(pcbnew.Cmts_User, 'SP3/TR4 cooler base under the spreader', 62, 104, 1.2)
text(pcbnew.F_SilkS, 'DUT+', 9, 20, 2.0)
text(pcbnew.F_SilkS, 'DUT-', 9, 105, 2.0)
text(pcbnew.F_SilkS, 'SENSE +/-', 8.5, 53.5, 1.2)
text(pcbnew.F_SilkS, '12V AUX', 160, 99, 1.2)
text(pcbnew.F_SilkS, 'FRONT PANEL', 115, 3.2, 1.1)
rect(pcbnew.F_Fab, 147.5, 8.1, 169.9, 33.8, 0.12)
text(pcbnew.Cmts_User, 'Wemos antenna beyond the board edge: no copper for x > 164 mm', 150, 37.5, 0.8)
text(pcbnew.F_SilkS, 'WEMOS D1 mini Pro  (antenna ->)', 156, 21.0, 1.0)
text(pcbnew.F_SilkS, 'FAN', 167, 80, 1.2)
text(pcbnew.F_SilkS, 'NTC', 167, 90, 1.2)
text(pcbnew.F_SilkS, 'E-LOAD 4CH 60V 20A 300W  rev 0.3  IV3HGA', 128, 121.5, 1.3)
text(pcbnew.F_SilkS, '! 60 V !', 62, 44, 2.0)
for i, cx in enumerate(CX):
    text(pcbnew.F_SilkS, 'CH%d' % (i + 1), cx, 41, 1.5)
    text(pcbnew.F_SilkS, 'CH%d' % (i + 3), cx, 83, 1.5)


# ------------------------------------------------------------------ instradamento potenza / Kelvin
def netof(ref, num):
    for p in fps[ref].Pads():
        if p.GetNumber() == str(num):
            return p.GetNet()


def track(pts, w, layer, n):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(*a)); t.SetEnd(V(*b))
        t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(layer); t.SetNet(n)
        board.Add(t)


def via(x, y, n, d=1.0, drill=0.5):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(x, y)); v.SetWidth(pcbnew.FromMM(d)); v.SetDrill(pcbnew.FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(n)
    board.Add(v)


def zone(layer, n, pts, clearance=0.3, prio=0, full=True, minw=0.25, name=''):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(n)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(pcbnew.FromMM(OX + x), pcbnew.FromMM(OY + y))
    z.SetLocalClearance(pcbnew.FromMM(clearance))
    z.SetMinThickness(pcbnew.FromMM(minw))
    z.SetAssignedPriority(prio)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if full else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.6))
    if name: z.SetZoneName(name)
    board.Add(z)
    return z


F, B = pcbnew.F_Cu, pcbnew.B_Cu
GND = nets['GND']; VL = nets['VLOAD']; DUTP = netof('J1', 1)

# zone di potenza (top)
zone(F, DUTP, [(2.5, 5.0), (24.5, 5.0), (24.5, 18.6), (2.5, 18.6)], clearance=0.6, prio=2, name='DUT+')
zone(F, VL, [(17.6, 20.6), (25.5, 20.6), (25.5, 34.0), (97.5, 34.0), (97.5, 90.0), (17.6, 90.0)],
     clearance=0.6, prio=2, name='VLOAD')
# piano di massa (bottom); niente rame nella fascia verso l'antenna del Wemos
zone(B, GND, [(0.4, 0.4), (164.0, 0.4), (164.0, 36.0), (169.6, 36.0), (169.6, 124.6), (0.4, 124.6)],
     clearance=0.3, prio=1, full=False, name='GND')

# source -> shunt (3 mm), ritorno shunt -> vias GND, gate, Kelvin
for q in ('Q1', 'Q2', 'Q3', 'Q4'):
    top = q in ('Q1', 'Q2')
    sh, rg, ina = SH[q], RG[q], INA[q]
    sx, sy = pad(q, 3)
    p1 = pad(sh, 1); p2 = pad(sh, 2); p3 = pad(sh, 3); p4 = pad(sh, 4)
    track([(sx, sy), p1], 2.0, F, netof(q, 3))
    if top:
        vy = [18.9, 17.3]; vx = [p4[0], p4[0] + 1.5]
    else:
        vy = [105.1, 106.7]; vx = [p4[0], p4[0] - 1.5]
    track([p4, (p4[0], vy[1])], 2.0, F, GND)
    track([(vx[0], vy[0]), (vx[1], vy[0])], 2.0, F, GND)
    track([(vx[0], vy[1]), (vx[1], vy[1])], 2.0, F, GND)
    for x in vx:
        for y in vy:
            via(x, y, GND, 1.0, 0.5)
    # gate
    gx, gy = pad(q, 1)
    track([pad(rg, 2), (gx, gy)], 0.6, F, netof(q, 1))
    # Kelvin: SHP -> Vin+ (10), SHN -> Vin- (9)
    a10 = pad(ina, 10); a9 = pad(ina, 9)
    nsp = netof(sh, 2); nsn = netof(sh, 3)
    if top:
        xs, yh = sx + 4.5, a10[1] + 1.2
    else:
        xs, yh = sx - 4.5, a10[1] - 1.2
    track([p2, (xs, p2[1]), (xs, yh), (a10[0], yh), a10], 0.25, F, nsp)
    track([p3, a9], 0.25, F, nsn)

# D1 anodi, D2 e C1 -> GND tramite vias
for num in (1, 3):
    x, y = pad('D1', num)
    track([(x, y), (x - 3.0, y)], 1.5, F, GND)
    via(x - 3.0, y, GND, 1.2, 0.6); via(x - 3.0, y + (1.6 if num == 1 else -1.6), GND, 1.2, 0.6)
    track([(x - 3.0, y), (x - 3.0, y + (1.6 if num == 1 else -1.6))], 1.5, F, GND)
x, y = pad('D2', 2); track([(x, y), (x - 2.0, y)], 1.5, F, GND); via(x - 2.0, y, GND, 1.2, 0.6)
x, y = pad('C1', 2); track([(x, y), (x - 3.2, y)], 0.8, F, GND); via(x - 3.2, y, GND, 1.0, 0.5)
x, y = pad('R7', 1); track([(x, y), (95.5, y)], 0.5, F, VL)
x, y = pad('R2', 1); track([(x, y), (20.5, y)], 0.5, F, VL)
# GND del Wemos (J5 pin 7) cucita al piano principale fuori dall'ombra del modulo
x, y = pad('J5', 7); track([(x, y), (x, 37.6)], 0.8, F, GND); via(x, 37.6, GND, 1.0, 0.5); via(x - 1.6, 37.6, GND, 1.0, 0.5); track([(x, 37.6), (x - 1.6, 37.6)], 0.8, F, GND)
# J2 (DUT-) e vias GND: connessione piena alla zona
for p in board.GetPads():
    if p.GetNetname() in HV_NETS and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
        p.SetLocalClearance(pcbnew.FromMM(0.65))
for p in board.GetPads():
    if p.GetNetname() in ('GND', 'GND1') and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
        p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

# ------------------------------------------------------------------ vias di massa per i pad SMD GND/GND1 sul top
def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def obstacles():
    obs = []   # (kind, net, data)
    for p in board.GetPads():
        bb = p.GetBoundingBox()
        obs.append(('r', p.GetNetCode(), (mm(bb.GetLeft()) - OX, mm(bb.GetTop()) - OY, mm(bb.GetRight()) - OX, mm(bb.GetBottom()) - OY), p))
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            q = t.GetPosition()
            obs.append(('c', t.GetNetCode(), (mm(q.x) - OX, mm(q.y) - OY, mm(t.GetWidth(pcbnew.F_Cu)) / 2), t))
        else:
            a, b_ = t.GetStart(), t.GetEnd()
            obs.append(('s', t.GetNetCode(), (mm(a.x) - OX, mm(a.y) - OY, mm(b_.x) - OX, mm(b_.y) - OY, mm(t.GetWidth()) / 2), t))
    return obs


HVC = set()


def free_circle(x, y, r, net, obs, cl=0.3, ignore=None):
    if x - r < 1.0 or y - r < 1.0 or x + r > W - 1.0 or y + r > H - 1.0:
        return False
    if (16.8 < x < 26.4 and 19.7 < y < 91.2) or (26.2 <= x < 98.5 and 33.0 < y < 91.2):      # zona VLOAD/MOSFET
        return False
    for k, n, d, it in obs:
        if it is ignore:
            continue
        same = (n == net.GetNetCode())
        c = (0.75 if n in HVC else cl) if not same else -0.01
        if k == 'r':
            l, t_, rr, bb = d
            dx = max(l - x, 0, x - rr); dy = max(t_ - y, 0, y - bb)
            if math.hypot(dx, dy) < r + c and not same:
                return False
            if same and math.hypot(dx, dy) < r + 0.1 and it is not ignore:
                return False
        elif k == 'c':
            if math.hypot(x - d[0], y - d[1]) < r + d[2] + max(c, 0.2):
                return False
        else:
            if not same and seg_dist(x, y, *d[:4]) < r + d[4] + c:
                return False
    return True


def seg_free(ax, ay, bx, by, w, net, obs, pad_self):
    for k, n, d, it in obs:
        if n == net.GetNetCode() or it is pad_self:
            continue
        if k == 'r':
            l, t_, rr, bb = d
            for i in range(11):
                x = ax + (bx - ax) * i / 10; y = ay + (by - ay) * i / 10
                dx = max(l - x, 0, x - rr); dy = max(t_ - y, 0, y - bb)
                if math.hypot(dx, dy) < w / 2 + (0.75 if n in HVC else 0.205):
                    return False
        elif k == 's':
            for i in range(11):
                x = ax + (bx - ax) * i / 10; y = ay + (by - ay) * i / 10
                if seg_dist(x, y, *d[:4]) < w / 2 + d[4] + 0.25:
                    return False
        elif k == 'c':
            if seg_dist(d[0], d[1], ax, ay, bx, by) < w / 2 + d[2] + 0.25:
                return False
    return True


HVC = {nets[x].GetNetCode() for x in HV_NETS if x in nets and x != 'VSENSE'}
added = 0; failed = []
for p in list(board.GetPads()):
    n = p.GetNet()
    if n.GetNetname() not in ('GND', 'GND1') or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        continue
    fp = p.GetParentFootprint()
    if fp.GetReference() in SH.values():
        continue
    q = p.GetPosition(); px, py = mm(q.x) - OX, mm(q.y) - OY
    c = fp.GetPosition(); cx, cy = mm(c.x) - OX, mm(c.y) - OY
    ang = math.atan2(py - cy, px - cx) if (px, py) != (cx, cy) else 0
    bbp = p.GetBoundingBox()
    if bbp.GetHeight() > 1.8 * bbp.GetWidth():
        ang = math.pi / 2 if py > cy else -math.pi / 2
    elif bbp.GetWidth() > 1.8 * bbp.GetHeight():
        ang = 0 if px > cx else math.pi
    obs = obstacles()
    done = False
    small = mm(p.GetSize(pcbnew.F_Cu).x) < 0.7 or mm(p.GetSize(pcbnew.F_Cu).y) < 0.7
    vd, vdr, tw = (0.7, 0.35, 0.2) if small else (0.9, 0.4, 0.4)
    for dist in (1.6, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        for da in (0, 0.5, -0.5, 1.0, -1.0, 1.57, -1.57, 2.2, -2.2, 3.14):
            vx, vy = px + dist * math.cos(ang + da), py + dist * math.sin(ang + da)
            vx, vy = round(vx, 2), round(vy, 2)
            if free_circle(vx, vy, vd / 2, n, obs, ignore=p) and seg_free(px, py, vx, vy, tw, n, obs, p):
                via(vx, vy, n, vd, vdr)
                track([(px, py), (vx, vy)], tw, F, n)
                added += 1; done = True
                break
        if done:
            break
    if not done:
        failed.append(fp.GetReference() + '.' + p.GetNumber())
print('vias GND aggiunte', added, 'non piazzate', failed)

board.Save(os.path.join(PRJ, 'eload_4ch.kicad_pcb'))
json.dump({k: list(v) for k, v in {}.items()}, open('/tmp/pcb_state.json', 'w'))
print('salvato')
