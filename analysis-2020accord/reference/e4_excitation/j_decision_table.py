import numpy as np
STEER_MAX=4096.0; DELTA=3.0     # normalised per second (STEER_DELTA_UP * DT_CTRL per 10 ms step)
SLEW=DELTA*STEER_MAX            # counts/s
print("SLEW CEILING = %.0f counts/s  (STEER_DELTA_UP=3 normalised/s x STEER_MAX=4096)"%SLEW)
print("  max sine amplitude:  8 Hz %.1f ct | 7.5 Hz %.1f | 21 Hz %.1f  (2*pi*f*A <= slew)"%(
    SLEW/(2*np.pi*8),SLEW/(2*np.pi*7.5),SLEW/(2*np.pi*21)))
print("  (the OLD assumption, 300 ct/s, would have given 5.97 ct at 8 Hz)\n")

# measured 6-9 Hz backgrounds, engaged HANDS-OFF, 3 Hz wide -> one-sided PSD
BG = {"gp-0x6b98 r73 (signed)":70.8, "gp-0x6b98 r75":63.4, "gp-0x6b98 r76":49.2,
      "kit-record 29.0 ct":29.0,
      "torsion bar r73":118.4, "torsion bar r75":57.6, "torsion bar r76":43.9}
GAIN = {"gp-0x6b98":[0.5,1.0], "torsion bar":[0.20,0.26]}
print("REQUIRED 0xE4 SINE AMPLITUDE AT 8 Hz FOR gamma^2 >= 0.5   (A = sqrt(2*Pn*df)/G, Hann ENBW df=1.5/T)")
print("%-26s %8s | %s"%("background (6-9 Hz rms)","PSD","required A [ct] at T = 5.12 / 15 / 30 s"))
for nm,rmsv in BG.items():
    Pn=rmsv**2/3.0
    ch = "torsion bar" if "bar" in nm else "gp-0x6b98"
    row=[]
    for G in GAIN[ch]:
        row.append("  G=%.2f: "%G + " / ".join("%6.1f"%(np.sqrt(2*Pn*1.5/T)/G) for T in (5.12,15.,30.)))
    print("%-26s %8.0f |%s"%(nm,Pn,"   ".join(row)))

print("\nACHIEVABLE gamma^2 AT A CHOSEN AMPLITUDE (T = 15 s single-frequency dwell)")
for A in (244.5, 100.0, 81.0, 40.0, 5.97):
    out=[]
    for nm,rmsv in [("gp-0x6b98 r73",70.8),("bar r73",118.4),("bar r76",43.9)]:
        Pn=rmsv**2/3.0; G=0.5 if "6b98" in nm else 0.20
        S=(G*A)**2/2; N=Pn*1.5/15.
        out.append("%s g2=%.3f"%(nm,S/(S+N)))
    print("  A=%6.1f ct (%.1f%% of the slew budget at 8 Hz): "%(A,100*A/(SLEW/(2*np.pi*8)))+" | ".join(out))
