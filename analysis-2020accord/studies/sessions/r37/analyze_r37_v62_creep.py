#!/usr/bin/env python3
"""V62 route `37` -- did the 2-5 mph creep grinding actually go away, and did the ratchet move?

V62 = V59 + two single-instruction immediates in FUN_0003aa2c: `sar 0xa -> sar 0x9` at 0x3AC20 (r24)
and 0x3AB76 (r26). That DOUBLES the torsion-bar torque-RATE (Kd) lead/damping lane on the 1 kHz
aggregator. It is the exact matched inverse of V61, which ZEROED the same lane and made the grinding
worse and spread it into manual driving.

Operator report after route 37: the 2-5 mph creep grinding is GONE; the ratchet is still present.
This script tries to confirm or refute that with numbers, against the historical controls.

CONTROLS (all pre-built caches, nothing re-extracted):
    V59 route 2c   _scratch/cache/r2c   segs SEGS_2C     -- the reference build the grinding was measured on
    V61 route 31   _scratch/cache/r31   segs [0..3]      -- Kd = 0, the signed WORSE result
    V64 route 35   _scratch/cache/r35   segs [0,1,2]     -- inert (detector never armed) => a V59 replicate
    V62 route 37   _scratch/cache/r37   segs [1..14]     -- 🛑 seg 0 is a stale 07:05 boot, EXCLUDED

METHODOLOGY -- every one of these is a trap the kit has already paid for:
  * engagement = carControl.latActive (`cc_lat`), corroborated by 0x18F byte4 bit3 (`sca`).
    NEVER cruiseState.enabled.
  * hands-off = SUSTAINED |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  * LOCATE the peak with a FREE 12-30 Hz argmax. A strict 18-26 Hz band pinned V61 to the band edge
    (18.04 Hz sd 0.00) because its mode had dropped below the band -- a truncation artifact.
  * PRESENCE = prominence (peak / local +/-6 Hz median floor) in the build's own tracking band,
    plus a pass fraction. Envelope ratios alone are not the defensible statistic; the mode is bursty.
  * average periodograms across DISJOINT runs; never splice.
  * cut windows over the WHOLE creep arm, then bin windows by their own mean |v|. Masking the speed
    bin BEFORE cutting windows destroys the 2.56 s contiguity requirement and manufactures nulls.
  * tyre order 1 is f ~ 0.489*v; at creep that is 0.5-2.5 Hz and cannot reach either band.

Usage:  python studies/sessions/r37/analyze_r37_v62_creep.py
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
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:                                    # Windows consoles default to cp1252 and die on the 🛑 marks
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import (NFFT, SEGS_2C, SEGS_31, band_envelope, fs_of,  # noqa: E402
                         load, peak_prom, periodogram, runs_of, sustained)
from analyze_r31_spectra import arm_mask  # noqa: E402

SEGS_35 = [0, 1, 2]
SEGS_37 = list(range(0, 15))
# 🛑 SEG 0 IS REAL DRIVING and is INCLUDED. An earlier pass excluded it as a "stale 07:05 boot";
# only its `clocks` messages carry a pre-NTP RTC, the DATA is fine (10:11:03->10:12:05, 6,168
# frames, vEgo 0.00-2.91 m/s, park->drive, latActive 2.6%). It is a large-angle near-stationary
# MANUAL creep segment, which is exactly the population the disengaged arm is otherwise thin on.
# ⚠ never read seg 0's own `wall_t0` scalar -- that one really is stale; the route-wide fit is in
# studies/sessions/r37/r37_wallclock.py.
LOT_37 = [13, 14]                     # the end-of-route parking-lot test

BUILDS = {
    "V59 r2c": dict(cache=ROOT / "_scratch/cache/r2c", pfx="r2cs", segs=SEGS_2C),
    "V61 r31": dict(cache=ROOT / "_scratch/cache/r31", pfx="r31s", segs=SEGS_31),
    "V64 r35": dict(cache=ROOT / "_scratch/cache/r35", pfx="r35s", segs=SEGS_35),
    "V62 r37": dict(cache=ROOT / "_scratch/cache/r37", pfx="r37s", segs=SEGS_37),
}
ORDER = ["V59 r2c", "V64 r35", "V61 r31", "V62 r37"]

GRIND = (12.0, 30.0)      # free LOCATE band for the creep mode
RATCH = (6.0, 9.0)        # the ratchet band
HALF = 1.5                # tracking half-width
SPEED_CAP = 5.35          # route 31's own max engaged speed -- the speed-matching cap of record
BINS = [(1.0, 2.0), (2.0, 3.0), (3.0, 4.0)]
PRESENCE = 10.0           # prominence cut for the presence test

FLAGS = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
         "immediateDisable", "steerSaturated"]


def hdr(s):
    print(f"\n{'=' * 118}\n{s}\n{'=' * 118}")


# ---------------------------------------------------------------- window records ---------------
def wrecs(build, arm="any_eng", vmin=0.3, vmax=SPEED_CAP, hands=None, nfft=NFFT,
          band=None, segs=None, chan="tq"):
    """Per-window records over DISJOINT runs of the arm. Stores the periodogram so any band can be
    integrated later without recutting windows."""
    B = BUILDS[build]
    out = []
    for s in (BUILDS[build]["segs"] if segs is None else segs):
        d = load(s, B["cache"], B["pfx"])
        m = arm_mask(d, arm, vmax=vmax, vmin=vmin, hands=hands)
        if not m.any():
            continue
        fs = fs_of(d)
        f = np.fft.rfftfreq(nfft, 1 / fs)
        for a, b in runs_of(m, d["t"], nfft):
            x = d[chan][a:b]
            env = band_envelope(x, fs, *band) if band else None
            for i in range(0, len(x) - nfft + 1, nfft):
                P = periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                f0g, prg = peak_prom(f, P, *GRIND)
                f0r, prr = peak_prom(f, P, *RATCH)
                sl = slice(a + i, a + i + nfft)
                out.append(dict(
                    f=f, P=P, f0=f0g, prom=prg, fr=f0r, promr=prr,
                    env=float(np.percentile(env[i:i + nfft], 99)) if env is not None else np.nan,
                    v=float(np.mean(np.abs(d["cs_v"][sl]))),
                    ang=float(np.mean(np.abs(d["ang"][sl]))),
                    eff=float(np.mean(np.abs(sustained(d["tq"][sl], fs)))),
                    seg=int(s), t0=float(d["t"][a + i]), run=(int(a), int(b))))
    return out


def col(recs, k):
    return np.array([r[k] for r in recs], float)


def nrun(recs):
    return len({(r["seg"], r["run"]) for r in recs})


def bandpower(recs, lo, hi):
    return np.array([r["P"][(r["f"] >= lo) & (r["f"] <= hi)].sum() for r in recs], float)


def track_prom(recs, f0):
    """Prominence of the strongest bin inside the build's OWN tracking band f0 +/- HALF."""
    return np.array([peak_prom(r["f"], r["P"], f0 - HALF, f0 + HALF)[1] for r in recs], float)


