"""SPEED SCHEDULE OF THE ASSIST-MAP SLOPE `a` -- re-derived from ROM, integer-exact.

WHY THIS EXISTS
---------------
`docs/handoffs/2026-08/HANDOFF-2026-08-21-v104-built-c4-boost-and-lever-b.md` sec 4.2 and `docs/STATE.md` both
state  `a` = 0.069 pooled engaged, speed-scheduled 0.123 (parking) -> 0.046 (120 km/h).
**No script on disk produces those three numbers** (grep for "0.069" hits only two .md files and
one comment line in model/eps_lkas_chain_model.py).  This file re-derives them from the ROM mirror so
the V104 dose can be re-priced per speed.

DEFINITIONS -- what `a` is, exactly
-----------------------------------
studies/dose/price_flat_6b86_boost.py:  G(f) = u/T_s   with u = aggregator SUM gp-0x6b94,
                           L(f) = -a.H_honda(f) = the gp-0x6b86 lane's contribution to G.
The lane is  T_s -> assist map -> gp-0x6b82 -> biquad -> gp-0x6b86 -> one slot of the sum.
=> a = w . d|gp-0x6b82| / d|T_s|,  with w the slot weight (taken as 1 by the record, since the
   handoff compares the ROM slope directly against the budget-closure 0.098).

SPEED UNITS -- 64.0625 counts per km/h  [EVIDENCE: docs/HANDOFF-2026-07-24-low-speed-steer-lockout
sec 4b, cal 0xC62EA = 320 = 5.000 km/h, 0xC62E8 = 12800 = 200.000 km/h, `mul 41 >> 6` decoded].
=> mode-24 speed breakpoints [0,960,2560,5120,7680,10240,12800] = 0/15/40/80/120/160/200 km/h.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import os
import sys
import numpy as np

os.environ.setdefault('ACCORD_FIRMWARE_ROOT', 'C:/Users/dudei/Desktop/Projects/accord-firmwares')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import assist_map_mirror as M                                     # noqa: E402
import _gate2_boost_lib as L                                      # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

CTS_PER_KPH = 64.0625
MODE = 24                       # the car is TVCA4; modes 24 and 26 are byte-identical
TQ_SCALE = 125.0 / 128.0        # CAN 399 tq = -(gp-0x4f60 * 125/128)


def lane_curve(speed_kph, tmax=8192, mode=MODE):
    """Integer-exact |gp-0x6b82| as a function of |gp-0x4f60|, at one speed."""
    sc = int(round(speed_kph * CTS_PER_KPH))
    A, B = M.stage_382d8(mode, sc)
    Xs, Ys = M.stage_389ec(A, B, sc, angle_10deg=0x2711)     # boost = 1024 (no angle boost)
    X, Y, Z, S = M.build_map(Xs, Ys)
    tt = np.arange(0, tmax + 1)
    out = np.array([abs(M.lane(int(t), X, Y, Z, S)['b82']) for t in tt], float)
    return tt, out, (X, Y, Z, S)


def slope_at(speed_kph, t_lo, t_hi, mode=MODE):
    """Secant slope d|b82|/d|Tsens| between two torque counts, then to per-CAN-count."""
    tt, out, _ = lane_curve(speed_kph, tmax=max(t_hi, 8192), mode=mode)
    return (out[t_hi] - out[t_lo]) / (t_hi - t_lo)


print("=" * 100)
print("0. SANITY -- the mirror's map at 0 / 40 / 120 km/h  (X = torque axis, Y = assist axis)")
print("=" * 100)
for v in (0, 40, 120):
    sc = int(round(v * CTS_PER_KPH))
    A, B = M.stage_382d8(MODE, sc)
    Xs, Ys = M.stage_389ec(A, B, sc, angle_10deg=0x2711)
    X, Y, Z, S = M.build_map(Xs, Ys)
    print(" %3d km/h (cnt %5d)  X=%s" % (v, sc, X))
    print("                       Y=%s" % (Y,))
    print("                       Z=%s   Z==Y: %s" % (Z, Z == Y))
    print("                       S/1024=%s" % ([round(s / 1024.0, 4) for s in S[1:]],))

# ------------------------------------------------------------------ 1. the schedule
print()
print("=" * 100)
print("1. THE SPEED SCHEDULE OF `a` -- secant slope of |gp-0x6b82| vs |gp-0x4f60|")
print("=" * 100)
SPEEDS = [0, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 140, 160, 200]
# operating-point windows.  p50 |tq| engaged is a few hundred counts; the ratchet lives small.
WINDOWS = [(0, 100), (0, 300), (100, 500), (300, 1000), (1000, 2000), (0, 8192)]
print("%8s" % 'km/h' + "".join("%14s" % ("dT %d-%d" % w) for w in WINDOWS))
SCHED = {}
for v in SPEEDS:
    tt, out, _ = lane_curve(v)
    row = [(out[hi] - out[lo]) / (hi - lo) for lo, hi in WINDOWS]
    SCHED[v] = row
    print("%8.0f" % v + "".join("%14.4f" % r for r in row))
print()
print("  ⇒ the record's 0.123 (parking) / 0.046 (120 km/h) is the LARGE-SIGNAL secant")
print("    (0 -> 8192 counts) column.  Reproduced: %.4f at 0 km/h, %.4f at 120 km/h."
      % (SCHED[0][-1], SCHED[120][-1]))
print("  ⚠ THE SMALL-SIGNAL SLOPE IS A COMPLETELY DIFFERENT NUMBER (see the left columns).")

# ------------------------------------------------------------------ 2. incremental slope curve
print()
print("=" * 100)
print("2. THE INCREMENTAL (LOCAL) SLOPE vs TORQUE -- the map is strongly CONCAVE")
print("=" * 100)
TQ_PTS = [50, 100, 200, 400, 800, 1600, 3200, 6400]
print("%8s" % 'km/h' + "".join("%10s" % ("@%d" % t) for t in TQ_PTS))
LOCAL = {}
for v in SPEEDS:
    tt, out, _ = lane_curve(v)
    row = []
    for t in TQ_PTS:
        h = max(8, int(0.05 * t))
        row.append((out[min(t + h, 8192)] - out[max(t - h, 0)]) / (min(t + h, 8192) - max(t - h, 0)))
    LOCAL[v] = row
    print("%8.0f" % v + "".join("%10.4f" % r for r in row))

np.savez(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '_scratch/data/_a_speed_schedule.npz'),
         speeds=np.array(SPEEDS, float),
         large=np.array([SCHED[v][-1] for v in SPEEDS]),
         windows=np.array([[SCHED[v][i] for i in range(len(WINDOWS))] for v in SPEEDS]),
         tq_pts=np.array(TQ_PTS, float),
         local=np.array([LOCAL[v] for v in SPEEDS]))
print()
print("  saved _scratch/data/_a_speed_schedule.npz")
