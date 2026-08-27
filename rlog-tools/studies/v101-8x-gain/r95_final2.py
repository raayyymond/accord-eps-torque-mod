#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- fixes and follow-ups to `studies/v101-8x-gain/r95_final.py`.

  E-4b  GRIP / RELEASE events, detector repaired (the first version required the LOW state to hold
        right up to the HIGH crossing, which no real transition does -- it found 0 events).
  E-5b  GRIP vs HANDS-LIGHT on an ABSOLUTE torque threshold, matched on wheel rate AND speed.
  F-5b  Is b5's excess toggling a DC confound or real in-lane ripple?
  B-2b  Block-bootstrap CI on the creep-speed engagement contrast.
  C-5   Amplitude vs speed with a CI -- the operator's "at ALL speeds now".
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
lat = L.engaged()
tq, ang, rate_f = L.col("tq"), L.col("ang"), L.col("rate_f")
sc_tq, x6b94 = L.col("sc_tq"), L.col("x6b94")
b5 = L.col("v101_b5")
vms = np.abs(L.col("cs_v"))
tq_sus = L.lowpass(tq, FS, 3.0, mask=lat)
ts = np.abs(tq_sus)
B8, B23, CTRL = (7.3, 9.3), (21.5, 25.5), (2.5, 4.5)
out = {}


def runs(mask, min_n=1):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


# ======================================================================================
#  F-5b.  IS b5's EXCESS TOGGLING A DC CONFOUND?
# ======================================================================================
print("=" * 104)
print("F-5b. b5 = sign(gp-0x6b4c) toggles 27.4/s vs 7.1/s for sign(openpilot's raw command).")
print("      Two readings: (a) the FIRMWARE LANE carries extra ripple, or (b) the lane simply has")
print("      a smaller DC so the SAME relative ripple crosses zero more often.  Separate them.")
print("=" * 104)
sgn_raw = (sc_tq < 0).astype(float)
print(f"    negative duty, engaged:  b5 (gp-0x6b4c<0) {b5[lat].mean():.4f}   "
      f"sign(sc_tq)<0 {sgn_raw[lat].mean():.4f}")
print(f"    negative duty, manual :  b5 {b5[~lat].mean():.4f}   sign(sc_tq)<0 "
      f"{sgn_raw[~lat].mean():.4f}")
agree = float((b5[lat] == sgn_raw[lat]).mean())
print(f"    b5 == sign(sc_tq) on {agree*100:.2f} % of engaged frames "
       f"(a pure positive scaling would give 100 %)")
# stratify the toggle rate by |sc_tq|: if it is a DC confound the excess vanishes at large |cmd|
print(f"\n    {'|sc_tq| bin':>16s} {'n':>7s} {'b5 toggles/s':>13s} {'raw toggles/s':>14s} "
      f"{'excess':>8s}")
q = np.percentile(np.abs(sc_tq)[lat], [0, 20, 40, 60, 80, 100])
tog = []
for k in range(5):
    m = lat & (np.abs(sc_tq) >= q[k]) & (np.abs(sc_tq) <= q[k + 1] if k == 4
                                         else np.abs(sc_tq) < q[k + 1])
    if m.sum() < 300:
        continue
    idx = np.where(m)[0]
    tb = float(np.sum(np.abs(np.diff(b5[idx]))) / (m.sum() / FS))
    tr = float(np.sum(np.abs(np.diff(sgn_raw[idx]))) / (m.sum() / FS))
    print(f"    {q[k]:7.0f}-{q[k+1]:<8.0f} {int(m.sum()):7d} {tb:13.2f} {tr:14.2f} "
          f"{tb/max(tr,1e-9):8.2f}x")
    tog.append(dict(lo=float(q[k]), hi=float(q[k + 1]), n=int(m.sum()), b5=tb, raw=tr))
out["F5b_toggle_by_cmd"] = tog
out["F5b_agreement"] = agree

