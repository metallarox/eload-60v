import numpy as np
def sim(I0, I1, C6, C5, T=1e-3, dt=4e-9, Vth=3.5, K=13.0, tstep=20e-6):
    GBW=2.5e6; SR=7.5e6; R14=1e3; Rgt=103; R16=10e3; Cg=8.1e-9; Rs=0.02; Rp=960.0
    n=int(T/dt); out=np.empty((n//50+1,2)); j=0
    Vp=I0*Rs; Vint=0.0; Vc=0.0; Vg=0.0; Id=I0
    # pre-settle at I0
    if I0>0:
        Vg=Vth+np.sqrt(I0/K)+I0*Rs; Vint=Vg*(1+Rgt/R16); Vc=I0*Rs-Vint
    for k in range(n):
        t=k*dt
        Vdac_eff=(I1 if t>=tstep else I0)*Rs
        Vp+= (Vdac_eff-Vp)/(Rp*C5)*dt
        Vs=Id*Rs
        i=(Vs-Vint-Vc)/R14          # current R14 -> C6 (Rz=0): Vn = Vint+Vc
        Vn=Vint+Vc
        Vc+= i/C6*dt
        dV=2*np.pi*GBW*(Vp-Vn)
        dV=max(-SR,min(SR,dV)); Vint=min(11.8,max(0.02,Vint+dV*dt))
        Vg+= ((Vint-Vg)/Rgt - Vg/R16)/Cg*dt
        vov=Vg-Vs-Vth
        Id=K*vov*vov if vov>0 else 0.0
        if k%50==0: out[j]=(t,Id); j+=1
    return out[:j]
if __name__=='__main__':
    import pickle
    res={}
    for C6,C5,lab in [(10e-9,100e-9,'attuale'),(1e-9,10e-9,'proposto')]:
        for I0,I1 in [(0,1.0),(0.01,1.0),(1.0,1.2)]:
            o=sim(I0,I1,C6,C5); res[(lab,I0,I1)]=o
            y=o[:,1]; t=o[:,0]-20e-6
            tgt=I1; i10=np.where(y>=I0+0.1*(tgt-I0))[0]; i90=np.where(y>=I0+0.9*(tgt-I0))[0]
            print(lab,I0,'->',I1, 't10=%.1f us t90=%.1f us overshoot=%.1f%%'%(t[i10[0]]*1e6 if len(i10) else -1, t[i90[0]]*1e6 if len(i90) else -1, (y.max()-tgt)/(tgt-I0)*100))
    pickle.dump(res,open('tsim.pkl','wb'))
