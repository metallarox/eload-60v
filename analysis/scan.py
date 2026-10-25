exec(open('cl.py').read().split('for C6,C5')[0])
fl=np.logspace(1,7,3000)
def bw(H):
    ww,hh=sg.freqresp(H,w=2*np.pi*fl); m=np.abs(hh)/2.0
    return fl[np.where(m<0.7071)[0][0]], 20*np.log10(m.max())
for C6 in (10e-9,2.2e-9,1e-9,470e-12,220e-12,100e-12):
    row=[]
    for I in (0.1,5):
        for ov in ({},{'Ro':600,'Cgs':12e-9}):
            L,_,_=resp(I,C6=C6,**ov); fc,ph,g=pm(L)
            H=closed(I,C5=1e-12,C6=C6,**ov); f3,pk=bw(H)
            row.append(f"{ph:5.1f}/{f3/1e3:5.1f}k/{pk:+.1f}")
    print(f"C6={C6*1e9:6.2f}n ", '  '.join(row))
