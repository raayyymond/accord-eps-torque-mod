#!/usr/bin/env python3
r"""
V110 -- V109 PLUS THE FIRST RATCHET LEVER THAT PASSES BOTH GATES.  Kd, 2048 -> 1024.

WHAT THIS IS
------------
V110 = V109, plus `cal(0xC6AE6)` 2048 -> 1024.  Nothing else.  **Two payload bytes, one CRC trailer.**
🛑 **FLY IT AFTER V108/V109, NOT INSTEAD OF THEM.**  There is an unrefutable risk that it removes
damping in the 18-35 Hz grinding bands -- see the block below before shipping.

`0xC6AE6` is **Kd**, the derivative gain of the Path-2 PID in `FUN_0003a382`:

    ERR   = clamp(gp-0x4f60 - bias, +-0x2800)                     # gp-0x4f60 IS the torque sensor
    D_raw = clamp( ((ERR[n] - ERR[n-1]) * cal(0xC6AE6)) >> 10 , +-0x2800 )   # 0x3A836/38/44
    out   = ((D + I + P) >> 5) * gainD/1024 * polarity * validity  # 0x3A874-88
      -- the EMA pole cal(0xC644A) = 1024 is EXACT PASS-THROUGH, so D really is a BARE differencer
      -- gainD (the L4 output table at tp+0x77b0) is FLAT 1024/1024 = unity at all three knots

**VIRGIN**: 2048 in stock, V108 and V109, byte-identical.  **One reader (`0x3A460`), zero writers.**

WHY THIS IS THE RIGHT SHAPE OF LEVER -- AND WHY THE CENSUS HAD TO BE FIXED FIRST
--------------------------------------------------------------------------------
The ratchet is a ~7.4-8.6 Hz LINE: engagement-required, hands-off, peaking at 25-40 km/h, **9.06x the
manual amplitude** -- the most engagement-selective band in the spectrum -- and **exactly zero on STOCK
in 3 of 4 highway cells**.  Sixty builds never moved it, and the reason is now understood:

    T_bar = Z0*Om_w + P*(agg),   agg = F*Om_w + L*T_bar
      =>   Z = T_bar/Om_w = (Z0 + P*F) / (1 - P*L)

**Every aggregator lane fed by column torque or motor rate is a term in `L` -- a DENOMINATOR term, not
an additive torque.**  The kit had been summing denominator terms into a numerator, which is why the
budget never closed and never could: the numerator actually required is **146-408 ct.s/rad, an order of
magnitude BELOW what was already priced.**  What is really happening is that
**`Q_eff/Q_passive = 14.3` -- the loop cancels ~93 % of the mode's own natural damping.**
⇒ **A calibration lever can touch this, but ONLY through Q, and ONLY if it is sized as a LOOP GAIN.**
An additive-torque lever is known-useless here, which retro-explains V39/V41/V43/V56/V97/V103/V105.

D IS THE ONLY PID BRANCH THAT PUMPS AT 7.8 Hz
----------------------------------------------
Measured into `gp-0x6ad4` at 7.79 Hz, POL included:
```
   P    |H| 0.2500   arg +180.00 deg    Re(Z)  +844   DAMPING
   I    |H| 0.0611   arg  +91.40 deg    Re(Z)  +296   damping
   D    |H| 0.09788  arg  -91.40 deg    Re(Z)  -458   ** PUMPING **
   P+I+D                                Re(Z)  +682   net damping
```
So the PID as a whole damps there -- **you cannot get the pump out of `gp-0x6ad4` without attacking the
D branch specifically**, which is exactly what this cell does.

⭐ **AND THE SIZE IS LEVERAGED.**  `|D| = 0.0979` against the L-table's nominal sum 1.876 (ceiling
2.825) ⇒ **D is 3.5-5.2 % of total loop gain**, and halving Kd removes **~1.7-2.6 % of `|L|`**.  That
sounds small.  It is not, because `Q ~ 1/(1 - |PL|)` and the loop is marginal:
```
   Q_eff/Q_pass    |PL|     amplification    Q reduction from -1.7%   from -2.6%
       14.3       0.9301        13.30              18.4 %                25.7 %
       10.0       0.9000         9.00              13.3 %                19.0 %
        6.0       0.8333         5.00               7.8 %                11.5 %
        4.0       0.7500         3.00               4.9 %                 7.2 %
```
⚠ **The 14.3 rests on a ring-down Q ~ 40 whose own estimators are recorded as SATURATING and REVERSING
above zeta ~ 0.05**, and `accord-ratchet-is-a-lightly-damped-resonance` says plainly that
"zeta 0.017-0.036's Q is an UPPER BOUND".  **So read the top row as optimistic and the bottom as
conservative.  Even the conservative row is a 5-7 % Q reduction from two bytes.**

D's SHAPE IS WHY IT IS SAFE -- and it is the opposite of the other candidate
----------------------------------------------------------------------------
`H_D(f) = (Kd/1024) * (1 - z^-1)`, internal to ERR.  **Kd scales MAGNITUDE ONLY -- D's own phase is
Kd-independent and never reverses sign anywhere from 2 to 500 Hz:**
```
   f Hz     Kd=2048 (stock)      Kd=1024 (V110)      Kd=512        Kd=0
    1.00   0.0126 <+89.8 deg   0.0063 <+89.8 deg   0.0031        0
    3.00   0.0377 <+89.5       0.0188 <+89.5       0.0094        0
    7.79   0.0979 <+88.6       0.0489 <+88.6       0.0245        0
   21.73   0.2729 <+86.1       0.1364 <+86.1       0.0682        0
   40.00   0.5013 <+82.8       0.2507 <+82.8       0.1253        0
  100.00   1.2361 <+72.0       0.6180 <+72.0       0.3090        0
```
⇒ **Halving Kd cannot rotate anything into a new sector.**  It is a pure magnitude change on a branch
whose phase is fixed, and it is **exactly zero at DC by construction** -- so it costs no steady-state
assist and no steering rate.
⭐ **Contrast with the candidate that was REJECTED**: `0xC6384` (the assist-map per-segment slope cap,
2048 = Q10 2.000) is **memoryless -- flat magnitude, 0 deg phase, IDENTICAL from DC to Nyquist.**  A
dose there changes loop gain by the same fraction at 1, 7.79, 21.73, 40 and 100 Hz **simultaneously**,
plus DC steady-state feel, plus manual steering.  There is no way to target 7.8 Hz with it without
re-litigating the 18-35 Hz bands V108 and V109 just spent their whole budget fixing.  **And whether it
is currently BINDING AT ALL is UNRESOLVED** -- the natural slope depends on a history-dependent slew
mechanism that cannot be evaluated from a static image.  **DO NOT SHIP `0xC6384`.**

GATE 1 -- CLEAN
---------------
`0xC6AE6`: **exactly 1 reader (`0x3A460`), 0 writers** (tp-relative ROM -- architecturally none
possible), confirmed by full function disassembly, not merely a byte scan.  No shadow-lockstep twin on
Kd or on its direct output `gp-0x6ad4`; the aggregate sum downstream IS shadow-checked, and that check
runs unmodified on whatever value it computes.  No int/float mirror of the `0xC674E`-quad class -- the
one that HARD-FAULTED V27 the instant the wheel was turned.
⚠ `get_bulk_xrefs` returned `[]` for this address -- the documented gp/tp-relative misleading-zero,
hit a fourth time this session-family.  **Never treat it as a zero.**

GATE 2 -- and one honest limit
-------------------------------
D's own phase is fixed and never reverses (table above), so no sector crossing is reachable by scaling
it.  🛑 **What CANNOT be given from the code: the closed-loop margin translation at frequencies other
than 7.79 Hz.**  That needs `G_bar(f)`, the mechanical plant's own torque/rate phase, which is **not in
the firmware image** and is anchored only at 7.79 Hz (via the assist map's memoryless identity).
**Undecidable from code beyond that point; it would need on-car Re(Z) at those frequencies.**

🛑🛑 THE ORCHESTRATOR DID NOT ACCEPT THE REFUTATION THIS BUILD WAS PROPOSED ON.  READ THIS FIRST.
--------------------------------------------------------------------------------------------------
The agent that gated this lever reported that
`memory/accord/builds/accord-six-levers-closed-on-arithmetic.md`'s verdict -- **"D damps 16-35 Hz,
cost 3-4x the benefit"** -- had **"no computation behind it anywhere in the kit."**  **CHECKED, AND THAT
IS NOT RIGHT.**  The numbers `-0.217` (18-22 Hz) and `-0.336` (26-31 Hz) appear in **five** files
including an archived session state, so they have provenance.  And the refutation does not survive the
same agent's own admission that **the closed-loop translation away from 7.79 Hz needs `G_bar(f)`, the
plant phase, which is NOT in the image and is anchored ONLY at 7.79 Hz.**

**The orchestrator's own arithmetic makes the risk concrete.**  D's phase in its OWN frame barely moves:
```
    f Hz     6.00   7.79   9.00  18.00  22.00  26.00  31.00  35.00
  phase   +88.92 +88.60 +88.38 +86.76 +86.04 +85.32 +84.42 +83.70   (own frame)
```
**Only -2.2 deg between 7.79 and 20 Hz.**  Anchored at the one place we have a rotation (7.79 Hz ->
-91.40 deg, Re(Z) -458, PUMPING), carrying D's own phase alone puts 20 Hz at -93.60 deg, cos = -0.063 --
still pumping.  ⇒ **For D to DAMP at 18-35 Hz as the memory claims, the PLANT must supply ~+90 deg of
rotation across that span.  A plant resonance at 7.8 Hz rotates ~180 deg through it, so that is entirely
possible.**  ⇒ **The memory's claim is PLAUSIBLE AND CANNOT BE REFUTED FROM THE IMAGE.**

🛑 **THEREFORE THE RISK IS REAL: halving Kd may REMOVE DAMPING at 18-22 and 26-31 Hz -- the exact bands
V108 and V109 exist to fix.**  If the memory is right, V110 trades a 7.8 Hz benefit for a 2.9-4.4x cost
in the operator's own grinding bands.
⇒ **DO NOT FLY V110 UNTIL V108 OR V109 HAS ESTABLISHED A GRINDING BASELINE.**  It is built, verified and
on disk as a LATER step, not as something to fold in.  Flying it first risks undoing the thing the
operator asked for first.
⇒ **What would settle it: on-car `Re(Z)` at 18-22 and 26-31 Hz** -- the same measurement that anchored
7.79 Hz.  Until then, nobody knows D's sign above 16 Hz, and that is a reason for caution, not confidence.

THE ORIGINAL GATING AGENT'S POSITION, KEPT FOR THE AUDIT TRAIL
---------------------------------------------
`memory/accord/builds/accord-six-levers-closed-on-arithmetic.md` carries **"D damps 16-35 Hz ... cost
3-4x the ratchet benefit"** as a CLOSED verdict.  **There is no computation behind it anywhere in the
kit** -- provenance-chased twice to a review file that explicitly DECLINES to compute 18-22 and
26-31 Hz.  It is contradicted by `BUILD-LINEAGE.md`'s own Kd row (22-26 Hz crossover) and by the
three-drive-replicated on-car `Re(Z)` (`accord-rez-antidamping-replicated-three-drives`): the worst
measured band is **9-12 Hz (-4130 to -4593)**, 12-16 Hz is still strongly anti-damped, the crossover is
**22-26 Hz**, and it is damped only above 26-31 Hz.  **Nothing supports "16-35 Hz damps."**
⇒ Its position was that the standing objection is refuted.  **The orchestrator does NOT accept that**
-- see the block above.  What both agree on: no OTHER GATE-2 objection was found, and the 22-26 Hz
crossover in the measured on-car `Re(Z)` is about the TOTAL `Z`, not about D's own contribution.

WHAT THIS IS NOT
----------------
🛑 **It is not a fix on its own, and it must not be sold as one.**  You cannot move a loop that cancels
~93 % of its own damping by cutting 2 % of the loop gain -- the leverage table above is a *Q* reduction
of 5-26 %, not an extinction.  **It is the first ratchet lever in this kit's history that passes GATE 1
and GATE 2 and is a genuine DENOMINATOR term.**  Score it as a dose step on Q, not as a cure.
⚠ **It touches MANUAL steering too.**  `FUN_0002214a` gates `FUN_0003a382` on `gp-0x67fa & 0xf` against
mask `0xc30` = states {4, 5, 10, 11}, so this is not LKAS-only.  Its DC cost is exactly zero, so there
should be no steady-state feel change -- but the operator should be told it is not engaged-gated.

Usage:
    ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares \
    ACCORD_V110_WRITE=rwd python builds/v108_plus/build_v110_tva.py
"""
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

