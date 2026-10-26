"""Reposition silkscreen reference designators and board texts so that none of them
overlaps pads, other silkscreen, other component bodies (courtyards) or the board edge."""
import sys, math, pcbnew
PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
MM = pcbnew.FromMM
def mm(v): return pcbnew.ToMM(v)
ed = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = mm(ed.GetLeft()) + 0.6, mm(ed.GetTop()) + 0.6, mm(ed.GetRight()) - 0.6, mm(ed.GetBottom()) - 0.6

def bb(o):
    r = o.GetBoundingBox(); return (mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom()))
def grow(r, m): return (r[0] - m, r[1] - m, r[2] + m, r[3] + m)
def hit(a, c): return not (a[2] <= c[0] or a[0] >= c[2] or a[3] <= c[1] or a[1] >= c[3])

SIDES = {pcbnew.F_SilkS: (pcbnew.F_Cu, pcbnew.F_CrtYd), pcbnew.B_SilkS: (pcbnew.B_Cu, pcbnew.B_CrtYd)}

def obstacles(silk, skip_fp=None, skip_item=None):
    cu, crt = SIDES[silk]
    pads, shapes, bodies = [], [], []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(cu):
                pads.append(grow(bb(p), 0.2))
        for g in fp.GraphicalItems():
            if g.GetLayer() == silk and g.GetClass() != 'PCB_FIELD' and g.GetClass() != 'PCB_TEXT':
                if g.GetClass() == 'PCB_SHAPE' and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                    a, c = g.GetStart(), g.GetEnd(); L = max(mm((c - a).EuclideanNorm()), 0.01); n = int(L / 0.25) + 1
                    w = mm(g.GetWidth()) / 2 + 0.15
                    for i in range(n + 1):
                        x = mm(a.x) + (mm(c.x) - mm(a.x)) * i / n; y = mm(a.y) + (mm(c.y) - mm(a.y)) * i / n
                        shapes.append((x - w, y - w, x + w, y + w))
                else:
                    shapes.append(grow(bb(g), 0.15))
        if skip_fp is None or fp.GetReference() != skip_fp.GetReference():
            try:
                cy = fp.GetCourtyard(crt)
                if cy.OutlineCount():
                    r = cy.BBox(); bodies.append((mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom())))
            except Exception:
                pass
    for d in b.GetDrawings():
        if d.GetLayer() == silk and (skip_item is None or d.m_Uuid.AsString() != skip_item.m_Uuid.AsString()):
            shapes.append(grow(bb(d), 0.15))
    return pads, shapes, bodies

placed = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
ANG = {0: pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T), 90: pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T)}

def try_place(txt, silk, cx, cy, box, obs, sizes, own_pads=(), angles=(0, 90)):
    pads, shapes, bodies = obs
    best = None
    for size in sizes:
        txt.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); txt.SetTextThickness(MM(max(0.1, size * 0.15)))
        for ang in angles:
            txt.SetTextAngle(ANG[ang])
            txt.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cy)))
            r0 = bb(txt); tw, th = r0[2] - r0[0], r0[3] - r0[1]
            l, t, rr, bo = box
            cands = []
            for gap in (0.25, 0.6, 1.0, 1.6, 2.4, 3.4, 4.6, 6.0):
                cands += [((l + rr) / 2, t - gap - th / 2), ((l + rr) / 2, bo + gap + th / 2),
                          (l - gap - tw / 2, (t + bo) / 2), (rr + gap + tw / 2, (t + bo) / 2),
                          (l + tw / 2, t - gap - th / 2), (rr - tw / 2, t - gap - th / 2),
                          (l + tw / 2, bo + gap + th / 2), (rr - tw / 2, bo + gap + th / 2),
                          (l - gap - tw / 2, t - gap - th / 2), (rr + gap + tw / 2, t - gap - th / 2),
                          (l - gap - tw / 2, bo + gap + th / 2), (rr + gap + tw / 2, bo + gap + th / 2)]
            inside = [((l + rr) / 2, (t + bo) / 2)]
            for k, (x, y) in enumerate(cands + inside):
                r = (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)
                if r[0] < EX0 or r[1] < EY0 or r[2] > EX1 or r[3] > EY1: continue
                if any(hit(r, p) for p in pads): continue
                if any(hit(r, s) for s in shapes): continue
                if any(hit(r, grow(q, 0.15)) for q in placed[silk]): continue
                body_hits = sum(1 for q in bodies if hit(r, q))
                dx = max(l - r[2], 0, r[0] - rr); dy = max(t - r[3], 0, r[1] - bo)
                dist = math.hypot(dx, dy)
                own = 3.0 if k >= len(cands) else 0.0
                score = body_hits * 100 + dist * 2 + own + (0 if ang == 0 else 0.3) + (sizes.index(size) * 20)
                if best is None or score < best[0]:
                    best = (score, size, ang, x, y, r)
            if best and best[0] < 1: break
        if best and best[0] < 100: break
    if best is None:
        return None
    score, size, ang, x, y, r = best
    txt.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); txt.SetTextThickness(MM(max(0.1, size * 0.15)))
    txt.SetTextAngle(ANG[ang]); txt.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    placed[silk].append(bb(txt))
    return score