def pooled_f0(recs, lo=GRIND[0], hi=GRIND[1]):
    """f0 of the run-averaged periodogram -- the pooled 'Method A' style locate."""
    if not recs:
        return np.nan, np.nan
    f = recs[0]["f"]
    P = np.mean([r["P"] for r in recs], axis=0)
    return peak_prom(f, P, lo, hi)


def msd(v):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v):
        return np.nan, np.nan
    return float(np.median(v)), float(v.std(ddof=1)) if len(v) > 1 else 0.0


# ---------------------------------------------------------------- 0. flight health -------------
def health():
    hdr("0.  FLIGHT HEALTH -- route 37 (V62), segs 1-14")
    tot, T = Counter(), 0
    for s in SEGS_37:
        d = load(s, BUILDS["V62 r37"]["cache"], "r37s")
        tot.update(d["sstat"].astype(int).tolist())
        T += len(d["t"])
    print(f"   STEER_STATUS (0x18F byte4 bits 7:4) over {T} frames: "
          + "  ".join(f"ST={k}:{v} ({100 * v / T:.3f}%)" for k, v in sorted(tot.items())))
    print(f"   *** ST==4 : {tot.get(4, 0)}"
          + ("   <-- NONZERO, the V42 state-4 governor is back" if tot.get(4, 0)
             else "   (clean -- the streak survives)"))
    if tot.get(3, 0):
        for s in SEGS_37:
            d = load(s, BUILDS["V62 r37"]["cache"], "r37s")
            m = d["sstat"] == 3
            if m.any():
                print(f"       ST==3 seg{s}: {int(m.sum())} frames  t={d['t'][m].min():.2f}.."
                      f"{d['t'][m].max():.2f}s  |v| {np.abs(d['cs_v'][m]).min():.3f}.."
                      f"{np.abs(d['cs_v'][m]).max():.3f} m/s  latActive "
                      f"{int((d['cc_lat'][m] > 0.5).sum())}")

    ev = Counter()
    for s in SEGS_37:
        p = BUILDS["V62 r37"]["cache"] / f"r37s{s}_events.json"
        if p.exists():
            for e in json.loads(p.read_text()):
                ev[e["name"]] += 1
    print("\n   the six watched onroadEvents:")
    for fl in FLAGS:
        n = ev.get(fl, 0)
        print(f"     {fl:24s} {n:5d}" + ("   <-- !!" if n else ""))
    print("   all event names seen: " + ", ".join(f"{k}={v}" for k, v in ev.most_common()))

    # V59 boost-index probe liveness (V62 carries V59's probe unchanged, NOT V64's detector)
    n = live = fault = viol = void = 0
    th, fld = Counter(), Counter()
    lat_agree = []
    for s in SEGS_37:
        d = load(s, BUILDS["V62 r37"]["cache"], "r37s")
        n += len(d["t"])
        live += int((d["live"] > 0.5).sum())
        fault += int((d["fault"] > 0.5).sum())
        viol += int(d["thermviol"].sum())
        void += int((d["field"] == 0).sum())
        th.update(d["therm"].astype(int).tolist())
        fld.update(d["field"].astype(int).tolist())
        lat_agree.append(((d["cc_lat"] > 0.5) == (d["sca"] == 1)).mean())
    print(f"\n   V59 boost-index probe on 0x14A byte4:  n={n}  live(bit7) {live} "
          f"({100 * live / n:.3f}%)  VOID(field==0) {void}  fault(bit6) {fault}  thermviol {viol}")
    print("   thermometer level (0 = index<512 pinned .. 3 = index>=2048): "
          + "  ".join(f"L{k}:{v} ({100 * v / n:.1f}%)" for k, v in sorted(th.items())))
    print("   raw field (probe>>3 & 0x1F): "
          + "  ".join(f"0x{k:02X}:{v}" for k, v in sorted(fld.items())))
    print(f"   latActive vs 0x18F b4 bit3 (sca) agreement per seg: "
          f"{100 * min(lat_agree):.2f}-{100 * max(lat_agree):.2f}%")


