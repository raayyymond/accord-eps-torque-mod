# -*- coding: utf-8 -*-
r"""V287 **rev 2** -- V282 + the LKAS rate-PID **D-term clamp**, 0xC61B6, 10240 (0x2800) -> 7680 (0x1E00).
ONE CAL HALFWORD.  Of its two bytes only the HIGH byte differs (0x28 -> 0x1E; the low byte is 0x00 either
way), so the payload diff is ONE byte, plus the 4-byte CRC trailer of the 0xC6000 cal page.

No code byte.  No authority change to P, the PID sum, the output clamp, Kp, Kd, Ki, the assist map, the
feedback clamp, r24, the V282 cave or the 427 tap.

This ONE script builds both revisions.  `REV` at the top selects the dose and every output name:
`REV = 2` -> 7680, the flyable candidate;  `REV = 1` -> 2560, WITHDRAWN, and its output names carry the
`SUPERSEDED-DO-NOT-FLASH` prefix so a rev-1 run can never produce a file that looks flashable.

=== 🛑 REV 1 (2560) IS WITHDRAWN -- WHY ==========================================================
Rev 1 was built at 2560 and **FAILED an adversarial pass**
(`docs/review/ADV-V287-B-UNITS-STRATA-2026-09-06.md`, verdict FAIL on its pre-written F2 and F4).  The
Appendix-B sizing proved the clamp is an excitation limiter in the **hands-off** strata and never
computed three ordinary-driving strata that together are 20-28 % of engaged time against creep's
4.4-6.7 %: hands-on `|bar| > 700`, loaded `|ang| > 60`, and fast wheel `> 25 deg/s`.  In those, 2560 is
not an excitation limiter at all -- D_sp dominance falls to 33-38 % and p99`|D_fb|`/clamp rises to
2.2-2.4, i.e. it acts as a **local Kd cut of ~38-40 %** in the 18-22 Hz band.  The re-sizing in
`docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md` APPENDIX C accepts the FAIL in full and quantifies
the cost: at 2560 the effective Kd in the loaded stratum falls to **95.4** (under the ZN record's ~118
floor) and the 7.3 Hz ring's `|L_tot|` reaches **1.038**, i.e. the ring is RE-ARMED.  Three of rev 1's
endpoint thresholds were also inside their own route-to-route spread.  **Rev 1 must not be flashed**; its
image and rwd are on disk under `SUPERSEDED-DO-NOT-FLASH…` names.

=== 🛑 WHAT REV 2 IS, AND WHAT IT IS NOT ========================================================
**7680 is a PARTIAL MITIGANT, not a cure, and the report says so in its own words** (Appendix C, C0 and
C6.1: *"I withdraw B0's 'it is the build' at 2560"*, *"the class is a partial mitigant"*).  It is the
largest ring-safe dose and the only one besides today's admissible in every stratum -- and that
admissibility is **borderline**, failing the report's own >= 80 % D_sp-dominance line in exactly one
stratum (SUBURBAN, 79.7 %, where today's 10240 sits at 84.7 %); its p99 ratio, the stronger criterion, is
<= 0.79 everywhere.  [C2]

  effect on the primary endpoint (18-22 Hz envelope of T at route-wide command-step onsets):
      x0.947 (r39) / x0.930 (r3c)          steady-tick control: x1.000 at every dose  [C3]
  7.3 Hz ring |L_tot| predicted:  **0.983 -- EXACTLY the gate, a pass with NO margin**  [C4]
  effective Kd in the loaded stratum:  121.7 (today) -> 120.4                          [C4]

🛑 **EXPOSURE IS THE BINDING CONSTRAINT, NOT THE DOSE.** The onset endpoint's 2-SE resolvability bar is
x0.914 on r39 (435 onset events in 880 s, SE of the median 4.3 %), so **x0.947 does not clear it on a
normal-length route**.  Resolving it needs SE <= 2.65 %, i.e. **n ~ 1,150 onset events ~ 2,320 s ~ 38
minutes of engaged time**, about 2.6 normal routes or one longer commute.  The one thing that makes this
buildable at all is that the onset statistic is **route-wide and does not need the symptom to occur**, so
`n` accrues on ordinary engaged driving.  ⚠ **Q2 above 0.95 on fewer than 1,150 events licenses NOTHING**
-- it is the under-powered case and must be reported as such, never as a null.  If the operator cannot
give that exposure, the report's own C6.3 says do not cut it.

=== 🛑 CELL IDENTITY -- THE ONE THING THIS BUILD MUST NOT GET WRONG ==============================
`docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md` Appendix B section B6 names the cell **`0xC61BA`**.
**THAT LABEL IS WRONG AND THIS BUILD DOES NOT USE IT.**  `0xC61BA` is the INTEGRATOR ANTI-WINDUP CEILING
and is FROZEN at 10240 here.  The D clamp is **`0xC61B6`**.  Both cells hold 10240, which is exactly why
they are easy to conflate.

[EVIDENCE -- my own byte decode of the V282 image, done before writing this script, not taken from a brief]
The four live readers are all `ld.hu 0x71b6[tp]` (tp = 0xBF000, so 0xBF000 + 0x71B6 = 0xC61B6):

    0x29EE8  e5 57 b7 71   hw1 0x57E5 -> reg1 = 5 (tp), opcode 0x3F (ld.h/ld.hu), reg2 = r10
    0x29EF2  e5 47 b7 71   hw1 0x47E5 ->                                          reg2 = r8
    0x29EF8  e5 3f b7 71   hw1 0x3FE5 ->                                          reg2 = r7
    0x29F02  e5 47 b7 71   hw1 0x47E5 ->                                          reg2 = r8
    hw2 = 0x71B7 at all four: disp16 0x71B6 with bit 0 = 1, which in this Format-VII form selects the
    UNSIGNED load (ld.hu).  Asserted byte-for-byte at [2b] against the built image.

Corroborated independently by `docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` ADDENDUM 4
(GATE 1 census: `0xC61B6` 4 live readers, all in the live FUN_00028ea6, 3 more in the block proven
unreachable in Addendum 3, ZERO writers; `0xC61BA` 1 live reader at 0x29DA0, the anti-windup path), and
by `build_v275_tva.py` lines 32-33, written by an earlier session, which records the same 4/4 and 1/1
`ld.hu` reader counts.  **The repo's own record has always been right; the slip is in the appendix only.**

=== THE ARITHMETIC, MIRRORED EXACTLY FROM THE DISASSEMBLY ========================================
FUN_00028ea6 (the 1 kHz LKAS rate PID), instruction addresses in the comments:

    def d_term(E, E_prev, Kd, L):
        r8 = E                                  # 0x29EE0  mov  r16, r8
        r8 = r8 - E_prev                        # 0x29EE2  sub  r27, r8       ; dE
        r8 = r8 * Kd                            # 0x29EE4  mul  r7, r8, r0    ; r7 = Kd LERP result (divq @0x29ED8)
        r10 = L                                 # 0x29EE8  ld.hu 0x71b6,tp,r10  [UNSIGNED]  L = cal(0xC61B6)
        r8 = r8 >> 3                            # 0x29EEC  sar  0x3, r8       ; D = (dE*Kd) >> 3
        if not (r8 <= r10):                     # 0x29EEE  cmp r10,r8 / 0x29EF0 ble
            r8 = L                              # 0x29EF2  ld.hu 0x71b6,tp,r8   ; clip HIGH
        else:
            r7 = L                              # 0x29EF8  ld.hu 0x71b6,tp,r7
            r7 = 0 - r7                         # 0x29EFC  subr r0, r7        ; -L, BUILT, not a second cell
            if not (r8 >= r7):                  # 0x29EFE  cmp r7,r8 / 0x29F00 bge
                r8 = L                          # 0x29F02  ld.hu 0x71b6,tp,r8
                r8 = 0 - r8                     # 0x29F06  subr r0, r8        ; clip LOW
        return r8                               # D, clamped symmetrically to +-L

The clamp is **symmetric from ONE cell** -- the negative limit is constructed by `subr r0`, so no value
of the cell can install an asymmetric or wrong-sign limit.  All four loads are `ld.hu`, so the latent
`ld.h`/`ld.hu` sign-extension defect that DOES exist on `0xC61B4` and `0xC61BE` (Addendum 4) does not
apply here; and 7680 (like rev 1's 2560) is far below 32768 in any case.

With the live Kd record 0xE511C flat at 128:   D = dE * 128 >> 3 = dE * 16.
    today        L = 10240  ->  D rails at |dE| = 640
    V287 rev 2   L =  7680  ->  D rails at |dE| = 480
    (rev 1, withdrawn: L = 2560 -> |dE| = 160)
Asserted arithmetically at [3] from the image's OWN Kd bytes, not from this docstring.
Adversary B's re-derived unit chain [EVIDENCE, its section 1, F1 CLEAN] converts the rail to physical
terms via the fb filter's DC gain 30.8911 and 8 raw counts per deg/s: 247.13 counts of fb per deg/s.  At
|dE| = 640 the FEEDBACK part alone rails only at a sustained 2590 deg/s^2, or a 61.7 deg/s amplitude
sinusoid at the 7.3 Hz ring; at rev 1's 160 that fell to 647 deg/s^2 / 15.4 deg/s, which is why 2560
reached into ordinary loaded cornering.  Rev 2's 480 sits at 3/4 of today's rail.

=== WHAT THE CHANGE DOES TO THE CAR =============================================================
Appendix B's measured decomposition (`rlog-tools/studies/grind/grind1_dclamp_decompose.py`, replayed on
r35/r39 against a byte-exact 1 kHz mirror) splits every tick's D into a SETPOINT part and a FEEDBACK
part, `E = 32*sp - fb`:

  * At today's 10240 the binding ticks are **92.6-100 % setpoint-dominated** and 93.6-100 % land on a
    command step.  The clamp is already an EXCITATION LIMITER, not a gain limiter.
  * At **7680** it stays an excitation limiter in EVERY stratum Appendix C tested -- D_sp dominance
    79.7-92.9 % across the eight, p99|D_fb|/clamp **<= 0.79 everywhere**, bind rate 0.1-3.8 %.  The one
    soft spot is SUBURBAN 8-15 m/s at 79.7 % dominance, just under the report's own 80 % line (today's
    10240 reads 84.7 % there), which is why C2 calls 7680 **admissible-BORDERLINE** rather than clean.
  * Predicted effect, T's 18-22 Hz envelope at route-wide command-step onsets: **x0.947 (r39) /
    x0.930 (r3c)**; the steady-tick control is **x1.000 to three decimals at every dose** -- the
    excitation-limiter signature holds route-wide, not only inside episodes.  [C3]
  * 7.3 Hz ring: `|L_tot|` 0.980 -> **0.983**, which is EXACTLY the gate's CI upper bound.  A pass with
    no margin.  Effective Kd in the loaded stratum 121.7 -> 120.4.  [C4]
  * Max-rate authority: measured over 180 hands-light full-demand steps, |T| p50 over the first
    50/100/200 ms is 617/677/651 at 10240 and moves +-3 %, non-monotone, at every dose in the ladder --
    i.e. no effect.  The D kick is a one-tick impulse; P carries the step.
  [BELIEF for the on-car effect -- it is a replay against a mirror, not a drive.  EVIDENCE for the
   arithmetic, the cell identity, the reader census and the byte diff.]

⚠ Standing caveat from the kit's own record, restated because it bounds the dose: **`0xC61BE` (the post-
gain sum clamp, 15360) is the binding constraint on D, not D's own clamp** -- P alone already fills
0xC61BE at low override index, so D is discarded downstream whenever it is large.  Lowering 0xC61B6 bites
only in frames where D was NOT already being discarded.  That is a null risk, not a safety risk.

=== WHAT THIS BUILD DOES *NOT* CHANGE ===========================================================
Kp (flat 248 on all 28 records, V281 rev 3) · Kd (128 flat) · Ki (0) · the integrator anti-windup ceiling
`0xC61BA` (10240, ASSERTED EQUAL BEFORE AND AFTER) · the P clamp `0xC61BC` (15360) · the post-gain sum
clamp `0xC61BE` (15360) · the T clamp `0xC61B4` (3072) · the post-lag deadband `0xC61B8` (102) · the
output-lag pole `0xC63EC`/`0xC63EE` (992/507 -- section 7's candidate, deliberately NOT flown here) · the
fb pole `0xC63E8`/`0xC63EA` (923/1560) · `0xC6446` (5244, the r24 gain arm) · the feedback clamp
`0xC62E6` (46080) · the assist-map family · the tapers · the V282 cave at 0xC4B34 · the 427 torque tap at
0x55DF0-0x55E11 · the hook at 0x55C0E · every code byte in [0x13000, 0xC0000).

=== LINEAGE OF 0xC61B6 -- FIRST FLIGHT ==========================================================
🛑 **`0xC61B6` HAS NEVER BEEN EDITED ON ANY BUILD, FLOWN OR SHELVED.  V287 IS ITS FIRST MOVE EVER.**
[EVIDENCE, three independent methods:]
  1. A census over the plain-image archive (`ACCORD_FIRMWARE_ROOT/analysis-2020accord/**/*plain_image.bin`)
     reads **10240 in every image**, and the stock dump `stock_fw_dump/code.bin` reads 10240 too.
  2. `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` row for the four parallel branch clamps: *"never edited in
     any build -- BYTE-STOCK from stock through V108"*.
  3. Every build script that names it lists it under FROZEN (V274/275/276/277/278/278r3/279/280/281/281r3/
     282/283/284/285).  ⚠ The older `build_v100..v105_tva.py` / `verify/diff_build_vs_stock.py` rows that
     read `(0xC61B2, 0xC61B6, ...)` are **(lo, hi_EXCLUSIVE) spans**, i.e. cells 0xC61B2 and 0xC61B4 only
     -- they do NOT record an edit at 0xC61B6.  Re-checked in this build's [11] step against the archive.
  `docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md` states the same independently ("identical in all
  287 images").

=== PRE-REGISTRATION ============================================================================
🛑 **`rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md`, which points at APPENDIX C section C5 of
`docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md`.  APPENDIX B's B6 pre-registration is SUPERSEDED --
it belonged to the withdrawn 2560 dose, and three of its thresholds sat inside their own route spread.**
Read every CELL NAME in Appendix B as `0xC61B6`, not `0xC61BA`.  Every C5 statistic is route-wide.

  Q1  LIVENESS   427 tap matches the 7680 mirror, not the 10240 one, on 0.1-3.8 % of engaged ticks,
                 conditioned on (|P| < 15360) OR (sign D != sign P).  Must fire over >= 20 s.
  Q2  PRIMARY    18-22 Hz envelope of T on route-wide command-step onsets: predicted x0.947 / x0.930.
                 🛑 Needs >= 1,150 onset events (~38 min engaged).  Below that it licenses NOTHING.
  Q3  CONTROL    the same envelope on steady ticks: x1.000, must stay in [0.95, 1.05].
  Q5  RING       7.3 Hz |L_tot| 0.980 -> 0.983.  FAIL if > 0.983.
  Q6  SHELF      0x18F rate 33-49.9 / 2-6 unchanged.  FAIL if > x1.6 on >= 20 qualifying windows.
  Q7  DETECTOR   motion per unit torque 0.375-0.5 s after an onset.  Any x0.6 step = FAIL.
  Q8  AUTHORITY  paired |T| over the first 50/100/200 ms of hands-light full-demand steps.  FAIL if -5 %.
  Q10 LOADED     0x18F rate 6-9 Hz and 18-22 Hz at |ang| > 60, engaged -- the stratum rev 1 died in.
                 FAIL above x1.9 (6-9) or x2.3 (18-22), both clear of their x1.44 / x1.86 route spreads.

Decision rule: Q1 fires first; then **Q2 <= 0.914 with Q3 in [0.95, 1.05] and Q10 flat** confirms the
excitation-limiter reading with the ring intact.
**Cost FAIL outranks every number: the operator reports weaker or slower response to a lane change or a
curve, any new vibration or noise, or any worsening of grinding, vibrating, micro-ratcheting, ratcheting
or excess friction.  Report symptoms in HIS words.  An absence of a complaint is not a cure.**

=== CLASS OF BUILD ==============================================================================
A **NONLINEAR, AMPLITUDE-SELECTIVE** edit -- the first in the post-V38 arc.  Every recent build moved a
LINEAR element: V276/V278/V280 the reference (the assist map), V281 rev 3 the proportional gain, V283 the
integral gain, V284/V285 Kp again, and section 7's shelved candidate the output-lag pole.  All of them
change the loop at EVERY amplitude.  This one changes nothing until the D term is large, which is why it
carries its own negative control (steady ticks) alongside its endpoint (onsets), both route-wide on the
same drive.
It is also the first edit ever to `0xC61B6`.

⚠ **AND IT IS DELIBERATELY A SMALL STEP.** Rev 1 tried to buy a 15-minute readout and bought a Kd cut in
three unsampled strata instead.  Rev 2 keeps the ring gate and the all-strata admissibility and pays for
it in statistical power, which is the one cost that can be bought back with ordinary driving time rather
than with another build.  It should be described to the operator as a **small, ring-neutral step whose
primary endpoint needs about 38 minutes of engaged driving** -- not as a grind cure.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V287_WRITE", "").strip().lower()

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
             "_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
GRANDPARENT_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GRANDPARENT_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
# ---- [C] THE ONE EDIT, and the REVISION that selects its dose and every output name ----------------------
REV = int(os.environ.get("ACCORD_V287_REV", "2"))
# rev -> dose, rail |dE| at Kd 128, output names, and a phrase that must appear in the doc recommending
#        this dose -- the DOSE PIN, so the value on the image is tied to the RECORD, not to a constant here.
REVISIONS = {
    # rev 1 -- WITHDRAWN.  Names reproduce EXACTLY the SUPERSEDED files already on disk, so a rev-1 run
    # overwrites them in place rather than creating a second copy under a new name.
    1: dict(dose=2560, rail=160, withdrawn=True,
            tag="V287-rev1-DCLAMP.2560",
            img_name="SUPERSEDED-DO-NOT-FLASH_v287_rev1_DCLAMP.2560_plain_image.bin",
            rwd_name="SUPERSEDED-DO-NOT-FLASH-39990-TVA,A160-V287-rev1-DCLAMP.2560-0x13000-0x100000.rwd",
            pin_phrase="I WOULD FLY 2560 FIRST",
            pin_doc="docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md"),
    2: dict(dose=7680, rail=480, withdrawn=False,
            tag="V287R2-V282BASE-DCLAMP.7680-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP",
            img_name=None,     # built from the tag below
            rwd_name=None,
            pin_phrase="Dose 7680, not 2560.",
            pin_doc="rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md"),
}
assert REV in REVISIONS, f"REV must be one of {sorted(REVISIONS)}"
_R = REVISIONS[REV]
DOSE, RAIL_EXPECT, TAG = _R["dose"], _R["rail"], _R["tag"]
DOSE_PIN_PHRASE, DOSE_PIN_DOC = _R["pin_phrase"], _R["pin_doc"]
WITHDRAWN = _R["withdrawn"]        # rev 1 failed adversary B; its names cannot look flashable
IMG_NAME = _R["img_name"] or f"_v287r{REV}_{TAG}_plain_image.bin"
RWD_NAME = _R["rwd_name"] or f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
assert WITHDRAWN == RWD_NAME.startswith("SUPERSEDED"), "a withdrawn revision must not emit a flashable name"

D_CLAMP, D_OLD, D_NEW = 0xC61B6, 10240, DOSE     # the LKAS rate-PID D-term clamp.  NOT 0xC61BA.
AW_CLAMP = 0xC61BA                               # integrator anti-windup ceiling -- the cell the appendix
                                                 # mislabels as "the D clamp".  MUST NOT MOVE.
# the four live readers of D_CLAMP, and the exact 4-byte encoding each must still carry (ld.hu 0x71b6[tp])
D_CLAMP_TP_DISP = 0x71B6
D_READERS = {
    0x29EE8: bytes.fromhex("e557b771"),   # ld.hu 0x71b6, tp, r10   -- the compare limit
    0x29EF2: bytes.fromhex("e547b771"),   # ld.hu 0x71b6, tp, r8    -- clip HIGH
    0x29EF8: bytes.fromhex("e53fb771"),   # ld.hu 0x71b6, tp, r7    -- limit LOW, negated by subr r0
    0x29F02: bytes.fromhex("e547b771"),   # ld.hu 0x71b6, tp, r8    -- clip LOW, negated by subr r0
}
TP_BASE = 0xBF000

# ---- [A] carried from V281 rev 3 / V282 -- asserted byte-identical, not re-derived here ------------------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y_R3 = (0, 68, 112, 136, 208), (248,) * 5
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)

# ---- [B] the V282 cave and the 427 tap -- this build touches NONE of it ----------------------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
HOOK = 0x55C0E
HOOK_STOCK4 = bytes.fromhex("86ff26ef")
V282_EDIT_SITES = (0xC4B36, 0xC4B42, 0xC4B64, 0xC4B70)
PACK_LO, PACK_HI = 0x55DF0, 0x55E12
MAP_PTR, MAP_N = 0xC9A88, 10
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

FROZEN = {
    0xC61B2: 3072,
    0xC61B4: 3072,                  # T clamp -- ld.h/ld.hu mismatch cell, must stay < 32768
    0xC61B8: 102,                   # post-lag deadband
    0xC61BA: 10240,                 # 🛑 the INTEGRATOR anti-windup ceiling -- the appendix's mislabel
    0xC61BC: 15360,                 # P clamp
    0xC61BE: 15360,                 # post-gain sum clamp -- the real binding constraint on D
    0xC63E6: 0,                     # Ki (V283's lever; NOT enabled here)
    0xC63E8: 923,    0xC63EA: 1560,  # fb pole
    0xC63EC: 992,    0xC63EE: 507,   # output-lag pole -- section 7's candidate, deliberately NOT flown
    0xC62E4: 4,
    0xC62E6: 46080,                 # feedback clamp (V280 rev 2)
    0xC6446: 5244,                  # r24 gain arm (V282's probe target)
    0xC644A: 1024,
    0xC6AE6: 2048,
    0xC6B12: 98,     0xC6B26: 256,
    0xC6CD0: 5346,
}
assert D_CLAMP not in FROZEN, "the edited cell must not also be frozen"

OK, BAD = "[PASS]", "[FAIL]"
# assertion census: S = substantive (could fail on a wrong edit), V = vacuous (entailed by the base sha256),
# T = tautological (readback of a value just written by this script)
_census = {"S": 0, "V": 0, "T": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def d_term(E, E_prev, Kd, L):
    """The decompiled D branch of FUN_00028ea6, mirrored EXACTLY in integer Python.
    Instruction addresses in the comments; V850 is little-endian and `sar` is an arithmetic shift."""
    r8 = E - E_prev                       # 0x29EE0 mov / 0x29EE2 sub  -> dE
    r8 = r8 * Kd                          # 0x29EE4 mul r7,r8,r0
    r10 = L                               # 0x29EE8 ld.hu 0x71b6,tp,r10
    r8 = r8 >> 3                          # 0x29EEC sar 0x3,r8   (Python >> on ints IS arithmetic)
    if not (r8 <= r10):                   # 0x29EEE cmp / 0x29EF0 ble
        return L                          # 0x29EF2 ld.hu -> clip HIGH
    r7 = 0 - L                            # 0x29EF8 ld.hu / 0x29EFC subr r0,r7
    if not (r8 >= r7):                    # 0x29EFE cmp / 0x29F00 bge
        return -L                         # 0x29F02 ld.hu / 0x29F06 subr r0,r8 -> clip LOW
    return r8


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: patch the D-clamp halfword
    directly, then re-CRC every block touched -- via FF.crc_block_map, not the address hardcoded elsewhere."""
    img = bytearray(base)
    assert u16(img, D_CLAMP) == D_OLD
    struct.pack_into("<H", img, D_CLAMP, D_NEW)
    touched = {D_CLAMP, D_CLAMP + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 108)
    print(f"  V287 rev {REV} -- V282 + the LKAS rate-PID D-TERM CLAMP, 0xC61B6, {D_OLD} -> {D_NEW}.  ONE CAL HALFWORD.")
    if WITHDRAWN:
        print("  🛑 REV 1 IS WITHDRAWN -- it FAILED adversary B (ADV-V287-B-UNITS-STRATA-2026-09-06.md, F2+F4).")
        print("     Its outputs are named SUPERSEDED-DO-NOT-FLASH so they cannot be mistaken for a candidate.")
    print("  🛑 NOT 0xC61BA (the integrator anti-windup ceiling, frozen at 10240) -- the appendix's label is wrong.")
    print("=" * 108)

    print("\n  [1] BASE = V282")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          "V282 base sha256 matches the record (BUILD-LINEAGE.md line 254, build_v283_tva.py BASE_SHA)", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    check(u16(base, D_CLAMP) == D_OLD, f"base D clamp 0x{D_CLAMP:05X} == {D_OLD} (0x{D_OLD:04X})", "V")
    check(u16(base, AW_CLAMP) == 10240, f"base anti-windup 0x{AW_CLAMP:05X} == 10240 -- the SAME value, "
                                        f"which is why the two cells are easy to conflate", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and n7 == 5
          and tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y_R3,
          f"base live Kp slot {LIVE_SLOT} @0x{LIVE_KP_REC:05X}: X {LIVE_KP_X} Y {LIVE_KP_Y_R3} (flat-248)", "V")
    nkd, _Xkd, Ykd = rec(base, u32(base, KD_PTR + 4 * LIVE_SLOT))
    check(u32(base, KD_PTR + 4 * LIVE_SLOT) == LIVE_KD_REC and tuple(Ykd) == LIVE_KD_Y,
          f"base live Kd slot {LIVE_SLOT} @0x{LIVE_KD_REC:05X}: Y {LIVE_KD_Y} (flat 128)", "V")
    check(bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4, "base hook 0x55C0E == jarl 0xc4b34,lp", "V")
    for a in V282_EDIT_SITES:
        check(s16(base, a) in (-0x6ADA, -0x6B38, -0x6B94),
              f"base cave site 0x{a:05X} carries a V282-repointed displacement", "V")

    print("\n  [2] 🛑 CELL IDENTITY -- the four live readers decoded from the BASE image's own bytes")
    for a, enc in D_READERS.items():
        got = bytes(base[a:a + 4])
        hw1, hw2 = struct.unpack_from("<HH", got, 0)
        reg1, opc, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
        disp, unsigned = hw2 & 0xFFFE, hw2 & 1
        print(f"      0x{a:05X}  {got.hex()}  hw1=0x{hw1:04X} reg1=r{reg1} opc=0x{opc:02X} reg2=r{reg2}  "
              f"hw2=0x{hw2:04X} disp=0x{disp:04X} {'ld.hu' if unsigned else 'ld.h'}  -> 0x{TP_BASE + disp:05X}")
        check(got == enc, f"0x{a:05X} carries the expected 4 reader bytes {enc.hex()}", "V")
        check(reg1 == 5 and opc == 0x3F, f"0x{a:05X} base register is r5 = tp and opcode is 0x3F (ld.h/ld.hu)", "S")
        check(disp == D_CLAMP_TP_DISP and TP_BASE + disp == D_CLAMP,
              f"0x{a:05X} displacement 0x{disp:04X} + tp 0x{TP_BASE:05X} == 0x{D_CLAMP:05X} -- this reader "
              f"reads THE CELL THIS BUILD EDITS, and NOT 0x{AW_CLAMP:05X}", "S")
        check(unsigned == 1, f"0x{a:05X} hw2 bit 0 == 1 -> ld.hu (UNSIGNED) -- no sign-extension trap on this "
                             f"clamp at any cell value (the ld.h defect is on 0xC61B4/0xC61BE only)", "S")
    check(len(set(D_READERS)) == 4, "exactly the 4 live readers of the D clamp are pinned (3 more exist in "
                                    "[0x2A508,0x2B422), the block proven UNREACHABLE in TRACE addendum 3)", "S")

    print("\n  [3] THE CLAMP ARITHMETIC, from the image's OWN Kd bytes -- what the dose actually does")
    kd_live = Ykd[0]
    check(len(set(Ykd)) == 1, f"live Kd record is FLAT at {kd_live} -- D = dE*{kd_live}>>3 = dE*{kd_live // 8}", "V")
    rail_old, rail_new = D_OLD * 8 // kd_live, D_NEW * 8 // kd_live
    check(d_term(rail_old, 0, kd_live, D_OLD) == D_OLD and d_term(rail_old - 1, 0, kd_live, D_OLD) < D_OLD,
          f"mirror: at L={D_OLD} the clamp rails at exactly |dE| = {rail_old}", "S")
    check(d_term(rail_new, 0, kd_live, D_NEW) == D_NEW and d_term(rail_new - 1, 0, kd_live, D_NEW) < D_NEW,
          f"mirror: at L={D_NEW} the clamp rails at exactly |dE| = {rail_new}", "S")
    check(d_term(-rail_new, 0, kd_live, D_NEW) == -D_NEW,
          f"mirror: the clamp is SYMMETRIC -- -L is built by `subr r0` from the same cell, so no cell value "
          f"can install an asymmetric or wrong-sign limit", "S")
    check(all(d_term(e, 0, kd_live, D_NEW) == d_term(e, 0, kd_live, D_OLD)
              for e in range(-rail_new, rail_new + 1)),
          f"mirror: for |dE| <= {rail_new} the D term is IDENTICAL before and after -- the edit is "
          f"amplitude-selective and changes nothing in the small-signal loop", "S")
    check(0 < D_NEW < D_OLD < 32768,
          f"dose is a REDUCTION ({D_OLD} -> {D_NEW}), non-zero, and both values are < 32768", "S")
    print(f"      D = dE*{kd_live}>>3 = dE*{kd_live // 8};  rail |dE| {rail_old} -> {rail_new}  "
          f"(0x{D_OLD:04X} -> 0x{D_NEW:04X})")

    print("\n  [4] APPLY -- one halfword")
    code = bytearray(base)
    attributed = {D_CLAMP, D_CLAMP + 1}
    check(u16(code, D_CLAMP) == D_OLD, f"pre-write value confirmed {D_OLD}", "T")
    struct.pack_into("<H", code, D_CLAMP, D_NEW)
    check(u16(code, D_CLAMP) == D_NEW, f"0x{D_CLAMP:05X} D clamp {D_OLD} -> {D_NEW}", "T")
    check(u16(code, AW_CLAMP) == u16(base, AW_CLAMP) == 10240,
          f"🛑 0x{AW_CLAMP:05X} (integrator anti-windup) reads 10240 BEFORE AND AFTER -- the appendix's "
          f"mislabelled cell is UNTOUCHED", "S")
    for a in (0xC61B4, 0xC61B8, 0xC61BC, 0xC61BE):
        check(u16(code, a) == u16(base, a), f"neighbour 0x{a:05X} == base ({u16(base, a)}) -- unchanged", "S")

    print("\n  [5] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    outside = [x for x in range(START, END) if x not in attributed and code[x] != base[x]]
    check(outside == [], f"no byte outside the D-clamp halfword changed before CRC recompute "
                         f"({len(outside)} stray diffs)", "S")
    for a, v in FROZEN.items():
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}", "S")
    for a, enc in D_READERS.items():
        check(bytes(code[a:a + 4]) == enc == bytes(base[a:a + 4]),
              f"reader instruction 0x{a:05X} byte-identical ({enc.hex()}) -- CAL ONLY, no code byte", "S")
    check(bytes(code[CAVE_START:CAVE_END]) == bytes(base[CAVE_START:CAVE_END]),
          f"the whole V282 cave 0x{CAVE_START:05X}-0x{CAVE_END - 1:05X} ({CAVE_END - CAVE_START} B) is "
          f"byte-identical (sha256[:8] "
          f"{hashlib.sha256(bytes(code[CAVE_START:CAVE_END])).hexdigest()[:8]})", "S")
    check(bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK4, "hook 0x55C0E byte-identical", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          f"427 tap window 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} byte-identical -- the delivered-torque tap "
          f"the whole pre-registration reads is kept", "S")
    code_region = [x for x in range(START, 0xC0000) if code[x] != base[x]]
    check(code_region == [], f"the entire code region [0x{START:05X},0xC0000) is byte-identical "
                             f"({len(code_region)} diffs) -- this build is CAL-ONLY", "S")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    for p in map_ptrs:
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]), f"map 0x{p:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        p = u32(base, KP_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kp slot {s} @0x{p:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        p = u32(base, KD_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kd slot {s} @0x{p:05X} byte-identical", "S")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "S")

    print("\n  [6] CRC TRAILER -- located GENERICALLY via V53.owning_block (content-derived, not hardcoded)")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns the D-clamp halfword ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b0 == 0xC6000 and b1 == 0xC6FFC, f"block is [0x{b0:05X},0x{b1:05X}) -- the main cal block", "S")
    check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
    oldc = u32(code, b1)
    newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved (the block carries the edit)", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      cal page [0x{b0:06X},0x{b1:06X})  trailer 0x{b1:06X}  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    print("\n  [7] FULL BYTE DIFF vs V282 -- every differing offset enumerated")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed, f"every one of the {len(diff)} differing bytes is the D-clamp halfword or "
                                   f"its CRC trailer", "S")
    payload_expected = sum(1 for j in (0, 1) if struct.pack("<H", D_OLD)[j] != struct.pack("<H", D_NEW)[j])
    check(payload_expected == 1,
          f"D clamp {D_OLD}->{D_NEW} (0x{D_OLD:04X}->0x{D_NEW:04X}): only the HIGH byte of the LE u16 differs "
          f"(0x{struct.pack('<H', D_OLD)[1]:02X}->0x{struct.pack('<H', D_NEW)[1]:02X}; the low byte is "
          f"0x{struct.pack('<H', D_OLD)[0]:02X} either way) -- {payload_expected} of the 2 TOUCHED bytes "
          f"actually change, computed from the base, not asserted", "S")
    check(len(diff) == payload_expected + 4,
          f"total diff vs V282 is exactly {payload_expected} payload byte + 4-byte CRC trailer = "
          f"{payload_expected + 4}, got {len(diff)}", "S")
    check(D_CLAMP + 1 in diff and D_CLAMP not in diff,
          f"the differing payload byte is 0x{D_CLAMP + 1:05X} (the high byte); 0x{D_CLAMP:05X} is written but "
          f"byte-identical to the base", "S")
    print("      offset      len  what                      base -> built")
    for s, e in runs(diff):
        kind = "CRC trailer (cal page)" if s == b1 else "D clamp 0xC61B6 high byte"
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind:26s} {bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    print(f"      ENUMERATED DIFFERING OFFSETS: {[hex(a) for a in diff]}")

    print("\n  [7b] CROSS-IMAGE vs V281 rev 3 and V280 rev 2")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    grandparent = Path(plain_image_path(GRANDPARENT_NAME)).read_bytes()
    check(hashlib.sha256(grandparent).hexdigest() == GRANDPARENT_SHA, "V280 rev 2 image sha256 matches", "S")
    d_v282_vs_parent = set(a for a in range(START, END) if base[a] != parent[a])
    d_parent_vs_gp = set(a for a in range(START, END) if parent[a] != grandparent[a])
    d_v287_vs_gp = set(a for a in range(START, END) if code[a] != grandparent[a])
    check(d_v287_vs_gp == d_v282_vs_parent | d_parent_vs_gp | set(diff),
          f"V287 vs V280 rev 2 ({len(d_v287_vs_gp)} B) == V282's cave diff ({len(d_v282_vs_parent)} B) UNION "
          f"V281 rev 3's Kp diff ({len(d_parent_vs_gp)} B) UNION this build's D-clamp+CRC diff ({len(diff)} B), "
          f"no overlap, nothing extra", "S")
    check(u16(parent, D_CLAMP) == D_OLD and u16(grandparent, D_CLAMP) == D_OLD,
          f"0x{D_CLAMP:05X} was {D_OLD} on both ancestor images", "S")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V287 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN exists -- the non-circular cipher test is reachable", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    print("\n  [9] END STATE -- re-read from the FINAL image and from the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        kind = "T" if nm == "code" else "S"
        check(u16(im, D_CLAMP) == D_NEW, f"{nm}: 0x{D_CLAMP:05X} (D clamp) == {D_NEW}", kind)
        check(u16(im, AW_CLAMP) == 10240, f"{nm}: 0x{AW_CLAMP:05X} (integrator anti-windup) == 10240, UNTOUCHED", kind)
        for a, v in FROZEN.items():
            check(u16(im, a) == v, f"{nm}: 0x{a:05X} == {v}", kind)
        for a, enc in D_READERS.items():
            check(bytes(im[a:a + 4]) == enc, f"{nm}: reader 0x{a:05X} still ld.hu 0x71b6[tp] ({enc.hex()})", kind)
        check(bytes(im[CAVE_START:CAVE_END]) == bytes(base[CAVE_START:CAVE_END]), f"{nm}: V282 cave untouched", kind)
        check(bytes(im[HOOK:HOOK + 4]) == HOOK_STOCK4, f"{nm}: hook untouched", kind)
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap window untouched", kind)
        _n7, X7i, Y7i = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X7i) == LIVE_KP_X and tuple(Y7i) == LIVE_KP_Y_R3, f"{nm}: live Kp record == flat-248", kind)
        _nk, _Xk, Yki = rec(im, u32(im, KD_PTR + 4 * LIVE_SLOT))
        check(tuple(Yki) == LIVE_KD_Y, f"{nm}: live Kd record == flat 128", kind)
        # DOSE PIN: tie the value on the image to the appendix's own dose ladder, not to D_NEW.
        _doc = Path(__file__).resolve().parents[3] / DOSE_PIN_DOC
        _txt = _doc.read_text(encoding="utf-8", errors="replace")
        check(DOSE_PIN_PHRASE in _txt and u16(im, D_CLAMP) == DOSE,
              f"{nm}: the value on the image ({u16(im, D_CLAMP)}) is the dose {DOSE_PIN_DOC} recommends "
              f"(\"{DOSE_PIN_PHRASE}\") -- pinned to the RECORD, not to a constant in this script", "S")
        # RAIL PIN: derive the new rail from the image's own Kd and clamp, independent of the constants above.
        _rail = u16(im, D_CLAMP) * 8 // Yki[0]
        check(_rail == RAIL_EXPECT, f"{nm}: rail |dE| computed from the image's own Kd ({Yki[0]}) and clamp "
                                    f"({u16(im, D_CLAMP)}) == {_rail}, the rev-{REV} value "
                                    f"({D_OLD * 8 // Yki[0]} -> {RAIL_EXPECT})", "S")

    print("\n  [10] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (direct halfword patch + generic re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n  [11] LINEAGE OF 0xC61B6 -- census over the plain-image archive and the stock dump")
    root = Path(plain_image_path(BASE_NAME)).parent
    seen = {}                # every V287-line image (either revision, superseded or not) is EXCLUDED, so the
    excluded = []            # census stays a statement about the RECORD BEFORE this build, not about itself
    for f in sorted(root.rglob("*plain_image.bin")):
        if "v287" in f.name.lower():
            excluded.append(f.name)
            continue
        b = f.read_bytes()
        if len(b) > D_CLAMP + 1:
            seen.setdefault(u16(b, D_CLAMP), []).append(f.name)
    stock = root / "stock_fw_dump" / "code.bin"
    stock_v = u16(stock.read_bytes(), D_CLAMP) if stock.exists() else None
    print(f"      archive: {sum(len(v) for v in seen.values())} plain images, values {sorted(seen)}"
          f"   stock code.bin: {stock_v}")
    print(f"      EXCLUDED as this build's own line ({len(excluded)}): {excluded}")
    check(set(seen) == {D_OLD}, f"EVERY archived plain image reads 0x{D_CLAMP:05X} == {D_OLD} -- "
                                f"the cell has NEVER been edited on any build, flown or shelved", "S")
    check(stock_v == D_OLD, f"the STOCK dump also reads {D_OLD} -- V287 is the FIRST EVER move of this cell", "S")

    _scr = os.environ.get("ACCORD_V287_SCRATCH", "").strip()
    if _scr:
        Path(_scr, IMG_NAME).write_bytes(bytes(code))
        Path(_scr, RWD_NAME).write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(IMG_NAME))
        out_rwd = Path(RWD_DIR, RWD_NAME)
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        v287_rwds = sorted(f.name for f in Path(RWD_DIR).glob("*V287*.rwd"))
        superseded = [n for n in v287_rwds if n.startswith("SUPERSEDED")]
        others = [n for n in v287_rwds if not n.startswith("SUPERSEDED") and n != out_rwd.name]
        print(f"      V287-line rwds on disk: {len(v287_rwds)}  ({len(superseded)} SUPERSEDED: {superseded})")
        check(not others, f"exactly ONE flashable V287 rwd on disk (other non-superseded: {others})", "S")
        check(WITHDRAWN or out_rwd.name in v287_rwds and not out_rwd.name.startswith("SUPERSEDED"),
              f"the flashable one is THIS build's: {out_rwd.name}", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V287_WRITE=rwd to emit the files")

    print("\n" + "=" * 108)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} substantive, "
          f"{_census['V']} vacuous (entailed by the base sha256), {_census['T']} tautological (readback of a write)")
    print(f"  ** V287 rev {REV} -- LKAS rate-PID D-TERM CLAMP 0xC61B6, {D_OLD} -> {D_NEW}.  ONE CAL HALFWORD, 1 BYTE MOVES. **")
    print(f"  ** D = dE*Kd>>3 clamped +-L, symmetric from one cell; rail |dE| {D_OLD // 16} -> {RAIL_EXPECT} at Kd 128.           **")
    if not WITHDRAWN:
        print("  ** PARTIAL MITIGANT, not a cure: onset endpoint x0.947/x0.930, ring |L_tot| 0.983 = the gate    **")
        print("  ** exactly, and the primary needs ~1,150 onset events ~ 38 MIN ENGAGED to resolve at 2 SE.      **")
    print("  ** 0xC61BA (integrator anti-windup) is FROZEN at 10240 -- Appendix B's cell label is WRONG.      **")
    print("  ** FIRST EVER edit of 0xC61B6: 10240 in the stock dump and in every archived plain image.        **")
    print("=" * 108)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
