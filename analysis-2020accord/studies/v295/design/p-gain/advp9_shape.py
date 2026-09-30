"""ADV-bytes (p-gain) step 9: the TAPER (X2 = 54 / Y2 = 1104, X3 = 100) is invisible to R-PLATEAU (flat 1248 and a
Y-only mis-write read identically there).  How much ordinary driving does a TAPER read need?
Statistic TI = a(idx 18-50)/a_V294(18-50)  divided by  a(idx 0-8)/a_V294(0-8)   (one number; CAND ~0.93, flat ~0.985).
Per E-second chunk of ENGAGED time (>= 3 s hands-off tap in each of the two idx ranges): classification against the
midpoint of the two noiseless expectations.  Plus whole-drive block-bootstrap CIs per bin."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (HERE, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant")):
    sys.path.insert(0, p)
import advp_lane as AL
import plib as P
rng = np.random.default_rng(3)
Z = dict(np.load(os.path.join(HERE, "out", "_advp4_marches.npz")))
d = P.load()
sg, tk, j = d["sg"], d["tick_tap"], d["j100"]
y = d["T_tap"].astype(float)
idx_t = d["idx"][j]
ok = d["ho"][j] & (np.abs(y) < 2300)
eng = d["eng"].astype(bool)
F = sg * Z["V294_ff"][tk].astype(float)
R = sg * Z["V294_live"][tk].astype(float) - F
noise = y - AL.quant(sg * Z["V294_live"][tk])
SYN = {"V294": y}
for k in ("CAND", "MB_flat1248", "MB_Yonly", "G12"):
    SYN[k] = AL.quant(sg * Z[k + "_live"][tk]) + noise


def a_of(yy, mask):
    mask = mask & (np.abs(yy) < 2300)
    if mask.sum() < 150:
        return np.nan
    X = np.vstack([F[mask], R[mask], np.ones(mask.sum())]).T
    return np.linalg.lstsq(X, yy[mask], rcond=None)[0][0]


PL, MID = idx_t < 9, (idx_t >= 18) & (idx_t < 50)
base_pl, base_mid = a_of(y, ok & PL), a_of(y, ok & MID)


def TI(yy, mask):
    p, q = a_of(yy, mask & PL), a_of(yy, mask & MID)
    return (q / base_mid) / (p / base_pl)


E_TI = {k: TI(AL.quant(sg * Z[(k if k != "V294" else "V294") + "_live"][tk]) + 0 * noise, ok) for k in SYN}
print("noiseless TI expectation:", {k: round(v, 4) for k, v in E_TI.items()})
print("whole-drive TI read (with r71b's residual):", {k: round(TI(SYN[k], ok), 4) for k in SYN})
mid = 0.5 * (E_TI["CAND"] + E_TI["MB_flat1248"])
print("decision midpoint CAND vs flat: %.4f" % mid)
ef = np.flatnonzero(eng)
for E in (20, 30, 60, 120, 300):
    step = int(E * 100)
    res = {k: [] for k in ("CAND", "MB_flat1248", "MB_Yonly")}
    n_all = 0
    for a0 in range(0, len(ef) - step + 1, step):
        lo, hi = ef[a0], ef[a0 + step - 1]
        wm = ok & (j >= lo) & (j <= hi) & eng[j]
        n_all += 1
        for k in res:
            v = TI(SYN[k], wm)
            if np.isfinite(v):
                res[k].append(v)
    c = np.array(res["CAND"]); f = np.array(res["MB_flat1248"]); yo = np.array(res["MB_Yonly"])
    if len(c) == 0:
        print("E %3d s: no qualifying chunk of %d" % (E, n_all)); continue
    print("E %3d s: %2d/%2d chunks read TI | CAND med %.3f [%.3f, %.3f] -> correct %d/%d | flat med %.3f [%.3f, %.3f] -> correct %d/%d | Y-only med %.3f -> correct %d/%d"
          % (E, len(c), n_all, np.median(c), c.min(), c.max(), np.sum(c < mid), len(c), np.median(f), f.min(), f.max(), np.sum(f > mid), len(f),
             np.median(yo), np.sum(yo > mid), len(yo)))
# whole-drive per-bin bootstrap CI (20 s engaged blocks)
BINS = [(0, 9), (9, 18), (18, 30), (30, 50), (50, 80), (80, 100)]
blocks = []
for a0 in range(0, len(ef) - 2000 + 1, 2000):
    blocks.append((ef[a0], ef[a0 + 1999]))
print("\nwhole-drive per-bin ratio, 95%% block-bootstrap over %d 20 s engaged blocks:" % len(blocks))
bm = [ok & (j >= lo) & (j <= hi) & eng[j] for lo, hi in blocks]
for lo, hi in BINS:
    row = "  idx %3d-%3d:" % (lo, hi)
    b0 = a_of(y, ok & (idx_t >= lo) & (idx_t < hi))
    for k in ("V294", "CAND", "MB_flat1248", "MB_Yonly"):
        pt = a_of(SYN[k], ok & (idx_t >= lo) & (idx_t < hi)) / b0
        bs = []
        for _ in range(300):
            s = rng.integers(0, len(bm), len(bm))
            mm = np.zeros_like(ok)
            for q in s:
                mm |= bm[q]
            # sampling with replacement via weights: duplicate blocks approximated by union + reweight -> use counts
            bs.append(a_of(SYN[k], mm & (idx_t >= lo) & (idx_t < hi)) / b0)
        bs = np.array([v for v in bs if np.isfinite(v)])
        row += "  %s %.3f [%.3f, %.3f]" % (k, pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5))
    print(row)