# ---------------------------------------------------------------- 1. headline ------------------
def headline():
    hdr("1.  ENGAGED CREEP, SPEED-MATCHED -- the headline. free 12-30 Hz locate, NFFT=256, chan tq")
    print("   Arm: latActive & 0.3 <= |v| <= %.2f m/s. Windows cut over the whole arm, then binned"
          % SPEED_CAP)
    print("   on the window's OWN mean |v|. 'all' = every window; 'hands-off' = sustained effort <= 200.")

    store = {}
    for hands, hlab in ((None, "all-hands"), (True, "hands-off")):
        print(f"\n   ---- {hlab} ----")
        base = {b: wrecs(b, hands=hands) for b in ORDER}
        f0b = {}
        for b in ORDER:
            pf, pp = pooled_f0(base[b])
            f0b[b] = pf
        print(f"   pooled (run-averaged) creep f0, whole arm: "
              + "   ".join(f"{b} {f0b[b]:.2f} Hz" for b in ORDER))
        store[hlab] = (base, f0b)

        # recut with the envelope band = each build's own tracking band
        rec = {b: wrecs(b, hands=hands, band=(f0b[b] - HALF, f0b[b] + HALF)) for b in ORDER}
        print(f"\n   {'bin':>9s} {'build':9s} {'ep':>3s} {'win':>4s} {'f0 med':>7s} {'sd':>5s} "
              f"{'promFREE':>9s} {'p90':>9s} {'promTRK':>8s} {'p90':>8s} {'envp99':>8s} "
              f"{'P(trk)':>10s} {'P(strict)':>10s} {'pres%':>6s} {'med|v|':>7s} {'eff':>6s}")
        for lo, hi in BINS + [(0.3, SPEED_CAP)]:
            for b in ORDER:
                r = [x for x in rec[b] if lo <= x["v"] < hi]
                if not r:
                    print(f"   {lo:4.1f}-{hi:<4.1f} {b:9s}   -- n=0 windows")
                    continue
                f0m, f0s = msd(col(r, "f0"))
                pf = col(r, "prom")
                pt = track_prom(r, f0b[b])
                Pt = bandpower(r, f0b[b] - HALF, f0b[b] + HALF)
                Ps = bandpower(r, 18.0, 26.0)
                ok = np.isfinite(pt)
                pres = 100 * np.mean(pt[ok] >= PRESENCE) if ok.any() else np.nan
                print(f"   {lo:4.1f}-{hi:<4.1f} {b:9s} {nrun(r):3d} {len(r):4d} {f0m:7.2f} {f0s:5.2f} "
                      f"{np.nanmedian(pf):9.1f} {np.nanpercentile(pf, 90):9.1f} "
                      f"{np.nanmedian(pt):8.1f} {np.nanpercentile(pt, 90):8.1f} "
                      f"{np.median(col(r, 'env')):8.1f} {np.median(Pt):10.3g} {np.median(Ps):10.3g} "
                      f"{pres:6.1f} {np.median(col(r, 'v')):7.2f} {np.median(col(r, 'eff')):6.0f}")
            print()
    return store


