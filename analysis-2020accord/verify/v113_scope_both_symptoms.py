import numpy as np
RATE=4.7121
def term(rate_dps,knee,K1,model=1.0):
    ct=rate_dps*RATE
    return model*(K1/1024.0)*min(ct*12.0/knee,1.0)
print("DOES V113's K1 CUT HELP BOTH SYMPTOMS?  friction = |model| * K1/1024 * sat(rate*12/knee)\n")
print("  Relay DUTY is set by the KNEE (unchanged 1800 in both) -- so V113 fires as often as V112.")
print("  Relay MAGNITUDE is set by K1 -- V113 is 204/612 = 0.333x of V112's.\n")
print("   rate     V112 (K1 612)   V113 (K1 204)   ratio   | saturated?")
for d in (3,10,20,31.8,40,60,100):
    a=term(d,1800,612); b=term(d,1800,204)
    sat = "SATURATED" if d*RATE*12/1800>=1.0 else ""
    print("   %5.1f d/s    %8.5f       %8.5f     %.3f   | %s"%(d,a,b,b/a,sat))
print("\n  => at EVERY rate the term is 0.333x.  Both the linear region and the saturated")
print("     plateau scale with K1, so V113 cuts:")
print("       * the ANTI-DAMPING (in phase with rate)      -> the 7.42 Hz oscillation")
print("       * the RELAY KICK magnitude at saturation     -> grind #1")
print("     ...with the relay CORNER (31.8 deg/s) untouched, so V112's authority win is kept.")
print("\n  SCALED AGAINST STOCK (K1 102):")
for nm,K1 in (('stock',102),('V111',204),('V112',612),('V113',204)):
    print("     %-6s K1 %3d  = %.1fx stock   plateau term %.5f"%(nm,K1,K1/102,term(100,1800 if nm in('V112','V113') else 600,K1)))
print("\n  ANGLE LEVERAGE: |model| rises 7-9x from <5 deg to >60 deg (measured, b5 rung),")
print("  and the term is LINEAR in |model|, so the absolute cut is 7-9x bigger at large angle")
print("  -- i.e. the fix is self-targeting to the regime where the symptom lives.")