# ======================================================================================
#  E-4b.  GRIP / RELEASE EVENTS -- repaired detector
# ======================================================================================
print("\n" + "=" * 104)
print("E-4b. GRIP / RELEASE EVENTS (detector repaired).")
print("   GRIP    = |lowpass(tq,3Hz)| < 200 for >= 1.0 s, then > 500 for >= 1.0 s, transition <= 2 s")
print("   RELEASE = the mirror image.  t=0 is the moment the HIGH (GRIP) / LOW (RELEASE) state is")
print("   first reached.")
print("=" * 104)
LOW, HIGH = 200.0, 500.0
HOLD = int(round(1.0 * FS))
MAXT = int(round(2.0 * FS))


def find_events(direction):
    ev = []
    lo_m, hi_m = ts < LOW, ts > HIGH
    a_m, b_m = (lo_m, hi_m) if direction == "grip" else (hi_m, lo_m)
    n = len(ts)
    i = HOLD + MAXT
    while i < n - HOLD - int(3 * FS):
        if not b_m[i] or b_m[i - 1]:
            i += 1
            continue
        if not b_m[i:i + HOLD].all():
            i += 1
            continue
        j = i - 1
        while j > i - MAXT and not a_m[j]:
            j -= 1
        if j <= i - MAXT or not a_m[j - HOLD:j].all():
            i += 1
            continue
        if not lat[j - HOLD:i + int(3 * FS)].all():
            i += 1
            continue
        ev.append(i)
        i += HOLD
    return ev


GRIP, REL = find_events("grip"), find_events("release")
print(f"    {len(GRIP)} GRIP events, {len(REL)} RELEASE events (engaged, uninterrupted)")
PRE, POST = int(2.0 * FS), int(3.0 * FS)
for bn, (lo, hi) in (("B8", B8), ("B23", B23), ("CTRL", CTRL)):
    env = L.band_envelope(tq, FS, lo, hi, mask=lat)
    envr = L.band_envelope(rate_f, FS, lo, hi, mask=lat)
    for tag, EV in (("GRIP", GRIP), ("RELEASE", REL)):
        M = np.array([env[i - PRE:i + POST] for i in EV
                      if i >= PRE and i + POST <= len(env)
                      and np.all(np.isfinite(env[i - PRE:i + POST]))])
        Mr = np.array([envr[i - PRE:i + POST] for i in EV
                       if i >= PRE and i + POST <= len(envr)
                       and np.all(np.isfinite(envr[i - PRE:i + POST]))])
        if len(M) < 3:
            print(f"    {bn:5s} {tag:8s}: {len(M)} usable events -- CANNOT ANSWER")
            continue
        prof = np.median(M, axis=0)
        profr = np.median(Mr, axis=0)
        pre = float(np.median(prof[:PRE - int(0.3 * FS)]))
        post = float(np.median(prof[PRE + int(0.5 * FS):]))
        prer = float(np.median(profr[:PRE - int(0.3 * FS)]))
        postr = float(np.median(profr[PRE + int(0.5 * FS):]))
        # tau: time for the profile to cover 63 % of (pre -> post)
        tgt = pre + 0.632 * (post - pre)
        seg = prof[PRE:]
        k = np.argmax((seg <= tgt) if post < pre else (seg >= tgt))
        tau = k / FS if ((seg <= tgt).any() if post < pre else (seg >= tgt).any()) else np.nan
        print(f"    {bn:5s} {tag:8s}: n={len(M):2d}  tq env {pre:8.1f} -> {post:8.1f} "
              f"({post/max(pre,1e-9):5.2f}x)  tau_63 {tau:5.2f} s   |   rate_f env {prer:6.2f} -> "
              f"{postr:6.2f} ({postr/max(prer,1e-9):5.2f}x)")
        out.setdefault("E4b_events", []).append(
            dict(band=bn, event=tag, n=int(len(M)), pre=pre, post=post,
                 ratio=float(post / max(pre, 1e-9)), tau63_s=float(tau),
                 rate_pre=prer, rate_post=postr))

# ======================================================================================
#  E-5b.  GRIP vs HANDS-LIGHT on an ABSOLUTE threshold, matched on wheel rate and speed
# ======================================================================================
print("\n" + "=" * 104)
print("E-5b. GRIP (|tq_sus| > 400 ct) vs HANDS-LIGHT (< 150 ct), 1 s windows, matched on speed")
print("      and wheel rate.  Suppression that survives matching is a DAMPING effect.")
print("=" * 104)
WL = int(round(1.0 * FS))
bps = {bn: L.bandpass(tq, FS, *br, mask=lat) for bn, br in
       (("B8", B8), ("B23", B23), ("CTRL", CTRL))}
