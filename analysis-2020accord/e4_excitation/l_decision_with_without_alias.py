import numpy as np
SLEW=3.0*4096.0
A8=SLEW/(2*np.pi*8)
print("slew ceiling %.0f ct/s -> max 8 Hz sine amplitude %.1f ct\n"%(SLEW,A8))
# 427-observed 6-9 Hz backgrounds on gp-0x6b98 (engaged hands-off), ct rms over 3 Hz
BG={"r73 (signed)":70.8,"r75":63.4,"r76":49.2,"kit-record 29.0":29.0}
# fold ratios R measured on the unaliased 0x18F channel; plus a hard worst case R=1.0
RS=[("measured R (0.003-0.020)",0.020),("stress test R = 1.0",1.0)]
GS=[0.5,0.72,1.07]   # forward gain bracket at 8 Hz (skew sweep 0.72-1.07; 0.5 = 1 kHz IIR model)
print("REQUIRED 0xE4 AMPLITUDE AT 8 Hz for gamma^2>=0.5, T=15 s dwell (Hann ENBW df=0.10 Hz)")
print("%-18s %10s | %-28s | %s"%("background","PSD obs","AS MEASURED (fold included)","FOLD REMOVED"))
for nm,r in BG.items():
    Pobs=r*r/3.0
    row=[]
    for lab,R in RS:
        Ptrue=Pobs/(1.0+R)
        row.append((lab,Ptrue))
    s1=" / ".join("%5.1f"%(np.sqrt(2*Pobs*0.10)/g) for g in GS)
    s2=" / ".join("%5.1f"%(np.sqrt(2*row[0][1]*0.10)/g) for g in GS)
    s3=" / ".join("%5.1f"%(np.sqrt(2*row[1][1]*0.10)/g) for g in GS)
    print("%-18s %10.0f | %-28s | R=0.02: %s   R=1.0: %s"%(nm,Pobs,s1,s2,s3))
print("\n  (each cell is G = 0.50 / 0.72 / 1.07 ct/ct, the forward-gain bracket)")
print("  ceiling at 8 Hz = %.1f ct.  Worst cell above = %.1f ct  ->  margin %.1fx"%(
    A8, np.sqrt(2*(70.8**2/3.0)*0.10)/0.5, A8/(np.sqrt(2*(70.8**2/3.0)*0.10)/0.5)))
