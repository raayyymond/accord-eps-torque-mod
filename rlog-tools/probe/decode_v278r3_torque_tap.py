#!/usr/bin/env python3
"""probe/decode_v278r3_torque_tap.py -- read the V279 rev-2 / V278 rev-3 DELIVERED-TORQUE tap
off CAN 427 (0x1AB).

WIRE (10-bit MOTOR_TORQUE field, DBC honda_accord_2017_can_ext: start bit 1, len 10, Motorola):
    value = ((d[0] & 0x7F) << 3) | (d[1] >> 5)
    sign  = (value >> 9) & 1            T = -(|T|) if sign else +|T|
    |T|   = (value & 0x1FF) << 3        (resolution 8 counts; structural ceiling 3072, the
                                          sum-clamp-driven ceiling actually reached is 2505 -> 313)
T = gp-0x6b38, the delivered LKAS lane torque -- see
memory/accord/firmware/accord-gp6b38-is-the-delivered-lane-torque-and-forwards-to-gp6b3c.md

🛑 BUILD GATE. This decoder is for V279 rev 2 / V278 rev 3's window (0x55DF0-0x55E11 rewritten to
this exact tap). V268 and everything upstream of it (V112 included) carry a DIFFERENT tap on this
same field (gp-0x6abc, see [[accord-check-build-lineage-before-proposing-lever]]). Reading a
non-V278r3/V279r2 route through this decoder produces NUMBERS THAT MEAN NOTHING -- pass
--build v278r3 (or v279r2) to say you know that and still want the raw decode printed with a loud
warning; otherwise the tool refuses to interpret (it will still print the CAN census).

Run:  python probe/decode_v278r3_torque_tap.py --build v278r3 <route-dir-or-segment-paths...>
"""
import argparse
import sys

# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
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

from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

FS_18F = 100.0
COUNTS_PER_DEGS = 8.0     # 0x18F rate wire, measured (see accord-feedback-operand memory)


def decode_1ab(d0, d1):
    val = ((d0 & 0x7F) << 3) | (d1 >> 5)
    sign = -1 if (val >> 9) & 1 else 1
    mag = (val & 0x1FF) << 3
    return sign * mag, val


def collect(paths):
    t1ab, Tv = [], []
    t18, rate, sca = [], [], []
    te4, cmd, req = [], [], []
    census = {}
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            if w != "can":
                continue
            ts = evt.logMonoTime * 1e-9
            for m in evt.can:
                src, addr = int(m.src), int(m.address)
                d = bytes(m.dat)
                census[(src, addr)] = census.get((src, addr), 0) + 1
                if src == 1 and addr == 0x1AB and len(d) >= 2:
                    T, raw = decode_1ab(d[0], d[1])
                    t1ab.append(ts); Tv.append(T)
                elif src == 1 and addr == 0x18F and len(d) >= 5:
                    r = (d[2] << 8) | d[3]
                    r = (r - 0x10000 if r & 0x8000 else r) * -1.0   # 0x18F rate_f = -gp-0x6a56
                    t18.append(ts); rate.append(r); sca.append((d[4] >> 3) & 1)
                elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                    c = (d[0] << 8) | d[1]
                    c = c - 0x10000 if c & 0x8000 else c
                    te4.append(ts); cmd.append(c); req.append((d[2] >> 7) & 1)
    return (np.array(t1ab), np.array(Tv), np.array(t18), np.array(rate), np.array(sca),
            np.array(te4), np.array(cmd), np.array(req))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="", help="v278r3 or v279r2 to enable interpretation")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)

    t1ab, Tv, t18, rate, sca, te4, cmd, req = collect(a.paths)
    print(f"events: 0x1AB {len(t1ab)}  0x18F {len(t18)}  0x0E4 {len(te4)}")
    if len(t1ab) == 0:
        print("NO 0x1AB FRAMES. Nothing to decode.")
        return 1

    interpret = a.build.lower() in ("v278r3", "v279r2", "v279")
    if not interpret:
        print("\n🛑 --build not given (or not v278r3/v279r2): printing raw decode only, no "
              "interpretation. If this route predates V278r3/V279r2 (e.g. it carries V112's "
              "gp-0x6abc tap, as the V276 reference route does), every number below is MEANINGLESS.")
    else:
        print(f"\nInterpreting as {a.build}'s delivered-torque tap (T = gp-0x6b38).")

    # join 0x18F rate and 0x0E4 cmd/req onto the 0x1AB (50 Hz) grid, most-recent-value-held
    def hold(t_src, v_src, t_dst):
        idx = np.searchsorted(t_src, t_dst, side="right") - 1
        out = np.full(len(t_dst), np.nan)
        ok = idx >= 0
        out[ok] = v_src[idx[ok]]
        return out

    rate_on1ab = hold(t18, rate, t1ab)
    sca_on1ab = hold(t18, sca, t1ab)
    cmd_on1ab = hold(te4, cmd, t1ab)
    req_on1ab = hold(te4, req, t1ab)
    eng = (sca_on1ab > 0.5) & (req_on1ab > 0.5)
    n_eng = int(np.nansum(eng))
    print(f"engaged frames on the 0x1AB grid: {n_eng} / {len(t1ab)}")

    if n_eng < 20:
        print("🛑 too few engaged frames -- no episode statistics computed.")
        return 0

    Te = Tv[eng]
    re = rate_on1ab[eng]
    ce = cmd_on1ab[eng]

    sat_duty = float((np.abs(Te) >= 2496).mean())
    valid_sign = re != 0
    damping_ne = float((np.sign(Te[valid_sign]) != np.sign(re[valid_sign])).mean())
    damping_eq = float((np.sign(Te[valid_sign]) == np.sign(re[valid_sign])).mean())

    print(f"\nSATURATION duty  P(|T| >= 2496)                         : {sat_duty:.4f}")
    print(f"DAMPING duty     P(sign(T) != sign(0x18F rate))  [derived]: {damping_ne:.4f}")
    print(f"DAMPING duty     P(sign(T) == sign(0x18F rate))  [docstr] : {damping_eq:.4f}")
    if interpret:
        print("  -> per adv278r3b's sign-chain derivation (T = -1*gain*lag(PID output ~ E), "
              "gain>0; fb DC gain positive on gp-0x6a56; wire = -gp-0x6a56), damping is the "
              "'!= ' row above. The build's docstring formula is the '==' row.")

    if len(Te) > 5 and np.nanstd(ce) > 0:
        slope, intercept = np.polyfit(ce, Te, 1)
        r = np.corrcoef(ce, Te)[0, 1]
        print(f"\nT vs 0xE4 command: slope {slope:.4f}  r {r:.4f}  n={len(Te)}")
    print(f"\n|T| p50 {np.median(np.abs(Te)):.0f}  p90 {np.percentile(np.abs(Te), 90):.0f}  "
          f"max {np.max(np.abs(Te)):.0f}  (structural clamp 3072, sum-clamp ceiling 2505)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
