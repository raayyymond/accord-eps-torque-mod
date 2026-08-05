#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §6 THE CONDITIONALS, AND THE ALTERNATIVES RULED IN OR OUT.

Three alternatives must be killed before either line is called a firmware effect:
  A. WHEEL ORDER -- a rotating-component line whose frequency tracks vEgo. 🛑 This kit has twice
     mistaken one for a firmware effect ("the 8.69 Hz line V56 introduced" was 0.489*v). Wheel
     order 1 = v / 2.073-2.088 m, so it SWEEPS THROUGH 6-9 Hz at 12.4-18.8 m/s -- route 59 has
     209.9 s of engaged driving in exactly that band. This is not a hypothetical risk here.
  B. ENGINE ORDER -- f = n * rpm / 60. At the 820 rpm creep idle, half-order is 6.83 Hz, which is
     within a bin and a half of the observed 7.7 Hz line. Vetoed with the cache's `rpm` channel.
  C. MOTOR / ROTOR RATE -- torque ripple and cogging scale with STEERING rate, not road speed.

Each is a TRACKING claim, so each gets a SLOPE and a SHUFFLED CONTROL, never a ratio
(memory: feedback-a-ratio-is-not-a-tracking-test). Every CI resamples EPISODES.

🛑 MATCHED SPEED: every conditional table carries a per-cell speed census, because a moving wheel
order concentrates in a narrow-speed cell and smears in a wide one, manufacturing a fake conditional
(memory: accord-averaged-spectrum-needs-matched-speed-distributions).

Writes `_r59_alternatives.json`.
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
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
FREE_R, FREE_G = (5.0, 12.0), (17.0, 26.0)
LOW = (1.0, 4.0)                # the "heaviness" band -- what a mechanically heavy ratchet loads
CREEP, VMIN = 4.0, 0.3
ANG0 = -4.40
CIRC_LO, CIRC_HI = 2.073, 2.088
RNG = np.random.default_rng(20260805)
CACHE, PFX, SEGS = ROOT / "_cache_r59", "r59s", list(range(12))
OUT = {}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def scan():
    recs = []
    for s in SEGS:
        p = CACHE / f"{PFX}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, CACHE, PFX)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        ev = {k: band_envelope(tq, fs, *b) for k, b in
              (("r", RATCH), ("g", GRIND), ("lo", LOW))}
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = R37.locate(f, P, *FREE_R)
            fg, pg = R37.locate(f, P, *FREE_G)
            r = dict(seg=int(s), i0=i, t0=float(t[i]), fs=fs, fr=fr, pr=pr, fg=fg, pg=pg,
                     v=float(v[w].mean()), lat=float(lat[w].mean()),
                     eff=float(np.median(eff[w])), ang=float(np.median(ang[w])),
                     absangc=float(np.median(np.abs(ang[w] - ANG0))),
                     rate=float(np.mean(np.abs(d["rate_c"][w]))),
                     rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                     rpm=float(np.nanmean(d["rpm"][w])),
                     e4=float(np.percentile(np.abs(d["e4tq"][w]), 90)))
            for k in ev:
                r["pp_" + k] = float(2 * np.percentile(ev[k][w], 99))
            recs.append(r)
    return recs


ALL = scan()


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


def slope_ci(rs, xk, yk, nb=3000):
    eps = episodes(rs)
    pt = theilsen([r[xk] for r in rs], [r[yk] for r in rs])
    dr = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        w = [r for j in k for r in eps[j]]
        dr[b] = theilsen([r[xk] for r in w], [r[yk] for r in w])
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def shuffle_slope(rs, xk, yk, nb=2000):
    x = np.array([r[xk] for r in rs], float)
    y = np.array([r[yk] for r in rs], float)
    dr = np.empty(nb)
    for b in range(nb):
        dr[b] = theilsen(x, y[RNG.permutation(len(y))])
    return float(np.nanmedian(dr)), float(np.nanpercentile(dr, 2.5)), \
        float(np.nanpercentile(dr, 97.5))


# ================================================================= §1 the order tests =============
hdr("§1  ★★ THE ORDER TESTS -- does either line's FREQUENCY track road speed, engine rpm, or "
    "steering rate?")