# ---------------------------------------------------------------- 2. presence ------------------
def presence(store):
    hdr("2.  PRESENCE, NOT AMPLITUDE -- fraction of windows whose tracking-band prominence passes")
    print("   Tracking band = each build's OWN pooled creep f0 +/- 1.5 Hz. If V62's creep line is")
    print("   genuinely gone, the pass fraction collapses; an amplitude ratio alone would not say that.")
    for hlab in ("all-hands", "hands-off"):
        base, f0b = store[hlab]
        print(f"\n   ---- {hlab} ----")
        print(f"   {'bin':>9s} {'build':9s} {'win':>4s} " +
              "".join(f"{'>=' + str(c) + 'x':>9s}" for c in (5, 10, 20, 50, 100)))
        for lo, hi in BINS + [(0.3, SPEED_CAP)]:
            for b in ORDER:
                r = [x for x in base[b] if lo <= x["v"] < hi]
                if not r:
                    continue
                pt = track_prom(r, f0b[b])
                ok = np.isfinite(pt)
                cells = "".join(f"{100 * np.mean(pt[ok] >= c):8.1f}%" for c in (5, 10, 20, 50, 100))
                print(f"   {lo:4.1f}-{hi:<4.1f} {b:9s} {len(r):4d} {cells}")
            print()

    print("   -- CROSS-BAND control: every build measured in EVERY build's tracking band (whole arm,")
    print("      all-hands). A build whose line has vanished reads low in ALL bands, including its own.")
    base, f0b = store["all-hands"]
    print(f"   {'measured':9s} " + "".join(f"{'in ' + b.split()[0] + ' band':>22s}" for b in ORDER))
    for b in ORDER:
        r = base[b]
        row = []
        for o in ORDER:
            pt = track_prom(r, f0b[o])
            ok = np.isfinite(pt)
            row.append(f"prom {np.median(pt[ok]):7.1f}x pres {100 * np.mean(pt[ok] >= PRESENCE):4.0f}%")
        print(f"   {b:9s} " + "".join(f"{c:>22s}" for c in row))


# ---------------------------------------------------------------- 3. ratchet -------------------
def ratchet():
    hdr("3.  THE RATCHET, 6-9 Hz -- operator says it is STILL PRESENT")
    print("   V59 route 2c reference of record: 7.56 +/- 0.36 Hz, prominence median 783x, max 2142x,")
    print("   15 windows / 5 runs.  Reproduced here with this script's own code for comparability.")
    print(f"\n   {'arm':30s} {'build':9s} {'ep':>3s} {'win':>4s} {'f0 med':>7s} {'sd':>5s} "
          f"{'prom med':>9s} {'p90':>9s} {'max':>9s} {'P(6-9)':>10s} {'pres%':>6s}")

    def row(lbl, b, r):
        if not r:
            print(f"   {lbl:30s} {b:9s}   -- n=0 windows")
            return
        f0m, f0s = msd(col(r, "fr"))
        pr = col(r, "promr")
        ok = np.isfinite(pr)
        P69 = bandpower(r, *RATCH)
        print(f"   {lbl:30s} {b:9s} {nrun(r):3d} {len(r):4d} {f0m:7.2f} {f0s:5.2f} "
              f"{np.nanmedian(pr):9.1f} {np.nanpercentile(pr, 90):9.1f} {np.nanmax(pr):9.1f} "
              f"{np.median(P69):10.3g} {100 * np.mean(pr[ok] >= PRESENCE):6.1f}")

    for b in ORDER:
        row("engaged creep 0.3-5.35 m/s", b, wrecs(b, hands=None))
    print()
    for b in ORDER:
        row("engaged creep, hands-off", b, wrecs(b, hands=True))
    print()
    for b in ORDER:
        row("manual (disengaged) 0.3-5.35", b, wrecs(b, arm="any_man"))
    print()
    print("   -- route 37 PARKING LOT (segs 13-14 only), where the operator ran the end-of-route test --")
    for arm, lbl in (("any_eng", "lot: engaged"), ("any_man", "lot: manual"),
                     ("man_rev", "lot: manual REVERSE")):
        row(lbl, "V62 r37", wrecs("V62 r37", arm=arm, segs=LOT_37))
    row("lot: all, |v| >= 0.1", "V62 r37", wrecs("V62 r37", arm="any", vmin=0.1, segs=LOT_37))


