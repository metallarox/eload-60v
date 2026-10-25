import numpy as np, pickle, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts():
    if 'Inter' in f: fm.fontManager.addfont(f)
plt.rcParams.update({'font.family':'Inter','font.size':12,'axes.edgecolor':'#9aa1ae','axes.labelcolor':'#1d2433',
  'xtick.color':'#4b5263','ytick.color':'#4b5263','axes.grid':True,'grid.color':'#e3e5ea','grid.linewidth':0.8,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':200})
OR='#e8692c'; NV='#1d2433'; GR='#8a91a0'; RD='#c0392b'; BL='#2b6cb0'
exec(open('scan.py').read().split('for C6 in')[0])
# ---------------- SOA
fig,ax=plt.subplots(figsize=(7.2,4.9))
V=np.logspace(0,2,400)
ax.loglog(V,np.minimum(75,400/V),color=GR,lw=1.6,label='400 W, Tc = 25 °C (rating)')
ax.loglog(V,np.minimum(75,174/V),color=NV,lw=1.8,ls='--',label='174 W thermal limit, Tc ≈ 96 °C')
env=np.where(V<=15,5,75/V); m=V<=60
ax.fill_between(V[m],0.1,env[m],color=OR,alpha=0.18,lw=0)
ax.loglog(V[m],env[m],color=OR,lw=3,label='Operating envelope per MOSFET (≤ 75 W)')
ax.plot([80],[3],'o',color=BL,ms=9,label='Guaranteed FBSOA 80 V / 3 A, Tc 75 °C, 5 s')
ax.plot([80],[2.16],'s',color=BL,ms=8,mfc='white',mew=2,label='Same point derated to Tc 96 °C (2.16 A)')
ax.plot([60],[5],'x',color=RD,ms=12,mew=3,label='Fault: 5 A at 60 V = 300 W (until ALERT)')
ax.plot([60],[1.25],'o',color=OR,ms=8)
ax.annotate('60 V · 1.25 A · 75 W',(60,1.25),xytext=(16,0.42),fontsize=11,color=NV,arrowprops=dict(arrowstyle='-',color=GR))
ax.axvline(100,color=GR,lw=1,ls=':'); ax.text(88,30,'VDSS',rotation=90,color=GR,fontsize=10)
ax.set_xlim(1,110); ax.set_ylim(0.1,80); ax.set_xlabel('VDS  [V]'); ax.set_ylabel('ID  [A]')
ax.set_xticks([1,2,5,10,20,50,100]); ax.set_xticklabels(['1','2','5','10','20','50','100'])
ax.set_yticks([0.1,0.2,0.5,1,2,5,10,20,50]); ax.set_yticklabels(['0.1','0.2','0.5','1','2','5','10','20','50'])
ax.legend(fontsize=9.2,loc='lower left',frameon=False)
fig.tight_layout(); fig.savefig('soa.png'); plt.close()
# ---------------- Bode loop gain
fig,(a1,a2)=plt.subplots(2,1,figsize=(7.4,5.0),sharex=True,gridspec_kw={'height_ratios':[1.2,1]})
cols={0.1:'#f2b48f',1.25:OR,5:'#8c3a12'}
for C6,ls,lab in [(10e-9,'--','C6 = 10 nF'),(1e-9,'-','C6 = 1 nF')]:
    for I in (0.1,1.25,5):
        L,_,_=resp(I,C6=C6); ph=np.unwrap(np.angle(L))*180/np.pi
        a1.semilogx(f,20*np.log10(np.abs(L)),ls=ls,color=cols[I],lw=1.8,label=f'{lab}, {I} A' if True else None)
        a2.semilogx(f,ph,ls=ls,color=cols[I],lw=1.8)
a1.axhline(0,color=NV,lw=1); a1.set_ylim(-60,140); a1.set_ylabel('|T|  [dB]')
a2.axhline(-180,color=RD,lw=1); a2.set_ylim(-200,0); a2.set_ylabel('Phase T  [deg]'); a2.set_xlabel('Frequency  [Hz]')
a2.set_yticks([-180,-135,-90,-45,0]); a1.set_xlim(1,1e8)
a1.legend(fontsize=8.6,ncol=2,frameon=False,loc='upper right')
fig.tight_layout(); fig.savefig('bode.png'); plt.close()
# ---------------- closed loop I/VDAC
fig,ax=plt.subplots(figsize=(6.4,3.6))
fl=np.logspace(1,7,2000)
for C6,C5,ls,lab in [(10e-9,100e-9,'--','rev 0.1: C6 10 nF, C5 100 nF'),(1e-9,10e-9,'-','rev 0.2: C6 1 nF, C5 10 nF')]:
    for I in (0.1,1.25,5):
        H=closed(I,C5=C5,C6=C6); _,h=sg.freqresp(H,w=2*np.pi*fl)
        ax.semilogx(fl,20*np.log10(np.abs(h)/2.0),ls=ls,color=cols[I],lw=1.8,label=(lab if I==1.25 else None))
ax.axhline(-3,color=GR,lw=1,ls=':'); ax.set_ylim(-40,5); ax.set_xlim(10,1e6)
ax.set_xlabel('Frequency  [Hz]'); ax.set_ylabel('I / I_set  [dB]'); ax.legend(fontsize=9.5,frameon=False,loc='lower left')
fig.tight_layout(); fig.savefig('closed.png'); plt.close()
# ---------------- time domain
res=pickle.load(open('tsim.pkl','rb'))
fig,axs=plt.subplots(1,3,figsize=(11.6,3.4),sharey=False)
titles={(0,1.0):'0 → 1 A (from clamp)',(0.01,1.0):'10 mA → 1 A (keep-alive)',(1.0,1.2):'1.0 → 1.2 A (small step)'}
for a,key in zip(axs,[(0,1.0),(0.01,1.0),(1.0,1.2)]):
    for lab,c,ls in [('attuale',GR,'--'),('proposto',OR,'-')]:
        o=res[(lab,)+key]; a.plot((o[:,0]-20e-6)*1e6,o[:,1],color=c,ls=ls,lw=2,label={'attuale':'rev 0.1 (C6 10 nF)','proposto':'rev 0.2 (C6 1 nF)'}[lab])
    a.set_title(titles[key],fontsize=12,color=NV); a.set_xlabel('t  [µs]'); a.set_xlim(-20,980)
axs[0].set_ylabel('I_D  [A]'); axs[0].legend(fontsize=9,frameon=False,loc='lower right')
axs[2].set_ylim(0.95,1.25)
fig.tight_layout(); fig.savefig('step.png'); plt.close()
print('ok')
