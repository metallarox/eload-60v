"""Esporta DSN, lancia Freerouting, reimporta le piste (senza toccare GND/GND1 e le piste esistenti)."""
import pcbnew, re, subprocess, sys, os, math
sys.path.insert(0, '/home/claude/gen')
from sexp import parse, find, find1, uq

PCB = '/home/claude/out/carico_attivo/carico_attivo.kicad_pcb'
SKIP = {'GND', 'GND1', 'VLOAD', 'Net-(J1-Pin_1)'}
b = pcbnew.LoadBoard(PCB)
import os as _os
LOCKALL = _os.environ.get('LOCKALL', '1') == '1'
PROT = ('GND', 'GND1', 'VLOAD', 'Net-(J1-Pin_1)')
for t in b.GetTracks():
    n = t.GetNetname()
    keep_fixed = LOCKALL or n in PROT or n.startswith('Net-(Q') or '/SHP' in n or '/SHN' in n
    t.SetLocked(bool(keep_fixed))
pcbnew.ExportSpecctraDSN(b, '/tmp/in.dsn')
dsn = open('/tmp/in.dsn').read()

# --- risoluzione / unita
unit = re.search(r'\(unit (\w+)\)', dsn).group(1)
div = 1
scale = {'um': 1e-3, 'mm': 1.0, 'mil': 0.0254}[unit]   # DSN unit -> mm


def to_dsn(v_nm):
    return v_nm / 1e6 / scale


# --- piani: via tutti quelli delle reti escluse
for n in SKIP:
    dsn = re.sub(r'\n\s*\(plane "?%s"? \(polygon[^)]*\)\)' % re.escape(n), '', dsn)
# --- reti escluse: restano definite (per le piste fisse) ma senza pin da collegare
def empty_pins(m):
    return m.group(1) + '(pins)'
for n in SKIP:
    dsn = re.sub(r'(\n\s*\(net "?%s"?\s*\n\s*)\(pins[^)]*\)' % re.escape(n), empty_pins, dsn)
keep = []
OX, OY = 50.0, 40.0
def P(x, y):
    return '%.1f %.1f' % ((OX + x) * 1000, -(OY + y) * 1000)
for poly in ([(16.8, 4.2), (25.2, 4.2), (25.2, 19.9), (26.2, 19.9), (26.2, 33.3), (98.3, 33.3), (98.3, 90.7), (16.8, 90.7)],):
    keep.append('(keepout "" (polygon F.Cu 0 %s))' % ' '.join(P(*q) for q in poly + [poly[0]]))
keep.append('(keepout "" (polygon F.Cu 0 %s))' % ' '.join(P(*q) for q in [(1.8, 4.2), (25.2, 4.2), (25.2, 19.4), (1.8, 19.4), (1.8, 4.2)]))
for L_ in ('F.Cu', 'B.Cu'):
    keep.append('(keepout "" (polygon %s 0 %s))' % (L_, ' '.join(P(*q) for q in [(164.6, 7.6), (169.8, 7.6), (169.8, 36.0), (164.6, 36.0), (164.6, 7.6)])))
for L in ('F.Cu', 'B.Cu'):
    for x0, y0, x1, y1 in ((0, 0, 170, 0.75), (0, 124.25, 170, 125), (0, 0, 0.75, 125), (169.25, 0, 170, 125)):
        keep.append('(keepout "" (polygon %s 0 %s %s %s %s %s))' % (L, P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1), P(x0, y0)))
# anelli HV attorno ai pad VLOAD / DUT+ (i pad di reti escluse non hanno classe)
for p in b.GetPads():
    if p.GetNetname() in ('VLOAD', 'Net-(J1-Pin_1)'):
        bb = p.GetBoundingBox(); q = p.GetPosition()
        d = math.hypot(bb.GetWidth(), bb.GetHeight()) / 1e3 + 1300
        Ls = ['F.Cu', 'B.Cu'] if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else ['F.Cu']
        for L in Ls:
            keep.append('(keepout "" (circle %s %.1f %.1f %.1f))' % (L, d, q.x / 1e3, -q.y / 1e3))
# piste esistenti protette
dsn = dsn.replace('(type route)', '(type protect)') if LOCKALL else dsn
i = dsn.index('\n    (via ', dsn.index('(structure'))
dsn = dsn[:i] + '\n    ' + '\n    '.join(keep) + dsn[i:]
open('/tmp/in2.dsn', 'w').write(dsn)
print('keepout', len(keep), 'unita', unit, div)

if '--norun' in sys.argv:
    sys.exit()
passes = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else '25'
if os.path.exists('/tmp/out.ses'):
    os.remove('/tmp/out.ses')
cmd = ['xvfb-run', '-a', 'java', '-jar', '/home/claude/freerouting.jar', '-de', '/tmp/in2.dsn', '-do', '/tmp/out.ses', '-mp', passes]
p = subprocess.run(cmd, capture_output=True, text=True, timeout=3000)
print(p.stdout[-1500:], p.stderr[-1500:])
