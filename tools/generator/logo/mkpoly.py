import cv2, json, sys
from mklogo import silk_bitmap
D, RES = 25.0, 0.04
bmp = silk_bitmap(D, RES); n = bmp.shape[0]
cnts, hier = cv2.findContours(bmp, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
mm = lambda p: [round((float(p[0]) - n / 2) * RES, 4), round((float(p[1]) - n / 2) * RES, 4)]
out = []
for i, c in enumerate(cnts):
    if hier[0][i][3] != -1: continue
    c = cv2.approxPolyDP(c, 0.6, True)
    holes = []; j = hier[0][i][2]
    while j != -1:
        h = cv2.approxPolyDP(cnts[j], 0.6, True)
        if len(h) >= 3: holes.append([mm(p) for p in h[:, 0, :]])
        j = hier[0][j][0]
    out.append({'outline': [mm(p) for p in c[:, 0, :]], 'holes': holes})
json.dump({'D': D, 'polys': out}, open(sys.argv[1], 'w'))
print(len(out), 'polygons')
