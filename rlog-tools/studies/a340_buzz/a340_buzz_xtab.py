"""Cross-tabs + as-sampled frequency tracking + cmd encoding check, from <cache>/_features.npz (built by census2) and raw cache.
usage: <cache dir>"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs

C = sys.argv[1]
A = dict(np.load(os.path.join(C, "_features.npz")))
mov = A["v"] > 2
aang = np.abs(A["ang"]); r = A["rlp"]; ttq = np.abs(A["tlp"]); eng = A["eng"]
still = np.abs(r) < 2
print("== MANUAL, wheel still |rlp|<2, moving: %% time BZ>4 (seconds) by |angle| x grip")
GR = [(0, 80), (80, 300), (300, 800), (800, 1e9)]
AN = [(0, 3), (3, 10), (10, 30), (30, 999)]
print("   |ang|\\|tq|  " + "  ".join("%9s" % ("%d-%s" % (g[0], int(g[1]) if g[1] < 1e8 else "")) for g in GR))
for a0, a1 in AN:
    cells = []
    for g0, g1 in GR:
        m = mov & ~eng & still & (aang >= a0) & (aang < a1) & (ttq >= g0) & (ttq < g1)
        cells.append("%4.0f%%(%4.0fs)" % (100 * (A["bz"][m] > 4).mean() if m.sum() else np.nan, m.sum() / 100))
    print("   %3d-%-3d     " % (a0, a1) + " ".join(cells))
print("== ENGAGED, still: same table")
for a0, a1 in AN:
    cells = []
    for g0, g1 in GR:
        m = mov & eng & still & (aang >= a0) & (aang < a1) & (ttq >= g0) & (ttq < g1)
        cells.append("%4.0f%%(%4.0fs)" % (100 * (A["bz"][m] > 4).mean() if m.sum() else np.nan, m.sum() / 100))
    print("   %3d-%-3d     " % (a0, a1) + " ".join(cells))
print("== MANUAL still |a|<10 by speed:")
for lo, hi in ((2, 5), (5, 8), (8, 12), (12, 16), (16, 25), (25, 50)):
    m = mov & ~eng & still & (aang < 10) & (A["v"] >= lo) & (A["v"] < hi)
    if m.sum() > 50:
        print("   v %2d-%2d  %5.1f s  BZ>4 %4.0f%%  BZ p50 %.1f" % (lo, hi, m.sum() / 100, 100 * (A["bz"][m] > 4).mean(), np.median(A["bz"][m])))

# as-sampled frequency (zero-crossing period of hr) per 0.64 s window in buzz
rows = []
for seg, p in segs(C):
    d = load(p)
    W = 64
    for i in range(0, len(d["t"]) - W, W):
        s = slice(i, i + W)
        if d["bz"][s].mean() < 5 or d["v"][s].mean() < 2:
            continue
        hr = d["hr"][s]
        zc = np.flatnonzero(np.diff(np.sign(hr)) != 0)
        if len(zc) < 4:
            continue
        f = 100 / (2 * np.mean(np.diff(zc)))
        rows.append((f, d["v"][s].mean(), np.abs(d["ang"][s]).mean(), np.abs(d["tlp"][s]).mean(), d["req"][s].mean(),
                     np.nanmean(np.abs(d["cmd"][s])) if d["has_e4"] else np.nan, np.abs(d["rlp"][s]).mean(), d["bz"][s].mean()))
R = np.array(rows)
print("== as-sampled buzz frequency (zero-crossing), windows with BZ>5: n=%d, f p10/p50/p90 %s" % (len(R), np.round(np.percentile(R[:, 0], [10, 50, 90]), 1)))
names = ["v", "|ang|", "|tq|", "engaged", "|cmd|", "|rate lp|", "BZ"]
for k, nm in enumerate(names, start=1):
    x = R[:, k]
    ok = np.isfinite(x)
    print("   corr(f, %-9s) = %+.2f   (Spearman %+.2f)" % (nm, np.corrcoef(R[ok, 0], x[ok])[0, 1],
          np.corrcoef(np.argsort(np.argsort(R[ok, 0])), np.argsort(np.argsort(x[ok])))[0, 1]))
for lab, m in (("eng |ang|<5", (R[:, 4] > 0.5) & (R[:, 2] < 5)), ("eng |ang|>20", (R[:, 4] > 0.5) & (R[:, 2] > 20)),
               ("man |ang|<5", (R[:, 4] < 0.5) & (R[:, 2] < 5)), ("man |ang|>20", (R[:, 4] < 0.5) & (R[:, 2] > 20)),
               ("any |rate lp|>30", R[:, 6] > 30)):
    if m.sum():
        print("   %-18s n=%4d f p25/p50/p75 %s  BZ p50 %.1f" % (lab, m.sum(), np.round(np.percentile(R[m, 0], [25, 50, 75]), 1), np.median(R[m, 7])))
for lo, hi in ((2, 8), (8, 12), (12, 16), (16, 22), (22, 40)):
    m = (R[:, 1] >= lo) & (R[:, 1] < hi) & (R[:, 2] < 5)
    if m.sum():
        print("   |ang|<5, v %2d-%2d n=%4d f p50 %.1f" % (lo, hi, m.sum(), np.median(R[m, 0])))

# cmd encoding check (engaged)
cs = []
for seg, p in segs(C):
    d = load(p)
    if not d["has_e4"]:
        break
    m = d["req"]
    if m.sum() > 100:
        cs.append(np.c_[d["cmd"][m], d["ang"][m]])
if cs:
    X = np.vstack(cs)
    print("== engaged 0xE4 cmd vs wheel angle: slope %.2f, intercept %.1f, corr %.3f (n=%d)" % (*np.polyfit(X[:, 1], X[:, 0], 1), np.corrcoef(X[:, 0], X[:, 1])[0, 1], len(X)))
