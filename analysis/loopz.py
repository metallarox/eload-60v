import sympy as sp, pickle
s=sp.symbols('s')
Vo,Vg,Vs,Vn,Vint=sp.symbols('Vo Vg Vs Vn Vint')
Ro,Rgt,R16,Rs,R14,C6,Cgs,Cgd,gm,Rz=sp.symbols('Ro Rgt R16 Rs R14 C6 Cgs Cgd gm Rz',positive=True)
Y6=1/(Rz+1/(s*C6))
eqs=[ (Vo-Vint)/Ro+(Vo-Vg)/Rgt+(Vo-Vn)*Y6,
      (Vg-Vo)/Rgt+Vg/R16+(Vg-Vs)*s*Cgs+Vg*s*Cgd,
      -gm*(Vg-Vs)-(Vg-Vs)*s*Cgs+Vs/Rs+(Vs-Vn)/R14,
      (Vn-Vs)/R14+(Vn-Vo)*Y6 ]
sol=sp.solve(eqs,[Vo,Vg,Vs,Vn],dict=True)[0]
pickle.dump((sp.simplify(sol[Vn]/Vint),sp.simplify(sol[Vs]/Vint)),open('h.pkl','wb'))
