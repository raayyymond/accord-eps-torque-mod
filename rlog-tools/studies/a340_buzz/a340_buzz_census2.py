"""Per-sample buzz census by condition. usage: a340_buzz_census2.py <cache dir> [label]
BZ = 0.32 s rms of >10 Hz wheel rate (deg/s). Cells report seconds, BZ p50/p90, and % of time BZ > 4 deg/s."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs

C = sys.argv[1]
TH = 4.0
cols = {k: [] for k in ("seg", "t", "bz", "bzt", "eng", "v", "ang", "rlp", "tlp", "pressed", "cmd")}
for seg, p in segs(C):
    d = load(p)
    cols["seg"].append(np.full(len(d["t"]), seg)); cols["t"].append(d["t"])
    for k in ("bz", "bzt", "v", "ang", "rlp", "tlp", "pressed", "cmd"):
        cols[k].append(d[k])
    cols["eng"].append(d["req"])
A = {k: np.concatenate(v) for k, v in cols.items()}
np.savez(os.path.join(C, "_features.npz"), **A)
mov = A["v"] > 2
aang = np.abs(A["ang"]); r = A["rlp"]; ttq = np.abs(A["tlp"])
toC = (A["ang"] * r < 0) & (np.abs(r) > 5)
away = (A["ang"] * r > 0) & (np.abs(r) > 5)
still = np.abs(r) < 2
eng = A["eng"]
print("== %s  total %.0f s, moving %.0f s, engaged-moving %.0f s, buzz(BZ>%g) moving: %.1f%%" % (
    C, len(A["t"]) / 100, mov.sum() / 100, (mov & eng).sum() / 100, TH, 100 * (A["bz"][mov] > TH).mean()))


def row(name, m, base=mov):
    m = m & base
    n = m.sum()
    if n < 50:
        print("  %-46s %7.1f s  (too few)" % (name, n / 100)); return
    b = A["bz"][m]
    print("  %-46s %7.1f s  BZ p50 %5.1f p90 %5.1f  >%g: %5.1f%%   tqHF p50 %5.0f" % (
        name, n / 100, np.median(b), np.percentile(b, 90), TH, 100 * (b > TH).mean(), np.median(A["bzt"][m])))


GR = [("hands-off |tq|<80", ttq < 80), ("light 80-300", (ttq >= 80) & (ttq < 300)),
      ("medium 300-800", (ttq >= 300) & (ttq < 800)), ("firm >=800", ttq >= 800)]
DIRS = [("still |r|<2", still), ("slow 2-5", (~still) & (np.abs(r) <= 5)), ("toCentre", toC), ("away", away)]
ANG = [("|a|<10", aang < 10), ("10-30", (aang >= 10) & (aang < 30)), ("30-60", (aang >= 30) & (aang < 60)), (">60", aang >= 60)]
for en, lab in ((False, "MANUAL"), (True, "ENGAGED")):
    e = eng == en
    print("\n-- %s : grip x direction (moving > 2 m/s)" % lab)
    for gn, g in GR:
        for dn, dm in DIRS:
            row("%s | %s" % (gn, dn), e & g & dm)
    print("-- %s : |angle| x direction" % lab)
    for an, am in ANG:
        for dn, dm in DIRS:
            row("%s | %s" % (an, dn), e & am & dm)
    print("-- %s : steeringPressed" % lab)
    row("pressed", e & (A["pressed"]))
    row("not pressed", e & (~A["pressed"]))
    print("-- %s : vehicle speed" % lab)
    for lo, hi in ((0, 0.5), (0.5, 2), (2, 8), (8, 16), (16, 25), (25, 50)):
        row("v %g-%g m/s" % (lo, hi), e & (A["v"] >= lo) & (A["v"] < hi), base=np.ones_like(mov))
    if en and np.isfinite(A["cmd"]).all():
        print("-- ENGAGED : |cmd| (0xE4 s16)")
        ac = np.abs(A["cmd"])
        for lo, hi in ((0, 50), (50, 200), (200, 600), (600, 1500), (1500, 99999)):
            row("|cmd| %g-%g" % (lo, hi), e & (ac >= lo) & (ac < hi))
