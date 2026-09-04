# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_lagpole.py -- price the output-lag pole 0xC63EC/0xC63EE (OA 992 / OB 507,
corner 5.05 Hz) against the 7 Hz ring and the 20 Hz creep grind, using the MEASURED loop shares from
stutter_v283_memoryless.py M2.  DC gain is held at 0.9902 at every candidate.  Subagent stutter283, 2026-09-03."""
import os, sys
import numpy as np
H=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,H)
import r24_deembed as RD
def Hlag(f,OA,OB):
    z=np.exp(-2j*np.pi*f/1000.0)
    return (OB/1024.0)/(1-(OA/1024.0)*z)*(1+z)/32.0
def dc(OA,OB): return abs(Hlag(1e-9,OA,OB))
print("corner of a pole a=OA/1024 at 1 kHz:  f = -ln(a)*1000/(2pi)")
for OA in (992,972,952,932,912,880):
    a=OA/1024.0; fc=-np.log(a)*1000/(2*np.pi)
    OB=round(0.99023*1024*(1-a)/0.0625/2*2)  # solve DC = (OB/1024)/(1-a)*2/32 = 0.99023
    OB=int(round(0.99023*32*1024*(1-a)/2))
    print("  OA %4d -> pole corner %5.2f Hz ; OB for DC held at 0.9902 = %5d ; check DC %.4f"%(OA,fc,OB,dc(OA,OB)))
print()
# pooled measured shares (stutter_v283_memoryless M2)
Ls=0.55*np.exp(1j*np.radians(96.0)); Lr=1.0-Ls
print("pooled Ls %.2f@%+.0f  Lr %.2f@%+.0f  |Ls+Lr| %.3f"%(abs(Ls),np.degrees(np.angle(Ls)),abs(Lr),np.degrees(np.angle(Lr)),abs(Ls+Lr)))
print()
print("  OA   corner    7 Hz: |Hnew/Hold| dphase | ratio(ring)   ||   20 Hz: |Hnew/Hold| dphase | servo-arm gain")
for OA in (992,952,932,912,880):
    a=OA/1024.0; fc=-np.log(a)*1000/(2*np.pi)
    OB=int(round(0.99023*32*1024*(1-a)/2))
    r7=Hlag(7.3,OA,OB)/Hlag(7.3,992,507)
    r20=Hlag(20.3,OA,OB)/Hlag(20.3,992,507)
    tot=abs(Ls*r7+Lr)
    print("  %4d %6.2f Hz   %6.3f  %+6.1f deg | %6.3f  (%+5.1f%%)  ||  %6.3f  %+6.1f deg | x%.2f"%(
        OA,fc,abs(r7),np.degrees(np.angle(r7)),tot,100*(tot-1),abs(r20),np.degrees(np.angle(r20)),abs(r20)))
print()
print("sensitivity of the 7 Hz ring ratio to the assumed Ls (the one measured quantity that matters):")
for m,ph in ((0.42,95),(0.55,96),(0.69,85),(0.55,60),(0.55,120)):
    L=m*np.exp(1j*np.radians(ph)); R=1.0-L
    OA,OB=932,int(round(0.99023*32*1024*(1-932/1024.0)/2))
    r7=Hlag(7.3,OA,OB)/Hlag(7.3,992,507)
    print("   Ls %.2f@%+3.0f -> ring ratio at the 15 Hz pole %.3f (%+.0f%%)"%(m,ph,abs(L*r7+R),100*(abs(L*r7+R)-1)))