bpr = {bn: L.bandpass(rate_f, FS, *br, mask=lat) for bn, br in
       (("B8", B8), ("B23", B23), ("CTRL", CTRL))}
W = []
for a, b in runs(lat, WL):
    for i in range(a, b - WL + 1, WL):
        sl = slice(i, i + WL)
        r = dict(i0=i, v=float(np.median(vms[sl])), rate=float(np.median(np.abs(rate_f[sl]))),
                 tqs=float(np.median(ts[sl])))
        for bn in bps:
            r["tq_" + bn] = float(np.sqrt(np.nanmean(bps[bn][sl] ** 2)))
            r["rf_" + bn] = float(np.sqrt(np.nanmean(bpr[bn][sl] ** 2)))
        W.append(r)
Wv = {k: np.array([r[k] for r in W], float) for k in W[0]}
NW = len(W)
grip = Wv["tqs"] > 400
light = Wv["tqs"] < 150
print(f"    {NW} one-second engaged windows:  GRIP {int(grip.sum())}   HANDS-LIGHT "
      f"{int(light.sum())}   between {int(NW-grip.sum()-light.sum())}")
print(f"    {'stratum':>26s} {'nG':>4s} {'nL':>4s} {'v G/L':>11s} {'rate G/L':>13s} | " +
      "  ".join(f"{c+'_'+bn:>11s}" for c in ("tq", "rf") for bn in ("B8", "B23", "CTRL")))
strata = [("v>=5, rate 0-10", (Wv["v"] >= 5) & (Wv["rate"] < 10)),
          ("v>=5, rate 10-25", (Wv["v"] >= 5) & (Wv["rate"] >= 10) & (Wv["rate"] < 25)),
          ("v>=5, rate 25-60", (Wv["v"] >= 5) & (Wv["rate"] >= 25) & (Wv["rate"] < 60)),
          ("v<5,  rate 0-25", (Wv["v"] < 5) & (Wv["rate"] < 25)),
          ("ALL v>=5", Wv["v"] >= 5)]
rng = np.random.default_rng(23)
for name, S in strata:
    g, l = S & grip, S & light
    if g.sum() < 4 or l.sum() < 4:
        print(f"    {name:>26s} {int(g.sum()):4d} {int(l.sum()):4d}   -- too few")
        continue
    line = (f"    {name:>26s} {int(g.sum()):4d} {int(l.sum()):4d} "
            f"{np.median(Wv['v'][g]):5.1f}/{np.median(Wv['v'][l]):<5.1f} "
            f"{np.median(Wv['rate'][g]):6.1f}/{np.median(Wv['rate'][l]):<6.1f} | ")
    rec = dict(stratum=name, nG=int(g.sum()), nL=int(l.sum()))
    for c in ("tq", "rf"):
        for bn in ("B8", "B23", "CTRL"):
            k = f"{c}_{bn}"
            ratio = np.median(Wv[k][g]) / max(np.median(Wv[k][l]), 1e-9)
            bs = []
            for _ in range(3000):
                gi = rng.integers(0, g.sum(), g.sum())
                li = rng.integers(0, l.sum(), l.sum())
                bs.append(np.median(Wv[k][g][gi]) / max(np.median(Wv[k][l][li]), 1e-9))
            lo95, hi95 = np.percentile(bs, [2.5, 97.5])
            line += f" {ratio:5.2f}[{lo95:.2f},{hi95:.2f}]"
            rec[k] = dict(ratio=float(ratio), lo=float(lo95), hi=float(hi95))
    print(line)
    out.setdefault("E5b", []).append(rec)
print("    (values are GRIP / HANDS-LIGHT: < 1 means the driver's torque SUPPRESSES the band)")