print(f"   Wheel order 1 = {1 / CIRC_HI:.4f}-{1 / CIRC_LO:.4f} Hz per m/s; order 2 is twice that.")
print("   Engine order n = n/60 Hz per rpm: order 0.5 = 0.00833, order 1 = 0.01667, order 2 = 0.0333.")
print("   Every slope carries its SHUFFLED control -- a slope that survives shuffling is not a")
print("   tracking result.\n")
ENGD = [r for r in ALL if r["lat"] > 0.9]          # engaged, ALL speeds -- the order test needs range
print(f"   engaged windows, all speeds: n={len(ENGD)}, {len(episodes(ENGD))} episodes, "
      f"v {min(r['v'] for r in ENGD):.1f}-{max(r['v'] for r in ENGD):.1f} m/s, "
      f"rpm {min(r['rpm'] for r in ENGD):.0f}-{max(r['rpm'] for r in ENGD):.0f}\n")
print(f"   {'line':22s} {'vs':10s} {'slope':>12s} {'95% CI':>24s} {'shuffled':>22s}   verdict")
ordt = {}
TARGETS = [("v", "road speed", 1 / CIRC_LO, "wheel order 1"),
           ("rpm", "engine rpm", 1 / 60.0, "engine order 1"),
           ("rate", "steer rate", np.nan, "rotor-rate lock")]
for lk, lbl, yk in (("fr", "LOW  line (5-12)", "fr"), ("fg", "HIGH line (17-26)", "fg")):
    for xk, xl, expect, ename in TARGETS:
        # amplitude gate: only windows where the line is actually present
        sub = [r for r in ENGD if r["pp_" + ("r" if lk == "fr" else "g")] >= 600
               and np.isfinite(r[yk])]
        if len(sub) < 6:
            print(f"   {lbl:22s} {xl:10s}   n={len(sub)} -- UNDERPOWERED")
            continue
        pt, lo, hi = slope_ci(sub, xk, yk)
        sm, slo, shi = shuffle_slope(sub, xk, yk)
        ordt[f"{lk}|{xk}"] = dict(slope=pt, lo=lo, hi=hi, sh=sm, shlo=slo, shhi=shi, n=len(sub),
                                  expect=expect)
        if np.isfinite(expect):
            vd = (f"{ename} EXCLUDED" if not (lo <= expect <= hi) else f"{ename} COMPATIBLE")
            for mult in (0.5, 2, 3):
                if lo <= expect * mult <= hi:
                    vd += f" / order {mult} compatible"
        else:
            vd = "no lock" if lo <= 0 <= hi else "TRACKS"
        print(f"   {lbl:22s} {xl:10s} {pt:>+12.5f} {f'[{lo:+.5f}, {hi:+.5f}]':>24s} "
              f"{f'{sm:+.5f}':>22s}   {vd}  (n={len(sub)})")
OUT["orders"] = ordt

print("\n   --- THE DIRECT WHEEL-ORDER CHECK: where SHOULD wheel order 1 sit, per speed cell,")
print("       and is a line actually there?")
print(f"   {'speed cell':14s} {'n':>4s} | {'wheel-1 Hz':>11s} {'wheel-2 Hz':>11s} | "
      f"{'LOW f0 med':>11s} {'HIGH f0 med':>12s} | {'6-9 pp':>8s} {'18-22 pp':>9s}")
VB = [(0.3, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 30)]
wo = {}
for lo_v, hi_v in VB:
    sub = [r for r in ENGD if lo_v <= r["v"] < hi_v]
    if not sub:
        continue
    vm = float(np.median([r["v"] for r in sub]))
    fr = np.array([r["fr"] for r in sub]); fr = fr[np.isfinite(fr)]
    fg = np.array([r["fg"] for r in sub]); fg = fg[np.isfinite(fg)]
    wo[f"{lo_v}-{hi_v}"] = dict(n=len(sub), v=vm, w1=vm / CIRC_LO,
                                fr=float(np.median(fr)) if len(fr) else np.nan,
                                fg=float(np.median(fg)) if len(fg) else np.nan,
                                ppr=float(np.median([r["pp_r"] for r in sub])),
                                ppg=float(np.median([r["pp_g"] for r in sub])))
    x = wo[f"{lo_v}-{hi_v}"]
    print(f"   {f'{lo_v}-{hi_v} m/s':14s} {len(sub):>4d} | {vm / CIRC_LO:>11.2f} "
          f"{2 * vm / CIRC_LO:>11.2f} | {x['fr']:>11.2f} {x['fg']:>12.2f} | "
          f"{x['ppr']:>8.0f} {x['ppg']:>9.0f}")
