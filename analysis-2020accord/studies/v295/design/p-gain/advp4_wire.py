"""ADV-bytes (p-gain) step 4: OBSERVABILITY of R1.3_8_100 on the existing wire, from r71b's own data.

Independent of the designer's s6/s10: own lane (advp_lane, from the listing), own regression, own windows.
Uses plib's r71b cache only for the recorded streams (idx/sgn/fade per frame, x at 1 kHz, the 427 tap and its alignment).

Variants marched on r71b's own command + rate:
  V294, CAND (R1.3_8_100), MB_flat1248 (plateau, no taper), MB_Yonly (Y written, X left at V294's slot-7 knots),
  RU (R1.35_4_100), G12 (flat 1152), G13 (flat 1248 == MB_flat1248).
Synthetic flight for variant v:  y_v = quant(T_v at the tap tick) + NOISE, NOISE = real tap - quant(V294 march)
  (NOISE_x = NOISE * Kp_v(idx)/960, the pessimistic "residual scales with torque" variant).
ANALYSIS ONLY -- reads caches, sends nothing."""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (HERE, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"),
          os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"), os.path.join(KIT, "rlog-tools", "studies", "grind"),
          os.path.join(KIT, "analysis-2020accord", "model")):
    sys.path.insert(0, p)
import advp_lane as AL
import plib as P

OUT = os.path.join(HERE, "out")
VAR = {
    "V294": ((0, 68, 112, 136, 208), (960,) * 5),
    "CAND": ((0, 8, 54, 100, 208), (1248, 1248, 1104, 960, 960)),
    "MB_flat1248": ((0, 68, 112, 136, 208), (1248,) * 5),
    "MB_Yonly": ((0, 68, 112, 136, 208), (1248, 1248, 1104, 960, 960)),
    "RU_1.35_4_100": ((0, 4, 52, 100, 208), (1296, 1296, 1128, 960, 960)),
    "G12": ((0, 68, 112, 136, 208), (1152,) * 5),
}
KPT = {k: AL.kp_table(*v) for k, v in VAR.items()}

d = P.load()
x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64).tolist()
idx, sgn, m = d["idx"].astype(int), d["sgn"].astype(int), d["m"].astype(int)
sg = d["sg"]
tk, j = d["tick_tap"], d["j100"]
y = d["T_tap"].astype(float)
idx_t = idx[j]
v_t = d["v"][j]
ok = d["ho"][j] & (np.abs(y) < 2300)
print("r71b: frames %d (%.0f s), engaged %.0f s, hands-off engaged %.0f s, usable tap frames %d (%.0f s)"
      % (len(idx), len(idx) / 100, d["eng"].sum() / 100, d["ho"].sum() / 100, ok.sum(), ok.sum() / 50))

cache = os.path.join(OUT, "_advp4_marches.npz")
if os.path.exists(cache):
    Z = dict(np.load(cache))
else:
    Z = {}
    t0 = time.time()
    for k in VAR:
        Z[k + "_live"] = np.array(AL.march(sgn, idx, m, KPT[k], x1k=x1k, trim=True), np.int32)
        Z[k + "_ff"] = np.array(AL.march(sgn, idx, m, KPT[k], x1k=None, trim=False), np.int32)
        print("  marched %s (%.0f s)" % (k, time.time() - t0))
    np.savez_compressed(cache, **Z)
# second method: my march == plib's byte-exact march for V294 (FF and live)
ffm = np.count_nonzero(sg * Z["V294_ff"] != d["T1k_null"])
lvm = np.count_nonzero(sg * Z["V294_live"] != d["T1k_live"])
print("own march vs plib march, V294: FF mismatches %d / %d ; live mismatches %d / %d" % (ffm, len(Z["V294_ff"]), lvm, len(Z["V294_live"])))

F294 = sg * Z["V294_ff"][tk].astype(float)
R294 = sg * Z["V294_live"][tk].astype(float) - F294
noise = y - AL.quant(sg * Z["V294_live"][tk])
print("tap residual on usable frames: rms %.2f, mean %+.2f" % (np.std(noise[ok]), np.mean(noise[ok])))
# does the residual scale with torque / its rate?  (pessimistic-noise justification)
dT = np.gradient(sg * Z["V294_live"][tk].astype(float))
cc = np.corrcoef(np.abs(noise[ok]), np.abs(F294[ok]))[0, 1]
cc2 = np.corrcoef(np.abs(noise[ok]), np.abs(dT[ok]))[0, 1]
print("corr(|resid|, |F|) %.3f ; corr(|resid|, |dT/dtap|) %.3f" % (cc, cc2))

