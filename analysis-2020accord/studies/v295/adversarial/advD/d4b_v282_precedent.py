"""ADV-D step 4b: the FLOWN precedent for large lane torque at low speed with the driver's hands on.  V282 flew with a
lane whose zero-command capability was the full rail; what did its 427 tap actually deliver at 0-5 m/s, engaged, and how
long did it dwell above the levels the V295 replay reaches (|T| 946 / 1277 in its long |trim| > 300 runs)?
Same statistic on the V295 open-loop replay of r71b (lane total, tap sign, 50 Hz-equivalent by taking the 1 kHz series).
Routes: V282 r36 r37 r38 r39 r3a r3c r6c (the kit's v280 cache, loaded by creep20_loop_id.load; the tap unit is T counts)."""
import os, sys, contextlib, io
import numpy as np
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, KIT + "/rlog-tools/studies/grind")
with contextlib.redirect_stdout(io.StringIO()):
    import creep20_loop_id as C20

def runs(mask):
    dd = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)))

TAGS = ("r36", "r37", "r38", "r39", "r3a", "r3c", "r6c")
tot = {}
print("V282 flown routes: lane torque (427 tap, 50 Hz) on ENGAGED frames at 0-5 m/s")
print("%-5s %7s %8s %8s | %s" % ("route", "eng s", "|T|max", "p99.9", "runs of |T| >= 946 / >= 1277 / >= 2000 : count, longest ms  (and with |bar|>=400)"))
for tag in TAGS:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            g = C20.load(tag)
    except Exception as e:
        print(tag, "load failed", e); continue
    tt = g["T_t"]; T = g["T"]
    eng = np.interp(tt, g["t"], g["eng"].astype(float)) > 0.5
    v = np.interp(tt, g["t"], g["vego"])
    bar = np.interp(tt, g["t"], g["bar"])
    lo = eng & (v < 5)
    if lo.sum() < 10:
        print(tag, "no low-speed engaged frames"); continue
    row = []
    for thr in (946, 1277, 2000):
        rr = runs(lo & (np.abs(T) >= thr))
        L = [(tt[b - 1] - tt[a]) * 1000 + 20 for a, b in rr]
        rr2 = runs(lo & (np.abs(T) >= thr) & (np.abs(bar) >= 400))
        L2 = [(tt[b - 1] - tt[a]) * 1000 + 20 for a, b in rr2]
        row.append("%3d, %4.0f (%3d, %4.0f)" % (len(L), max(L) if L else 0, len(L2), max(L2) if L2 else 0))
        tot.setdefault(thr, []).extend(L)
    print("%-5s %7.0f %8.0f %8.0f | %s" % (tag, lo.sum() / 50, np.abs(T[lo]).max(), np.percentile(np.abs(T[lo]), 99.9), " / ".join(row)))
print("\nPOOLED V282: runs >= 946: %d (longest %.0f ms, >= 75 ms: %d); >= 1277: %d (longest %.0f ms, >= 75 ms: %d); >= 2000: %d (longest %.0f)" % (
    len(tot[946]), max(tot[946]), sum(x >= 75 for x in tot[946]), len(tot[1277]), max(tot[1277]), sum(x >= 75 for x in tot[1277]),
    len(tot[2000]), max(tot[2000]) if tot[2000] else 0))

# the same statistic on the V295 / V294 open-loop replays of r71b (d4's cache), lane TOTAL in the tap sign, engaged, 0-5 m/s
V295D = KIT + "/analysis-2020accord/studies/v295"
for p in (V295D + "/plant", V295D + "/lib"):
    sys.path.insert(0, p)
import plib as P
d = P.load()
z = np.load(r"C:/Users/dudei/AppData/Local/Temp/claude/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/aa635277-343b-4774-be4a-fa2982d3b91e/scratchpad/_d4_march.npz")
k1 = np.arange(len(z["T4"])) // 10
eng = d["eng"][k1].astype(bool); v = d["v"][k1]; bar = d["bar"][k1]
for nm, key in (("V294 replay", "T4"), ("V295 replay", "T5")):
    Tl = d["sg"] * z[key]
    lo = eng & (v < 5)
    row = []
    for thr in (946, 1277, 2000):
        rr = runs(lo & (np.abs(Tl) >= thr))
        L = [b - a for a, b in rr]
        row.append("%3d, %4d" % (len(L), max(L) if L else 0))
    print("%-12s engaged 0-5 m/s %.0f s, |T| max %d | runs >= 946 / 1277 / 2000: %s" % (nm, lo.sum() / 1000, np.abs(Tl[lo]).max(), " / ".join(row)))
