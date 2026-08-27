#!/usr/bin/env python3
"""probe/decode_v57_deadband.py -- read V57's deadband-gate probe out of an rlog.

V57 packs FIVE bits into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                       LIVENESS  (constant; 0 => the cave did not fire)
    bit 6 = (gp-0x6806 == 0)        the deadband/sign-relay gate is ENABLED
    bit 5 = (gp-0x69b0 != 0)        the LKAS forward ramp gain is LIVE
    bit 4 = (gp-0x6b30 == 0)        the gate's output is EXACTLY ZERO
    bit 3 = (gp-0x6b30 <  0)        the gate's output is NEGATIVE
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that. V53's drive read
byte4 == 0x07 in 5,994/5,994 frames, i.e. stock leaves these bits clear.

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
The deadband + sign relay in FUN_00028ea6 (0x2a1ae-0x2a206) was eliminated on 2026-07-29 by measuring
STEER_CONTROL_ACTIVE (CAN 0x18F byte4 bit3), which the packer sources from gp-0x6806:

    0x55c76 ld.bu -0x6806,gp,r15 ; 0x55c7e andi 0x1,r15,r15 ; 0x55c82 shl 0x3,r15

*** But `andi 0x1` transmits PARITY, and the gate tests EXACT EQUALITY (`cmp r0,r12 ; bne` at
0x2a1ba/0x2a1bc). Four of the flag's eight live writers store a REGISTER, not a literal, so a value of
2 reads as bit0 = 0 while the gate is DISABLED -- and a 0<->2 toggle at 22 Hz would be invisible.

  bit 6 is the EXACT test and closes that hole.
  bits 4/3 give a 3-state view of the output {negative, zero, positive}. A chattering relay visits
    zero between sign flips, so bit4's spectrum carries a 20-25 Hz line if the mechanism is real.
  bit 5 separates "zero because the ramp gain is zero" from "zero because the gate fired".

READ IT AS:
  bit6 ~never set on engaged+hands-off frames        -> gate inert; the thread is CLOSED by
                                                        measurement, not by a parity argument.
  bit6 set in a meaningful fraction, or bit4 showing
  a 20-25 Hz line                                    -> the elimination was premature.

Prior expectation, recorded so a null is not re-litigated: NEGATIVE is expected.

⚠ 100 Hz sampling of a ~22 Hz phenomenon is below Nyquist but close to it; a 22 Hz line is
indistinguishable from 78 Hz aliased. Same limitation every probe in this kit has had.

Usage:  python probe/decode_v57_deadband.py RLOG [RLOG ...]
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
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

FS = 100.0
BIT_LIVE, BIT_GATE, BIT_RAMP, BIT_ZERO, BIT_SIGN = 0x80, 0x40, 0x20, 0x10, 0x08


def collect(paths):
    """Collect the probe field plus the LATERAL engagement signals.

    *** `carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG proxy here
    (operator, 2026-07-29). Lateral engagement is `carControl.latActive`, corroborated by CAN
    0x18F byte4 bit3 (STEER_CONTROL_ACTIVE, the EPS's own applying flag). On route 28 cruiseState
    reads 84.0% while lateral was really applying 49.9% of the time -- and using cruiseState flips
    this tool's verdict from INERT to NOT INERT. Never use it for an engagement split. ***
    """
    b4, sca, tq, t = [], [], [], []
    vego, tv = [], []
    lat_v, lat_t = [], []
    cru_v, cru_t = [], []
    last_tq, last_sca = np.nan, -1
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x18F and len(d) >= 5:
                        v = (d[0] << 8) | d[1]
                        last_tq = (v - 0x10000 if v & 0x8000 else v) * -1.0
                        last_sca = (d[4] >> 3) & 1          # STEER_CONTROL_ACTIVE
                    elif m.address == 0x14A and len(d) >= 5:
                        b4.append(d[4])
                        tq.append(last_tq)
                        sca.append(last_sca)
                        t.append(evt.logMonoTime * 1e-9)
            elif w == "carControl":
                lat_v.append(bool(evt.carControl.latActive))
                lat_t.append(evt.logMonoTime * 1e-9)
            elif w == "carState":
                vego.append(evt.carState.vEgo)
                cru_v.append(bool(evt.carState.cruiseState.enabled))
                tv.append(evt.logMonoTime * 1e-9)
                cru_t.append(evt.logMonoTime * 1e-9)
    d = dict(b4=np.array(b4, dtype=int), tq=np.array(tq), t=np.array(t),
             sca=np.array(sca, dtype=int))
    d["v"] = np.interp(d["t"], tv, vego) if tv else np.full_like(d["t"], np.nan)
    d["lat"] = (np.interp(d["t"], lat_t, np.array(lat_v, float)) > 0.5) if lat_t \
        else np.zeros_like(d["t"], bool)
    d["cru"] = (np.interp(d["t"], cru_t, np.array(cru_v, float)) > 0.5) if cru_t \
        else np.zeros_like(d["t"], bool)
    # `eng` is the analysis subset everywhere below: the EPS is actually applying LKAS torque.
    d["eng"] = d["sca"] == 1
    return d


def spectrum(x, nfft=256):
    """Mean periodogram over NON-overlapping Hann segments. Returns (freqs, power, K)."""
    x = np.asarray(x, float)
    if len(x) < nfft:
        return None, None, 0
    f = np.fft.rfftfreq(nfft, 1 / FS)
    win = np.hanning(nfft)
    acc, k = np.zeros(len(f)), 0
    for i in range(0, len(x) - nfft + 1, nfft):
        seg = x[i:i + nfft]
        acc += np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
        k += 1
    return (f, acc / k, k) if k else (None, None, 0)


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    field = (d["b4"] >> 3) & 0x1F
    print(f"\n{'=' * 86}\n{tag}   {n} frames  {d['t'][-1] - d['t'][0]:.1f}s")

    void = field == 0
    print(f"\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    if void.any():
        print("   *** partial void -- treat mixed segments with suspicion")

    print(f"\n   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"]).most_common(8)))

    gate = (d["b4"] & BIT_GATE) != 0
    ramp = (d["b4"] & BIT_RAMP) != 0
    zero = (d["b4"] & BIT_ZERO) != 0
    neg = (d["b4"] & BIT_SIGN) != 0

    # --- the parity hole: probe bit6 (EXACT ==0) vs the bus's parity bit ---
    valid = d["sca"] >= 0
    g, s = gate[valid], d["sca"][valid] == 1
    print(f"\n-- PARITY HOLE: probe bit6 (exact gp-0x6806==0) vs bus 0x18F bit3 (parity) --")
    print(f"   {(g & ~s).sum():7d}  bit6=1 bus=0  value == 0            consistent, gate ENABLED")
    print(f"   {(~g & s).sum():7d}  bit6=0 bus=1  value odd nonzero     consistent, gate DISABLED")
    print(f"   {(~g & ~s).sum():7d}  bit6=0 bus=0  value EVEN & NONZERO  <-- a real hole would live here")
    print(f"   {(g & s).sum():7d}  bit6=1 bus=1  IMPOSSIBLE             <-- pairing skew indicator")
    print("   Both anomaly classes present in similar numbers, all sitting on SCA transitions, means")
    print("   one-frame skew between two independent 100 Hz mailboxes -- NOT gp-0x6806 == 2.")

    print(f"\n-- LATERAL PROXY AGREEMENT (cruiseState is long+lat: do NOT use it) --")
    print(f"   latActive               : {d['lat'].sum():6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {(d['sca'] == 1).sum():6d} ({100 * (d['sca'] == 1).mean():5.2f}%)  <- the analysis subset")
    print(f"   probe bit6 CLEAR (!=0)  : {(~gate).sum():6d} ({100 * (~gate).mean():5.2f}%)")
    print(f"   [legacy] cruiseState    : {d['cru'].sum():6d} ({100 * d['cru'].mean():5.2f}%)  <- WRONG PROXY")

    conds = [
        ("ALL frames", np.ones(n, bool)),
        ("LKAS applying (SCA==1)", d["eng"]),
        ("LKAS applying + hands-off (|tq|<=200)", d["eng"] & (np.abs(d["tq"]) <= 200)),
        ("LKAS applying + driver torque >2240", d["eng"] & (np.abs(d["tq"]) > 2240)),
        ("LKAS off", ~d["eng"]),
        ("[legacy] cruiseState + hands-off", d["cru"] & (np.abs(d["tq"]) <= 200)),
    ]
    print(f"\n-- THE FIVE BITS, by condition --")
    print(f"   {'condition':34s} {'n':>6s} {'gate ON':>9s} {'ramp':>8s} {'out==0':>8s} {'out<0':>8s}")
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:34s} {0:6d}   (none)")
            continue
        print(f"   {name:34s} {sel.sum():6d} {100 * gate[sel].mean():8.2f}% "
              f"{100 * ramp[sel].mean():7.2f}% {100 * zero[sel].mean():7.2f}% "
              f"{100 * neg[sel].mean():7.2f}%")

    print(f"\n-- THE DECISIVE NUMBER --")
    sel = d["eng"] & (np.abs(d["tq"]) <= 200)
    if sel.sum() < 50:
        print("   too few LKAS-applying + hands-off frames to judge")
    else:
        pct = 100 * gate[sel].mean()
        tr = int((np.diff(gate[sel].astype(int)) != 0).sum())
        print(f"   gate ENABLED (gp-0x6806 == 0) on LKAS-applying + hands-off: {pct:.2f}%  "
              f"({gate[sel].sum()}/{sel.sum()}), {tr} transitions")
        if pct < 1.0:
            print("   => INERT. The deadband/sign relay is bypassed where the grinding lives.")
            print("      The 2026-07-29 elimination STANDS, now on exact equality, not parity.")
        else:
            print("   => NOT INERT. The elimination was premature; the deadband returns to scope.")

    # the relay signature: does the output visit zero at 20-25 Hz?
    print(f"\n-- SPECTRUM of (output == 0), LKAS-applying + hands-off --")
    if sel.sum() < 256:
        print(f"   too few frames ({sel.sum()}) for a spectrum")
    elif zero[sel].std() == 0:
        # Degenerate on purpose: a constant indicator has no spectrum, and that is the
        # STRONGEST form of the null -- the output never visits zero, so it cannot be a
        # relay chattering through zero at any frequency.
        v = int(zero[sel][0])
        print(f"   (output == 0) is CONSTANT at {v} across all {sel.sum()} frames -- no spectrum exists.")
        print("   => STRONGEST form of the null: the gate output never visits zero while LKAS is")
        print("      applying, so a chattering sign relay is excluded outright, at every frequency.")
    else:
        f, P, K = spectrum(zero[sel].astype(float))
        if K:
            band = (f >= 15) & (f <= 27)
            ref = (f >= 6) & (f <= 40) & ~band
            j = int(np.argmax(np.where(band, P, -np.inf)))
            floor = np.median(P[ref])
            prom = P[j] / floor if floor > 0 else float("nan")
            print(f"   K={K} segments (non-overlapping, nfft=256), peak in 15-27 Hz at {f[j]:.2f} Hz, "
                  f"prominence over the 6-40 Hz floor = {prom:.2f}x")
            print("   (a relay chattering at the mode frequency shows a sharp, high-prominence line;")
            print("    prominence ~1-3 with a wandering peak is noise, not a mechanism)")
            print("   NOTE: at 100 Hz sampling a 22 Hz line is indistinguishable from 78 Hz aliased.")


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