SYN = {"REAL_V294": y}
for k in VAR:
    base = AL.quant(sg * Z[k + "_live"][tk])
    SYN[k] = base + noise
    SYN[k + "_xnoise"] = base + noise * (np.array(KPT[k])[idx_t] / 960.0)


def regress(yy, cols, mask):
    X = np.vstack([c[mask] for c in cols] + [np.ones(mask.sum())]).T
    co, *_ = np.linalg.lstsq(X, yy[mask], rcond=None)
    return co


PLAT = idx_t < 9
a_base = regress(y, (F294, R294), ok & PLAT)[0]
b_base = regress(y, (F294, R294), ok & PLAT)[1]
print("\nR-PLATEAU baseline (real V294 tap, whole drive, idx 0-8): a %.4f  b %.4f  (design: 0.938)" % (a_base, b_base))

# ---------------- windows on the 100 Hz frame axis, over ENGAGED time only
eng = d["eng"].astype(bool)


def make_windows(secs):
    """contiguous blocks of `secs` of ENGAGED frames (the clock only runs while laterally engaged)."""
    ef = np.flatnonzero(eng)
    step = int(secs * 100)
    out = []
    for a0 in range(0, len(ef) - step + 1, step):
        fr = ef[a0:a0 + step]
        out.append((fr[0], fr[-1]))
    return out


def win_mask(w):
    lo, hi = w
    return (j >= lo) & (j <= hi) & eng[j]


def plateau_read(yy, w, min_frames=150):
    mm = win_mask(w) & ok & (np.abs(yy) < 2300) & PLAT
    if mm.sum() < min_frames:
        return None, int(mm.sum())
    co = regress(yy, (F294, R294), mm)
    return (co[0] / a_base, co[1] / b_base if b_base else np.nan), int(mm.sum())


RES = {}
for secs in (15, 20, 30):
    W = make_windows(secs)
    row = {"n_windows": len(W)}
    for key in ("REAL_V294", "CAND", "CAND_xnoise", "MB_flat1248", "MB_Yonly", "RU_1.35_4_100", "G12"):
        rr, nq = [], 0
        for w in W:
            r, nf = plateau_read(SYN[key], w)
            if r is not None:
                rr.append(r)
        rr = np.array(rr)
        a = rr[:, 0]
        row[key] = dict(n=len(rr), med=float(np.median(a)), p2=float(np.percentile(a, 2.5)), p97=float(np.percentile(a, 97.5)),
                        mn=float(a.min()), mx=float(a.max()), in_null=float(np.mean(np.abs(a - 1.0) <= 0.05)),
                        in_live=float(np.mean(np.abs(a - 1.30) <= 0.05)), above115=float(np.mean(a > 1.15)),
                        b_med=float(np.median(rr[:, 1])), b_p2=float(np.percentile(rr[:, 1], 2.5)), b_p97=float(np.percentile(rr[:, 1], 97.5)))
    RES["win%d" % secs] = row
    print("\n== %d s ENGAGED windows: %d total; qualifying (>= 3 s of hands-off idx 0-8 tap frames): %d (%.0f %%)"
          % (secs, len(W), row["REAL_V294"]["n"], 100.0 * row["REAL_V294"]["n"] / len(W)))
    for key in ("REAL_V294", "CAND", "CAND_xnoise", "MB_flat1248", "MB_Yonly", "RU_1.35_4_100", "G12"):
        r = row[key]
        print("  %-14s a/a_base med %.3f [p2.5 %.3f, p97.5 %.3f] min %.3f max %.3f | in 1.00+-0.05: %4.0f %% | in 1.30+-0.05: %4.0f %% | >1.15: %4.0f %% | trim b/b_base med %.2f [%.2f, %.2f]"
              % (key, r["med"], r["p2"], r["p97"], r["mn"], r["mx"], 100 * r["in_null"], 100 * r["in_live"], 100 * r["above115"],
                 r["b_med"], r["b_p2"], r["b_p97"]))