# ---------------------------------------------------------------- 4. common shift --------------
def common_shift():
    hdr("4.  THE STRUCTURAL PREDICTION -- a lagged-derivative Kd shifts EVERY mode by the SAME factor")
    print("   studies/models/rate_lane_damping_model.py: d(omega_n^2)/omega_n^2 ~ Kd*k*tau/J_c, FREQUENCY-INDEPENDENT.")
    print("   V61 (Kd=0) measured grinding x0.865 and ratchet x0.849 -- the same fraction, downward.")
    print("   V62 (Kd x2) must therefore shift BOTH modes UP by a common factor. Testing that here.\n")
    ref = "V59 r2c"
    res = {}
    for b in ORDER:
        r = wrecs(b, hands=None)
        gf = pooled_f0(r, *GRIND)[0]
        rf = pooled_f0(r, *RATCH)[0]
        # per-window medians restricted to windows where each mode is actually present
        pg = col(r, "prom")
        pr = col(r, "promr")
        gw = col(r, "f0")[np.isfinite(pg) & (pg >= PRESENCE)]
        rw = col(r, "fr")[np.isfinite(pr) & (pr >= PRESENCE)]
        res[b] = dict(gp=gf, rp=rf,
                      gw=np.median(gw) if len(gw) else np.nan, ngw=len(gw),
                      rw=np.median(rw) if len(rw) else np.nan, nrw=len(rw))
    print(f"   {'build':9s} {'grind pooled':>13s} {'grind win(med)':>15s} {'n':>4s} "
          f"{'ratchet pooled':>15s} {'ratchet win(med)':>17s} {'n':>4s}")
    for b in ORDER:
        x = res[b]
        print(f"   {b:9s} {x['gp']:13.2f} {x['gw']:15.2f} {x['ngw']:4d} "
              f"{x['rp']:15.2f} {x['rw']:17.2f} {x['nrw']:4d}")
    print(f"\n   {'build':9s} {'grind / V59':>13s} {'ratchet / V59':>15s}  {'agree?':>8s}")
    for b in ORDER:
        if b == ref:
            continue
        g = res[b]["gw"] / res[ref]["gw"]
        rr = res[b]["rw"] / res[ref]["rw"]
        print(f"   {b:9s} {g:13.3f} {rr:15.3f}  {abs(g - rr):8.3f} apart")
    print("\n   (a common factor => the two ratios match; a mode moving alone => they diverge)")


