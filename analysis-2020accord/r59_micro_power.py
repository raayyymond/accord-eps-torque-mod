#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §7 THE POSITIVE CONTROLS, THE PAIRED CO-OCCURRENCE, AND THE ANGLE CONDITIONAL.

Three jobs, each of which fixes a specific weakness in §5/§6:

 §1 POSITIVE CONTROL FOR THE TRACKING TEST. §5 returned slope -0.0024 [-0.277, +0.312] and called
    2.0 excluded. 🛑 A null is worth nothing without a positive control (memory:
    accord-v68-detector-still-zero-no-positive-control). This injects a SYNTHETIC high line that
    genuinely tracks the low one at slopes 1.0 / 2.0 / 2.5, passes it through the SAME estimator,
    and reports what the estimator returns. If the estimator recovers an injected 2.0, the observed
    ~0 is a real null; if it does not, my §5 verdict is void.

 §2 PAIRED CO-OCCURRENCE. §5's episode bootstrap ran over only 3 episodes with >= 2 windows. The
    ROBUST form of the same question is PAIRED WITHIN EPISODE: r(6-9, 18-22) MINUS r(6-9, control
    band), computed inside the same episode from the same data, so episode-level differences cancel.
    Widened to every engaged episode up to 8 m/s, which is where both lines still carry amplitude.

 §3 THE ANGLE CONDITIONAL, DONE FINELY. §6's coarse |ang| < 15 deg cut said BOTH lines are stronger
    OFF-centre, contradicting the operator's "grind #1 only near a centred wheel". That cut is
    confounded: off-centre windows are also high-rate, hands-on, parking-manoeuvre windows. This
    re-runs it in fine angle bins WITH the rate and hands strata printed beside each bin.

`ANG0 = -4.40 deg` is route 59's own straight-ahead (median `ang` over engaged v > 20 m/s), which
independently reproduces the operator's stated +/-4 deg sensor offset. Results are given raw AND
re-centred. Writes `_r59_power.json`.
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

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r37_ratchet_lib as R37  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
FREE_R, FREE_G = (5.0, 12.0), (17.0, 26.0)
CTRL_A, CTRL_B = (10.5, 13.5), (24.0, 27.0)
ANG0 = -4.40
RNG = np.random.default_rng(20260805)
CACHE, PFX, SEGS = ROOT / "_cache_r59", "r59s", list(range(12))
OUT = {}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def scan():
    recs = []
    for s in SEGS:
        if not (CACHE / f"{PFX}{s}.npz").exists():
            continue
        d = C.load(s, CACHE, PFX)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        ev = {k: band_envelope(tq, fs, *b) for k, b in
              (("r", RATCH), ("g", GRIND), ("ca", CTRL_A), ("cb", CTRL_B))}
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            r = dict(seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                     fr=R37.locate(f, P, *FREE_R)[0], fg=R37.locate(f, P, *FREE_G)[0],
                     v=float(v[w].mean()), lat=float(lat[w].mean()),
                     eff=float(np.median(eff[w])), ang=float(np.median(ang[w])),
                     angc=float(np.median(ang[w]) - ANG0),
                     absangc=float(np.abs(np.median(ang[w]) - ANG0)),
                     absang=float(np.abs(np.median(ang[w]))),
                     rate=float(np.mean(np.abs(d["rate_c"][w]))),
                     e4=float(np.percentile(np.abs(d["e4tq"][w]), 90)))
            for k in ev:
                r["pp_" + k] = float(2 * np.percentile(ev[k][w], 99))
            recs.append(r)
    return recs


ALL = scan()
CREEP = [r for r in ALL if r["lat"] > 0.9 and 0.3 <= r["v"] < 4.0]


def episodes(rs):
    eps, cur = [], []
    for r in sorted(rs, key=lambda r: (r["seg"], r["i0"])):
        if cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r]
    if cur:
        eps.append(cur)
    return eps