# qualifying windows by speed band (is the plateau read available in each band's episodes?)
W20 = make_windows(20)
print("\nper 20 s window, hands-off idx 0-8 tap seconds: quartiles", np.percentile([int((win_mask(w) & ok & PLAT).sum()) / 50 for w in W20], [0, 25, 50, 75, 100]))
# the SYMPTOMATIC episodes: hard turns at medium speed. Hard = idx >= 40 at 5-22 m/s; are plateau frames inside them?
hard = (idx >= 40) & (d["v"] >= 5) & (d["v"] < 22) & eng
runs = P.runs(hard, 50)
print("hard-turn runs (>= 0.5 s): %d, total %.0f s" % (len(runs), sum(b - a for a, b in runs) / 100))
ep_ok = 0
ep_list = []
for a0, b0 in runs:
    c = (a0 + b0) // 2
    w = (max(0, c - 1500), min(len(idx) - 1, c + 1500))           # the 30 s around the symptom
    mm = win_mask(w) & ok & PLAT
    ep_list.append(int(mm.sum()))
    ep_ok += mm.sum() >= 150
print("30 s windows centred on each hard-turn run: plateau frames quartiles %s ; qualifying %d / %d" % (np.percentile(ep_list, [0, 25, 50, 75, 100]), ep_ok, len(runs)))

# ---------------- R-SHAPE: per-bin ratio, whole drive and per exposure chunk; can each knot be read?
BINS = [(0, 5), (5, 9), (9, 18), (18, 30), (30, 50), (50, 80), (80, 100), (100, 241)]
def bin_ratio(yy, mask, lo, hi):
    mb = mask & (idx_t >= lo) & (idx_t < hi) & (np.abs(yy) < 2300)
    mb0 = ok & (idx_t >= lo) & (idx_t < hi)
    if mb.sum() < 50 or mb0.sum() < 50:
        return np.nan, int(mb.sum())
    return regress(yy, (F294, R294), mb)[0] / regress(y, (F294, R294), mb0)[0], int(mb.sum())

print("\nR-SHAPE whole drive (bin ratio = a / V294's own a in the bin)")
hdr = "  bin      sec  " + "  ".join("%-13s" % k for k in ("REAL_V294", "CAND", "CAND_xnoise", "MB_flat1248", "MB_Yonly", "RU_1.35_4_100"))
print(hdr)
shape = {}
for lo, hi in BINS:
    vals = [bin_ratio(SYN[k], ok, lo, hi) for k in ("REAL_V294", "CAND", "CAND_xnoise", "MB_flat1248", "MB_Yonly", "RU_1.35_4_100")]
    shape["%d-%d" % (lo, hi)] = [v[0] for v in vals]
    print("  %3d-%3d %5.0f  " % (lo, hi, vals[0][1] / 50) + "  ".join("%-13.3f" % v[0] for v in vals))

# exposure needed: split the drive into chunks of E s of ENGAGED time; per chunk and bin, compare CAND read vs each
# alternative hypothesis's NOISELESS expectation; the fraction of chunks where CAND is closer to its own expectation.
def expect(k, lo, hi):
    return bin_ratio(AL.quant(sg * Z[k + "_live"][tk]) + 0 * noise, ok, lo, hi)[0]

print("\nKNOT READS by exposure: fraction of E-second engaged chunks in which the synthetic CAND flight's bin ratio is")
print("closer to CAND's own expectation than to the alternative's (and the chunk has >= 3 s of hands-off tap in the bin)")
for E in (30, 60, 120, 300, 600):
    W = make_windows(E)
    for alt in ("MB_Yonly", "MB_flat1248", "RU_1.35_4_100", "V294"):
        line = []
        for lo, hi in ((5, 9), (18, 30), (30, 50), (50, 80), (80, 100)):
            ec, ea = shape_c = bin_ratio(SYN["CAND"], ok, lo, hi)[0], bin_ratio(SYN[alt] if alt != "V294" else y, ok, lo, hi)[0]
            good = n = 0
            for w in W:
                mw = win_mask(w) & ok
                r, nf = bin_ratio(SYN["CAND"], mw, lo, hi)
                if nf < 150 or np.isnan(r):
                    continue
                n += 1
                good += abs(r - ec) < abs(r - ea)
            line.append("%d-%d: %s (|dE| %.3f)" % (lo, hi, ("%d/%d" % (good, n)) if n else "0 chunks", abs(ec - ea)))
        print("  E %4d s vs %-14s %s" % (E, alt, " | ".join(line)))

json.dump(dict(a_base=float(a_base), b_base=float(b_base), windows=RES, shape=shape), open(os.path.join(OUT, "advp4_wire.json"), "w"),
          indent=1, default=float)