# ======================================================================================
#  B-2b.  CI on the creep-speed engagement contrast
# ======================================================================================
print("\n" + "=" * 104)
print("B-2b. ENGAGEMENT CONTRAST at 1.0-2.0 m/s, block-bootstrapped over 1 s windows.")
print("=" * 104)
sel = (vms >= 1.0) & (vms < 2.0)
Wc = []
for m, tag in ((lat & sel, "eng"), ((~lat) & sel, "man")):
    for a, b in runs(m, WL):
        for i in range(a, b - WL + 1, WL):
            sl = slice(i, i + WL)
            r = dict(tag=tag)
            for bn, br in (("B8", B8), ("B23", B23), ("CTRL", CTRL)):
                bt = L.bandpass(tq, FS, *br, mask=m)[sl]
                bfr = L.bandpass(rate_f, FS, *br, mask=m)[sl]
                r["tq_" + bn] = float(np.sqrt(np.nanmean(bt ** 2)))
                r["rf_" + bn] = float(np.sqrt(np.nanmean(bfr ** 2)))
            Wc.append(r)
tags = np.array([r["tag"] for r in Wc])
print(f"    engaged windows {int((tags=='eng').sum())}   manual windows "
      f"{int((tags=='man').sum())}")
for c in ("tq", "rf"):
    for bn in ("B8", "B23", "CTRL"):
        k = f"{c}_{bn}"
        v = np.array([r[k] for r in Wc], float)
        e, m_ = v[tags == "eng"], v[tags == "man"]
        if len(e) < 4 or len(m_) < 4:
            continue
        bs = []
        for _ in range(4000):
            bs.append(np.median(e[rng.integers(0, len(e), len(e))]) /
                      max(np.median(m_[rng.integers(0, len(m_), len(m_))]), 1e-9))
        lo95, hi95 = np.percentile(bs, [2.5, 97.5])
        print(f"      {k:9s}  engaged/manual = {np.median(e)/max(np.median(m_),1e-9):7.2f}x  "
              f"[{lo95:.2f}, {hi95:.2f}]")
        out.setdefault("B2b", []).append(dict(k=k, ratio=float(np.median(e) / max(np.median(m_), 1e-9)),
                                              lo=float(lo95), hi=float(hi95)))

# ======================================================================================
#  C-5.  AMPLITUDE vs SPEED, engaged, with CIs -- "at ALL speeds now"
# ======================================================================================
print("\n" + "=" * 104)
print("C-5. BAND RMS vs SPEED, engaged, 1 s windows, block bootstrap over 4 s blocks.")
print("=" * 104)
Wf = []
for a, b in runs(lat, WL):
    for i in range(a, b - WL + 1, WL):
        sl = slice(i, i + WL)
        r = dict(v=float(np.median(vms[sl])), tqs=float(np.median(ts[sl])))
        for bn in bps:
            r["tq_" + bn] = float(np.sqrt(np.nanmean(bps[bn][sl] ** 2)))
            r["rf_" + bn] = float(np.sqrt(np.nanmean(bpr[bn][sl] ** 2)))
        Wf.append(r)
Fv = {k: np.array([r[k] for r in Wf], float) for k in Wf[0]}
print(f"    {'v km/h':>12s} {'n':>4s} {'|tq_sus|':>9s} | " +
      "  ".join(f"{c+'_'+bn:>20s}" for c in ("tq",) for bn in ("B8", "B23", "CTRL")) +
      "  " + "  ".join(f"{'rf_'+bn:>18s}" for bn in ("B8", "B23")))
for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70)):
    m = (Fv["v"] * 3.6 >= lo) & (Fv["v"] * 3.6 < hi)
    if m.sum() < 5:
        continue
    line = f"    {lo:5d}-{hi:<6d} {int(m.sum()):4d} {np.median(Fv['tqs'][m]):9.0f} | "
    rec = dict(lo=lo, hi=hi, n=int(m.sum()))
    for c, bl in (("tq", ("B8", "B23", "CTRL")), ("rf", ("B8", "B23"))):
        for bn in bl:
            k = f"{c}_{bn}"
            v = Fv[k][m]
            bs = [np.median(v[rng.integers(0, len(v), len(v))]) for _ in range(2000)]
            lo95, hi95 = np.percentile(bs, [2.5, 97.5])
            line += f" {np.median(v):8.1f}[{lo95:6.1f},{hi95:6.1f}]"
            rec[k] = dict(med=float(np.median(v)), lo=float(lo95), hi=float(hi95))
    print(line)
    out.setdefault("C5_amp_vs_speed", []).append(rec)

(L.CACHE / "r95_FINAL2.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_FINAL2.json'}")
