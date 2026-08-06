#!/usr/bin/env python3
"""Route 5a, final pass: the DECISIVE regime check, e4tq/tq coherence, and PRIORITY 3 localisation.

WHY THIS FILE EXISTS. Stage 3 matched the rail-vs-just-below contrast and found only FOUR surviving
cells -- and every one of them is at |angle| > 20 deg. That is because the +-4096 rail regime is a
BIG-TURN regime (median |angle| 88.5 deg, |rate| 35 deg/s), not the operator's stated grind-#1 regime
(5 mph, angle near zero). So the matched contrast answers a question about big turns. The question
that actually decides the saturation hypothesis is:

    ★ IN THE OPERATOR'S OWN GRIND-#1 REGIME -- engaged, creep, |angle| < 3 deg -- how big is the
      command during bursts, as a fraction of the rail?

If it is a small fraction, saturation cannot be the driver THERE, whatever happens in big turns.

Also here:
  · COHERENCE between openpilot's request and the bar at 18-22 Hz. Stage 3's Q3 found e4tq carries
    an 18-22 Hz line at 14.9x its own 24-28 Hz control band -- weaker than the bar's 160.7x but not
    nothing. Coherence + the in-burst/out-burst contrast says whether that is real coupling or the
    ~88 Hz zero-order hold's broadband residue.
  · PRIORITY 3: is 18-22 Hz maximal near 2.2 m/s and |angle| < 3 deg? is 6-9 Hz flat across speed?
    Both as tables with a PER-BIN EXPOSURE CENSUS. 🛑 "EMPTY" IS NOT "NULL".
  · LEVER D at creep with RELAXED cell thresholds (the strict ones leave 1 shared cell), null
    recomputed at the SAME relaxed thresholds.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5a_lib as L  # noqa: E402
from r5a_rail import CREEP, MIN_CYC, RAIL, THR, bursts, frames  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(99)
out = {}
F = frames()
minlen = int(round(MIN_CYC / 20.0 * 100))
sel = (F["v"] >= CREEP[0]) & (F["v"] < CREEP[1]) & F["eng"]
IV = [(a, b) for a, b in bursts(F, THR, minlen) if sel[a:b].mean() > 0.8]
inb = np.zeros(len(F["t"]), bool)
for a, b in IV:
    inb[a:b] = True

# ------------------------------------------------------------------ THE DECISIVE CHECK -----------
L.hdr("★ THE DECISIVE CHECK -- the command size in the OPERATOR'S OWN grind-#1 regime")
print("regime: engaged, 0.5 <= v < 4 m/s, |steering angle| < 3 deg  (the operator's '5 mph, angle")
print("near zero'). If saturation drove grind #1, the command must be at or near 4096 HERE.\n")
for alo, ahi, lab in ((0, 3, "|ang| < 3 deg   <-- THE OPERATOR'S REGIME"), (3, 8, "|ang| 3-8"),
                      (8, 20, "|ang| 8-20"), (20, 1e9, "|ang| > 20 deg")):
    m = sel & (F["aang"] >= alo) & (F["aang"] < ahi)
    mi = m & inb
    if m.sum() < 50:
        print(f"  {lab:38s} UNPOWERED ({int(m.sum())} frames)")
        continue
    print(f"  {lab:38s} exposure {m.sum() / 100:6.1f} s  duty {inb[m].mean() * 100:5.2f}%  "
          f"in-burst {mi.sum() / 100:5.2f} s")
    if mi.sum() >= 20:
        a = F["ae4"][mi]
        print(f"     IN-BURST |e4tq|: p50 {np.percentile(a, 50):6.0f} "
              f"({np.percentile(a, 50) / RAIL * 100:5.1f}% of rail)  "
              f"p90 {np.percentile(a, 90):6.0f}  max {a.max():6.0f}  "
              f"AT RAIL {np.mean(a >= RAIL - .5) * 100:6.2f}%  "
              f">=0.5R {np.mean(a >= .5 * RAIL) * 100:6.2f}%")
        out.setdefault("regime", {})[lab.split()[1]] = dict(
            exposure_s=float(m.sum() / 100), duty=float(inb[m].mean()),
            p50=float(np.percentile(a, 50)), at_rail=float(np.mean(a >= RAIL - .5)))
    else:
        print(f"     IN-BURST |e4tq|: UNPOWERED ({int(mi.sum())} in-burst frames)")

# burst-level view, which is what the operator actually feels
print("\nburst-by-burst in the near-zero-angle regime (each burst = one event):")
print(f"  {'#':>3s} {'t (s)':>9s} {'seg':>4s} {'v':>6s} {'|ang|':>7s} {'dur s':>7s} "
      f"{'peak A':>8s} {'med|e4tq|':>10s} {'% of rail':>10s}")
nz = []
for i, (a, b) in enumerate(IV):
    if F["aang"][a:b].mean() >= 3.0 or F["v"][a:b].mean() >= 4.0:
        continue
    md = float(np.median(F["ae4"][a:b]))
    nz.append(md)
    print(f"  {len(nz):3d} {F['t'][a]:9.2f} {int(F['seg'][a]):4d} {F['v'][a:b].mean():6.2f} "
          f"{F['aang'][a:b].mean():7.2f} {(b - a) / 100:7.2f} {F['env'][a:b].max():8.0f} "
          f"{md:10.0f} {md / RAIL * 100:9.1f}%")
if nz:
    print(f"\n  ⇒ {len(nz)} near-zero-angle creep bursts; median command "
          f"{np.median(nz):.0f} counts = {np.median(nz) / RAIL * 100:.1f}% of the +-4096 rail; "
          f"max {max(nz):.0f}")
    out["regime_nz"] = dict(n=len(nz), med=float(np.median(nz)), mx=float(max(nz)))

# ------------------------------------------------------------------ coherence --------------------
L.hdr("COHERENCE: openpilot's request vs the bar at 18-22 Hz -- real coupling or hold residue?")
f = np.fft.rfftfreq(256, 1 / 100.0)
bm = (f >= 18) & (f <= 22)
cm = (f >= 24) & (f <= 28)


def spec(idx, chan):
    x = F[chan][idx:idx + 256]
    return np.fft.rfft((x - np.polyval(np.polyfit(np.arange(256), x, 1), np.arange(256)))
                       * np.hanning(256))


def coh_over(starts):
    Sxx = Syy = 0.0
    Sxy = 0j
    n = 0
    for i in starts:
        if i < 0 or i + 256 > len(F["t"]):
            continue
        if len(set(F["run"][i:i + 256].astype(int))) != 1:
            continue
        X, Y = spec(i, "e4"), spec(i, "tq")
        Sxx = Sxx + np.abs(X) ** 2
        Syy = Syy + np.abs(Y) ** 2
        Sxy = Sxy + X * np.conj(Y)
        n += 1
    if n < 6:
        return None, n
    return np.abs(Sxy) ** 2 / (Sxx * Syy), n


st_in = [(a + b) // 2 - 128 for a, b in IV]
selidx = np.flatnonzero(sel & ~inb)
st_out = [int(i) for i in selidx[::128]]
for st, lab in ((st_in, "IN-BURST"), (st_out, "OUT-BURST (engaged creep)")):
    Cxy, n = coh_over(st)
    if Cxy is None:
        print(f"  {lab:28s} UNPOWERED ({n} windows)")
        continue
    print(f"  {lab:28s} n={n:4d}  coherence 18-22 Hz {Cxy[bm].mean():.3f}   "
          f"24-28 Hz control {Cxy[cm].mean():.3f}")
    out.setdefault("coh", {})[lab] = [float(Cxy[bm].mean()), float(Cxy[cm].mean()), n]
print("\n  🛑 With n windows, the coherence of INDEPENDENT signals is ~1/n, not 0. Compare the")
print("     18-22 Hz value against the 24-28 Hz control in the SAME estimate, never against 0.")

# also: is e4tq's own 18-22 line ELEVATED in bursts, or always there?
print("\n  e4tq 18-22 Hz band power, in-burst vs matched out-of-burst (engaged creep):")
for st, lab in ((st_in, "IN-BURST"), (st_out, "OUT-BURST")):
    v = []
    for i in st:
        if i < 0 or i + 256 > len(F["t"]):
            continue
        if len(set(F["run"][i:i + 256].astype(int))) != 1:
            continue
        P = C.periodogram(F["e4"][i:i + 256], 100.0, 256, True)
        v.append(P[bm].sum() / max(P[cm].sum(), 1e-12))
    if len(v) >= 6:
        print(f"     {lab:12s} n={len(v):4d}  median (P18-22/P24-28) = {np.median(v):8.3f}")

# ------------------------------------------------------------------ PRIORITY 3 -------------------
L.hdr("PRIORITY 3a. IS 18-22 Hz MAXIMAL NEAR 2.2 m/s (5 mph)?  engaged, with exposure census")
R = L.records()
v73 = [r for r in R["V73/r5a"] if r["seg"] != 17]
VB = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0), (3.0, 4.0),
      (4.0, 6.0), (6.0, 8.0), (8.0, 12.0), (12.0, 18.0), (18.0, 1e9)]
print(f"{'v bin m/s':>12s} {'n win':>6s} {'expo s':>7s} {'ep':>4s} {'18-22 med':>10s} "
      f"{'[95% CI]':>20s} {'6-9 med':>9s} {'24-28 med':>10s} {'wheel ord Hz':>13s}")
p3a = []
for lo, hi in VB:
    rs = [r for r in v73 if r["eng"] == 1 and lo <= r["v"] < hi]
    if len(rs) < 6:
        print(f"{lo:5.1f}-{hi if hi < 1e8 else 99:<6.1f} {len(rs):6d} {len(rs) * 1.28:7.1f} "
              f"{len({r['ep'] for r in rs}):4d}   UNPOWERED (<6 windows) -- exposure, not a null")
        continue
    p, cl, ch = G.boot_median_ci(rs, "e_18-22", RNG, nboot=1000)
    m69 = np.median([r["e_6-9"] for r in rs])
    m24 = np.median([r["e_24-28"] for r in rs])
    wo = np.median([r["v"] for r in rs]) / L.CIRC
    print(f"{lo:5.1f}-{hi if hi < 1e8 else 99:<6.1f} {len(rs):6d} {len(rs) * 1.28:7.1f} "
          f"{len({r['ep'] for r in rs}):4d} {p:10.1f} [{cl:8.1f},{ch:8.1f}] {m69:9.1f} "
          f"{m24:10.1f} {wo:13.2f}")
    p3a.append((lo, hi, len(rs), p, cl, ch, m69, m24))
out["p3a"] = p3a
if p3a:
    j = int(np.argmax([r[3] for r in p3a]))
    print(f"\n  ⇒ 18-22 Hz PEAKS in the {p3a[j][0]}-{p3a[j][1]} m/s bin at {p3a[j][3]:.1f}")
    k69 = [r[6] for r in p3a]
    print(f"  ⇒ 6-9 Hz across the same bins: min {min(k69):.1f} max {max(k69):.1f} "
          f"= {max(k69) / max(min(k69), 1e-9):.2f}x spread "
          f"({'NOT flat' if max(k69) / max(min(k69), 1e-9) > 3 else 'roughly flat'})")

L.hdr("PRIORITY 3b. IS 18-22 Hz MAXIMAL AT |ANGLE| < 3 deg?  engaged CREEP, with exposure")
AB = [(0, 1), (1, 3), (3, 6), (6, 12), (12, 30), (30, 1e9)]
print(f"{'|ang| deg':>12s} {'n win':>6s} {'expo s':>7s} {'ep':>4s} {'18-22 med':>10s} "
      f"{'[95% CI]':>20s} {'6-9 med':>9s} {'24-28 med':>10s}")
p3b = []
for lo, hi in AB:
    rs = [r for r in v73 if r["eng"] == 1 and CREEP[0] <= r["v"] < CREEP[1] and lo <= r["ang"] < hi]
    if len(rs) < 6:
        print(f"{lo:5.0f}-{hi if hi < 1e8 else 999:<6.0f} {len(rs):6d} {len(rs) * 1.28:7.1f} "
              f"{len({r['ep'] for r in rs}):4d}   UNPOWERED (<6 windows) -- exposure, not a null")
        p3b.append((lo, hi, len(rs), None, None, None, None, None))
        continue
    p, cl, ch = G.boot_median_ci(rs, "e_18-22", RNG, nboot=1000)
    print(f"{lo:5.0f}-{hi if hi < 1e8 else 999:<6.0f} {len(rs):6d} {len(rs) * 1.28:7.1f} "
          f"{len({r['ep'] for r in rs}):4d} {p:10.1f} [{cl:8.1f},{ch:8.1f}] "
          f"{np.median([r['e_6-9'] for r in rs]):9.1f} "
          f"{np.median([r['e_24-28'] for r in rs]):10.1f}")
    p3b.append((lo, hi, len(rs), p, cl, ch, float(np.median([r["e_6-9"] for r in rs])),
                float(np.median([r["e_24-28"] for r in rs]))))
out["p3b"] = p3b

L.hdr("PRIORITY 3c. IS 6-9 Hz FLAT ACROSS SPEED?  engaged, all speeds, with exposure")
print(f"{'v bin m/s':>12s} {'n win':>6s} {'expo s':>7s} {'6-9 med':>9s} {'[95% CI]':>20s} "
      f"{'ratio to 24-28':>15s}")
p3c = []
for lo, hi in VB:
    rs = [r for r in v73 if r["eng"] == 1 and lo <= r["v"] < hi]
    if len(rs) < 6:
        print(f"{lo:5.1f}-{hi if hi < 1e8 else 99:<6.1f} {len(rs):6d} {len(rs) * 1.28:7.1f}   "
              f"UNPOWERED -- exposure, not a null")
        continue
    p, cl, ch = G.boot_median_ci(rs, "e_6-9", RNG, nboot=1000)
    m24 = np.median([r["e_24-28"] for r in rs])
    print(f"{lo:5.1f}-{hi if hi < 1e8 else 99:<6.1f} {len(rs):6d} {len(rs) * 1.28:7.1f} "
          f"{p:9.1f} [{cl:8.1f},{ch:8.1f}] {p / max(m24, 1e-9):15.2f}")
    p3c.append((lo, hi, len(rs), p, cl, ch, float(m24)))
out["p3c"] = p3c

# ------------------------------------------------------------------ LEVER D, relaxed -------------
L.hdr("LEVER D at CREEP -- RELAXED cell thresholds (strict left 1 shared cell), null at the SAME")
v72 = R["V72/r59"]
for lab, kw in (("engaged CREEP 0.5-4", dict(creep=True)),
                ("engaged CREEP, |ang|<6", dict(creep=True, angmax=6.0)),
                ("engaged ALL speed", dict())):
    def s(rs):
        o = [r for r in rs if r["eng"] == 1]
        if kw.get("creep"):
            o = [r for r in o if CREEP[0] <= r["v"] < CREEP[1]]
        if kw.get("angmax"):
            o = [r for r in o if r["ang"] < kw["angmax"]]
        return o
    a, b = s(v73), s(v72)
    print(f"\n  {lab}:  V73 n={len(a)} ({len({r['ep'] for r in a})} ep)   "
          f"V72 n={len(b)} ({len({r['ep'] for r in b})} ep)")
    if len(a) < 10 or len(b) < 10:
        print("     UNPOWERED -- exposure, not a null")
        continue
    for k, kl in (("e_18-22", "GRIND #1 18-22"), ("e_6-9", "RATCHET 6-9"),
                  ("e_24-28", "CONTROL 24-28")):
        pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(a, b, k, RNG, nboot=1000,
                                                         min_ep=1, min_win=2)
        _, nlo, nhi = G.split_half_null(b, k, RNG, nrep=200, min_ep=1, min_win=2)
        if not np.isfinite(pt):
            print(f"     {kl:16s} no shared cell -- UNPOWERED")
            continue
        cl = "CLEARS" if (lo > nhi or hi < nlo) else "inside null"
        print(f"     {kl:16s} V73/V72 {pt:6.3f} [{lo:6.3f}, {hi:6.3f}]  "
              f"null [{nlo:6.3f}, {nhi:6.3f}]  {nc:2d} cells   {cl}")
        out.setdefault("leverD_relaxed", {})[f"{lab}|{k}"] = [pt, lo, hi, nlo, nhi, nc, cl]

with open(ROOT / "_r5a_final.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _r5a_final.json")