OUT["wheel_order_cells"] = wo

# ================================================================= §2 conditionals ================
hdr("§2  ★★ THE CONDITIONALS -- engaged / manual, speed, near-centre, hands. Exposure in EVERY cell")
print("   A shared conditional SET is much stronger evidence of a shared mechanism than a shared")
print("   band. Criterion: p-p >= 1200 counts, the record's own.\n")


def cellstat(rs, name):
    if not rs:
        return dict(n=0, name=name)
    ppr = np.array([r["pp_r"] for r in rs])
    ppg = np.array([r["pp_g"] for r in rs])
    v = np.array([r["v"] for r in rs])
    return dict(name=name, n=len(rs), neps=len(episodes(rs)), secs=len(rs) * 2.56,
                vmed=float(np.median(v)), v10=float(np.percentile(v, 10)),
                v90=float(np.percentile(v, 90)),
                hr=float((ppr >= 1200).mean()), hg=float((ppg >= 1200).mean()),
                mr=float(np.median(ppr)), mg=float(np.median(ppg)))


CELLS = [
    ("engaged  creep 0.3-4",      [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP]),
    ("manual   creep 0.3-4",      [r for r in ALL if r["lat"] < 0.1 and VMIN <= r["v"] < CREEP]),
    ("engaged  creep hands-OFF",  [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP
                                   and r["eff"] <= 300]),
    ("engaged  creep hands-ON",   [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP
                                   and r["eff"] > 300]),
    ("engaged  creep NEAR ctr<15", [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP
                                    and r["absangc"] < 15]),
    ("engaged  creep OFF  ctr>=15", [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP
                                     and r["absangc"] >= 15]),
    ("engaged  4-8 m/s",          [r for r in ALL if r["lat"] > 0.9 and 4 <= r["v"] < 8]),
    ("engaged  8-16 m/s",         [r for r in ALL if r["lat"] > 0.9 and 8 <= r["v"] < 16]),
    ("engaged  16+ m/s",          [r for r in ALL if r["lat"] > 0.9 and r["v"] >= 16]),
    ("manual   all moving",       [r for r in ALL if r["lat"] < 0.1 and r["v"] >= VMIN]),
    ("stopped  v<0.3 (any)",      [r for r in ALL if r["v"] < VMIN]),
]
print(f"   {'cell':28s} {'eps':>4s} {'wins':>5s} {'secs':>6s} {'v p10-p90':>12s} | "
      f"{'6-9 hit':>8s} {'6-9 med':>8s} | {'18-22 hit':>10s} {'18-22 med':>10s}")
cond = {}
for name, rs in CELLS:
    x = cellstat(rs, name)
    cond[name] = x
    if not x["n"]:
        print(f"   {name:28s}   EMPTY")
        continue
    print(f"   {name:28s} {x['neps']:>4d} {x['n']:>5d} {x['secs']:>6.0f} "
          f"{f'{x[chr(118) + chr(49) + chr(48)]:.1f}-{x[chr(118) + chr(57) + chr(48)]:.1f}':>12s} | "
          f"{100 * x['hr']:>7.0f}% {x['mr']:>8.0f} | {100 * x['hg']:>9.0f}% {x['mg']:>10.0f}")
OUT["conditionals"] = cond