# ---------------------------------------------------------------- 5. manual arm ----------------
def manual():
    hdr("5.  THE MANUAL / REVERSE ARM -- V61 put grinding INTO manual; V62 should have removed it")
    print("   🛑 Standing convention: the manual population that matters is NEAR-STATIONARY and")
    print("   HIGH-EFFORT. Both a |v| >= 0.3 moving gate AND a missing effort gate erase it, so the")
    print("   near-stationary arm is run at NFFT=128 (1.28 s) because no run reaches 2.56 s.")
    print("   ⚠ the route-2c cache predates cs_gear, so V59 has NO reverse/forward split -- 'any_man'.")

    def line(lbl, b, r, f0):
        if not r:
            print(f"   {lbl:34s} {b:9s}   -- n=0 windows")
            return
        f0m, f0s = msd(col(r, "f0"))
        pf = col(r, "prom")
        pt = track_prom(r, f0)
        ok = np.isfinite(pt)
        Pt = bandpower(r, f0 - HALF, f0 + HALF)
        print(f"   {lbl:34s} {b:9s} {nrun(r):3d} ep {len(r):4d} win  f0 {f0m:6.2f} sd {f0s:4.2f}  "
              f"promFREE med {np.nanmedian(pf):8.1f} p90 {np.nanpercentile(pf, 90):8.1f}  "
              f"promTRK med {np.nanmedian(pt):8.1f} p90 {np.nanpercentile(pt, 90):8.1f}  "
              f"P(trk) {np.median(Pt):9.3g}  pres {100 * np.mean(pt[ok] >= PRESENCE) if ok.any() else float('nan'):5.1f}%")

    f0b = {}
    for b in ORDER:
        f0b[b] = pooled_f0(wrecs(b, hands=None))[0]

    for arm, lbl, nf, vmn in (("any_man", "manual, |v| 0.3-5.35", NFFT, 0.3),
                              ("man_fwd", "manual FORWARD (D)", NFFT, 0.3),
                              ("man_rev", "manual REVERSE, |v|>=0.3", NFFT, 0.3),
                              ("man_rev", "manual REVERSE, all v", 128, 0.0),
                              ("man_rev", "manual REVERSE, all v", NFFT, 0.0)):
        for b in ORDER:
            line(f"{lbl}  nfft={nf}", b, wrecs(b, arm=arm, vmin=vmn, nfft=nf), f0b[b])
        print()

    print("   -- NEAR-STATIONARY HIGH-EFFORT manual (|v| <= 0.6 m/s, sustained effort 2200-3300) --")
    print("      V61 read 470x median / 1571x p90 here; V64 read 8.9x / 12.4x.")
    for nf in (256, 128):
        for b in ORDER:
            r = nearstat(b, nf)
            line(f"near-stat manual  nfft={nf}", b, r, f0b[b])
        print()


def nearstat(build, nfft=128):
    """~stationary, high-effort, disengaged. Effort gate applied per-sample, then runs cut."""
    B = BUILDS[build]
    out = []
    for s in B["segs"]:
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        eff = np.abs(sustained(d["tq"], fs))
        m = (d["cc_lat"] <= 0.5) & (np.abs(d["cs_v"]) <= 0.6) & (eff >= 2200) & (eff <= 3300)
        if not m.any():
            continue
        f = np.fft.rfftfreq(nfft, 1 / fs)
        for a, b in runs_of(m, d["t"], nfft):
            x = d["tq"][a:b]
            for i in range(0, len(x) - nfft + 1, nfft):
                P = periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                f0g, prg = peak_prom(f, P, *GRIND)
                f0r, prr = peak_prom(f, P, *RATCH)
                sl = slice(a + i, a + i + nfft)
                out.append(dict(f=f, P=P, f0=f0g, prom=prg, fr=f0r, promr=prr, env=np.nan,
                                v=float(np.mean(np.abs(d["cs_v"][sl]))),
                                ang=float(np.mean(np.abs(d["ang"][sl]))),
                                eff=float(np.mean(eff[sl])),
                                seg=int(s), t0=float(d["t"][a + i]), run=(int(a), int(b))))
    return out


# ---------------------------------------------------------------- 6. spectra -------------------
def spectra():
    hdr("6.  POOLED RUN-AVERAGED SPECTRUM, engaged creep -- every peak above 3x, 3-46 Hz")
    for b in ORDER:
        r = wrecs(b)
        if not r:
            print(f"   {b}: n=0")
            continue
        f = r[0]["f"]
        P = np.mean([x["P"] for x in r], axis=0)
        out = []
        for j in range(1, len(P) - 1):
            if not (3.0 <= f[j] <= 46.0) or not (P[j] > P[j - 1] and P[j] >= P[j + 1]):
                continue
            near = (np.abs(f - f[j]) <= 6.0) & (np.abs(f - f[j]) > 1.5) & (f > 0.3)
            if near.sum() < 5:
                continue
            fl = float(np.median(P[near]))
            out.append((f[j], P[j] / fl if fl > 0 else np.inf, P[j]))
        out.sort(key=lambda z: -z[1])
        print(f"\n   {b}  ({len(r)} windows / {nrun(r)} runs)")
        for f0, pr, pw in out[:7]:
            print(f"        {f0:6.2f} Hz   prom {pr:9.1f}x   P {pw:.3e}")


def main():
    health()
    store = headline()
    presence(store)
    ratchet()
    common_shift()
    manual()
    spectra()


if __name__ == "__main__":
    main()