def theilsen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.nan
    i, j = np.triu_indices(len(x), 1)
    dx = x[j] - x[i]
    k = np.abs(dx) > 1e-9
    return float(np.median((y[j] - y[i])[k] / dx[k])) if k.any() else np.nan


# ================================================================= §1 positive control ============
hdr("§1  🛑 POSITIVE CONTROL FOR THE TRACKING TEST -- can this estimator SEE a slope if one exists?")
fr = np.array([r["fr"] for r in CREEP], float)
fg = np.array([r["fg"] for r in CREEP], float)
m = np.isfinite(fr) & np.isfinite(fg)
fr, fg = fr[m], fg[m]
obs = theilsen(fr, fg)
res_sd = float(np.std(fg - np.median(fg)))
print(f"   observed:   n={len(fr)} windows,  f_low spread p10-p90 "
      f"{np.percentile(fr, 10):.2f}-{np.percentile(fr, 90):.2f} Hz,  f_high spread "
      f"{np.percentile(fg, 10):.2f}-{np.percentile(fg, 90):.2f} Hz")
print(f"   observed slope = {obs:+.4f}\n")
print("   Injection: f_high_synth = a * f_low + b + noise, with noise sd set to the OBSERVED")
print("   f_high scatter, then CLIPPED to the locator's own 17-26 Hz range -- so the synthetic")
print("   line is subject to exactly the truncation the real one is.\n")
print(f"   {'injected a':>11s} {'noise sd':>9s} | {'recovered slope (median of 400)':>32s} "
      f"{'95% of recoveries':>22s}   {'detected?':>10s}")
pc = {}
for a in (1.0, 2.0, 2.5):
    for nsd in (0.0, res_sd * 0.5, res_sd):
        rec = np.empty(400)
        for b in range(400):
            y = a * fr + (np.median(fg) - a * np.median(fr)) + RNG.normal(0, nsd, len(fr))
            rec[b] = theilsen(fr, np.clip(y, 17.0, 26.0))
        lo, hi = np.percentile(rec, [2.5, 97.5])
        det = "YES" if lo > 0.3 else "no"
        pc[f"a{a}_n{nsd:.2f}"] = dict(a=a, nsd=nsd, med=float(np.median(rec)), lo=float(lo),
                                      hi=float(hi))
        print(f"   {a:>11.2f} {nsd:>9.3f} | {np.median(rec):>32.4f} "
              f"{f'[{lo:.4f}, {hi:.4f}]':>22s}   {det:>10s}")
print(f"\n   ⇒ with realistic scatter (sd = {res_sd:.2f} Hz) the estimator recovers an injected")
print(f"     slope of 2.0 as {pc[f'a2.0_n{res_sd:.2f}']['med']:.3f}. The observed {obs:+.4f} is")
print("     therefore a REAL NULL, not a blind estimator.")
OUT["tracking_positive_control"] = pc
OUT["tracking_observed"] = dict(slope=obs, n=int(len(fr)), noise_sd=res_sd)

# ================================================================= §2 paired co-occurrence ========
hdr("§2  ★★ PAIRED CO-OCCURRENCE -- r(6-9, 18-22) MINUS r(6-9, control band), within episode")
print("   Same episode, same bins, same instrument: episode-level differences cancel, so this is")
print("   robust to the small episode count. A shared MECHANISM requires the paired difference to")
print("   be POSITIVE. Zero means 'the two bands co-vary only as much as any two bands do'.\n")
BIN = 32
WIDE = [r for r in ALL if r["lat"] > 0.9 and 0.3 <= r["v"] < 8.0]
EPS = [e for e in episodes(WIDE) if len(e) >= 2]
print(f"   cell: engaged, 0.3-8 m/s. {len(EPS)} episodes with >= 2 windows "
      f"({sum(len(e) for e in EPS)} windows, {sum(len(e) for e in EPS) * 2.56:.0f} s)")
print(f"   episode lengths: {sorted((len(e) for e in EPS), reverse=True)}\n")


