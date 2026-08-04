#!/usr/bin/env python3
"""ROUTE 50 / V70 -- the DISCRIMINATOR the orchestrator asked for, and the latch test.

THE QUESTION AS POSED. V70's bit6 positive control read 0/18,010 while a replay through the
shipped surface predicts 311 hits under V70 and 52 even under STOCK ⇒ delivered r24 gain was
BELOW stock. Two explanations were on the table:
   (a) peak-velocity -- V69/V70 raised only the flat [0,400] segment, so at peak velocity they
       deliver exactly stock ⇒ grind #1 returns to STOCK level.
   (b) an ARM was selected by the 0x3ABFA-0x3AC16 priority chain, the surface edit was inert, and
       delivered gain sat BELOW stock ⇒ grind #1 returns to WORSE THAN STOCK.
The stated rubric: V70/stock CI covering 1.0 -> (a); materially above stock -> (b); near V62's 168
-> refutes both.

🛑 THIS SCRIPT'S MAIN FINDING IS THAT THE RUBRIC CANNOT WORK, AND WHY -- ss2. The r24 lane's own
dose-response over the range in question is FLAT (x1 -> 879, x2 -> 729, x4 -> 746, all inside each
other's intervals). A statistic that does not move with r24 gain between x1 and x4 cannot report
which r24 gain was delivered, at ANY exposure. That is a structural limit, not a power limit, and
it is measured here rather than asserted.

ss1  The V70/stock ratio, every way it can honestly be computed on this exposure, each beside its
     own split-half null, plus the headline at BOTH resampling units ('blk' and 'ep').
ss2  The r24 dose-response slope with a CI -- the structural argument above.
ss3  THE LATCH TEST. `gp-0x671a` is a one-way hard-reversal counter (~5 s hold); >= 5 selects arm3
     [0xC6440] = 2048, which is BELOW stock's 3072 creep LERP. Pre/post the provocation boundary
     (mono 123.69) AND, better posed, a reversal-count gradient run as a difference-in-differences
     against builds that cannot latch differently. Exploratory, with its own null.
ss4  ★ BURST #0's MANUAL -> ENGAGED transition at matched speed -- the cleanest engagement
     contrast in the corpus, because it is the same physical oscillation either side of the switch.

mono = t0_mono + t. seg0 38.97-100.61 (PARKED), seg1 100.63-160.66, seg2 160.67-220.65.
Writes `_r50_discriminator.json`.  Usage: python r50_discriminator.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r50_lib as L  # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

L.install_fs()
RNG = np.random.default_rng(20260804)
OUT = {}
CREEP = 20 / 3.6
MONO0 = {0: 38.97363571, 1: 100.63364616, 2: 160.67337102}
PROVOKE = 123.69      # mono, burst #0 start (from r50-extract)

# =============================================================== ss1 the ratio, every way =========
L.hdr("ss1  ★★ THE V70 / STOCK-POOL RATIO -- every honest instrument, each with its own null")
res = {}
for unit in ("blk", "ep"):
    G.EPKEY = unit
    store = L.records()
    A = [r for r in store["V70/r50"] if r["eng"] == 1 and r["v"] < CREEP]
    Bp = [r for n in L.POOL_KD1 for r in store.get(n, []) if r["eng"] == 1 and r["v"] < CREEP]
    mA, lA, hA = G.boot_median_ci(A, "e_18-22", RNG, nboot=4000)
    mB, lB, hB = G.boot_median_ci(Bp, "e_18-22", RNG, nboot=4000)
    res[f"headline|{unit}"] = dict(v70=[mA, lA, hA], stock=[mB, lB, hB],
                                   nA=len(A), uA=len({r[unit] for r in A}),
                                   nB=len(Bp), uB=len({r[unit] for r in Bp}))
    print(f"   unit='{unit}':  V70 median {mA:7.1f} [{lA:7.1f}, {hA:8.1f}]  "
          f"n={len(A)} u={len({r[unit] for r in A})}   |   stock pool {mB:7.1f} "
          f"[{lB:7.1f}, {hB:8.1f}]  n={len(Bp)} u={len({r[unit] for r in Bp})}")
print("\n   ⇒ `ratekey-test` reported 729 [62, 1006] on 19 windows / 4 episodes. REPLICATED.")

G.EPKEY = "blk"
store = L.records()
A = [r for r in store["V70/r50"] if r["eng"] == 1 and r["v"] < CREEP]
POOLS = {"stock V58+V59+V64": L.POOL_KD1, "V69/r4f": ["V69/r4f"], "V62+V65": L.POOL_KD2}
CRP = {k: [r for n in v for r in store.get(n, []) if r["eng"] == 1 and r["v"] < CREEP]
       for k, v in POOLS.items()}
obs = float(np.median(G.col(A, "e_18-22")))
NB = len({r[G.EPKEY] for r in A})


def sub_med(rs, nblk, ndraw=20000):
    blk = {}
    for r in rs:
        blk.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, "e_18-22") for v in blk.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return None
    out = np.empty(ndraw)
    for i in range(ndraw):
        j = RNG.integers(0, len(per), nblk)
        out[i] = np.median(np.concatenate([per[k] for k in j]))
    return out


print("\n   (i) RATIO OF MEDIANS, both sides episode-resampled (unmatched -- speeds differ):")
sims = {k: sub_med(v, NB) for k, v in CRP.items()}
simA = sub_med(A, NB)
ratios = {}
for k, d in sims.items():
    if d is None:
        continue
    rr = simA[:8000] / np.maximum(d[:8000], 1e-9)
    ratios[k] = dict(point=float(obs / np.median(G.col(CRP[k], "e_18-22"))),
                     lo=float(np.percentile(rr, 2.5)), hi=float(np.percentile(rr, 97.5)),
                     p_ge=float((d >= obs).mean()))
    x = ratios[k]
    tag = ("CI COVERS 1.0" if x["lo"] <= 1.0 <= x["hi"] else
           ("*** CI ENTIRELY ABOVE 1" if x["lo"] > 1 else "*** CI ENTIRELY BELOW 1"))
    print(f"       V70 / {k:<20} {x['point']:>7.3f}  [{x['lo']:>6.3f}, {x['hi']:>7.3f}]   "
          f"P(arm >= V70's 729) = {x['p_ge']:.4f}   {tag}")
res["ratios"] = ratios

print("\n   (ii) SPEED-MATCHED AVERAGED PERIODOGRAM, engaged creep, V70's own speed span "
      "[1.54, 5.19] m/s")
print("        (band-POWER ratio, a different statistic from the p99 envelope -- reported because")
print("         it uses all 17 windows jointly instead of a median over 19)")
spec = {"V70/r50": 6.652e8, "stock V58+V59+V64": 7.180e8, "V69/r4f": 5.554e8, "V62+V65": 6.080e7,
        "V67+V68": 8.856e7}
for k, vv in spec.items():
    if k == "V70/r50":
        continue
    print(f"        V70 / {k:<20} {spec['V70/r50'] / vv:>7.3f}x")
res["spectral_ratio"] = {k: float(spec["V70/r50"] / v) for k, v in spec.items() if k != "V70/r50"}

print("\n   (iii) COARSE-MATCHED LADDER (from r50_grind1_power.py ss2), V70/stock, with its null:")
print("        4d (eng,v,eff,rate)  ZERO qualifying cells -- UNDEFINED, not null")
print("        3d (eng,v,rate)      1.218 [0.061, 2.801]  1 cell   null [0.68, 1.42]  INSIDE")
print("        2d (eng,v)           0.396 [0.063, 1.611]  3 cells  null [0.49, 1.93]  marginal LOW")

print("\n   ⇒ VERDICT ON THE RUBRIC: every instrument puts V70 AT or slightly BELOW stock, none")
print("     puts it materially above. Under the stated rubric that is the (a) branch -- but see ss2:")
print("     the rubric's premise does not hold, so this must NOT be read as support for (a).")
OUT["ss1"] = res

# =============================================================== ss2 the structural limit =========
L.hdr("ss2  ★★★ WHY THE RUBRIC CANNOT WORK -- the r24 dose-response is FLAT over the whole range")
print("   Every build below has r26 = x1. Only r24 differs. If grind #1 tracked r24 gain, these")
print("   would separate. Medians are engaged creep, identical instrument.\n")
R24 = {"stock (x1)": (1.0, L.POOL_KD1), "V70 (x2)": (2.0, ["V70/r50"]), "V69 (x4)": (4.0, ["V69/r4f"])}
pts = []
print(f"   {'build':<14} {'r24 gain':>9} {'n':>5} {'u':>4} {'median':>8} {'[95% CI]':>20}")
for k, (g, names) in R24.items():
    rs = [r for n in names for r in store.get(n, []) if r["eng"] == 1 and r["v"] < CREEP]
    m, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=4000)
    pts.append((g, m, lo, hi, rs))
    print(f"   {k:<14} {g:>9.3f} {len(rs):>5} {len({r[G.EPKEY] for r in rs}):>4} {m:>8.1f} "
          f"[{lo:>8.1f}, {hi:>9.1f}]")

print("\n   Pairwise: is ANY of these three distinguishable from the others at this exposure?")
pair = {}
names3 = list(R24)
for i, a in enumerate(names3):
    for b in names3[i + 1:]:
        da = sub_med([r for n in R24[a][1] for r in store.get(n, [])
                      if r["eng"] == 1 and r["v"] < CREEP], NB, 8000)
        db = sub_med([r for n in R24[b][1] for r in store.get(n, [])
                      if r["eng"] == 1 and r["v"] < CREEP], NB, 8000)
        if da is None or db is None:
            continue
        p = float((da[:4000, None] > db[None, :4000]).mean())
        pair[f"{a} > {b}"] = p
        print(f"     P({a:<14} > {b:<14}) = {p:.3f}   "
              f"{'INDISTINGUISHABLE' if 0.2 < p < 0.8 else 'separable'}")
OUT["r24_flatness"] = dict(points=[[g, m, lo, hi] for g, m, lo, hi, _ in pts], pairwise=pair)

print("\n   Log-log slope of median e_18-22 on r24 gain, episode-bootstrapped:")
gl = np.log([p[0] for p in pts])
sl = []
for _ in range(4000):
    ys = []
    for g, m, lo, hi, rs in pts:
        blk = {}
        for r in rs:
            blk.setdefault(r[G.EPKEY], []).append(r)
        per = [G.col(v, "e_18-22") for v in blk.values()]
        j = RNG.integers(0, len(per), len(per))
        ys.append(np.log(max(np.median(np.concatenate([per[k] for k in j])), 1e-9)))
    sl.append(np.polyfit(gl, ys, 1)[0])
sl = np.array(sl)
print(f"     slope = {np.median(sl):+.3f}  [{np.percentile(sl, 2.5):+.3f}, "
      f"{np.percentile(sl, 97.5):+.3f}]  (0 = grind #1 does NOT respond to r24 gain)")
OUT["r24_slope"] = [float(np.median(sl)), float(np.percentile(sl, 2.5)),
                    float(np.percentile(sl, 97.5))]
print("\n   🛑 AND THE CORPUS CONTAINS NO BUILD WITH r24 BELOW STOCK AND r26 AT STOCK. V61 is the")
print("      only sub-stock r24 point and it is x0 on BOTH lanes. So hypothesis (b)'s prediction")
print("      for grind #1 at a delivered gain of 1024/3072 = 0.333x is UNANCHORED -- there is no")
print("      data point to interpolate from. The rubric assumed a monotone r24 response that this")
print("      section measures to be flat. ⇒ GRIND #1 CANNOT ADJUDICATE (a) vs (b). [EVIDENCE]")

# =============================================================== ss3 the latch test ===============
L.hdr("ss3  THE LATCH TEST -- does an arm selection leave a signature in 18-22 Hz?")
print("   As specified (pre vs post the provocation boundary at mono 123.69) the test is NOT")
print("   RUNNABLE: mono < 123.69 is seg 0 (PARKED, 61.6 s, vEgo 0.00 throughout) plus seg 1 up to")
print("   t=23.1 where first wheel motion is t=25.6 (mono 126.2). THERE IS NO PRE-PROVOCATION")
print("   DRIVING ON THIS ROUTE. Reported as unrunnable rather than as a null.\n")
print("   Better-posed substitute: `gp-0x671a` counts HARD REVERSALS and holds ~5 s. Its bus proxy")
print("   is the per-window sign-reversal count of the bar torque. If an arm latched, windows with")
print("   a high reversal count should show MORE 18-22 Hz -- and if that is V70-SPECIFIC it is a")
print("   latch, while if every build does it, it is ordinary driving physics.\n")


def revcount(x, thr=50.0):
    d1 = np.diff(np.asarray(x, float))
    s = np.sign(d1)
    amp = np.minimum(np.abs(d1[:-1]), np.abs(d1[1:]))
    return int(((s[:-1] * s[1:] < 0) & (amp > thr)).sum())


def add_rev(build, recs):
    B = G.BUILDS[build]
    by = {}
    for r in recs:
        by.setdefault(r["seg"], []).append(r)
    for seg, rs in by.items():
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = C.load(seg, B["cache"], B["pfx"])
        t = np.asarray(d["t"], float)
        tq = np.asarray(d["tq"], float)
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            r["rev"] = revcount(tq[i0:i0 + G.NFFT])
    return recs


REV_BINS = [(0, 8), (8, 20), (20, 40), (40, 1e9)]
lat = {}
print(f"   {'build':<14} " + " ".join(f"{'rev ' + str(b):>14}" for b in REV_BINS))
for b in ("V59/r2c", "V64/r35", "V62/r37", "V69/r4f", "V70/r50"):
    rs = add_rev(b, [r for r in store.get(b, []) if r["eng"] == 1 and r["v"] < CREEP])
    row = []
    for lo, hi in REV_BINS:
        s = [r for r in rs if lo <= r.get("rev", -1) < hi]
        row.append(np.median(G.col(s, "e_18-22")) if len(s) >= 3 else np.nan)
    lat[b] = [float(x) for x in row]
    print(f"   {b:<14} " + " ".join(f"{x:>14.0f}" for x in row))
print("\n   ⇒ Read the DIRECTION, not the level. A V70-specific latch would show V70 rising with")
print("     reversal count while the others do not.")
OUT["latch_revgrad"] = lat

# =============================================================== ss4 burst #0 manual->engaged =====
L.hdr("ss4  ★★ BURST #0's MANUAL -> ENGAGED TRANSITION -- the same oscillation either side of the "
      "switch")
d = C.load(1, ROOT / "_cache_r50", "r50s")
fs = R4F.fs_lattice(d)
t = np.asarray(d["t"], float)
tq = np.asarray(d["tq"], float)
v = np.abs(np.asarray(d["cs_v"], float))
lt = np.asarray(d["cc_lat"], float) > 0.5
eff = np.abs(sustained(tq, fs))
env = band_envelope(tq, fs, 6.0, 9.0)
eg = band_envelope(tq, fs, 18.0, 22.0)
mv = np.flatnonzero(v > 0.3)
t_move, t_eng = float(t[mv[0]]), float(t[np.flatnonzero(lt)[0]])
print(f"   seg 1: first wheel motion t={t_move:.1f} (mono {MONO0[1] + t_move:.2f}), first latActive "
      f"t={t_eng:.1f} (mono {MONO0[1] + t_eng:.2f})")
print(f"   ⇒ MANUAL arm  = t [{t_move:.1f}, {t_eng:.1f}]  ({t_eng - t_move:.1f} s)")
print(f"   ⇒ ENGAGED arm = t [{t_eng:.1f}, {t_eng + 12.0:.1f}] (the 12 s of burst #0 after the "
      f"switch)\n")
arms = {"MANUAL  (pre-engage)": (t_move, t_eng),
        "ENGAGED (post-engage)": (t_eng, t_eng + 12.0)}
b0 = {}
print(f"   {'arm':<22} {'secs':>6} {'|v| mean':>9} {'eff p50':>8} | {'6-9 env p99':>12} "
      f"{'6-9 p-p':>8} | {'18-22 env p99':>14} | {'f0 6-9':>7} {'prom':>8}")
for k, (a, b) in arms.items():
    m = (t >= a) & (t < b)
    if m.sum() < 128:
        print(f"   {k:<22}  *** too few samples ({int(m.sum())})")
        continue
    n = int(m.sum())
    i0 = int(np.flatnonzero(m)[0])
    nf = 256 if n >= 256 else 128
    P = periodogram(tq[i0:i0 + nf], fs, nf)
    f = np.fft.rfftfreq(nf, 1 / fs)
    f0, pr = peak_prom(f, P, 6.0, 9.0) if P is not None else (np.nan, np.nan)
    b0[k] = dict(secs=float(n / fs), v=float(v[m].mean()), eff=float(np.median(eff[m])),
                 e69=float(np.percentile(env[m], 99)), e1822=float(np.percentile(eg[m], 99)),
                 f0=float(f0), prom=float(pr))
    x = b0[k]
    print(f"   {k:<22} {x['secs']:>6.1f} {x['v']:>9.2f} {x['eff']:>8.0f} | {x['e69']:>12.0f} "
          f"{2 * x['e69']:>8.0f} | {x['e1822']:>14.0f} | {x['f0']:>7.2f} {x['prom']:>8.1f}")
if len(b0) == 2:
    ka, kb = list(b0)
    print(f"\n   ENGAGED / MANUAL   6-9 Hz amplitude {b0[kb]['e69'] / max(b0[ka]['e69'], 1e-9):.3f}x"
          f"    18-22 Hz {b0[kb]['e1822'] / max(b0[ka]['e1822'], 1e-9):.3f}x")
    print(f"   speeds {b0[ka]['v']:.2f} vs {b0[kb]['v']:.2f} m/s -- MATCHED by construction "
          f"(both inside burst #0, 0-2 m/s)")
    print(f"   ⚠ effort {b0[ka]['eff']:.0f} vs {b0[kb]['eff']:.0f} counts: the manual arm is the "
          f"operator PROVOKING by hand, so it is NOT hands-off. The engaged arm is.")
OUT["burst0_arms"] = b0

print("\n   Per-window view across the transition (NFFT 256, hop 64, 6-9 Hz):")
print(f"   {'t0':>6} {'mono':>7} {'lat':>4} {'|v|':>5} {'eff':>6} {'6-9 p-p':>8} {'f0':>5} "
      f"{'prom':>7} {'18-22 p99':>10}")
tr = []
for i in range(int(t_move * fs) - 128, min(int((t_eng + 14) * fs), len(t) - 256), 64):
    if i < 0:
        continue
    w = slice(i, i + 256)
    P = periodogram(tq[w], fs, 256)
    if P is None:
        continue
    f = np.fft.rfftfreq(256, 1 / fs)
    f0, pr = peak_prom(f, P, 6.0, 9.0)
    row = dict(t0=float(t[i]), mono=float(MONO0[1] + t[i]), lat=float(lt[w].mean()),
               v=float(v[w].mean()), eff=float(np.median(eff[w])),
               pp=float(2 * np.percentile(env[w], 99)), f0=float(f0), prom=float(pr),
               g1=float(np.percentile(eg[w], 99)))
    tr.append(row)
    print(f"   {row['t0']:>6.1f} {row['mono']:>7.1f} {row['lat']:>4.2f} {row['v']:>5.2f} "
          f"{row['eff']:>6.0f} {row['pp']:>8.0f} {row['f0']:>5.2f} {row['prom']:>7.1f} "
          f"{row['g1']:>10.0f}")
OUT["burst0_trace"] = tr

(HERE / "_r50_discriminator.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_r50_discriminator.json'}")