print("\n   --- FISHER 2x2, each band, at MATCHED creep speed (0.3-4 m/s)")
ec = [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP]
mc = [r for r in ALL if r["lat"] < 0.1 and VMIN <= r["v"] < CREEP]
fish = {}
for bl, k in (("6-9 Hz", "pp_r"), ("18-22 Hz", "pp_g")):
    a11 = sum(1 for r in ec if r[k] >= 1200)
    a01 = sum(1 for r in mc if r[k] >= 1200)
    p = fisher2x2(a11, len(ec) - a11, a01, len(mc) - a01)
    fish[bl] = dict(eng=a11, engn=len(ec), man=a01, mann=len(mc), p=float(p))
    print(f"   {bl:10s} engaged {a11}/{len(ec)} = {100 * a11 / len(ec):.0f}%   "
          f"manual {a01}/{len(mc)} = {100 * a01 / len(mc):.0f}%   Fisher p = {p:.4g}   "
          f"{'ENGAGEMENT REQUIRED' if p < 0.05 else 'not separable at this n'}")
    # speed census of the two arms, so the conditional is not a speed artefact
    print(f"              speed: engaged p10-p90 "
          f"{np.percentile([r['v'] for r in ec], 10):.2f}-{np.percentile([r['v'] for r in ec], 90):.2f}"
          f"   manual p10-p90 "
          f"{np.percentile([r['v'] for r in mc], 10):.2f}-{np.percentile([r['v'] for r in mc], 90):.2f}")
OUT["fisher_engagement"] = fish
print("\n   ⚠ EMPTY IS NOT NULL. If the manual arm shows 0 hits, P(observe 0 | true rate = engaged")
print("     rate) is printed here:")
for bl, k in (("6-9 Hz", "pp_r"), ("18-22 Hz", "pp_g")):
    a11 = sum(1 for r in ec if r[k] >= 1200)
    a01 = sum(1 for r in mc if r[k] >= 1200)
    if a01 == 0 and len(mc):
        pe = a11 / len(ec)
        print(f"     {bl:10s} manual 0/{len(mc)};  P(0 hits | rate {pe:.2f}) = "
              f"{(1 - pe) ** len(mc):.3g}")

# ================================================================= §3 heaviness ===================
hdr("§3  WHAT CHANGED, IF NOT AMPLITUDE? the 1-4 Hz 'heaviness' band during 6-9 Hz events")
print("   A mechanically HEAVY ratchet loads the low-frequency band as well; a 'micro' one need")
print("   not. Cell: creep windows with 6-9 Hz p-p >= 1200, any engagement, per route.\n")
ROUTES = {"V59 r2c": ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
          "V62 r37": ("_cache_r37", "r37s", list(range(15)), []),
          "V67 r47": ("_cache_r47", "r47s", list(range(26)), []),
          "V69 r4f": ("_cache_r4f", "r4fs", list(range(8)), []),
          "V70 r50": ("_cache_r50", "r50s", [0, 1, 2], [0]),
          "V71B r54": ("_cache_r54", "r54s", list(range(21)), [10, 11]),
          "V71C r58": ("_cache_r58", "r58s", list(range(16)), [12, 13, 14, 15]),
          "V72 r59": ("_cache_r59", "r59s", list(range(15)), [12, 13, 14])}


def scan_low(tag):
    cache, pfx, segs, skip = ROUTES[tag]
    out = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        er = band_envelope(tq, fs, *RATCH)
        el = band_envelope(tq, fs, *LOW)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        for i in range(0, len(tq) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            if not (VMIN <= v[w].mean() < CREEP):
                continue
            out.append(dict(seg=int(s), i0=i, pp_r=float(2 * np.percentile(er[w], 99)),
                            pp_lo=float(2 * np.percentile(el[w], 99)),
                            lat=float(lat[w].mean()), v=float(v[w].mean())))
    return out


print(f"   {'route':10s} {'n events':>9s} | {'6-9 pp med':>11s} {'1-4 pp med':>11s} "
      f"{'ratio low/ratchet':>18s}")
heavy = {}
for tag in ROUTES:
    rs = [r for r in scan_low(tag) if r["pp_r"] >= 1200]
    if len(rs) < 3:
        print(f"   {tag:10s} {len(rs):>9d} |  too few events")
        continue
    a = float(np.median([r["pp_r"] for r in rs]))
    b = float(np.median([r["pp_lo"] for r in rs]))
    heavy[tag] = dict(n=len(rs), ratchet=a, low=b, ratio=b / a)
    print(f"   {tag:10s} {len(rs):>9d} | {a:>11.0f} {b:>11.0f} {b / a:>18.3f}")
OUT["heaviness"] = heavy

json.dump(OUT, open(ROOT / "_r59_alternatives.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_r59_alternatives.json'}")