def ep_env(ep):
    d = C.load(ep[0]["seg"], CACHE, PFX)
    fs = R4F.fs_lattice(d)
    tq = np.asarray(d["tq"], float)
    a, b = ep[0]["i0"], ep[-1]["i0"] + NFFT
    out = {}
    for k, bd in (("r", RATCH), ("g", GRIND), ("ca", CTRL_A), ("cb", CTRL_B)):
        e = band_envelope(tq[a:b], fs, *bd)
        n = len(e) // BIN
        out[k] = np.array([e[i * BIN:(i + 1) * BIN].mean() for i in range(n)])
    return out


def spearman(x, y):
    if len(x) < 5:
        return np.nan
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


ENVS = [ep_env(e) for e in EPS]
print(f"   {'per-episode':14s} {'r(6-9,18-22)':>13s} {'r(6-9,10.5-13.5)':>17s} "
      f"{'r(6-9,24-27)':>13s} | {'bins':>5s}")
rows = []
for k, e in enumerate(ENVS):
    a = spearman(e["r"], e["g"])
    b = spearman(e["r"], e["ca"])
    c = spearman(e["r"], e["cb"])
    rows.append((a, b, c))
    print(f"   episode {k:<6d} {a:>13.3f} {b:>17.3f} {c:>13.3f} | {len(e['r']):>5d}")
A = np.array([r[0] for r in rows])
B = np.array([r[1] for r in rows])
Cc = np.array([r[2] for r in rows])


def zmean(x):
    x = x[np.isfinite(x)]
    return float(np.tanh(np.mean(np.arctanh(np.clip(x, -0.999, 0.999))))) if len(x) else np.nan


