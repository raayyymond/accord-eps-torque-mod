import numpy as np
fs=1000.
def F(f,a2,d=1,a1=37/128):
    z=np.exp(1j*2*np.pi*f/fs)
    return a1/(1-(1-a1)/z)*a2/(1-(1-a2)/z)*z**(-d)
print("f  | anti-damping coefficient  w*|F|*sin(lag) (arb), alpha2=22 vs 14 (d=1)  ratio14/22")
for f in (2,5,10,20,30,50,80):
    w=2*np.pi*f
    r=[]
    for a2n in (22,14):
        Fv=F(f,a2n/64); r.append(w*abs(Fv)*np.sin(-np.angle(Fv)))
    print(f,f"{r[0]:.1f} {r[1]:.1f} {r[1]/r[0]:.2f}")
# effective stock vs x3 gain at 22 and x3 with 14: anti-damp scales with Y
