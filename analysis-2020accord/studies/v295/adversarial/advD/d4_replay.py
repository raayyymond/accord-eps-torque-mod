"""ADV-D step 4: byte-exact OPEN-LOOP replay of r71b (V294's own command and 1 kHz wheel rate) through the V294 lane and
the V295 lane (b read from the V295 IMAGE), for the interlock-exposure questions:
  - soft-EME dwell: ENGAGED runs of |trim| > 300 T (trim = T_live - T_null in the tap sign), longest run vs the 75 ms SM2
    residency, by speed; total |T| peak;
  - fb clamp C binding, P clamp binding;
  - driver-override exposure: |trim| on steeringPressed / |bar| >= 400 engaged frames, and whether it opposes the bar.
The replay is open loop (x is V294's recorded motion); a real V295 drive would move the wheel differently.  Used for
EXPOSURE bounds only (as the design adversaries did)."""
import os, sys, struct, hashlib, time
import numpy as np
V295D = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295"
for p in (V295D + "/plant", V295D + "/lib"):
    sys.path.insert(0, p)
import plib as P
import r71b_cache as RC
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
B5 = open(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
assert hashlib.sha256(B5).hexdigest().startswith("5c044d65")
b_img = struct.unpack_from("<H", B5, 0xC63EA)[0]
a_img = struct.unpack_from("<h", B5, 0xC63E8)[0]
C_img = struct.unpack_from("<H", B5, 0xC62E6)[0]
print("from V295 image: b %d a %d C %d" % (b_img, a_img, C_img))
d = P.load()
c = RC.v294_cells()
assert int(c["fb_a"]) == a_img and int(c["fb_clamp"]) == C_img and int(c["fb_b"]) == 567
sg = d["sg"]
cache = r"C:/Users/dudei/AppData/Local/Temp/claude/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/aa635277-343b-4774-be4a-fa2982d3b91e/scratchpad/_d4_march.npz"
if os.path.exists(cache):
    z = np.load(cache); T4, T5, R4, R5, P4, P5 = (z[k] for k in ("T4", "T5", "R4", "R5", "P4", "P5"))
else:
    t0 = time.time()
    T4, R4, P4, _, _ = P.march(d["sgn"], d["idx"], d["m"], c, x1k=d["x1k"], trim=True, want=True)
    T5, R5, P5, _, _ = P.march(d["sgn"], d["idx"], d["m"], c, x1k=d["x1k"], trim=True, fb_b=b_img, want=True)
    np.savez(cache, T4=T4, T5=T5, R4=R4, R5=R5, P4=P4, P5=P5)
    print("marched 2 x %d ticks in %.0f s" % (len(T4), time.time() - t0))
mm = int(np.sum(sg * T4 != d["T1k_live"]))
print("POSITIVE CONTROL: V294 re-march vs cached T1k_live: %d mismatching ticks (must be 0)" % mm)
assert mm == 0
Tn = d["T1k_null"]
k1 = np.arange(len(T4)) // 10
eng = d["eng"][k1].astype(bool)
v = d["v"][k1]
bar = d["bar"][k1]
pressed = d["pressed"][k1]
print("engaged ticks %d (%.0f s)" % (eng.sum(), eng.sum() / 1000))

def runs(mask):
    dd = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)))

for nm, T, R, PP in (("V294", T4, R4, P4), ("V295", T5, R5, P5)):
    Tl = sg * T
    trim = Tl - Tn
    hi = (np.abs(trim) > 300) & eng
    rr = runs(hi)
    L = np.array([b - a for a, b in rr]) if rr else np.zeros(0, int)
    print("\n== %s ==" % nm)
    print("  engaged |T| max %d (|T_null| max %d); engaged |trim| max %d, p99.9 %.0f, rms %.1f" % (
        np.abs(Tl[eng]).max(), np.abs(Tn[eng]).max(), np.abs(trim[eng]).max(), np.percentile(np.abs(trim[eng]), 99.9),
        np.sqrt(np.mean(trim[eng] ** 2))))
    print("  |trim| > 300 T engaged: %d ticks, %d runs, longest %d ms" % (hi.sum(), len(rr), L.max() if len(L) else 0))
    for a_, b_ in sorted(rr, key=lambda t: -(t[1] - t[0]))[:10]:
        print("     run %4d ms at t=%.2f s  v %.1f m/s  |bar| max %d  pressed %.2f  |T| max %d  trim max %d" % (
            b_ - a_, a_ / 1000, v[a_], np.abs(bar[a_:b_]).max(), pressed[a_:b_].mean(), np.abs(Tl[a_:b_]).max(),
            np.abs(trim[a_:b_]).max()))
    for lo, hi_ in ((0, 5), (5, 10), (10, 99)):
        msk = hi & (v >= lo) & (v < hi_)
        r2 = runs(msk)
        L2 = [b - a for a, b in r2]
        print("  speed %2d-%2d m/s: ticks %d, runs %d, longest %d ms, runs >= 75 ms: %d" % (
            lo, hi_, msk.sum(), len(r2), max(L2) if L2 else 0, sum(1 for x in L2 if x >= 75)))
    print("  fb clamp |r26| == C on engaged ticks: %.4f %%;  P clamp |P| == 15360: %.4f %%" % (
        100 * np.mean(np.abs(R[eng]) >= C_img), 100 * np.mean(np.abs(PP[eng]) >= 15360)))
    ho = eng & ((np.abs(bar) >= 400) | pressed)
    # opposing the driver: trim sign vs bar sign (tap + = steer RIGHT; bar is sign RAW = -steeringTorque*1.024 -> BELIEF on
    # the sign chain, so report both the magnitude and the sign agreement)
    agree = np.mean(np.sign(trim[ho & (np.abs(trim) > 50)]) == np.sign(bar[ho & (np.abs(trim) > 50)]))
    print("  hands-on engaged ticks %d: |trim| p50 %.0f p95 %.0f p99 %.0f max %d; sign(trim)==sign(bar) on |trim|>50: %.2f" % (
        ho.sum(), np.percentile(np.abs(trim[ho]), 50), np.percentile(np.abs(trim[ho]), 95), np.percentile(np.abs(trim[ho]), 99),
        np.abs(trim[ho]).max(), agree))
d5 = sg * T5 - Tn; d4 = sg * T4 - Tn
print("\nV295 - V294 torque on engaged ticks: rms %.1f, p99 %.0f, max %d" % (
    np.sqrt(np.mean((d5 - d4)[eng] ** 2)), np.percentile(np.abs(d5 - d4)[eng], 99), np.abs(d5 - d4)[eng].max()))
print("ratio of |trim| rms V295/V294 (engaged): %.3f" % (np.sqrt(np.mean(d5[eng] ** 2)) / np.sqrt(np.mean(d4[eng] ** 2))))
print("max |x| on the route %d (bail 12000); max |bar| %d (bar bail |gp-0x4f60| > 25600 raw = %d wire)" % (
    np.abs(d["x1k"]).max(), np.abs(d["bar"]).max(), int(25600 * 1.024)))
