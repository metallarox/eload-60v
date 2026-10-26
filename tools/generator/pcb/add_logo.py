"""Adds the IV3HGA logo as a board-only silkscreen footprint (eload:Logo_IV3HGA_25mm) at a free spot.
Usage: add_logo.py board.kicad_pcb X Y   (mm from the top-left corner of the board outline)"""
import sys, os, json, pcbnew
PCB = sys.argv[1]; X, Y = float(sys.argv[2]), float(sys.argv[3])
data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_polys.json'))); D = data['D']
PRJ = os.path.dirname(os.path.abspath(PCB)); LIB = os.path.join(PRJ, 'eload.pretty'); os.makedirs(LIB, exist_ok=True)
M = pcbnew.FromMM
polys = []
for poly in data['polys']:
    ps = pcbnew.SHAPE_POLY_SET(); o = ps.NewOutline()
    for x, y in poly['outline']: ps.Append(M(x), M(y), o)
    for h in poly['holes']:
        hi = ps.NewHole(o)
        for x, y in h: ps.Append(M(x), M(y), o, hi)
    ps.Fracture()
    for k in range(ps.OutlineCount()):
        ch = ps.Outline(k)
        polys.append([(pcbnew.ToMM(ch.CPoint(i).x), pcbnew.ToMM(ch.CPoint(i).y)) for i in range(ch.PointCount())])
txt = ['(footprint "Logo_IV3HGA_25mm"', '  (version 20240108)', '  (generator "eload")', '  (layer "F.Cu")',
       '  (descr "IV3HGA logo, %g mm, silkscreen")' % D, '  (attr board_only exclude_from_pos_files exclude_from_bom)',
       '  (property "Reference" "LOGO1" (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',
       '  (property "Value" "Logo_IV3HGA" (at 0 2 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))']
for p in polys:
    txt.append('  (fp_poly (pts %s) (stroke (width 0) (type solid)) (fill yes) (layer "F.SilkS"))' % ' '.join('(xy %.4f %.4f)' % q for q in p))
txt.append('  (fp_circle (center 0 0) (end %.3f 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))' % (D / 2 + 0.3))
txt.append(')')
open(os.path.join(LIB, 'Logo_IV3HGA_25mm.kicad_mod'), 'w').write('\n'.join(txt) + '\n')
open(os.path.join(PRJ, 'fp-lib-table'), 'w').write('(fp_lib_table\n  (version 7)\n  (lib (name "eload")(type "KiCad")(uri "${KIPRJMOD}/eload.pretty")(options "")(descr "Project footprints: logo"))\n)\n')
b = pcbnew.LoadBoard(PCB)
for f in list(b.GetFootprints()):
    if f.GetReference() == 'LOGO1': b.Remove(f)
fp = pcbnew.FootprintLoad(LIB, 'Logo_IV3HGA_25mm')
fp.SetFPIDAsString('eload:Logo_IV3HGA_25mm'); fp.SetReference('LOGO1')
ed = b.GetBoardEdgesBoundingBox()
fp.SetPosition(pcbnew.VECTOR2I(ed.GetLeft() + M(X), ed.GetTop() + M(Y)))
b.Add(fp); b.Save(PCB)
print('logo: %d silkscreen polygons at (%.1f, %.1f)' % (len(polys), X, Y))
