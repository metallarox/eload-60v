from num import *
import scipy.signal as sg
def closed(I, C5=100e-9, **ov):
    p=dict(BASE); p.update(ov); p['gm']=gm_of(I)
    nn,dn=tf(Hn,p); ns,ds=tf(Hs,p)
    wp1=2*np.pi*GBW/A0; wp2=2*np.pi*P2
    dA=np.polymul([1/wp1,1],[1/wp2,1])
    num=np.polymul(A0*np.array(ns),dn)
    den=np.polymul(np.polyadd(np.polymul(dA,dn),A0*np.array(nn)),ds)
    # prefilter: Vp/Vdac = (R13/(R12+R13)) / (1 + s*C5*R12||R13)
    Rp=24e3*1e3/25e3
    num=np.polymul(num,[1/25]); den=np.polymul(den,[C5*Rp,1])
    num=np.array(num)/p['Rs']   # -> current A per V_DAC
    return reduce_tf(num,den)
for C6,C5 in [(10e-9,100e-9),(1e-9,10e-9),(2.2e-9,10e-9)]:
    print('C6',C6,'C5',C5)
    for I in (0.1,1.25,5):
        L,_,_=resp(I,C6=C6); fc,ph,g=pm(L)
        H=closed(I,C5=C5,C6=C6)
        ww,hh=sg.freqresp(H,w=2*np.pi*np.logspace(1,7,3000)); mag=np.abs(hh)/np.abs(hh[0])
        f3=np.logspace(1,7,3000)[np.where(mag<0.7071)[0][0]]
        t=np.linspace(0,5e-3,50001); t,y=sg.step(H,T=t); y=y/2.0
        tr=t[np.where(y>0.9)[0][0]]-t[np.where(y>0.1)[0][0]]; os_=(y.max()-1)*100
        print(f"  I={I:4.2f}  PM={ph:5.1f}  f-3dB={f3/1e3:6.2f} kHz  tr={tr*1e6:6.1f} us  OS={os_:4.1f}%  peak={20*np.log10(mag.max()):.2f} dB")