import cmath
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V110_WRITE", "").strip().lower()

BASE_NAME = "_v109_V109-V108BASE-ALPHA2.C40DC.14_plain_image.bin"
BASE_SHA = "e9eb51fcad9ffc8768cd3e8eb601619d0f2acc0f702f01c4732243c70cc7f4d6"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
Y_STOCK, Y_V108 = V106B.Y_STOCK, (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

KD_CAL, KD_OLD, KD_NEW = 0xC6AE6, 2048, 1024   # THE ONLY EDIT
AD_CAL, AD_VAL = 0xC644A, 1024                 # the D EMA pole -- EXACT pass-through.  V43 flew 1024->64, NULL.
SLOPE_CAP = 0xC6384                            # the REJECTED candidate.  Must stay 2048.
ALPHA2_CAL, ALPHA2_V109 = 0xC40DC, 14
CLAMP_CAL, MONITOR_TRIP = V106B.CLAMP_CAL, V106B.MONITOR_TRIP
BQ_ADDR, BQ_LEN = 0xC60A8, 16
GAIN_CAL = 0xC6CD0

# |D| as a fraction of the measured loop-gain sum, and the Q leverage it buys.
L_NOMINAL, L_CEILING = 1.876, 2.825

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def H_D(kd, f, fs=1000.0):
    """H_D(f) = (Kd/1024) * (1 - z^-1), internal to ERR.  Kd scales MAGNITUDE ONLY."""
    z = cmath.exp(-2j * cmath.pi * f / fs)
    h = (kd / 1024.0) * (1 - z)
    return abs(h), cmath.phase(h) * 180 / cmath.pi


FROZEN = dict(V106B.FROZEN)
FROZEN[GAIN_CAL] = (2, 5346, "0xC6CD0 -- the 6.000x forward LKAS gain.  NEVER lower it.")
FROZEN[ALPHA2_CAL] = (2, ALPHA2_V109, "0xC40DC -- alpha2, from V109")
FROZEN[AD_CAL] = (2, AD_VAL, "0xC644A -- the D EMA pole, EXACT pass-through.  V43 flew 1024->64: NULL.")
FROZEN[SLOPE_CAP] = (2, 2048, "0xC6384 -- the REJECTED candidate: memoryless, DC-to-Nyquist flat.  DO NOT SHIP.")
FROZEN[0xC40DA] = (2, 3, "0xC40DA -- alpha2's sibling -> gp-0x6c2e.  Independent at the producer.")
FROZEN[0xC643C] = (2, 37, "0xC643C -- alpha0, SHARED with the 0xC520C cap-table index.")
FROZEN[0xC620A] = (2, 12800, "0xC620A -- the oscillation detector's threshold.")
FROZEN[0xC40BC] = (2, 600, "0xC40BC -- Honda's 600, restored by V108.")
FROZEN[0xC40D2] = (1, 204, "K1 -- kept knowingly; reverting makes the wheel HEAVIER")
FROZEN[0xC61BE] = (2, 15360, "0xC61BE -- measured IDLE; E3 was pulled at V108.")
FROZEN[0x55E10] = (1, 0xA5, "427 SCALER -- sar 5, from V108")
FROZEN[0x55DF2] = (1, 0xD4, "427 SOURCE low byte -- gp-0x6c2c, from V107")
FROZEN[KD_CAL] = (2, KD_NEW, "0xC6AE6 -- Kd, THE EDIT")


def assert_frozen(buf, label, extra_exempt=()):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        if a in extra_exempt:
            continue
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got!r}, expected {exp!r} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN) - len(extra_exempt)} FROZEN cells at expected values")


