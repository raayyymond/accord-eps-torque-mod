import os, sys, numpy as np
from scipy import signal
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import dflib as D
import v282cmp as C
print("logged lateralDelay and the setpoint's lead over the model reference, per route")
print(f"{'route':24s} {'grp':8s} {'ld_delay s':>11s} {'sR med':>7s} | setpoint lead (s), xcorr 0.05-0.5 Hz")
sos=signal.butter(4,[0.05,0.5],btype='band',fs=100.,output='sos')
for rk,meta in C.ROUTES.items():
    S=C.load(rk); m=C.usable(S,5.0)
    ld=np.nan_to_num(S["lat_delay"])[m]
    num={}
    for a,b in C.runs(m,S["t"],min_s=30.0):
        x=signal.sosfiltfilt(sos,np.nan_to_num(S["model"][a:b]))
        y=signal.sosfiltfilt(sos,np.nan_to_num(S["setpoint"][a:b]))
        for L in range(-40,41):
            xa,ya=(x[:len(x)-L],y[L:]) if L>=0 else (x[-L:],y[:len(y)+L])
            num[L]=num.get(L,0.0)+float(np.dot(xa,ya))/np.sqrt(float(np.dot(xa,xa)*np.dot(ya,ya))+1e-12)
    bl=sorted(num)[int(np.argmax(np.array([num[L] for L in sorted(num)])))] if num else 0
    print(f"{rk:24s} {meta['group']:8s} {np.median(ld):11.4f} {np.median(np.nan_to_num(S['sR'])[m]):7.3f} | "
          f"{-bl/100.0:+.3f} s  (negative = setpoint LEADS the model)")
    del S
