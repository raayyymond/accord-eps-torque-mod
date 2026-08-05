#!/usr/bin/env python3
"""ANGLE vs ANGLE-RATE -- the crux of the near-centre conditional, on the whole cached corpus.

`nearcentre_grind1.py` ss4 showed the marginal near-centre ladder is NOT monotone (0-5 deg is
LOWER than 5-15 / 15-45), and that near-centre engaged-creep windows are overwhelmingly LOW-RATE.
So the marginal comparison is confounded in the operator's favour AND against him at once. This
file settles the direction, three ways that fail differently:

  ss1  FINER RATE STRATA. The `32+` bin holds 489 of 932 engaged-creep windows and spans 32 to
       several hundred deg/s, so an "angle effect" inside it can be pure residual rate. Re-binned
       with the top bin split.
  ss2  A LEAKAGE-IMMUNE SECOND METRIC. `e_18-22` is an ENVELOPE, so a fast wheel motion lifts it
       through spectral leakage and 1/f alone. `p_18-22` (peak / local median floor) cannot be
       lifted that way, and `e_18-22 / e_24-28` divides the pre-declared negative control out
       PER WINDOW. If the rate effect is leakage it dies here; if the angle effect is, so does it.
  ss3  SLOPES, not ratios. Rank-partial association of log e_18-22 on |angle| controlling |rate|,
       and on |rate| controlling |angle|, with episode-cluster bootstrap CIs and a SHUFFLED-PAIRING
       control -- because a ratio of two marginals is not a tracking test (kit rule 5).

Usage:  python nearcentre_deconfound.py [ep|blk]   ->  writes _nearcentre_deconfound.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT = 2000
OUT = {"epkey": G.EPKEY}

store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["a_c"] = r["a_mean"] - c
        r["absa"] = abs(r["a_c"])
        r["ab"] = N.abin(r["absa"])
# per-window leakage-immune statistics
for b in N.LADDER:
    for r in store[b]:
        r["exc"] = (r["e_18-22"] / r["e_24-28"]) if r["e_24-28"] > 0 else np.nan

ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
POOL = [r for b in N.LADDER for r in ENGC[b]]

# ★ finer rate bins -- the top bin of G.R_BINS holds >half the corpus and spans an order of magnitude
RB2 = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 64.0), (64.0, 128.0), (128.0, 1e9)]
RB2N = ["0-4", "4-16", "16-32", "32-64", "64-128", "128+"]
RATEKEY = sys.argv[2] if len(sys.argv) > 2 else "rate_lp"
print(f"\n  RATE AXIS = {RATEKEY}")
print("  rate_lp   = mean |lowpass(rate_c, 3 Hz)| -- the MANOEUVRE rate, oscillation removed")
print("  rate_absm = raw mean |rate_c|, which CONTAINS the 21 Hz grind itself and is therefore")
print("              PARTLY CIRCULAR as a rate axis. See `_nearcentre_lib.augment_angle`.")
for r in POOL:
    r["rb2"] = G.binof(r[RATEKEY], RB2)

# ------------------------------------------------------------------ ss1 finer rate strata --------
N.hdr("ss1  ★★★ THE 2-WAY TABLE WITH THE TOP RATE BIN SPLIT -- pooled engaged creep, n=932")
print("  The `32+` bin of `G.R_BINS` holds 489/932 windows and spans 32 -> ~400 deg/s. An angle")
print("  effect measured inside it is not deconfounded at all. Split into 32-64 / 64-128 / 128+.\n")


def table(rs, rowkey, rownames, colkey, colnames, metric, fmt="{:>8.0f}"):
    print(f"      {'|ang| \\ |rate|':<14} " + " ".join(f"{n:>15}" for n in colnames)
          + f"{'ROW ALL':>15}")
    tab = {}
    for i, rn in enumerate(rownames):
        cells = []
        for j in range(len(colnames)):
            c = [r for r in rs if r[rowkey] == i and r[colkey] == j]
            v = G.col(c, metric)
            v = v[np.isfinite(v)]
            m = float(np.median(v)) if len(v) else np.nan
            tab[f"{rn}|{colnames[j]}"] = dict(n=len(c), med=m)
            cells.append(f"{'--':>15}" if not len(v)
                         else (fmt.format(m) + f"(n{len(c)})").rjust(15))
        ra = [r for r in rs if r[rowkey] == i]
        va = G.col(ra, metric)
        va = va[np.isfinite(va)]
        cells.append((fmt.format(np.median(va)) + f"(n{len(ra)})").rjust(15)
                     if len(va) else f"{'--':>15}")
        print(f"      {rn:<14} " + " ".join(cells))
    cells = []
    for j in range(len(colnames)):
        c = [r for r in rs if r[colkey] == j]
        v = G.col(c, metric)
        v = v[np.isfinite(v)]
        cells.append((fmt.format(np.median(v)) + f"(n{len(c)})").rjust(15)
                     if len(v) else f"{'--':>15}")
    print(f"      {'COL ALL':<14} " + " ".join(cells))
    return tab


print("  --- median e_18-22  (the kit's standard grind-#1 metric)")
OUT["t_e"] = table(POOL, "ab", N.A_NAMES, "rb2", RB2N, "e_18-22")
print("\n  --- median e_18-22 / e_24-28  (the negative control divided out PER WINDOW)")
OUT["t_exc"] = table(POOL, "ab", N.A_NAMES, "rb2", RB2N, "exc", "{:>8.2f}")
print("\n  --- median p_18-22  (PROMINENCE: peak / local median floor -- leakage cannot lift it)")
OUT["t_p"] = table(POOL, "ab", N.A_NAMES, "rb2", RB2N, "p_18-22", "{:>8.2f}")
print("\n  --- median f_18-22  (where the line actually sits, Hz)")
OUT["t_f"] = table(POOL, "ab", N.A_NAMES, "rb2", RB2N, "f_18-22", "{:>8.2f}")
print("\n  --- median mean |rate_c| INSIDE each cell (deg/s) -- the residual-confound audit")
OUT["t_r"] = table(POOL, "ab", N.A_NAMES, "rb2", RB2N, RATEKEY, "{:>8.1f}")

# ------------------------------------------------------------------ ss2 within-stratum ladders ---
N.hdr("ss2  ★★★ THE TWO LADDERS, EACH INSIDE THE OTHER'S STRATUM -- pooled, episode CIs")
print("  ANGLE ladder is read DOWN a single rate column; RATE ladder is read ACROSS a single")
print("  angle row. A conditional that only exists in the margin is a confound, not an effect.\n")


def ladder(rs, key, names, metric, label):
    print(f"      {label}")
    for i, nm in enumerate(names):
        c = [r for r in rs if r[key] == i]
        nb = len({r[G.EPKEY] for r in c})
        if len(c) < 8 or nb < 3:
            v = G.col(c, metric)
            v = v[np.isfinite(v)]
            print(f"        {nm:<10} n={len(c):<4} b={nb:<3} "
                  + (f"med={np.median(v):>9.1f}  *** THIN" if len(v) else "*** EMPTY"))
            continue
        m, lo, hi = G.boot_median_ci(c, metric, RNG, nboot=NBOOT)
        print(f"        {nm:<10} n={len(c):<4} b={nb:<3} med={m:>9.1f}  [{lo:>8.1f},{hi:>9.1f}]")


for j, rn in enumerate(RB2N):
    sub = [r for r in POOL if r["rb2"] == j]
    if len(sub) < 20:
        print(f"      rate {rn:<8} n={len(sub)}  *** too thin for an angle ladder")
        continue
    ladder(sub, "ab", N.A_NAMES, "e_18-22", f"ANGLE ladder INSIDE rate bin {rn} (n={len(sub)})")
    print()
print()
for i, an in enumerate(N.A_NAMES):
    sub = [r for r in POOL if r["ab"] == i]
    if len(sub) < 20:
        continue
    ladder(sub, "rb2", RB2N, "e_18-22", f"RATE ladder INSIDE angle bin {an} deg (n={len(sub)})")
    print()

# ------------------------------------------------------------------ ss3 slopes -------------------
N.hdr("ss3  ★★★ SLOPES, NOT RATIOS -- rank-partial association with episode-cluster bootstrap")
print("  Spearman on ranks; the partial removes the other variable by regressing BOTH the metric")
print("  and the predictor on the other's rank (and on rank v, rank eff) and correlating residuals.")
print("  🛑 SHUFFLED-PAIRING CONTROL: the same statistic after permuting the metric across windows")
print("  WITHIN episodes -- it must sit at zero, or the estimator itself manufactures association.\n")


def rk(x):
    x = np.asarray(x, float)
    o = np.argsort(np.argsort(x))
    return (o - o.mean()) / (o.std() + 1e-12)


def partial(rs, metric, pred, ctrl):
    y = rk(G.col(rs, metric))
    x = rk(G.col(rs, pred))
    if not ctrl:
        return float(np.mean(y * x))
    Z = np.column_stack([rk(G.col(rs, c)) for c in ctrl] + [np.ones(len(rs))])
    by, _, _, _ = np.linalg.lstsq(Z, y, rcond=None)
    bx, _, _, _ = np.linalg.lstsq(Z, x, rcond=None)
    ry, rx = y - Z @ by, x - Z @ bx
    s = ry.std() * rx.std()
    return float(np.mean(ry * rx) / s) if s > 0 else np.nan


def boot_partial(rs, metric, pred, ctrl, nboot=1000):
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    ep = list(eps.values())
    pt = partial(rs, metric, pred, ctrl)
    d = np.full(nboot, np.nan)
    for k in range(nboot):
        i = RNG.integers(0, len(ep), len(ep))
        s = [r for j in i for r in ep[j]]
        if len(s) > len(ctrl) + 4:
            d[k] = partial(s, metric, pred, ctrl)
    return pt, float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


def shuffle_ctrl(rs, metric, pred, ctrl, nrep=300):
    eps = {}
    for r in rs:
        eps.setdefault(r[G.EPKEY], []).append(r)
    out = []
    for _ in range(nrep):
        s = []
        for e in eps.values():
            v = G.col(e, metric)
            RNG.shuffle(v)
            for r, vv in zip(e, v):
                q = dict(r)
                q[metric] = vv
                s.append(q)
        out.append(partial(s, metric, pred, ctrl))
    out = np.array(out, float)
    return float(np.nanmedian(out)), float(np.nanpercentile(out, 2.5)), \
        float(np.nanpercentile(out, 97.5))


sl = {}
for metric in ("e_18-22", "exc", "p_18-22"):
    print(f"  --- metric = {metric}")
    print(f"      {'predictor':<16} {'controls':<26} {'rho':>7} {'[95% CI]':>17} "
          f"{'shuffled-pairing null':<26}")
    for pred, ctrl, lab in (("absa", [], "none"),
                            ("absa", [RATEKEY], "|rate|"),
                            ("absa", [RATEKEY, "v", "eff"], "|rate|, v, eff"),
                            (RATEKEY, [], "none"),
                            (RATEKEY, ["absa"], "|angle|"),
                            (RATEKEY, ["absa", "v", "eff"], "|angle|, v, eff")):
        rs = [r for r in POOL if np.isfinite(r[metric])]
        pt, lo, hi = boot_partial(rs, metric, pred, ctrl)
        nm, nlo, nhi = shuffle_ctrl(rs, metric, pred, ctrl, nrep=200)
        sl[f"{metric}|{pred}|{lab}"] = dict(rho=pt, lo=lo, hi=hi, null=[nm, nlo, nhi], n=len(rs))
        print(f"      {pred:<16} {lab:<26} {pt:>7.3f} [{lo:>7.3f},{hi:>8.3f}] "
              f"{nm:>7.3f} [{nlo:>6.3f},{nhi:>6.3f}]")
    print()
OUT["slopes"] = sl

# ------------------------------------------------------------------ ss4 the interaction ----------
N.hdr("ss4  ★★ THE INTERACTION -- near-centre vs off-centre INSIDE the high-rate stratum, per build")
print("  Grind #1 lives at |rate| >= 16 deg/s (ss1). If the operator's conditional is real it must")
print("  show up as near-centre > off-centre WITHIN that stratum, and it must REPLICATE.\n")
print(f"      {'arm':<12} {'n near':>7} {'n off':>6} {'med near':>9} {'med off':>8} "
      f"{'ratio':>7} {'[95% CI]':>17}  units n/o")
inter = {}
for k in ["POOLED"] + list(N.ARMS):
    rs = [r for r in (POOL if k == "POOLED" else ARM[k]) if r[RATEKEY] >= 16.0]
    A = [r for r in rs if r["absa"] < 5.0]
    B = [r for r in rs if r["absa"] >= 15.0]
    ua, ub = len({r[G.EPKEY] for r in A}), len({r[G.EPKEY] for r in B})
    if len(A) < 5 or len(B) < 5:
        print(f"      {k:<12} {len(A):>7} {len(B):>6}   *** UNDERPOWERED "
              f"(units {ua}/{ub})")
        inter[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    mA = float(np.median(G.col(A, "e_18-22")))
    mB = float(np.median(G.col(B, "e_18-22")))
    epA = {}
    epB = {}
    for r in A:
        epA.setdefault(r[G.EPKEY], []).append(r)
    for r in B:
        epB.setdefault(r[G.EPKEY], []).append(r)
    pa, pb = list(epA.values()), list(epB.values())
    d = np.full(NBOOT, np.nan)
    for i in range(NBOOT):
        ia = RNG.integers(0, len(pa), len(pa))
        ib = RNG.integers(0, len(pb), len(pb))
        va = np.concatenate([G.col(pa[j], "e_18-22") for j in ia])
        vb = np.concatenate([G.col(pb[j], "e_18-22") for j in ib])
        if len(va) and len(vb) and np.median(vb) > 0:
            d[i] = np.median(va) / np.median(vb)
    lo, hi = float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))
    inter[k] = dict(nA=len(A), nB=len(B), uA=ua, uB=ub, medA=mA, medB=mB,
                    ratio=mA / mB if mB else np.nan, lo=lo, hi=hi)
    print(f"      {k:<12} {len(A):>7} {len(B):>6} {mA:>9.0f} {mB:>8.0f} "
          f"{mA / mB if mB else np.nan:>7.2f} [{lo:>7.2f},{hi:>8.2f}]  {ua}/{ub}")
OUT["interaction"] = inter

(HERE.parent / "_nearcentre_deconfound.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_nearcentre_deconfound.json'}")