def build():
    print("=" * 102)
    print("  V110 -- V109 + Kd 2048 -> 1024.  The first ratchet lever to pass both gates.")
    print("=" * 102)

    print("\n  [1] LOAD AND PIN THE BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(base).hexdigest() == BASE_SHA, f"base is V109 ({BASE_SHA[:16]}...)")
    check(hashlib.sha256(stock).hexdigest() == STOCK_SHA, "stock image sha256 matches the record")
    check(walk_all_blocks(bytes(base)) == 0, "base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] PRE-IMAGE")
    check(u16(base, KD_CAL) == KD_OLD == u16(stock, KD_CAL),
          f"  0x{KD_CAL:05X} (Kd) = {KD_OLD} on the car AND in stock -- VIRGIN")
    check(u16(base, AD_CAL) == AD_VAL == u16(stock, AD_CAL),
          f"  0x{AD_CAL:05X} (the D EMA pole) = {AD_VAL} = EXACT pass-through, so D is a BARE differencer")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V109, "  alpha2 = 14, carried from V109")
    check(rd(base, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN),
          "  the biquad is Honda's -- V108's revert, and alpha2's prerequisite")
    check(rec_y(base, ENGAGED_MODES[0]) == Y_V108, f"  the Y row is V108's {Y_V108}")
    assert_frozen(base, "BASE(V109)", extra_exempt=(KD_CAL,))

    print("\n  [3] THE EDIT -- Kd 2048 -> 1024.  TWO BYTES.")
    struct.pack_into("<H", code, KD_CAL, KD_NEW)
    attributed |= {KD_CAL, KD_CAL + 1}
    print(f"      0x{KD_CAL:05X}  {KD_OLD} -> {KD_NEW}   (Kd/1024: {KD_OLD/1024:.3f} -> {KD_NEW/1024:.3f})")
    print()
    print(f"      {'f Hz':>7}  {'|D| Kd=2048':>12} {'|D| Kd=1024':>12}  {'phase':>9}  (phase is Kd-INDEPENDENT)")
    for f in (1, 3, 7.79, 21.73, 40, 100):
        a, pa = H_D(KD_OLD, f)
        b, pb = H_D(KD_NEW, f)
        check_phase = abs(pa - pb) < 1e-9
        print(f"      {f:7.2f}  {a:12.4f} {b:12.4f}  {pa:+8.2f}   {'same' if check_phase else 'MOVED'}")
        if not check_phase:
            raise SystemExit("phase moved with Kd -- the model is wrong")
    check(abs(H_D(KD_OLD, 7.79)[0] - 0.09788) < 5e-4,
          "  |D| at 7.79 Hz reproduces the census's 0.09788 -- the mirror is right")
    check(abs(H_D(KD_OLD, 0.0)[0]) < 1e-12,
          "  |D| is EXACTLY ZERO at DC -- no steady-state assist cost, no steering-rate cost")

    print()
    d_frac_lo = H_D(KD_OLD, 7.79)[0] / L_CEILING
    d_frac_hi = H_D(KD_OLD, 7.79)[0] / L_NOMINAL
    dl_lo, dl_hi = d_frac_lo / 2, d_frac_hi / 2
    print(f"      |D| at 7.79 Hz = {H_D(KD_OLD, 7.79)[0]:.4f} against |L| {L_CEILING} (ceiling) .. "
          f"{L_NOMINAL} (nominal)")
    print(f"      => D is {100*d_frac_lo:.1f}-{100*d_frac_hi:.1f} % of the loop gain; "
          f"halving Kd removes {100*dl_lo:.1f}-{100*dl_hi:.1f} % of |L|")
    print()
    print(f"      LEVERAGE -- Q ~ 1/(1-|PL|), so dQ/Q = (|PL|/(1-|PL|)) * d|L|/|L|:")
    print(f"      {'Qeff/Qpass':>11} {'|PL|':>8} {'amp':>7} | {'Q cut lo':>9} {'Q cut hi':>9}")
    for ratio in (14.3, 10.0, 6.0, 4.0):
        PL = 1 - 1 / ratio
        amp = PL / (1 - PL)
        print(f"      {ratio:11.1f} {PL:8.4f} {amp:7.2f} | "
              f"{100*(1-1/(1+amp*dl_lo)):8.1f}% {100*(1-1/(1+amp*dl_hi)):8.1f}%")
    print("      ⚠ the 14.3 row rests on a ring-down Q ~ 40 whose estimators SATURATE and REVERSE")
    print("        above zeta ~ 0.05; read it as optimistic and the 4.0 row as conservative.")

    print("\n  [4] EVERYTHING THAT MUST NOT HAVE MOVED")
    check(u16(code, SLOPE_CAP) == 2048,
          "  0xC6384 UNTOUCHED -- the rejected candidate: memoryless, flat DC-to-Nyquist, binding UNRESOLVED")
    check(u16(code, AD_CAL) == AD_VAL, "  0xC644A untouched -- V43 flew it 1024->64 and it was NULL")
    check(u16(code, ALPHA2_CAL) == ALPHA2_V109, "  alpha2 = 14 carried")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN), "  the biquad is still Honda's")
    check(s16(code, CLAMP_CAL) == 511 and 511 < MONITOR_TRIP,
          f"  0xC407E = 511 < {MONITOR_TRIP} -- RULE-11 interlock intact BY CONSTRUCTION")
    check(rd(code, V106B.CAVE_BASE, V106B.CAVE_LEN) == rd(base, V106B.CAVE_BASE, V106B.CAVE_LEN),
          "  THE CAVE IS BYTE-IDENTICAL -- no code-cave edit, the kit's only bricking class")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == Y_STOCK, f"  mode {m} (MANUAL) still Honda stock")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == Y_V108 and rec_x(code, m) == X_EXPECT,
              f"  mode {m} Y row unchanged from V108")
    assert_frozen(code, "V110")

    print("\n  [5] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [6] FULL BYTE DIFF vs V109 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        tag = "CRC" if any(lo <= x < hi for x in (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V110 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V110-V109BASE-KD.C6AE6.1024"
    img_out = plain_image_path(f"_v110_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [8] NOT WRITTEN -- set ACCORD_V110_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