fps = [f for f in b.GetFootprints() if f.Reference().IsVisible() and not f.GetReference().startswith('H')]
def area(f):
    r = bb(f); return (r[2] - r[0]) * (r[3] - r[1])
fps.sort(key=lambda f: -area(f))
fails, overbody = [], []
for f in fps:
    ref = f.Reference(); silk = ref.GetLayer()
    if silk not in SIDES: continue
    ref.SetKeepUpright(True)
    crt = SIDES[silk][1]
    try:
        cy = f.GetCourtyard(crt); r = cy.BBox(); box = (mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom()))
        if cy.OutlineCount() == 0: raise ValueError
    except Exception:
        box = bb(f)
    small = (box[2] - box[0]) * (box[3] - box[1]) < 30
    sizes = (0.8,) if small else (1.0, 0.8)
    c = f.GetPosition()
    s = try_place(ref, silk, mm(c.x), mm(c.y), box, obstacles(silk, skip_fp=f), sizes)
    if s is None: fails.append(f.GetReference())
    elif s >= 100: overbody.append(f.GetReference())
# board texts
for d in list(b.GetDrawings()):
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() in SIDES:
        silk = d.GetLayer(); r = bb(d)
        size = mm(d.GetTextSize().x)
        obs = obstacles(silk, skip_item=d)
        pads, shapes, bodies = obs
        if not any(hit(r, p) for p in pads) and not any(hit(r, s) for s in shapes) and not any(hit(r, grow(q, 0.15)) for q in placed[silk]):
            placed[silk].append(r); continue
        c = d.GetPosition(); ox, oy = mm(c.x), mm(c.y); oang = d.GetTextAngle()
        s = try_place(d, silk, ox, oy, (r[0], r[1], r[2], r[3]), obs, (size,), angles=(0,))
        if s is None or s >= 100:
            # global search on a 0.5 mm grid, nearest free spot to the original position, horizontal
            d.SetTextAngle(ANG[0]); d.SetPosition(pcbnew.VECTOR2I(MM(ox), MM(oy)))
            r0 = bb(d); tw, th = r0[2] - r0[0], r0[3] - r0[1]
            best = None
            y = EY0 + th / 2
            while y < EY1 - th / 2:
                x = EX0 + tw / 2
                while x < EX1 - tw / 2:
                    rr = (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)
                    dd = math.hypot(x - ox, y - oy)
                    if (best is None or dd < best[0]) and not any(hit(rr, p) for p in pads) and not any(hit(rr, q) for q in shapes) \
                       and not any(hit(rr, grow(q, 0.15)) for q in placed[silk]) and not any(hit(rr, q) for q in bodies):
                        best = (dd, x, y)
                    x += 0.5
                y += 0.5
            if best:
                d.SetPosition(pcbnew.VECTOR2I(MM(best[1]), MM(best[2]))); placed[silk].append(bb(d))
            else:
                d.SetTextAngle(oang); d.SetPosition(pcbnew.VECTOR2I(MM(ox), MM(oy))); fails.append(d.GetText())
b.Save(PCB)
print('relabel: %d refs, failed %s, over another body %s' % (len(fps), fails, overbody))
