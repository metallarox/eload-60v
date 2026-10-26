"""Remove degenerate track stubs (< 0.05 mm) left by the SES import; DRC re-checks connectivity afterwards."""
import sys, os, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); n = 0
STAGE2 = len(sys.argv) > 2
for t in ([] if STAGE2 else list(b.GetTracks())):
    if t.GetClass() == 'PCB_TRACK' and pcbnew.ToMM(t.GetLength()) < 0.05:
        b.Remove(t); n += 1
if not STAGE2:
    print('cleanup: removed %d stubs' % n)
    if n:
        b.Save(sys.argv[1]); sys.stdout.flush()
        os.execv(sys.executable, [sys.executable, __file__, sys.argv[1], 'snap'])

# snap dangling ends that already overlap a same-net track onto that track's centreline
import math
tr = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
pads = list(b.GetPads()); vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
def proj(p, a, c):
    ax, ay, cx, cy, px, py = a.x, a.y, c.x, c.y, p.x, p.y
    L = (cx - ax) ** 2 + (cy - ay) ** 2
    u = 0 if L == 0 else max(0, min(1, ((px - ax) * (cx - ax) + (py - ay) * (cy - ay)) / L))
    return pcbnew.VECTOR2I(int(ax + u * (cx - ax)), int(ay + u * (cy - ay)))
snapped = 0
for t in tr:
    for end in ('start', 'end'):
        p = t.GetStart() if end == 'start' else t.GetEnd()
        net = t.GetNetCode()
        shared = any(o is not t and o.GetNetCode() == net and (o.GetStart() == p or o.GetEnd() == p) for o in tr if o.m_Uuid.AsString() != t.m_Uuid.AsString())
        shared = shared or any(v.GetNetCode() == net and v.GetPosition() == p for v in vias)
        shared = shared or any(pd.GetNetCode() == net and pd.HitTest(p) for pd in pads)
        if shared: continue
        for o in tr:
            if o.m_Uuid.AsString() == t.m_Uuid.AsString() or o.GetNetCode() != net or o.GetLayer() != t.GetLayer(): continue
            q = proj(p, o.GetStart(), o.GetEnd())
            if math.hypot(q.x - p.x, q.y - p.y) <= min((o.GetWidth() + t.GetWidth()) / 2, pcbnew.FromMM(0.05)):
                if end == 'start': t.SetStart(q)
                else: t.SetEnd(q)
                if q != o.GetStart() and q != o.GetEnd():   # T-junction: split the other track at q
                    nt = pcbnew.PCB_TRACK(b); nt.SetStart(q); nt.SetEnd(o.GetEnd()); nt.SetWidth(o.GetWidth())
                    nt.SetLayer(o.GetLayer()); nt.SetNetCode(o.GetNetCode()); o.SetEnd(q); b.Add(nt); tr.append(nt)
                snapped += 1; break
b.Save(sys.argv[1]); print('cleanup: snapped %d dangling ends' % snapped)