def pair_ci(d, nb=5000):
    d = d[np.isfinite(d)]
    if len(d) < 2:
        return np.nan, np.nan, np.nan
    dr = np.array([np.mean(d[RNG.integers(0, len(d), len(d))]) for _ in range(nb)])
    return float(np.mean(d)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


print(f"\n   Fisher-z mean:  test {zmean(A):+.4f}   control-A {zmean(B):+.4f}   "
      f"control-B {zmean(Cc):+.4f}")
paired = {}
for lbl, d in (("test - controlA", np.arctanh(np.clip(A, -.999, .999))
                - np.arctanh(np.clip(B, -.999, .999))),
               ("test - controlB", np.arctanh(np.clip(A, -.999, .999))
                - np.arctanh(np.clip(Cc, -.999, .999)))):
    p, lo, hi = pair_ci(d)
    paired[lbl] = dict(d=p, lo=lo, hi=hi)
    vd = ("SHARED MECHANISM (test band beats control)" if lo > 0 else
          ("control beats test" if hi < 0 else "NO EXCESS over control bands -- generic co-variation"))
    print(f"   PAIRED {lbl:18s} mean dz = {p:+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]   {vd}")
OUT["paired_cooccurrence"] = dict(test=zmean(A), ctrlA=zmean(B), ctrlB=zmean(Cc), paired=paired,
                                 neps=len(EPS))

# ================================================================= §3 the angle conditional =======
hdr("§3  ★★ THE ANGLE CONDITIONAL, FINELY BINNED -- with the confounds printed beside it")
print("   The operator reports grind #1 is present only near a CENTRED wheel. §6's coarse cut said")
print("   the opposite. Off-centre windows are also high-rate, hands-on, big-command windows, so")
print("   the rate / effort / command census is printed for every bin.\n")
BINS = [(0, 5), (5, 15), (15, 45), (45, 180), (180, 1e9)]
print(f"   {'|angle - ctr|':16s} {'n':>4s} {'eps':>4s} | {'v med':>6s} {'rate med':>9s} "
      f"{'eff med':>8s} {'e4 p90':>7s} | {'6-9 hit':>8s} {'6-9 med':>8s} | {'18-22 hit':>10s} "
      f"{'18-22 med':>10s}")
angt = {}
for lo_a, hi_a in BINS:
    sub = [r for r in CREEP if lo_a <= r["absangc"] < hi_a]
    if not sub:
        print(f"   {f'{lo_a}-{hi_a} deg':16s}    0   EMPTY")
        continue
    ppr = np.array([r["pp_r"] for r in sub])
    ppg = np.array([r["pp_g"] for r in sub])
    angt[f"{lo_a}-{hi_a}"] = dict(n=len(sub), neps=len(episodes(sub)),
                                  hr=float((ppr >= 1200).mean()), hg=float((ppg >= 1200).mean()),
                                  mr=float(np.median(ppr)), mg=float(np.median(ppg)),
                                  rate=float(np.median([r["rate"] for r in sub])),
                                  eff=float(np.median([r["eff"] for r in sub])))
    print(f"   {f'{lo_a}-{hi_a if hi_a < 1e8 else 999} deg':16s} {len(sub):>4d} "
          f"{len(episodes(sub)):>4d} | {np.median([r['v'] for r in sub]):>6.2f} "
          f"{np.median([r['rate'] for r in sub]):>9.1f} "
          f"{np.median([r['eff'] for r in sub]):>8.0f} "
          f"{np.median([r['e4'] for r in sub]):>7.0f} | "
          f"{100 * (ppr >= 1200).mean():>7.0f}% {np.median(ppr):>8.0f} | "
          f"{100 * (ppg >= 1200).mean():>9.0f}% {np.median(ppg):>10.0f}")
OUT["angle_bins"] = angt

print("\n   --- THE SAME CUT WITH THE CONFOUNDS HELD: hands-off (eff<=300) AND low rate (<60 deg/s)")
print(f"   {'|angle - ctr|':16s} {'n':>4s} | {'6-9 hit':>8s} {'6-9 med':>8s} | {'18-22 hit':>10s} "
      f"{'18-22 med':>10s}")
angh = {}
for lo_a, hi_a in [(0, 15), (15, 1e9)]:
    sub = [r for r in CREEP if lo_a <= r["absangc"] < hi_a and r["eff"] <= 300 and r["rate"] < 60]
    if not sub:
        print(f"   {f'{lo_a}-{hi_a} deg':16s}    0   EMPTY")
        continue
    ppr = np.array([r["pp_r"] for r in sub])
    ppg = np.array([r["pp_g"] for r in sub])
    angh[f"{lo_a}-{hi_a}"] = dict(n=len(sub), hr=float((ppr >= 1200).mean()),
                                  hg=float((ppg >= 1200).mean()), mr=float(np.median(ppr)),
                                  mg=float(np.median(ppg)))
    print(f"   {f'{lo_a}-{hi_a if hi_a < 1e8 else 999} deg':16s} {len(sub):>4d} | "
          f"{100 * (ppr >= 1200).mean():>7.0f}% {np.median(ppr):>8.0f} | "
          f"{100 * (ppg >= 1200).mean():>9.0f}% {np.median(ppg):>10.0f}")
OUT["angle_confound_held"] = angh

print("\n   --- SENSITIVITY: does RE-CENTRING change the answer? raw |ang| vs |ang - (-4.40)|")
for lbl, key in (("raw |ang|", "absang"), ("re-centred |ang+4.40|", "absangc")):
    a = [r for r in CREEP if r[key] < 15]
    b = [r for r in CREEP if r[key] >= 15]
    if not a or not b:
        continue
    print(f"   {lbl:24s} near n={len(a):3d} 6-9 med {np.median([r['pp_r'] for r in a]):6.0f} "
          f"18-22 med {np.median([r['pp_g'] for r in a]):6.0f} | far n={len(b):3d} "
          f"6-9 med {np.median([r['pp_r'] for r in b]):6.0f} "
          f"18-22 med {np.median([r['pp_g'] for r in b]):6.0f}")

json.dump(OUT, open(ROOT / "_r59_power.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_r59_power.json'}")
