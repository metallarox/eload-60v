import pickle, numpy as np, sympy as sp
Hn,Hs=pickle.load(open('h.pkl','rb'))
syms={str(x):x for x in Hn.free_symbols|Hs.free_symbols}
s=syms['s']
def tf(H,p):
    e=H.subs({syms[k]:v for k,v in p.items() if k in syms})
    n,d=sp.fraction(sp.together(sp.simplify(e)))
    return [float(c) for c in sp.Poly(n,s).all_coeffs()],[float(c) for c in sp.Poly(d,s).all_coeffs()]
def gm_of(I):  # square law from gfs=44 S at 37.5 A, capped by weak inversion I/(n Vt)
    return min(44*np.sqrt(I/37.5), I/(1.5*0.02585))
BASE=dict(Rz=0.0,Ro=300.0,Rgt=103.0,R16=10e3,Rs=0.02,R14=1e3,C6=10e-9,Cgs=7.75e-9,Cgd=0.35e-9)
GBW=2.5e6; A0=1e6; P2=4.5e6
def A(w): return A0/((1+1j*w/(2*np.pi*GBW/A0))*(1+1j*w/(2*np.pi*P2)))
f=np.logspace(0,8,4000); w=2*np.pi*f
def resp(I,**ov):
    p=dict(BASE); p.update(ov); p['gm']=gm_of(I)
    nn,dn=tf(Hn,p); ns,ds=tf(Hs,p)
    hn=np.polyval(nn,1j*w)/np.polyval(dn,1j*w); hs=np.polyval(ns,1j*w)/np.polyval(ds,1j*w)
    L=A(w)*hn
    return L, A(w)*hs/(1+L), p
def pm(L):
    mag=np.abs(L); i=np.where(mag<1)[0][0]
    ph=np.unwrap(np.angle(L))[i]*180/np.pi
    # gain margin
    phs=np.unwrap(np.angle(L))*180/np.pi
    j=np.where(phs<-180)[0]
    gmarg= -20*np.log10(np.abs(L[j[0]])) if len(j) else np.inf
    return f[i], 180+ph, gmarg
if __name__=='__main__':
    for I in (0.02,0.1,0.5,1.25,2.5,5):
        L,_,p=resp(I); fc,ph,g=pm(L)
        print(f"I={I:5.2f} A gm={p['gm']:5.2f} S  fc={fc/1e3:8.1f} kHz  PM={ph:6.1f} deg  GM={g:5.1f} dB")
    print('--- sensitivity at 1.25 A')
    for k,v in [('Ro',100),('Ro',600),('C6',4.7e-9),('C6',22e-9),('R14',2.2e3),('Cgs',12e-9),('Rgt',47)]:
        L,_,_=resp(1.25,**{k:v}); fc,ph,g=pm(L); print(k,v,f"fc={fc/1e3:.1f}k PM={ph:.1f} GM={g:.1f}")

import scipy.signal as sg
def reduce_tf(num, den, fmax=1e10):
    z,p,k=sg.tf2zpk(num,den)
    z=list(z); p=list(p)
    for zz in list(z):
        for pp in p:
            if abs(zz-pp) < 1e-6*abs(pp)+1e-9:
                z.remove(zz); p.remove(pp); break
    z=[x for x in z if abs(x)<fmax]; p=[x for x in p if abs(x)<fmax]
    dc=np.real(np.polyval(num,0)/np.polyval(den,0))
    zz=np.array(z); pp=np.array(p)
    knew=dc*np.real(np.prod(-pp))/np.real(np.prod(-zz)) if len(zz) else dc*np.real(np.prod(-pp))
    return sg.ZerosPolesGain(zz,pp,knew)
