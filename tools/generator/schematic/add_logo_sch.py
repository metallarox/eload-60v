"""Places the IV3HGA logo next to the title block of every schematic sheet."""
import sys, os, re, io, base64, uuid
from PIL import Image
D = sys.argv[1]; SRC = sys.argv[2]
PAPER = {'A4': (297, 210), 'A3': (420, 297), 'A2': (594, 420), 'A1': (841, 594), 'A0': (1189, 841)}
im = Image.open(SRC).convert('RGBA')
px = 300                                   # 300 px at 300 ppi = 25.4 mm
im = im.resize((px, px), Image.LANCZOS)
a = im.split()[3].load()
for yy in range(px):
    for xx in range(px):
        if (xx - px / 2 + 0.5) ** 2 + (yy - px / 2 + 0.5) ** 2 > (px / 2 - 0.5) ** 2: a[xx, yy] = 0   # transparent corners
buf = io.BytesIO(); im.save(buf, 'PNG'); b64 = base64.b64encode(buf.getvalue()).decode()
data = ' '.join('"%s"' % b64[i:i + 76] for i in range(0, len(b64), 76))
for f in sorted(os.listdir(D)):
    if not f.endswith('.kicad_sch'): continue
    p = os.path.join(D, f); t = open(p).read()
    t = re.sub(r'\n\s*\(image \(at [^\n]*\n?(?:[^\n]*\n)*?\s*\)\s*\)\s*(?=\n)', '', t) if '(image' in t else t
    m = re.search(r'\(paper "(A\d)"', t); w, h = PAPER[m.group(1) if m else 'A3']
    x, y = w - 10 - 110 - 26, h - 10 - 18           # left of the 110 mm wide title block
    img = '(image (at %.2f %.2f) (scale 1) (uuid "%s") (data %s))' % (x, y, uuid.uuid4(), data)
    i = t.rstrip().rfind(')')
    t = t[:i].rstrip() + '\n' + img + '\n)\n'
    open(p, 'w').write(t)
    print('logo ->', f, m.group(1) if m else '?')
