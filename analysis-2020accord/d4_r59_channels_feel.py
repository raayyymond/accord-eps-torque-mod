#!/usr/bin/env python3
"""D4 -- (1) the channel test that can reconcile the operator with the instrument, and
        (2) the MANUAL-FEEL change he reports.

★ WHY THE CHANNEL TEST MATTERS. d4_r59_ratchet.py says the 7.79 Hz ratchet is UNCHANGED on V72:
63% duty in engaged hands-off creep, median 3,647 counts p-p, 25 bouts, 122.9 s. The operator says
it is gone. Both can be true in exactly one way: the line is still in the BAR TORQUE but no longer
moves the COLUMN. The record's own characterisation is "the line is in the BAR and ANGLE-RATE but
NOT in openpilot's command"; if V72 has dropped the ANGLE-RATE leg, the driver feels torque ripple
in the rim rather than the wheel ratcheting round, which is exactly the reported "micro-ratcheting,
not heavy, felt in the column". So: measure per-channel prominence AND per-channel physical
amplitude at the 6-9 Hz hits, per build, with the identical instrument (`r58_ratchet.py` §7).

MANUAL FEEL. V72's Lever B/C open the base-assist damper at creep -- where stock has NO base-assist
damping at all -- and Lever A doses both rate lanes UNGATED, so the manual arm is dosed too. A
velocity-opposing damper costs the driver torque IN PROPORTION TO ANGLE RATE. So the test is the
slope of |bar torque| on |column rate| in MANUAL creep, per build, plus the 1-4 Hz driver band.

Writes `_d4_r59_feel.json`.
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
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
HANDS_OFF = 300.0
CREEP_R = 4.0
AMP_MIN = 600.0
OUT = {}

ROUTES = {
    "V59 r2c":  ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_cache_r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_cache_r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_cache_r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_cache_r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_cache_r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_cache_r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_cache_r59", "r59s", list(range(15)), [12, 13, 14]),
}
NEW = "V72 r59"
CHANS = (("tq", "bar torque"), ("rate_c", "COLUMN RATE"), ("ang", "column angle"),
         ("e4tq", "op command"))


def hdr(s):
    print("\n" + "=" * 124 + f"\n{s}\n" + "=" * 124)


# =============================================================== §1 per-channel at the hits =======
hdr("§1  ★★★ WHICH CHANNEL CARRIES THE 6-9 Hz LINE? Every amplitude hit (bar 6-9 Hz envelope p99\n"
    "    >= 600 counts), per channel: PROMINENCE (criterion > 10 = present) and PHYSICAL amplitude\n"
    "    (6-9 Hz envelope p99 in that channel's own units).")
res = {}
for tag, (cache, pfx, segs, skip) in ROUTES.items():
    rows = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = {k: band_envelope(np.asarray(d[k], float), fs, *RATCH) for k, _ in CHANS}
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            if np.percentile(env["tq"][w], 99) < AMP_MIN:
                continue
            r = dict(seg=int(s), t0=float(t[i]), v=float(v[w].mean()),
                     eff=float(np.median(eff[w])), lat=float(lat[w].mean()),
                     ep=(tag, int(s), i // (NFFT * 4)))
            for k, _ in CHANS:
                P = periodogram(np.asarray(d[k], float)[w], fs, NFFT)
                r["p_" + k] = peak_prom(f, P, *RATCH)[1] if P is not None else np.nan
                r["a_" + k] = float(np.percentile(env[k][w], 99))
            rows.append(r)
    res[tag] = rows

print(f"   {'route':10s} {'nhit':>5s} | " +
      " ".join(f"{n + ' prom':>16s}" for _, n in CHANS))
for tag, rows in res.items():
    if not rows:
        continue
    print(f"   {tag:10s} {len(rows):>5d} | " +
          " ".join(f"{np.nanmedian([r['p_' + k] for r in rows]):>16.2f}" for k, _ in CHANS))
print("\n   PHYSICAL AMPLITUDE at the same hits -- 6-9 Hz envelope p99, median over hits.")
print(f"   {'route':10s} {'nhit':>5s} | {'bar (counts)':>14s} {'COLUMN RATE (deg/s)':>21s} "
      f"{'angle (deg)':>13s} {'op cmd':>9s} | {'rate/bar x1e3':>14s}")
ch = {}
for tag, rows in res.items():
    if not rows:
        continue
    a = {k: float(np.nanmedian([r["a_" + k] for r in rows])) for k, _ in CHANS}
    p = {k: float(np.nanmedian([r["p_" + k] for r in rows])) for k, _ in CHANS}
    ch[tag] = dict(n=len(rows), amp=a, prom=p, ratio=a["rate_c"] / max(a["tq"], 1e-9))
    print(f"   {tag:10s} {len(rows):>5d} | {a['tq']:>14.0f} {a['rate_c']:>21.2f} "
          f"{a['ang']:>13.3f} {a['e4tq']:>9.1f} | {1000 * a['rate_c'] / max(a['tq'], 1e-9):>14.2f}")
OUT["channels_allhits"] = ch

print("\n   ★ RESTRICTED to the recorded conditional -- ENGAGED HANDS-OFF CREEP hits only:")
print(f"   {'route':10s} {'nhit':>5s} | {'bar p-p':>10s} {'COLUMN RATE p-p':>16s} "
      f"{'angle p-p (deg)':>16s} | {'bar prom':>9s} {'rate prom':>10s} {'ang prom':>9s}")
ch2 = {}
for tag, rows in res.items():
    s = [r for r in rows if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
    if len(s) < 3:
        print(f"   {tag:10s} {len(s):>5d} |  *** too few")
        continue
    a = {k: float(np.nanmedian([r["a_" + k] for r in s])) for k, _ in CHANS}
    p = {k: float(np.nanmedian([r["p_" + k] for r in s])) for k, _ in CHANS}
    ch2[tag] = dict(n=len(s), amp=a, prom=p)
    print(f"   {tag:10s} {len(s):>5d} | {2 * a['tq']:>10.0f} {2 * a['rate_c']:>16.2f} "
          f"{2 * a['ang']:>16.4f} | {p['tq']:>9.1f} {p['rate_c']:>10.1f} {p['ang']:>9.1f}")
OUT["channels_conditional"] = ch2

# =============================================================== §2 manual feel ===================
hdr("§2  ★★ THE MANUAL-FEEL CHANGE. V72 is UNGATED, so the manual arm is DOSED -- it is not a stock\n"
    "    control. Lever B/C open the base-assist damper at creep, where stock has NONE. A\n"
    "    velocity-opposing damper costs bar torque IN PROPORTION TO COLUMN RATE.")
print("    TEST: robust (Theil-Sen) slope of |bar torque| on |column rate|, MANUAL creep frames.")
print("    ⚠ This is an OBSERVATIONAL slope, not a plant identification: the driver closes the loop.")


def theilsen(x, y, npair=200000, nboot=600, rng=None):
    rng = rng or np.random.default_rng(20260805)
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 20:
        return np.nan, np.nan, np.nan, len(x)

    def sl(xx, yy):
        i = rng.integers(0, len(xx), npair)
        j = rng.integers(0, len(xx), npair)
        dx = xx[j] - xx[i]
        k = np.abs(dx) > 1e-6
        return float(np.median((yy[j] - yy[i])[k] / dx[k])) if k.any() else np.nan
    pt = sl(x, y)
    dr = np.empty(nboot)
    for b in range(nboot):
        k = rng.integers(0, len(x), len(x))
        dr[b] = sl(x[k], y[k])
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(x)


print(f"\n   {'route':10s} {'arm':>8s} {'n frames':>9s} | {'slope |tq|/|rate|':>18s} "
      f"{'95% CI':>21s} | {'med |tq|':>9s} {'med |rate|':>10s} {'1-4 Hz env p50':>15s}")
feel = {}
for tag, (cache, pfx, segs, skip) in ROUTES.items():
    for arm, want in (("manual", False), ("ENGAGED", True)):
        TQ, RT, E14 = [], [], []
        for s in segs:
            if s in skip:
                continue
            p = ROOT / cache / f"{pfx}{s}.npz"
            if not p.exists():
                continue
            d = C.load(s, ROOT / cache, pfx)
            fs = R4F.fs_lattice(d)
            v = np.abs(np.asarray(d["cs_v"], float))
            lat = np.asarray(d["cc_lat"], float) > 0.5
            m = (v >= 0.3) & (v < CREEP_R) & (lat if want else ~lat)
            if m.sum() < 50:
                continue
            e14 = band_envelope(np.asarray(d["tq"], float), fs, 1.0, 4.0)
            TQ.append(np.abs(np.asarray(d["tq"], float))[m])
            RT.append(np.abs(np.asarray(d["rate_c"], float))[m])
            E14.append(e14[m])
        if not TQ:
            continue
        tq = np.concatenate(TQ)
        rt = np.concatenate(RT)
        e14 = np.concatenate(E14)
        sl, lo, hi, n = theilsen(rt, tq)
        feel[f"{tag}|{arm}"] = dict(n=int(n), slope=sl, lo=lo, hi=hi,
                                    tq=float(np.median(tq)), rate=float(np.median(rt)),
                                    e14=float(np.median(e14)))
        print(f"   {tag:10s} {arm:>8s} {n:>9d} | {sl:>18.3f} [{lo:>9.3f},{hi:>9.3f}] | "
              f"{np.median(tq):>9.0f} {np.median(rt):>10.1f} {np.median(e14):>15.1f}")
OUT["feel"] = feel

# =============================================================== §3 manual band levels ============
hdr("§3  MANUAL-ARM BAND LEVELS at creep -- what the driver's own hands are in contact with.")
print(f"   {'route':10s} {'n win':>6s} {'secs':>7s} | " +
      " ".join(f"{b:>12s}" for b in ("1-4 Hz", "6-9 Hz", "10-16 Hz", "18-22 Hz")) +
      " (median window envelope p99, counts)")
bands = {"1-4 Hz": (1, 4), "6-9 Hz": (6, 9), "10-16 Hz": (10, 16), "18-22 Hz": (18, 22)}
ml = {}
for tag, (cache, pfx, segs, skip) in ROUTES.items():
    acc = {k: [] for k in bands}
    nw = 0
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        env = {k: band_envelope(tq, fs, *b) for k, b in bands.items()}
        for i in range(0, len(tq) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            if not (0.3 <= v[w].mean() < CREEP_R) or lat[w].mean() > 0.1:
                continue
            nw += 1
            for k in bands:
                acc[k].append(float(np.percentile(env[k][w], 99)))
    if nw < 4:
        continue
    ml[tag] = dict(n=nw, **{k: float(np.median(acc[k])) for k in bands})
    print(f"   {tag:10s} {nw:>6d} {nw * NFFT / 100:>7.1f} | " +
          " ".join(f"{np.median(acc[k]):>12.0f}" for k in bands))
OUT["manual_bands"] = ml

(ROOT / "_d4_r59_feel.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_d4_r59_feel.json'}")
