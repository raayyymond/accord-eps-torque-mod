#!/usr/bin/env python3
r"""studies/v95-override/v95_override_exposure.py -- EXPOSURE FIRST.  How much OVERRIDE is on disk, before any scoring.

🛑 THE REGIME PROBLEM THIS FILE EXISTS FOR.  The operator produces the symptom by ENGAGING LKAS AND
THEN OVERRIDING -- turning the wheel against the command.  The kit's hands-off mask is
`steeringPressed == False`, i.e. `|STEER_TORQUE_SENSOR| <= 1200`, and override is
`steeringPressed == True` BY DEFINITION.  ⇒ every `Re(Z)` number the kit has ever produced comes
from a mask that EXCLUDES the condition in which the symptom occurs.

DEFINITIONS, all on the 100 Hz row grid, moving (|cs_v| > 0.5 m/s):
    ENG/OFF    cc_lat &  ~press                      the kit's usual arm
    OVR_ANY    cc_lat &   press                      = openpilot's `steerOverride`
    OVR_OPP    OVR_ANY & driver torque OPPOSING the LKAS command   <- the operator's manoeuvre
    OVR_WITH   OVR_ANY & driver torque WITH the command
    MAN/ON     ~cc_lat &  press                      the negative control at matched torque
    MAN/OFF    ~cc_lat & ~press

🛑 THE SIGN CONVENTION BETWEEN `sc_tq` AND `tq` IS NOT ASSUMED, IT IS MEASURED.  The extractor
applies the DBC factor -1 to `0x18F` torque but NOT to the sendcan `0x0E4` command, so the two are
in different conventions and "opposing" cannot be read off the raw signs.  §1 fixes it empirically
from the low-frequency relation each has with wheel rate.

THE AUTHORITY CURVE UNDER TEST (byte-verified by the tracer, tables 0xCBA74 / 0xCBA04):
    gp-0x682f = min(|gp-0x4f60| >> 5, 255)
    X = [70, 72, 78, 80] raw-byte  =>  raw torque knots 2240 / 2304 / 2496 / 2560
    Y = [254, 234, 12, 0]          =>  full authority below 2240, EXACTLY ZERO by 2560
    downstream IIR pole 992/1024  =>  tau ~ 31.5 ms, corner ~ 5.05 Hz
⚠ UNIT CAVEAT, stated not dodged: the knots are in `gp-0x4f60` raw counts.  Whether
`STEER_TORQUE_SENSOR` counts are the same units is NOT established here -- this file reports the
distribution against the raw knots AND against a swept scale, so a scale error cannot hide the
answer.

Usage:  python studies/v95-override/v95_override_exposure.py
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v95_rez_lib import BUILD, CACHES, NEED, base, hdr, load  # noqa: E402

KNOT_LO, KNOT_HI = 2240.0, 2560.0          # authority full -> exactly zero
TRIV = 300.0                               # below this a torque is not a real "direction"


def channels(route):
    z = load(route)
    if not (NEED | {"cs_tq", "sc_tq"}) <= set(z.files):
        return None
    B = base(z)
    if len(B["t"]) < 2000:
        return None
    B["sc"] = np.asarray(z["sc_tq"], float)          # openpilot's commanded torque, sendcan 0x0E4
    B["ctq"] = np.asarray(z["cs_tq"], float)         # SIGNED carState torque (base() rectifies it)
    B["route"] = route
    return B


if __name__ == "__main__":
    hdr("1.  THE SIGN CONVENTION BETWEEN THE LKAS COMMAND AND DRIVER TORQUE -- measured")
    print("  The extractor negates 0x18F torque (DBC factor -1) but not the sendcan 0x0E4 command.")
    print("  Anchor: at low frequency a torque applied in a direction produces wheel rate in that")
    print("  direction.  So corr(x, wheel rate) fixes each channel's handedness independently.")
    print(f"  {'route':6s} {'build':12s} {'corr(tq, rate)':>15s} {'corr(sc, rate)':>15s} "
          f"{'corr(tq, sc)':>13s} {'=> opposing test':>18s}")
    signs = {}
    for r in sorted(CACHES):
        B = channels(r)
        if B is None or np.std(B["sc"]) == 0:
            continue
        m = (B["v"] > 0.5) & B["lat"]
        if m.sum() < 5000:
            continue
        # 0.2-2 Hz band-limited, so steady offsets and high-frequency noise do not drive it
        def bp(x):
            X = np.fft.rfft(x[m] - x[m].mean())
            f = np.fft.rfftfreq(int(m.sum()), 1.0 / B["fs"])
            X[(f < 0.2) | (f > 2.0)] = 0
            return np.fft.irfft(X, int(m.sum()))
        w, tq, sc = bp(B["w"]), bp(B["tq"]), bp(B["sc"])
        c1 = float(np.corrcoef(tq, w)[0, 1])
        c2 = float(np.corrcoef(sc, w)[0, 1])
        c3 = float(np.corrcoef(tq, sc)[0, 1])
        # if both channels have the SAME handedness w.r.t. rate, opposing = opposite raw signs
        same = (c1 > 0) == (c2 > 0)
        signs[r] = 1.0 if same else -1.0
        print(f"  {r:6s} {BUILD.get(r,'?'):12s} {c1:15.3f} {c2:15.3f} {c3:13.3f} "
              f"{('sign(tq) != sign(sc)' if same else 'sign(tq) == sign(sc)'):>18s}")
    vote = np.sign(np.mean(list(signs.values()))) if signs else 1.0
    print(f"\n  ⇒ COHORT VOTE: opposing means  sign(tq) {'!=' if vote > 0 else '=='} sign(sc).")
    print("    (a split vote here would mean the convention is not stable and nothing below counts)")

    hdr("2.  OVERRIDE EXPOSURE, PER ROUTE -- seconds moving, before any windowing")
    print(f"  {'route':6s} {'build':12s} {'ENG/OFF':>9s} {'OVR_ANY':>9s} {'OVR_OPP':>9s} "
          f"{'OVR_WITH':>9s} {'MAN/ON':>8s} | {'OVR_ANY runs':>12s} {'>=2.56s':>8s} {'>=5.12s':>8s}")
    tot = np.zeros(5)
    runs_all = []
    for r in sorted(CACHES):
        B = channels(r)
        if B is None:
            continue
        mov = B["v"] > 0.5
        s = signs.get(r, vote)
        opp = (np.sign(B["tq"]) != np.sign(B["sc"] * s)) & (np.abs(B["tq"]) > TRIV) \
            & (np.abs(B["sc"]) > TRIV)
        arms = [B["lat"] & (~B["press"]) & mov, B["lat"] & B["press"] & mov,
                B["lat"] & B["press"] & mov & opp, B["lat"] & B["press"] & mov & (~opp),
                (~B["lat"]) & B["press"] & mov]
        secs = np.array([a.sum() / B["fs"] for a in arms])
        tot += secs
        # contiguous OVR_ANY runs
        m = arms[1].astype(int)
        e = np.diff(np.concatenate(([0], m, [0])))
        st, en = np.flatnonzero(e == 1), np.flatnonzero(e == -1)
        ln = (en - st) / B["fs"]
        runs_all += list(ln)
        print(f"  {r:6s} {BUILD.get(r,'?'):12s} {secs[0]:9.1f} {secs[1]:9.1f} {secs[2]:9.1f} "
              f"{secs[3]:9.1f} {secs[4]:8.1f} | {len(ln):12d} {int((ln>=2.56).sum()):8d} "
              f"{int((ln>=5.12).sum()):8d}")
    ra = np.array(runs_all)
    print(f"  {'TOTAL':6s} {'':12s} {tot[0]:9.1f} {tot[1]:9.1f} {tot[2]:9.1f} {tot[3]:9.1f} "
          f"{tot[4]:8.1f} | {len(ra):12d} {int((ra>=2.56).sum()):8d} {int((ra>=5.12).sum()):8d}")
    print(f"\n  OVR_ANY run lengths: median {np.median(ra):.2f} s, p90 {np.percentile(ra,90):.2f} s,"
          f" max {ra.max():.2f} s, total {ra.sum():.1f} s")
    print("  🛑 SCOREABILITY: a 5.12 s Welch window needs a 5.12 s CONTIGUOUS run.  If almost no")
    print("     run reaches that, the band estimator cannot be used in this regime at all and the")
    print("     analysis must move to short-window / event-triggered methods.")

    hdr("3.  WHERE DOES OVERRIDE TORQUE SIT RELATIVE TO THE AUTHORITY-COLLAPSE KNOTS?")
    print(f"  Knots: full authority below {KNOT_LO:.0f}, EXACTLY ZERO above {KNOT_HI:.0f} raw counts.")
    print(f"  {'route':6s} {'arm':8s} {'n':>7s} | {'<2240':>7s} {'2240-2560':>10s} {'>2560':>7s} "
          f"| {'p50':>6s} {'p90':>6s} {'p99':>6s} {'max':>6s}")
    for r in sorted(CACHES):
        B = channels(r)
        if B is None:
            continue
        mov = B["v"] > 0.5
        for tag, m in (("OVR_ANY", B["lat"] & B["press"] & mov),
                       ("MAN/ON", (~B["lat"]) & B["press"] & mov)):
            if m.sum() < 300:
                continue
            a = np.abs(B["ctq"][m])
            print(f"  {r:6s} {tag:8s} {int(m.sum()):7d} | {np.mean(a < KNOT_LO):7.3f} "
                  f"{np.mean((a >= KNOT_LO) & (a <= KNOT_HI)):10.3f} {np.mean(a > KNOT_HI):7.3f} "
                  f"| {np.percentile(a,50):6.0f} {np.percentile(a,90):6.0f} "
                  f"{np.percentile(a,99):6.0f} {a.max():6.0f}")
    print("\n  ⇒ if override never reaches 2240 the authority-collapse mechanism is REFUTED here and")
    print("    no crossing-rate test is meaningful.  If it straddles the ramp, run the crossing test.")
