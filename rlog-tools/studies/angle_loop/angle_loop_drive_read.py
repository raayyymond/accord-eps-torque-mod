# -*- coding: utf-8 -*-
r"""angle_loop_drive_read.py -- THE DRIVE-READ INSTRUMENT FOR THE FIRST ANGLE-LOOP FLIGHT (V296 = C3-rev2-P).

    python rlog-tools/studies/angle_loop/angle_loop_drive_read.py <route id | counter--hash | v280 cache tag>
            [--refs r6c,r39,r71b_v294] [--no-replay] [--no-presence] [--json PATH]

ANALYSIS ONLY.  Reads rlogs / kit caches / the V295 image's cells; writes only under _scratch/.  Sends nothing,
flashes nothing, touches no fork file.  No new telemetry bit exists in the design (C3-rev2 §7): every read below is
on signals ALREADY on the wire.

WHAT IT READS (design page docs/specs/design/DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md §5 / §7, with C3 §8's table
for the clauses rev2 inherits) -- every threshold is in THR below with its source; none is tuned on a flight:

  0  attribution   carFw EPS = 39990-TVA,A16A (F181); AccordEpsAngleLoop in initData; camera (bus-2 0xE4) silent;
                   STEER_STATUS / 0x14A b4 health (R8).
  1  LIVE / NOT LIVE / INVERTED   per speed band, hands-off (|0x18F bar| < 500 wire), request 1, >= 1.2 s after
                   engage, on the 0x1AB tap's native 50 Hz instants (lag scanned):
                   DECISION-BEARING = the STRUCTURAL regression on the C3-rev2-P lane's own components, each carried
                   through the image's linear output path (no free constant inside the chain):
                       tap = a P_raw + b P_meas + c I + d D            (LIVE design: a = b = c = d = 1)
                       c_meas/c_raw = -b/a ; c_P = a c_P,pred ; c_I/c_P = (c/a) 2.79 /s ; c_D = d 0.566 tap/(deg/s)
                   with three corrections made 2026-10-02 after route 79 fired a FALSE R1 (c_D -0.135, c_I/c_P 1.24,
                   while seven independent estimators found D opposing and Ki at design -- docs/scoring/
                   DRIVE-READ-V298-r79-2026-10-02.md sections 1 and 6; M1-attribution-identity.md section 3.4;
                   M3-integrator-freeze.md sections 4 and 6):
                     (a) the replayed I uses the ENGAGE-RAMP ARM that ran: direction 2 (+328 / -66 per tick, image cells
                         0xC63FC / 0xC63FA) when the fork ran the angle interface (AccordEpsAngleLoop = 1 => 0xE4 byte-2
                         arm 2), else direction 0 (+33 / -16).  Direction 0 froze the replayed I for 0.99 s at every
                         engage instead of 0.10 s.
                     (b) the firmware's torque word LEADS the 0x18F sample by 10 ticks (one frame) on the car: the
                         replay's freezes and fade read it one frame early (M3 timing scan: replay R2 0.834 -> 0.928).
                     (c) the replayed I is RE-ANCHORED per ~5 s window: one intercept per window of each hands-off run
                         (within-window demeaning of the tap and every regressor), the regression form of M1's per-window
                         I0.  The un-anchored I drifts after hands-on manoeuvres and a single intercept let that drift
                         drag c toward 0 (errors-in-variables) and push the error into b and d.
                   The pre-2026-10-02 structural form (direction-0 ramp, word on the 0x18F frame, one intercept) is
                   still computed and PRINTED for comparison; it is not decision-bearing.
                   R1 (INVERTED) needs TWO METHODS TO AGREE: the structural fit above AND a second estimator -- the
                   design's literal regression band-passed at 2-5 Hz, where D is identified (M1 section 3.2: the 0.3-3
                   Hz band cannot identify D; there D is a small quadrature term beside P and I):
                       tap = c_raw*raw + c_meas*f14a + c_I*Sum(raw - f14a)dt + c_D*w18 (+c0)       [ratio test]
                       tap = c_P*(raw - f14a) + c_I*Sum(raw - f14a)dt + c_D*w18 (+c0)              [P/I/D test]
                   regressors passed through the image's own output-lag pole (0xC63EC/0xC63EE).  A clause of R1 fires
                   only when BOTH methods cross its sign threshold; both values are printed beside it.  The same literal
                   form at 0.3-3 Hz (C0 §6) is printed as before, not decision-bearing.
                   And a REPLAY method: the byte-exact lane REPLAYED on the wire inputs for each candidate image
                   (C3-rev2-P, C3 Ki 56, cave skipped, V295) -> R2 of the tap against each replay (zero free params),
                   with the direction-0 ramp and the word on the 0x18F frame for every candidate (the image-identity
                   comparison, unchanged); the corrected C3-rev2-P replay (a)+(b) is printed beside it.
  2  stop bands    R1 INVERTED, R2 |tap| >= 300 LSB hands-off > 0.3 s, R3* 0.25-5.5 Hz ring (grows, or >= 4 cycles
                   zeta < 0.25) on 0x14A angle / 0x18F rate / the tracking error, R4 a new 5-30 Hz line vs the
                   reference routes, R5 ring presence > 0.5 % or F7 > 0, R6 |theta - theta_sp| > 10 deg hands-off
                   > 0.5 s at > 8 m/s, R7 tap pushing toward 0 deg > 0.2 s after a request drop, R8 STEER_STATUS /
                   0x14A b4 bits 0-2 != 7 engaged.
  3  the goal      tracking gain (0.5 Hz LPF slope of theta on theta_sp, real paths), turn-hold (>= 0.90), dwell-then-
                   jump (the harness's own NS.dwell_jump AND the symptom instrument's dwells/min vs the V282 routes,
                   both re-derived at run time), ring presence, F7, a 5-30 Hz line census, the 18-22 Hz engaged/
                   disengaged gain vs the V294 route (V295's rlog is not on disk -- stated, not hidden).
  4  next step     breakaway (stick->slip tap) and Coulomb friction (sign(w) coefficient) per speed band -- the
                   sizing data for friction compensation.  NOT a verdict.
  6  V299 / DRIVE 2 (added 2026-10-02, drive_read_v299.py; every block above is unchanged on a V298 wire):
                   attribution of carFw A16B + the V299 fork params + starpilotCarState.accordAngleStatus (the fork
                   cache, r79_extract_fork.py, schema pinned to the route's commit); the RULE-IDENTITY replay (V298 vs
                   V299 rule, pooled + 30-s windows; the V299 rule validated against the spec mirror cave_rev2 every
                   run); the stutter readouts vs V282 + the surge enrichment at |bar| 300/512/1229 crossings; F3/F5
                   release-relative; F4 turn-ins; F10; the cap-shortfall read; F7/F7b/F9; the F8 bar check; and the
                   DRIVE-2 VERDICT block.  On an A16B wire the structural regression's I component is the V299 rule's
                   replay (the rule that ran), printed as such.

UNITS AND SIGNS (each EVIDENCE, source in brackets):
  raw     0xE4 STEER_TORQUE, i16 BE bytes 0-1 (bus 129 = what the EPS received).  The fork sends raw = -10*theta_sp_deg
          [SPEC-angle-setpoint-interface C1].  The firmware stores gp-0x69ae = clamp(-4 raw) [lane_mirror e4_handler].
  ang     0x14A STEER_ANGLE in deg = field * -0.1 = gp-0x6a00 / 10, carState sign [TRACE angle §2.1; r71b_cache].
  f14a    the 0x14A field itself = -10*ang = -gp-0x6a00.  So e_w = raw - f14a = raw + 10*ang = -10*(theta_sp - theta):
          LIVE gives c_meas/c_raw = -1 [C3-rev2 §7; the firmware's E = 16*(theta_sp - theta) = -16*e_w].
  w18     0x18F STEER_ANGLE_RATE: x = gp-0x6a56 = -raw18, 8 counts per deg/s (motor frame); w18 = -raw18/8 deg/s,
          same sign as d(theta)/dt [r71b_cache s18_rate_raw; creep20_loop_id rate_x].
  bar     0x18F STEER_TORQUE_SENSOR raw * 1.024 (the kit's wire torque); gp-0x4f60 ~= -bar [score_time r71b_runs].
  tap     0x1AB: T = gp-0x6b38, field = sign<<9 | |T|>>3; THIS FILE REPORTS TAP IN FIELD LSB = T/8, the unit every
          pre-registered tap threshold is written in ("|tap| >= 300 (rail)" = 2400 T; C0 §6 "the tap reads T/8").
          Polarity sign(T) = +sign(raw) [memory accord-cereal-slot-137-collision-and-tap-polarity-plus].
  Damping: the motor torque on the wheel is u = -T, so a D that OPPOSES motion has c_D > 0; c_D < 0 = AIDING = R1.

THE SCHEMA TRAP: kit cereal slot 137 collides with the fork's starpilotLateralState; nothing here reads slot 137.
The extraction uses v293_flight_read.extract (patched schema, proven on fork routes) plus one extra pass for the
fields that cache omits (STEER_STATUS, 0x14A b4, carFw, initData params, the camera's bus-2 0xE4).

Marked throughout: EVIDENCE = measured on the wire or read from the image; BELIEF = modelled or inherited.
Score bands; the OPERATOR scores symptoms.  Nothing here licenses the word "fixed".
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import io
import json
import math
import os
import re
import sys
import time as _time
import types
from pathlib import Path

_T0 = _time.time()

import numpy as np
from scipy import signal

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent                       # .../rlog-tools/studies/angle_loop
KIT = HERE.parents[2]                                        # repo root
AL = KIT / "analysis-2020accord" / "studies" / "angle_loop"
GRIND = KIT / "rlog-tools" / "studies" / "grind"
for _q in (GRIND, KIT / "rlog-tools" / "studies" / "osc-highangle", KIT / "analysis-2020accord" / "studies" / "v280",
           KIT / "analysis-2020accord" / "lib", AL / "refute_c2r2_nonlinear", AL / "c3" / "rev2B", AL,
           AL / "panel", AL / "c1", HERE):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = KIT / "_scratch" / "angle_loop" / "drive-read"
FS = 100.0
DT = 0.01
# RUNTIME (operator rule 2026-10-02: analyses run in seconds on a per-route cache).  The 1 kHz lane replays are the
# integer-exact fast lane (drive_read_fastlane.py: memoryless stages in numpy, only the recursions in a scalar loop,
# bit-exact against the source lane), cached per (wire inputs + image + VERSION) under SCR/replay.
import drive_read_fastlane as FL                             # noqa: E402
_RT = dict(replay_s=0.0, hits=0, misses=0, fallback=[])
_MEMO = {}

# =====================================================================================================================
# PRE-REGISTERED THRESHOLDS -- each from the design record, cited by heading.  None is fitted on a flight.
# =====================================================================================================================
THR = dict(
    # ---- C3-rev2 §7 "The instrument" + C3 §8 table (the rows rev2 inherits)
    ratio_lo=-1.25, ratio_hi=-0.80,       # LIVE angle loop: c_meas/c_raw in [-1.25, -0.80]           (rev2 §7)
    notlive_ratio=0.20,                   # NOT LIVE wrong image: |c_meas| < 0.2 |c_raw|                 (C3 §8)
    cP_tol=0.30,                          # LIVE schedule: c_P within +-30 % of the band prediction       (C3 §8)
    dip_lo=0.25, dip_hi=0.60,             # c_P(10-12.5)/c_P(5-8)                                         (C3 §8)
    hi_lo=1.05, hi_hi=1.80,               # c_P(>22)/c_P(5-8)                                             (C3 §8)
    cIcP_lo=1.9, cIcP_hi=3.6,             # LIVE Ki-40: c_I/c_P in [1.9, 3.6] /s (~2.8; C3 Ki 56 gave 3.9) (rev2 §7)
    cD_lo=0.45, cD_hi=0.70,               # LIVE re-sized D: c_D in [0.45, 0.70] tap LSB per deg/s        (rev2 §7)
    cave_skipped_cP=0.14,                 # NOT LIVE cave skipped: c_P ~ 0.14 in every band              (C3 §8)
    a2_tap=20.0, a2_t=0.15,               # LIVE A2: |tap| < 20 LSB within 0.15 s of every request drop   (C3 §8)
    r2_tap=300.0, r2_t=0.30,              # R2 |tap| >= 300 LSB (the rail) hands-off > 0.3 s              (rev2 §7)
    r3_flo=0.25, r3_fhi=5.5, r3_cycles=4, r3_zeta=0.25,   # R3* (rev2 §5 stop bands, lower edge 0.25 Hz)
    r5_ring_pct=0.5, r5_f7=0.0,           # R5 ring presence > 0.5 %, F7 > 0                              (rev2 §5)
    r6_deg=10.0, r6_t=0.5, r6_v=8.0,      # R6 |theta - theta_sp| > 10 deg hands-off > 0.5 s at > 8 m/s   (rev2 §7)
    r7_t=0.20,                            # R7 tap pushing toward 0 deg > 0.2 s after a request drop      (rev2 §7)
    handsoff_bar=500.0,                   # hands-off = |0x18F| < 500 wire                                (rev2 §7)
    settle_s=1.2,                         # >= 1.2 s after engage                                         (rev2 §7)
    i_flat_T=200.0,                       # light hold: the I component flat within ~200 T (= 25 LSB)     (rev2 §7)
    rel_over_add=2.0,                     # release overshoot <= the §4 value + 2 deg                      (rev2 §7)
    track_lo=0.95, track_hi=1.05,         # the goal: tracking gain in every band >= 8 m/s               (STATE goal)
    turnhold=0.90,                        # the goal: turn-hold >= 0.90                                   (STATE goal)
    goal_min_s=60.0,                      # "FAILED its stated goal" clauses need >= 60 s in a band      (C3 §10)
    # ---- detector floors set on SYNTHETIC controls and HISTORICAL routes only (angle_loop_controls.py), before
    #      any angle-loop flight exists.  They are instrument constants, not goal bars.
    r3_amp_theta=0.40,                    # deg, half-cycle peak floor on the band-passed 0x14A angle
    r3_amp_err=0.25,                      # deg, on the tracking error theta - theta_sp
    r3_amp_rate=2.0,                      # deg/s on the band-passed 0x18F rate
    r3_narrow=0.60,                       # the ring carries >= 60 % of the 0.1-10 Hz energy of its own span
    r3_period_tol=0.25,                   # half-periods within +-25 % of their median
    r3_amp_ratio=1.25,                    # theta / w18: >= 1.25x the setpoint's own band content = amplified
    r3_amp_ratio_err=1.25,                # err: the same 1.25 (C3-rev2-P's own tracking error reaches 1.02 x the
                                          #   setpoint's band content at 0.65 Hz on the positive control)
    r4_excess_db=4.0,                     # a line: >= 4 dB over the +-2 Hz running-median shoulder (pooled, engaged;
                                          #   V282's own 20 Hz grind line reads 5.9-6.5 dB this way on r6c/r39)
    r4_ref_db=2.0,                        # "absent" on a reference: < 2 dB excess within +-0.75 Hz
    r4_amp_ratio=1.5,                     # and >= 1.5x every reference's +-1 Hz band amplitude
    # ---- R1's sign tests (unchanged since rev2 §7): INVERTED = c_meas/c_raw > 0, or c_D < 0 (aiding)
    r1_ratio=0.0, r1_cD=0.0,              # R1 INVERTED: c_meas/c_raw > 0 ; c_D aiding < 0                 (rev2 §7)
    # ---- the structural regression's INPUT corrections and R1's second method, set 2026-10-02 AFTER route 79 (they
    #      are identification fixes of the instrument, not bars fitted on a flight; the sign tests above are unchanged)
    struct_anchor_s=5.0,                  # replayed I re-anchored per ~5 s window (one intercept each)    (M1 §2.1, §3.4)
    tq_lead_frames=1,                     # torque word leads the 0x18F sample by 10 ticks = 1 frame       (M3 §4 scan)
    r1b_lo=2.0, r1b_hi=5.0,               # R1 second method: the literal regression at 2-5 Hz, where D   (M1 §3.2;
                                          #   is identified; R1 needs it AND the structural fit to agree    synthesis §6.1)
)
# the engage-ramp cells (u16 LE, per tick): direction 0 in/out, direction 2 in/out -- read from the V298 image at run
# time when it is on disk (ramp_cells), else these values (M1 §1 "Ramp cells 0xC63F6..FC = 16 / 33 / 66 / 328")
RAMP_CELLS = dict(in0=0xC63F8, out0=0xC63F6, in2=0xC63FC, out2=0xC63FA)
RAMP_FALLBACK = dict(in0=33, out0=16, in2=328, out2=66)
# the release-overshoot values C3-rev2 §4 states (judge's n1_ki40 re-run, worst over members)
REL_S4 = dict(inward=7.2, outward_lo=7.2, outward_hi=2.8, nudge=2.0)

BANDS_CP = (("5-8", 5.0, 8.0), ("8-10", 8.0, 10.0), ("10-12.5", 10.0, 12.5), ("12.5-15", 12.5, 15.0),
            ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))
BANDS_GOAL = (("8-15", 8.0, 15.0), ("15-22", 15.0, 22.0), (">22", 22.0, 99.0))
BANDS_FRIC = (("0-5", 0.0, 5.0), ("5-8", 5.0, 8.0), ("8-12.5", 8.0, 12.5), ("12.5-18", 12.5, 18.0),
              ("18-25", 18.0, 25.0), (">25", 25.0, 99.0))
REFS_DEFAULT = ("r6c", "r39", "r71b_v294")          # V282 x2 (the goal's dwell reference, r6c first) + V294
REF_BUILD = {"r6c": "V282", "r39": "V282", "r3a": "V282", "r3c": "V282", "r71b_v294": "V294 (V295 stand-in)"}


def pr(s=""):
    print(s, flush=True)


# =====================================================================================================================
# THE IMAGE'S CONSTANTS (read from the V295 image -- the V296 design changes none of these cells) + the GB-P table
# =====================================================================================================================
_K = {}


def image_constants():
    """kappa_out (T per S-unit), c_P per G, c_D, c_I/c_P -- from the image's cells, integer-marched where integer."""
    if _K:
        return _K
    import nl_sim as NS                      # V295 image cells, sha-asserted in nl_sim
    import rb_table as RT                    # the GB-P / GB-F tables (C3-rev2 §1.3)
    c = NS.CAL
    fA = int(NS.lerp_vec(*c["fadeA"], np.zeros(1, np.int64))[0])
    fB = int(NS.lerp_vec(*c["fadeB"], np.zeros(1, np.int64))[0])
    f = ((fA * fB) & 0xFFFF) >> 8                                    # 0x2A0B4..0x2A0BC: 254 at rest
    # output lag 0x2A174..0x2A1B0, marched to steady state on a constant Sc (integer exact)
    Sc, ol = 10000, 0
    for _ in range(4000):
        t1 = (Sc * c["ob"]) >> 10
        t2 = (c["oa"] * ol) >> 10
        on = t1 + t2
        y = (ol + on) >> 5
        ol = on
    lagdc = y / Sc
    kout = (f / 256.0) * lagdc * c["fwd"] / 32768.0                  # T per S-unit (x pol -1 -> sign handled below)
    _K.update(f=f, lagdc=lagdc, kout=kout, oa=c["oa"], ob=c["ob"], fwd=c["fwd"],
              cP_per_G=16.0 * 112.0 / 256.0 / 256.0 * kout / 8.0,    # tap LSB per wire count, per unit G
              cD=6.0 * 4.712 * kout / 8.0,                           # (48*abe)>>3, abe = -4.712 w_motor   [nl_sim]
              cIcP=lambda ki: 1000.0 * ki / (8.0 * 32.0 * 128.0) * 16.0 / (16.0 * 112.0 / 256.0),
              GB_P=tuple(RT.GB_P), GB_F=tuple(RT.GB_F),
              a100=(c["oa"] / 1024.0) ** 10)                         # the lag pole sampled at 100 Hz
    return _K


def G_of_v(v_mps, rows=None):
    """the cave's integer walk G(gp-0x6a5e), gp-0x6a5e ~= round(v * 3.6 * 64) [BELIEF: the speed word = vEgo*230.4;
    0x158's XMISSION_SPEED reads 0.976 x vEgo on r71b]."""
    import nl_cave as NC
    K = image_constants()
    rows = list(rows or K["GB_P"])
    vw = np.clip(np.round(np.asarray(v_mps, float) * 3.6 * 64), 0, 12000).astype(int)
    lut = _glut(tuple(rows))
    return lut[vw]


_GL = {}


def _glut(rows):
    import nl_cave as NC
    if rows not in _GL:
        _GL[rows] = np.array([NC.walk_G(list(rows), v) for v in range(0, 12001)], float)
    return _GL[rows]


# =====================================================================================================================
# THE WIRE DICT -- one 100 Hz grid + the native 50 Hz tap.  Built from a route (C20.load + extras) or by the
# synthetic generator (angle_loop_controls.py) through the SAME constructor, so the reader cannot tell them apart.
# =====================================================================================================================
def make_wire(t, ang, raw, req, sca, bar, wire18, vego, T_t, T, status=None, b4=None, pressed=None, have=None,
              meta=None):
    """t: 100 Hz frame times (s).  ang deg (0x14A), raw 0xE4 counts, req/sca 0/1, bar = raw18*1.024, wire18 = 0x18F
    rate raw counts, vego m/s, T_t/T = the tap's native instants and gp-0x6b38 counts (multiples of 8)."""
    W = dict(t=np.asarray(t, float), ang=np.asarray(ang, float), raw=np.asarray(raw, float),
             req=np.asarray(req, float) > 0.5, sca=np.asarray(sca, float) > 0.5, bar=np.asarray(bar, float),
             wire=np.asarray(wire18, float), vego=np.asarray(vego, float),
             T_t=np.asarray(T_t, float), T=np.asarray(T, float), meta=dict(meta or {}))
    n = len(W["t"])
    W["status"] = np.full(n, np.nan) if status is None else np.asarray(status, float)
    W["b4"] = np.full(n, np.nan) if b4 is None else np.asarray(b4, float)
    W["pressed"] = np.full(n, np.nan) if pressed is None else np.asarray(pressed, float)
    W["have"] = np.ones(n, bool) if have is None else np.asarray(have, bool)
    return derive(W)


def derive(W):
    n = len(W["t"])
    W["eng"] = W["req"] & W["sca"] & W["have"]
    W["theta"] = W["ang"]
    W["theta_sp"] = -W["raw"] / 10.0
    W["f14a"] = -10.0 * W["ang"]
    W["ew"] = W["raw"] - W["f14a"]                         # = -10 (theta_sp - theta), wire counts
    W["w18"] = -W["wire"] / 8.0                            # deg/s, sign of d(theta)/dt (motor frame)
    W["handsoff"] = np.abs(W["bar"]) < THR["handsoff_bar"]
    # engaged episodes, time since the request rising edge, and the integral regressor (reset at each engage)
    eid = np.zeros(n, int)
    tse = np.full(n, -1.0)
    Iw = np.zeros(n)
    k, acc, t0 = 0, 0.0, None
    for i in range(n):
        if W["eng"][i]:
            if i == 0 or not W["eng"][i - 1]:
                k += 1
                acc, t0 = 0.0, W["t"][i]
            acc += W["ew"][i] * DT
            eid[i], tse[i], Iw[i] = k, W["t"][i] - t0, acc
    W["eid"], W["tse"], W["Iw"] = eid, tse, Iw
    W["T_lsb"] = W["T"] / 8.0
    W["T100"] = _zoh(W["T_t"], W["T_lsb"], W["t"])
    return W


def _zoh(t_src, x_src, t_dst):
    j = np.searchsorted(t_src, t_dst, side="right") - 1
    out = np.asarray(x_src, float)[np.clip(j, 0, max(len(x_src) - 1, 0))].copy()
    out[j < 0] = np.nan
    return out


def runs(mask, minlen):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


# =====================================================================================================================
# ROUTE LOADING (v293_flight_read's extraction + one extras pass)
# =====================================================================================================================
def _fr():
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_flight_read as FR
    FR.g = {}                       # the documented NameError workaround (run_flight_read.py)
    return FR


def _c20():
    with contextlib.redirect_stdout(io.StringIO()):
        import creep20_loop_id as C20
    return C20


def extras_path(prefix):
    return SCR / "routes" / (prefix + "_extras.npz")


def extract_extras(prefix, force=False):
    """ONE pass for what the v280 cache omits: 0x18F byte 4 (STEER_STATUS nibble), 0x14A byte 4, the camera's bus-2
    0xE4 (request + torque), carParams.carFw (EPS fwVersion), initData params (every key), Testing-Ground-free."""
    out = extras_path(prefix)
    if out.exists() and not force:
        return out
    FR = _fr()
    clog, patched = FR.fork_log_schema()
    import zstandard
    segs = sorted(glob.glob(os.path.join(FR.RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        raise SystemExit("no rlogs for %s in %s -- fetch them (fetch-rlogs skill)" % (prefix, FR.RLOGS))
    t18, st18, t14, b414, tcam, rcam, qcam, tps, pss = ([] for _ in range(9))
    carfw, params, git = [], {}, {}
    for p in segs:
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception:
                break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    if m.src == 1 and m.address == 0x18F and len(d) >= 5:
                        t18.append(tm); st18.append(d[4])
                    elif m.src == 1 and m.address == 0x14A and len(d) >= 5:
                        t14.append(tm); b414.append(d[4])
                    elif m.src == 2 and m.address == 0x0E4 and len(d) >= 3:
                        v = (d[0] << 8) | d[1]
                        tcam.append(tm); qcam.append((d[2] >> 7) & 1); rcam.append(v - 65536 if v >= 32768 else v)
            elif w == "carState":
                tps.append(tm); pss.append(1 if evt.carState.steeringPressed else 0)
            elif w == "carParams" and not carfw:
                try:
                    for fw in evt.carParams.carFw:
                        carfw.append(dict(ecu=str(fw.ecu), fw=bytes(fw.fwVersion).decode("latin-1", "replace"),
                                          addr=int(fw.address)))
                except Exception as e:
                    carfw.append(dict(err=str(e)[:100]))
            elif w == "initData" and not params:
                try:
                    for e in evt.initData.params.entries:
                        try:
                            s = bytes(e.value).decode("utf-8")
                            params[e.key] = s if len(s) < 300 else s[:300] + "..."
                        except UnicodeDecodeError:
                            params[e.key] = "<binary>"
                    m = evt.initData
                    git = dict(commit=str(m.gitCommit), branch=str(m.gitBranch), remote=str(m.gitRemote))
                except Exception:
                    pass
    out.parent.mkdir(parents=True, exist_ok=True)
    A = lambda x: np.asarray(x, float)  # noqa: E731
    np.savez(out, t18=A(t18), st18=A(st18), t14=A(t14), b414=A(b414), tcam=A(tcam), rcam=A(rcam), qcam=A(qcam),
             tps=A(tps), pss=A(pss),
             meta=np.array(json.dumps(dict(carfw=carfw, params=params, git=git, prefix=prefix, patched=bool(patched)))))
    return out


def load_route(arg, with_extras=True):
    """-> W.  <arg> = a v280 cache tag (references) or a route id (extracted on first use)."""
    FR = _fr()
    C20 = _c20()
    cache = os.path.join(FR.CACHE, arg + ".npz")
    prefix = None
    if os.path.exists(cache):
        tag = arg
        prefix = FR.tag_prefix(tag)
    else:
        m = re.match(r"^([0-9a-f]{16}_[0-9a-f]{8}--[0-9a-f]+)", arg)
        if not m:
            tag, prefix = FR.resolve(arg)
        else:
            prefix = m.group(1)
        ctr = prefix.split("_")[1].split("--")[0].lstrip("0") or "0"
        tag = "r%s_%s_al" % (ctr, prefix.split("--")[1][:6])          # counter + hash: the counter is REUSED
        if not os.path.exists(os.path.join(FR.CACHE, tag + ".npz")):
            FR.extract(prefix, tag)
    g = C20.load(tag)
    t = g["t"]
    meta = dict(tag=tag, prefix=prefix, source="route")
    status = b4 = pressed = None
    if with_extras and prefix:
        try:
            E = np.load(extract_extras(prefix), allow_pickle=False)
            status = np.round(np.interp(t, E["t18"], E["st18"])) if len(E["t18"]) else None
            if status is not None:
                status = (status.astype(int) >> 4).astype(float)
            b4 = _zoh(E["t14"], E["b414"], t) if len(E["t14"]) else None
            pressed = _zoh(E["tps"], E["pss"], t) if len(E["tps"]) else None
            mj = json.loads(str(E["meta"]))
            meta.update(carfw=mj["carfw"], params=mj["params"], git=mj["git"],
                        cam=dict(n=int(len(E["tcam"])), n_req=int(np.sum(E["qcam"] > 0)),
                                 max_abs=float(np.max(np.abs(E["rcam"]))) if len(E["rcam"]) else 0.0))
        except SystemExit as e:
            meta["extras_error"] = str(e)
    else:
        bp = os.path.join(FR.CACHE, tag + "_b4.npz")
        if os.path.exists(bp):
            B = np.load(bp)
            b4 = _zoh(B["t14b"], B["b4"], t)
    D = np.load(os.path.join(FR.CACHE, tag + ".npz"))
    if pressed is None and "cs_press" in D.files:
        pressed = _zoh(D["tcs"], D["cs_press"], t)
    W = make_wire(t, g["ang"], np.round(g["cmd"]), g["req"], g["sca"], g["bar"], g["wire"], g["vego"],
                  g["T_t"], g["T"], status=status, b4=b4, pressed=pressed, have=g["have18"], meta=meta)
    return W


# =====================================================================================================================
# 1.  THE REGRESSION (pre-registered form) -- per band, on the tap's native 50 Hz instants
# =====================================================================================================================
def _lagfilt(x, a):
    """the image's output-lag pole (0xC63EC = 992 at 1 kHz) sampled at 100 Hz, unity DC: y = a y + (1-a) x."""
    return signal.lfilter([1.0 - a], [1.0, -a], np.nan_to_num(x))


_BPSOS = {}


def _bp(x, lo=0.3, hi=3.0, fs=50.0):
    k = (lo, hi, fs)
    if k not in _BPSOS:                                      # butter() is deterministic: the same sos, designed once
        _BPSOS[k] = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(_BPSOS[k], x)


def regress(W, lag_frames=None, lagfilter=True, bp=(0.3, 3.0), bands=BANDS_CP, min_run_s=2.0, extra_mask=None):
    """returns dict(per band rows, pooled, best lag).  Coefficients in TAP LSB per regressor unit."""
    K = image_constants()
    a = K["a100"]
    regs = dict(ew=W["ew"], raw=W["raw"], f14a=W["f14a"], Iw=W["Iw"], w18=W["w18"])
    if lagfilter:
        # the filter must not smear across episode boundaries: run it per engaged episode
        R = {k: np.zeros_like(v) for k, v in regs.items()}
        for a0, b0 in runs(W["eng"], 2):
            for k, v in regs.items():
                R[k][a0:b0] = _lagfilt(v[a0:b0], a)
        regs = R
    base = W["eng"] & W["handsoff"] & (W["tse"] >= THR["settle_s"])
    if extra_mask is not None:
        base = base & extra_mask
    tt = W["T_t"]
    lags = range(-2, 9) if lag_frames is None else [lag_frames]
    best = None
    out_by_lag = {}
    for L in lags:
        j = np.searchsorted(W["t"], tt - L * DT, side="right") - 1
        ok = (j >= 0) & (j < len(W["t"]))
        jj = np.clip(j, 0, len(W["t"]) - 1)
        m50 = ok & base[jj] & np.isfinite(W["T"])
        rows = {}
        pool = dict(X1=[], X2=[], y=[])
        for nm, lo, hi in bands:
            mb = m50 & (W["vego"][jj] >= lo) & (W["vego"][jj] < hi)
            X1, X2, Y, G, nsamp = [], [], [], [], 0
            for r0, r1 in runs(mb, int(min_run_s * 50)):
                idx = jj[r0:r1]
                y = W["T"][r0:r1] / 8.0
                f = (lambda z: _bp(z, *bp)) if bp else (lambda z: z - z.mean())
                e_ = 25 if bp else 0
                sl = slice(e_, (r1 - r0) - e_)
                if bp:
                    # one sosfiltfilt over the stacked rows (y + the five regressors): the filter runs each row on its
                    # own, so every row is the 1-D call's result
                    Z = _bp(np.vstack([y] + [regs[k][idx] for k in regs]), *bp)
                    y_ = Z[0][sl]
                    c = {k: Z[1 + i][sl] for i, k in enumerate(regs)}
                else:
                    y_ = f(y)[sl]
                    c = {k: f(regs[k][idx])[sl] for k in regs}
                X1.append(np.c_[c["ew"], c["Iw"], c["w18"]])
                X2.append(np.c_[c["raw"], c["f14a"], c["Iw"], c["w18"]])
                Y.append(y_)
                G.append(G_of_v(W["vego"][idx])[sl])
                nsamp += len(y_)
            if nsamp < 100:
                rows[nm] = dict(n=nsamp, ok=False)
                continue
            X1, X2, Y, G = np.vstack(X1), np.vstack(X2), np.concatenate(Y), np.concatenate(G)
            b1, r2_1, se1 = _ols(X1, Y)
            b2, r2_2, se2 = _ols(X2, Y)
            cP, cI, cD = b1
            ratio = b2[1] / b2[0] if abs(b2[0]) > 1e-12 else np.nan
            # delta-method SE of the ratio from the X2 fit
            rows[nm] = dict(n=nsamp, s=nsamp / 50.0, ok=True, cP=cP, cI=cI, cD=cD, r2=r2_1,
                            se_cP=se1[0], se_cI=se1[1], se_cD=se1[2],
                            c_raw=b2[0], c_meas=b2[1], ratio=ratio, r2_ratio=r2_2,
                            se_ratio=_ratio_se(b2, se2),
                            cIcP=(cI / cP if abs(cP) > 1e-12 else np.nan),
                            G_mean=float(G.mean()), cP_pred=float(G.mean() * K["cP_per_G"]))
            pool["X1"].append(X1); pool["X2"].append(X2); pool["y"].append(Y)
        if pool["y"]:
            X1, X2, Y = np.vstack(pool["X1"]), np.vstack(pool["X2"]), np.concatenate(pool["y"])
            b2, r2_2, se2 = _ols(X2, Y)
            b1, r2_1, se1 = _ols(X1, Y)
            pooled = dict(n=len(Y), ratio=b2[1] / b2[0] if abs(b2[0]) > 1e-12 else np.nan, r2_ratio=r2_2,
                          se_ratio=_ratio_se(b2, se2), c_raw=b2[0], c_meas=b2[1], cD=b1[2], cI=b1[1], cP=b1[0],
                          r2=r2_1, cIcP=b1[1] / b1[0] if abs(b1[0]) > 1e-12 else np.nan)
        else:
            pooled = dict(n=0)
        out_by_lag[L] = dict(rows=rows, pooled=pooled)
        score = pooled.get("r2", -np.inf) if pooled.get("n", 0) else -np.inf
        if best is None or score > best[0]:
            best = (score, L)
    L = best[1] if best else 0
    res = out_by_lag[L]
    res["lag_frames"] = L
    res["lag_r2"] = {k: (v["pooled"].get("r2") if v["pooled"].get("n") else None) for k, v in out_by_lag.items()}
    res["lagfilter"], res["bp"] = lagfilter, bp
    return res


def _ols(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    ss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(r ** 2)) / ss if ss > 0 else np.nan
    n, p = X.shape
    s2 = float(np.sum(r ** 2)) / max(n - p, 1)
    try:
        cov = s2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.maximum(np.diag(cov), 0))
    except np.linalg.LinAlgError:
        se = np.full(p, np.nan)
    # samples are band-passed and autocorrelated: inflate by sqrt(effective-sample factor) ~ sqrt(50/(2*3))
    return b, r2, se * math.sqrt(50.0 / 6.0)


def _ratio_se(b, se):
    if abs(b[0]) < 1e-12:
        return np.nan
    return abs(b[1] / b[0]) * math.sqrt((se[0] / b[0]) ** 2 + (se[1] / b[1]) ** 2) if abs(b[1]) > 1e-12 else np.nan


def verdict(R, W=None, a2=None, rep=None, r1b=None):
    """LIVE / NOT LIVE / INVERTED / INCONCLUSIVE, with every clause and its margin.
    r1b = R1's SECOND METHOD (regress() at THR r1b_lo..r1b_hi Hz).  When given, each R1 clause fires only if BOTH the
    fit R and r1b cross its sign threshold (both values printed); when None, R alone decides (the synthetic controls'
    and the literal read's form, unchanged)."""
    rows = {k: v for k, v in R["rows"].items() if v.get("ok")}
    cl = []
    P = R["pooled"]
    structural = R.get("kind") == "structural"
    rb = [(v["ratio"], v["n"]) for v in rows.values() if np.isfinite(v.get("ratio", np.nan))]
    # structural: a, b, c, d are dimensionless (1 for the live design in EVERY band), so the pooled fit is the
    # efficient estimate; plain: c_P differs by band, so the ratio is read per band (exposure-weighted median)
    ratio = P.get("ratio", np.nan) if structural else (_wmed(rb) if rb else P.get("ratio", np.nan))
    cm_cr = [(abs(v.get("c_meas", -v.get("b", np.nan))) / max(abs(v.get("c_raw", v.get("a", np.nan))), 1e-12), v["n"])
             for v in rows.values()]
    cm_cr = [p for p in cm_cr if np.isfinite(p[0])]
    inv_ratio = bool(np.isfinite(ratio) and ratio > THR["r1_ratio"])
    cDs = [v["cD"] for v in rows.values() if v["n"] >= 500]
    cD_med = P.get("cD", np.nan) if structural else (float(np.median(cDs)) if cDs else P.get("cD", np.nan))
    inv_D = bool(np.isfinite(cD_med) and cD_med < THR["r1_cD"])
    r1b_ratio = r1b_cD = np.nan
    if r1b is not None:
        # the second method is a plain (non-structural) fit: read per band, exposure-weighted median ratio, median c_D
        rows_b = {k: v for k, v in r1b["rows"].items() if v.get("ok")}
        rb_b = [(v["ratio"], v["n"]) for v in rows_b.values() if np.isfinite(v.get("ratio", np.nan))]
        r1b_ratio = _wmed(rb_b) if rb_b else r1b["pooled"].get("ratio", np.nan)
        cDs_b = [v["cD"] for v in rows_b.values() if v["n"] >= 500]
        r1b_cD = float(np.median(cDs_b)) if cDs_b else r1b["pooled"].get("cD", np.nan)
        inv_ratio_b = bool(np.isfinite(r1b_ratio) and r1b_ratio > THR["r1_ratio"])
        inv_D_b = bool(np.isfinite(r1b_cD) and r1b_cD < THR["r1_cD"])
        votes = dict(ratio=(inv_ratio, inv_ratio_b), cD=(inv_D, inv_D_b))
        inv_ratio, inv_D = inv_ratio and inv_ratio_b, inv_D and inv_D_b
    live_ratio = bool(THR["ratio_lo"] <= ratio <= THR["ratio_hi"])
    q = (abs(P.get("c_meas", np.nan)) / max(abs(P.get("c_raw", np.nan)), 1e-12)) if structural else         (_wmed(cm_cr) if cm_cr else np.nan)
    notlive_img = bool(np.isfinite(q) and q < THR["notlive_ratio"])
    if r1b is None:
        cl.append(("R1 INVERTED: c_meas/c_raw > 0", inv_ratio, ("pooled %.3f" if structural else "band median %.3f") % ratio))
        cl.append(("R1 INVERTED: c_D aiding (< 0)", inv_D, ("pooled %.3f tap/(deg/s)" if structural else "median over bands %.3f tap/(deg/s)") % cD_med))
    else:
        yn = {True: "fires", False: "no"}
        bp_ = "%g-%g Hz" % tuple(r1b.get("bp") or (np.nan, np.nan))
        cl.append(("R1 INVERTED: c_meas/c_raw > 0 (BOTH methods must agree)", inv_ratio,
                   "%s %.3f [%s] ; %s band median %.3f [%s]" % ("structural pooled" if structural else "band median",
                                                                ratio, yn[votes["ratio"][0]], bp_, r1b_ratio,
                                                                yn[votes["ratio"][1]])))
        cl.append(("R1 INVERTED: c_D aiding (< 0) (BOTH methods must agree)", inv_D,
                   "%s %.3f [%s] ; %s band median %.3f [%s] tap/(deg/s)" % (
                       "structural pooled" if structural else "band median", cD_med, yn[votes["cD"][0]], bp_, r1b_cD,
                       yn[votes["cD"][1]])))
    cl.append(("LIVE angle loop: c_meas/c_raw in [%.2f, %.2f]" % (THR["ratio_lo"], THR["ratio_hi"]), live_ratio,
               ("pooled %.3f" if structural else "band median %.3f") % ratio))
    cl.append(("NOT LIVE wrong image: |c_meas| < 0.2 |c_raw|", notlive_img,
               ("|c_meas|/|c_raw| = %.3f (pooled)" if structural else "|c_meas|/|c_raw| = %.3f (band median)") % q))
    # schedule
    sched = {}
    for nm, v in rows.items():
        sched[nm] = (v["cP"] / v["cP_pred"]) if v["cP_pred"] > 0 else np.nan
    within = [abs(x - 1.0) <= THR["cP_tol"] for x in sched.values() if np.isfinite(x)]
    live_sched_bands = bool(within) and all(within)
    dip = (rows["10-12.5"]["cP"] / rows["5-8"]["cP"]) if ("10-12.5" in rows and "5-8" in rows) else np.nan
    hi = (rows[">22"]["cP"] / rows["5-8"]["cP"]) if (">22" in rows and "5-8" in rows) else np.nan
    cl.append(("LIVE schedule: c_P within +-30 %% of the band prediction (%d bands)" % len(within),
               live_sched_bands, " ".join("%s %.2f" % (k, x) for k, x in sched.items())))
    cl.append(("LIVE schedule: dip c_P(10-12.5)/c_P(5-8) in [%.2f, %.2f]" % (THR["dip_lo"], THR["dip_hi"]),
               bool(THR["dip_lo"] <= dip <= THR["dip_hi"]) if np.isfinite(dip) else None, "%.3f" % dip))
    cl.append(("LIVE schedule: c_P(>22)/c_P(5-8) in [%.2f, %.2f]" % (THR["hi_lo"], THR["hi_hi"]),
               bool(THR["hi_lo"] <= hi <= THR["hi_hi"]) if np.isfinite(hi) else None, "%.3f" % hi))
    skipped = [abs(v["cP"] / THR["cave_skipped_cP"] - 1.0) <= THR["cP_tol"] for v in rows.values()]
    cave_skipped = bool(skipped) and all(skipped) and len(skipped) >= 2
    cl.append(("NOT LIVE cave skipped: c_P ~ 0.14 (+-30 %) in every band", cave_skipped,
               " ".join("%s %.3f" % (k, v["cP"]) for k, v in rows.items())))
    cIcPs = [(v["cIcP"], v["n"]) for v in rows.values() if np.isfinite(v["cIcP"]) and v["n"] >= 500]
    cIcP = P.get("cIcP", np.nan) if structural else (_wmed(cIcPs) if cIcPs else P.get("cIcP", np.nan))
    cl.append(("LIVE Ki 40: c_I/c_P in [%.1f, %.1f] /s" % (THR["cIcP_lo"], THR["cIcP_hi"]),
               bool(THR["cIcP_lo"] <= cIcP <= THR["cIcP_hi"]) if np.isfinite(cIcP) else None, "%.2f" % cIcP))
    cl.append(("LIVE re-sized D: c_D in [%.2f, %.2f]" % (THR["cD_lo"], THR["cD_hi"]),
               bool(THR["cD_lo"] <= cD_med <= THR["cD_hi"]) if np.isfinite(cD_med) else None, "%.3f" % cD_med))
    if a2 is not None:
        cl.append(("LIVE A2: |tap| < %d LSB within %.2f s of every request drop" % (THR["a2_tap"], THR["a2_t"]),
                   a2.get("live"), "%d/%d drops pass" % (a2.get("n_pass", 0), a2.get("n", 0))))
    # the replay identity (C0/C1 §6: "...and the tap reproduces V295's raw-only surface (R2 >= 0.9)")
    rep_best, rep_v295, rep_p = None, np.nan, np.nan
    if rep:
        rr_ = {k: v.get("r2", np.nan) for k, v in rep.items() if v.get("n")}
        if rr_:
            rep_best = max(rr_, key=lambda k: rr_[k] if np.isfinite(rr_[k]) else -1e9)
            rep_v295, rep_p = rr_.get("V295", np.nan), rr_.get("C3B-P", np.nan)
        cl.append(("REPLAY: the tap reproduces V295's lane (R2 >= 0.9) [wrong image]",
                   bool(np.isfinite(rep_v295) and rep_v295 >= 0.9), "R2 V295 %.3f, C3B-P %.3f, best %s"
                   % (rep_v295, rep_p, rep_best)))
        cl.append(("REPLAY: the tap reproduces C3-rev2-P's lane (R2 >= 0.9) [the image is live]",
                   bool(np.isfinite(rep_p) and rep_p >= 0.9), "best %s" % rep_best))
    wrong_by_replay = bool(np.isfinite(rep_v295) and rep_v295 >= 0.9 and not (np.isfinite(rep_p) and rep_p >= 0.9))
    # IMAGE IDENTITY by replay model selection.  It separates what the regression clauses only bound (C3 Ki 56 reads
    # c_I/c_P 3.6-3.7 structurally, a 0.1 margin over the 3.6 bar; its replay reads 1.000 vs C3-rev2-P's 0.93 --
    # angle_loop_controls.py section A)
    ident = None
    if rep:
        rr_ = sorted(((v.get("r2", np.nan), k) for k, v in rep.items() if v.get("n") and np.isfinite(v.get("r2", np.nan))),
                     reverse=True)
        # the replay separates the P/I structure (table, Ki, cave present, V295) by a wide margin but NOT the D gain
        # alone (C3B-P vs Kd 34 vs the held-D fallback differ by 0.001-0.02 in R2 on the controls): every image within
        # 0.03 of the best is "not separable by replay" and the c_D clause decides among them
        if rr_ and rr_[0][0] >= 0.9:
            ident = tuple(k for r, k in rr_ if rr_[0][0] - r < 0.03)
        cl.append(("REPLAY IDENTITY: images within 0.03 of the best R2 (>= 0.9)", ident is not None,
                   "-> %s ;  %s" % (ident, "  ".join("%s %.3f" % (k, r) for r, k in rr_[:6]))))
    # INVERTED is a claim about a LIVE angle loop whose sign is wrong: it needs the angle P to be present
    # (structural a >= 0.5); without that the tap is some other image and the identity clauses decide
    p_present = (not structural) or (abs(P.get("a", 0.0)) >= 0.5)
    rail = R.get("rail_frac", 0.0)
    cl.append(("RAIL: settled hands-off tap frames at the 2461 rail <= 20 %", rail <= 0.20, "%.1f %%" % (100 * rail)))
    if rail > 0.20:
        v = "RAILED (R2) -- the lane sits on the 2461 rail; the regression is void; REVERT"
        return dict(verdict=v, clauses=cl, ratio=ratio, cD=cD_med, cIcP=np.nan, dip=np.nan, hi=np.nan, sched={},
                    ident=None)
    if wrong_by_replay or (notlive_img and not (inv_ratio and p_present)):
        v = "NOT LIVE (wrong image / torque firmware)"
    elif p_present and (inv_ratio or inv_D):
        v = "INVERTED"
    elif notlive_img:
        v = "NOT LIVE (wrong image / torque firmware)"
    elif cave_skipped or (ident is not None and "SKIP" in ident and "C3B-P" not in ident):
        v = "NOT LIVE (cave skipped)"
    elif live_ratio:
        v = "LIVE"
    else:
        v = "INCONCLUSIVE"
    if v == "LIVE" and ident is not None and "C3B-P" not in ident:
        v = "LIVE angle loop, but the image is %s, not C3-rev2-P" % "/".join(ident)
    elif v == "LIVE":
        # the angle loop is live; the sub-clauses say whether it is the DESIGNED loop (rev2 §7's null sentence:
        # "c_I/c_P ~ 3.9 -> Ki-40 did not ship"; C3 §8: "c_D 0.40 -> the D was not re-sized")
        bad = [nm.split(":")[0].replace("LIVE ", "") for nm, ok, _ in cl
               if ok is False and nm.startswith("LIVE ") and not nm.startswith("LIVE angle loop")]
        bad = list(dict.fromkeys(bad))
        if bad:
            v = "LIVE angle loop, NOT the designed loop: %s" % ", ".join(bad)
    return dict(verdict=v, clauses=cl, ratio=ratio, cD=cD_med, cIcP=cIcP, dip=dip, hi=hi, sched=sched, ident=ident,
                r1b_ratio=r1b_ratio, r1b_cD=r1b_cD)


def _wmed(pairs):
    pairs = sorted(pairs)
    w = np.array([p[1] for p in pairs], float)
    c = np.cumsum(w) / w.sum()
    return float(pairs[int(np.searchsorted(c, 0.5))][0])


# =====================================================================================================================
# 1b. SECOND METHOD -- the byte-exact lane REPLAYED on the wire's own inputs (zero free parameters)
# =====================================================================================================================
def replay(W, cands=("C3B-P", "C3-P56", "SKIP", "C3B-P-kd34", "C3B-F"), with_v295=True, max_s=None):
    """march each candidate's lane at 1 kHz on ZOH'd wire inputs; return R2 / gain of the tap vs each replay over the
    regression mask (hands-off, request 1, settled).  The lane is a deterministic function of its inputs, so the
    closed loop does not enter: this asks only 'which image's arithmetic produced this tap?'."""
    ST = load_score_time()
    cl = replay_cands(ST)
    use = [cl[c] for c in cands if c in cl]
    n = len(W["t"])
    if max_s is not None:
        n = min(n, int(max_s * FS))
    eng = W["eng"][:n]
    out = {}
    th, cmd, tq, x, abe, vws = wire_inputs(W, n)
    if use:
        T = _replay_cand(ST, use, th, cmd, tq, x, abe, vws, eng)
        for c, Tc in zip(use, T.T):
            out[c.id] = _score_replay(W, Tc, n)
    if with_v295:
        T95 = _replay_v295(th, cmd, tq, x, vws, eng)
        out["V295"] = _score_replay(W, T95, n)
    return out


def _replay_cand(ST, use, th, cmd, tq, x, abe, vws, eng, rec_I=False, ramp_steps=(33, 16), tag=""):
    """_replay_cand_source's output, word for word, from drive_read_fastlane.cand_lane (one column per candidate;
    the columns of the source lane are independent), cached per (wire inputs + candidate + cal + VERSION).  A candidate
    whose cave feature the fast lane does not implement falls back to the source march.  ramp_steps != (33, 16) (the
    direction-2 arm) exists only in the fast lane: there the source fallback is refused (the caller drops to (33, 16)
    and says so)."""
    n = len(th)
    B = len(use)
    out = np.zeros((n, B))
    Ilog = np.zeros((n, B)) if rec_I else None
    eng = np.asarray(eng, bool)
    for b, c in enumerate(use):
        job = _cand_job(ST, c, th, cmd, tq, x, abe, vws, eng, ramp_steps=ramp_steps, tag=tag)
        if job is None and tuple(ramp_steps) != (33, 16):
            raise NotImplementedError("ramp %s needs the fast lane" % (ramp_steps,))
        if job is None:
            r = _replay_cand_source(ST, [c], th, cmd, tq, x, abe, vws, eng, rec_I=True)
            T, I = r[0][:, 0], r[1][:, 0]
        else:
            T, I = _cached(*job)
        out[:, b] = T
        if rec_I:
            Ilog[:, b] = I
    return (out, Ilog) if rec_I else out


def _inkey(*arrs):
    """sha256 of the replay's wire inputs (int64 words; the engaged mask as bool)."""
    return FL.key_of(*(np.asarray(a, bool) if np.asarray(a).dtype == bool else np.asarray(a, np.int64) for a in arrs))


def _fast_lane_drift(ST=None):
    """[] when every source function the fast lanes mirror is unchanged (drive_read_fastlane.SOURCE_SHA); else the
    names that moved -- and then the replays run the SOURCE march (slow, correct) and RUNTIME says so."""
    if "drift" not in _MEMO:
        import lane_mirror_v295 as LM
        import nl_sim as NS
        ST = ST or load_score_time()
        _MEMO["drift"] = FL.drift({
            "score_time.CandLane": ST.CandLane, "score_time.Cand": ST.Cand, "nl_sim.lerp_vec": NS.lerp_vec,
            "nl_sim.s32": NS.s32, "nl_sim.s16": NS.s16, "lane_mirror_v295.lane_tick": LM.lane_tick,
            "lane_mirror_v295.setpoint_chain": LM.setpoint_chain, "lane_mirror_v295.lerp": LM.lerp,
            "drive_read._replay_cand_source": _replay_cand_source, "drive_read._replay_v295_source": _replay_v295_source})
        if _MEMO["drift"]:
            _RT["fallback"].append("fast lane OFF (source changed: %s)" % ",".join(_MEMO["drift"]))
    return _MEMO["drift"]


def _cand_job(ST, c, th, cmd, tq, x, abe, vws, eng, ramp_steps=(33, 16), tag=""):
    """(key, label, fn, args) of one candidate's fast replay, or None when the fast lane does not implement it.
    The default (33, 16) ramp keeps the pre-2026-10-02 cache key; any other ramp or a tag extends it."""
    if _fast_lane_drift(ST):
        return None
    try:
        p = FL.cand_params(c)
    except NotImplementedError:
        return None
    import nl_sim as NS
    calk = {k: NS.CAL[k] for k in ("PCL", "SCL", "OCL", "oa", "ob", "g74a3", "dz", "fwd", "fadeA", "fadeB")}
    glut = ST.glut(c.rows)
    key = FL.key_of(_inkey(th, cmd, tq, x, abe, vws, eng), "cand", p, calk, glut)
    if tuple(ramp_steps) != (33, 16) or tag:
        key = FL.key_of(key, "ramp", list(ramp_steps), tag)
    r0, R = _ramp(eng, ramp_steps)
    return (key, "cand_" + c.id + ("_" + tag if tag else ""), FL.cand_lane,
            (p, glut, NS.CAL, th, cmd, tq, x, abe, vws, eng, R, r0, True))


def _v295_job(th, cmd, tq, x, vws, eng):
    import lane_mirror_v295 as LM
    cal = LM.load_cal()
    key = FL.key_of(_inkey(th, cmd, tq, x, vws, eng), "v295", cal)
    r0, R = _ramp(eng)
    return key, "V295", FL.v295_lane, (cal, th, cmd, tq, x, vws, eng, R, r0)


def _ramp(eng, ramp_steps=(33, 16)):
    k = ("ramp", tuple(ramp_steps), FL.key_of(np.asarray(eng, bool)))
    if k not in _MEMO:
        _MEMO[k] = FL.ramp_ticks(eng, *ramp_steps)
    return _MEMO[k]


def ramp_cells():
    """the engage-ramp per-tick steps {in0, out0, in2, out2}, u16 LE from the V298 image when it is on disk (cells
    RAMP_CELLS), else RAMP_FALLBACK (the same values, M1 §1).  -> (cells, source)."""
    if "rampcells" not in _MEMO:
        import struct
        p = sorted(glob.glob(os.path.join(os.environ.get("ACCORD_FIRMWARE_ROOT", ""), "analysis-2020accord",
                                          "_v298_*_plain_image.bin")))
        cells, src = dict(RAMP_FALLBACK), "RAMP_FALLBACK (no V298 image on disk)"
        if len(p) == 1:
            img = Path(p[0]).read_bytes()
            cells = {k: struct.unpack_from("<H", img, a)[0] for k, a in RAMP_CELLS.items()}
            src = "cells read from the V298 image"
        _MEMO["rampcells"] = (cells, src)
    return _MEMO["rampcells"]


def struct_inputs(W):
    """the structural regression's replay inputs for THIS wire (the 2026-10-02 corrections a and b, docstring §1):
    ramp arm 2 when the fork ran the angle interface (initData AccordEpsAngleLoop == "1": the angle fork sends 0xE4
    byte-2 bits 3:2 = 2 -- BELIEF from the param; EVIDENCE on route 79, arm 2 on 120 763 / 120 763 frames, M1 §4),
    else arm 0; the torque word's lead THR tq_lead_frames on a real route (a property of the car's 0x18F timing, M3 §4),
    0 on a synthetic wire (its generator latches the word on its own frame)."""
    cells, src = ramp_cells()
    meta = W.get("meta") or {}
    arm = 2 if str((meta.get("params") or {}).get("AccordEpsAngleLoop", "")).strip() == "1" else 0
    steps = (cells["in2"], cells["out2"]) if arm == 2 else (cells["in0"], cells["out0"])
    lead = int(THR["tq_lead_frames"]) if meta.get("source") == "route" else 0
    return dict(arm=arm, ramp=[int(steps[0]), int(steps[1])], ramp_src=src, q_lead=lead,
                anchor_s=THR["struct_anchor_s"])


def _cache_path(key, label):
    return SCR / "replay" / ("%s_%s.npz" % (key[:32], label))


def _cached(key, label, fn, args):
    """in-process memo, then SCR/replay/<key>_<label>.npz, else fn(*args) -> (T, I|None), stored on first
    computation.  (Worker processes were tried and REJECTED: on Windows each spawn re-imports scipy, and six of them
    cost more than the ~4 s of serial fast-lane marching they would overlap -- 17-18 s vs 15 s cold on route 79.)"""
    if key in _MEMO:
        return _MEMO[key]
    p = _cache_path(key, label)
    t0 = _time.time()
    res = None
    if p.exists():
        try:
            Z = np.load(p)
            res = (Z["T"], Z["I"] if "I" in Z.files else None)
            _RT["hits"] += 1
        except Exception:
            res = None
    if res is None:
        res = fn(*args)
    if not isinstance(res, tuple):
        res = (res, None)
    if not p.exists():
        _RT["misses"] += 1
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.stem + ".tmp.npz")
            np.savez(tmp, **({"T": res[0]} if res[1] is None else {"T": res[0], "I": res[1]}))
            os.replace(tmp, p)
        except OSError:
            pass
    _RT["replay_s"] += _time.time() - t0
    _MEMO[key] = res
    return res


def _replay_cand_source(ST, use, th, cmd, tq, x, abe, vws, eng, rec_I=False):
    """the CandLane at 1 kHz on the wire's inputs.  The speed word enters only through G(v) (the cave's walk) and the
    A3 policy's speed tests, so the lane's per-column G / vw are refreshed whenever the frame's speed word changes.
    Frames more than 1 s after a request drop with the ramp at 0 are skipped (the lane's output is 0 there and its
    state is reset exactly as the skip epilogue does: I8 := 0, Eprev := sentinel)."""
    B = len(use)
    n = len(th)
    out = np.zeros((n, B))
    Ilog = np.zeros((n, B)) if rec_I else None
    lane = ST.CandLane(use, np.full(B, int(vws[0])))
    luts = [ST.glut(c.rows) for c in use]
    vprev = int(vws[0])
    ramp = 0
    last_eng = -10 ** 9
    for k in range(n):
        e = bool(eng[k])
        if e:
            last_eng = k
        elif ramp == 0 and k - last_eng > 100:
            lane.I8[:] = 0
            lane.Eprev[:] = ST.SENT32
            lane.olag[:] = 0
            lane.Tprev[:] = 0
            continue
        vw = int(vws[k])
        if vw != vprev:
            lane.vw = np.full(B, vw, np.int64)
            lane.G = np.array([lu[vw] for lu in luts], np.int64)
            vprev = vw
        # TIMING (score_time.run's convention, the harness's model of the firmware): the 100 Hz cells gp-0x6a00 and
        # gp-0x6a56 are written at slot 4 AFTER the lane, so ticks 10k..10k+4 still see frame k-1's values and ticks
        # 10k+5..10k+9 see frame k's; the 0xE4 command is latched at tick 10k; the fresh rate is nearest-frame.
        kp = max(k - 1, 0)
        kn = min(k + 1, n - 1)
        a6p, xxp = np.full(B, th[kp]), np.full(B, x[kp])
        a6n, xxn = np.full(B, th[k]), np.full(B, x[k])
        ab0, ab1 = np.full(B, abe[k]), np.full(B, abe[kn])
        cm, q = np.full(B, cmd[k]), np.full(B, tq[k])
        for s in range(10):
            if e:
                ramp = min(0x8000, ramp + 33)
                req = act = 1
            else:
                ramp = max(0, ramp - 16)
                req = act = 0
            a6, xx = (a6p, xxp) if s <= 4 else (a6n, xxn)
            ab = ab0 if s <= 8 else ab1
            Tk = lane.tick(a6, a6, xx, ab, cm, q, ramp, act, req)
            if s == 4:
                out[k] = Tk
                if rec_I:
                    Ilog[k] = lane.log["I"]
    return (out, Ilog) if rec_I else out


def wire_inputs(W, n=None):
    """the lane's inputs reconstructed from the wire, per 100 Hz frame (EVIDENCE for the mapping, reader docstring):
    gp-0x6a00 = -f14a = 10*ang ; gp-0x69ae = clamp(-4*raw) ; gp-0x4f60 ~ -bar ; gp-0x6a56 = -raw18 ;
    gp-0x6abe ~ -gp-0x6a56 * 32768/(48*1159) (the 100 Hz-held rate stands in for the fresh 1 kHz one: BELIEF, <= 10 ms);
    gp-0x6a5e ~ round(v * 230.4)."""
    n = len(W["t"]) if n is None else n
    th = np.round(10.0 * np.nan_to_num(W["ang"][:n])).astype(np.int64)
    cmd = np.clip(-4 * np.round(np.nan_to_num(W["raw"][:n])).astype(np.int64), -0x4000, 0x4000)
    tq = np.round(-np.nan_to_num(W["bar"][:n])).astype(np.int64)
    x = np.round(-np.nan_to_num(W["wire"][:n])).astype(np.int64)
    abe = np.round(-x * 32768.0 / (48 * 1159)).astype(np.int64)
    vws = np.clip(np.round(np.nan_to_num(W["vego"][:n]) * 230.4), 0, 12000).astype(np.int64)
    return th, cmd, tq, x, abe, vws


def components(W, ref="C3B-P", ramp_steps=(33, 16), q_lead=0):
    """the C3-rev2-P lane's COMPONENT signals reconstructed from the wire, each carried through the image's own
    linear output path (fade f(|tq|>>5), the 0xC63EC/EE lag at 1 kHz, x ramp/32768, x -fwd/32768, /8 = tap LSB):
        P_raw  = ((4 gp-0x69ae) G >> 8) 112 >> 8          the setpoint half of P
        P_meas = (-(r26) G >> 8) 112 >> 8, r26 = 8 th[n] + 8 th[n-1]   the measured-angle half of P
        D      = (48 gp-0x6abe) >> 3                      the fresh-rate D (Kd 48)
        I      = I >> 7 from the byte-exact lane march (the A3 bound, the hard and opposing-hand freezes, ICL, Ki 40)
    For the LIVE design every coefficient of  tap = a P_raw + b P_meas + c I + d D (+ c0)  is 1.  The P/D/I terms
    are memoryless given the inputs except I, which the march supplies; nothing is fitted inside the chain.
    ramp_steps / q_lead (defaults = the pre-2026-10-02 inputs): the engage-ramp per-tick steps the replay marches, and
    the torque word's lead over the 0x18F frame in frames (the replay's freezes and the fade read tq[k + q_lead])."""
    ST = load_score_time()
    C = replay_cands(ST)
    th, cmd, tq, x, abe, vws = wire_inputs(W)
    if q_lead:
        tq = np.r_[tq[q_lead:], np.repeat(tq[-1:], q_lead)]
    tag = "" if (tuple(ramp_steps) == (33, 16) and not q_lead) else "r%d_%d_q%d" % (ramp_steps[0], ramp_steps[1], q_lead)
    T, Il = _replay_cand(ST, [C[ref]], th, cmd, tq, x, abe, vws, W["eng"], rec_I=True, ramp_steps=ramp_steps, tag=tag)
    n = len(th)
    G = _glut(tuple(C[ref].rows))[vws]
    th1 = np.repeat(th, 10).astype(float)
    th1 = np.r_[np.full(5, th1[0]), th1[:-5]]                 # ticks 10k..10k+4 see frame k-1 (see _replay_cand)
    r26 = 8 * th1 + 8 * np.r_[th1[:1], th1[:-1]]
    sp1 = np.repeat(cmd, 10).astype(float)
    G1 = np.repeat(G, 10)
    Praw = (4.0 * sp1 * G1 / 256.0) * 112.0 / 256.0
    Pmeas = (-r26 * G1 / 256.0) * 112.0 / 256.0
    ab1 = np.repeat(abe, 10).astype(float)
    D1 = 48.0 * np.r_[ab1[1:], ab1[-1:]] / 8.0                # tick 10k+9 sees frame k+1's rate
    I1 = np.repeat(Il[:, 0], 10)
    import nl_sim as NS
    c = NS.CAL
    fB = NS.lerp_vec(*c["fadeB"], np.minimum(np.abs(np.repeat(tq, 10) >> 5), 255))
    fA = int(NS.lerp_vec(*c["fadeA"], np.zeros(1, np.int64))[0])
    f = ((fA * fB) & 0xFFFF) >> 8
    e10 = np.repeat(W["eng"], 10)
    # the per-tick ramp (+33 capped at 0x8000 engaged, -16 floored at 0 otherwise), closed-form per frame
    ramp = _ramp(W["eng"], ramp_steps)[1].ravel().astype(float)
    run = e10 & (ramp > 0)
    from scipy.signal import lfilter
    out = {}
    for nm, z in (("Praw", Praw), ("Pmeas", Pmeas), ("I", I1), ("D", D1)):
        Sz = np.where(run, z * f / 256.0, 0.0)
        o = lfilter([c["ob"] / 1024.0], [1.0, -c["oa"] / 1024.0], Sz)
        y = (np.r_[0.0, o[:-1]] + o) / 32.0
        Tz = -(y * ramp / 32768.0) * c["fwd"] / 32768.0 / 8.0
        out[nm] = Tz[4::10]
    out["T_replay"] = T[:, 0] / 8.0
    return out


def regress_struct(W, comp, bands=BANDS_CP, min_run_s=2.0, anchor_s=None):
    """tap = a P_raw + b P_meas + c I + d D + c0 per band (hands-off, request 1, settled), on the tap's native
    instants (lag scanned), rail frames excluded.  Mapped onto the design's quantities with NO free constant:
        c_meas/c_raw = -b/a ; c_P = a * c_P,pred(band) ; c_I/c_P = (c/a) * 2.79 ; c_D = d * 0.566.
    anchor_s (None = the pre-2026-10-02 form, one intercept): each hands-off run is cut into ~anchor_s windows and the
    tap and every regressor are demeaned within each window (= one intercept per window), which re-anchors the
    replayed I's slow offset window by window (M1 §2.1's per-window I0).  R2 is then the within-window R2."""
    K = image_constants()
    base = W["eng"] & W["handsoff"] & (W["tse"] >= THR["settle_s"])
    tt = W["T_t"]
    keys = ("Praw", "Pmeas", "I", "D")
    best = None
    res_by = {}
    for L in range(-2, 7):
        j = np.searchsorted(W["t"], tt - L * DT, side="right") - 1
        ok = (j >= 0) & (j < len(W["t"]))
        jj = np.clip(j, 0, len(W["t"]) - 1)
        m_all = ok & base[jj] & np.isfinite(W["T"])
        m50 = m_all & (np.abs(W["T"]) < 0.95 * 2461)
        rail_frac = float(1.0 - m50.sum() / max(m_all.sum(), 1))
        rows = {}
        allX, ally = [], []
        for nm, lo, hi in bands:
            mb = m50 & (W["vego"][jj] >= lo) & (W["vego"][jj] < hi)
            rr = runs(mb, int(min_run_s * 50))
            if not rr or sum(r1 - r0 for r0, r1 in rr) < 100:
                rows[nm] = dict(ok=False, n=int(sum(r1 - r0 for r0, r1 in rr)))
                continue
            idx = np.concatenate([jj[r0:r1] for r0, r1 in rr])
            sel = np.concatenate([np.arange(r0, r1) for r0, r1 in rr])
            X = np.c_[[comp[k][idx] for k in keys]].T
            Y = W["T"][sel] / 8.0
            Gm = G_of_v(W["vego"][idx])
            if anchor_s:
                # window id per sample: each run cut into round(len / (anchor_s * 50)) (>= 1) equal windows
                gid = np.concatenate([_win_ids(r1 - r0, anchor_s * 50.0) + 1000000 * i for i, (r0, r1) in enumerate(rr)])
                Xi = _demean_by(X, gid)
                Yf = _demean_by(Y[:, None], gid)[:, 0]
            else:
                Xi = np.c_[X, np.ones(len(Y))]
                Yf = Y
            b, r2, se = _ols(Xi, Yf)
            a_, b_, c_, d_ = b[:4]
            pred = float(Gm.mean() * K["cP_per_G"])
            rows[nm] = dict(ok=True, n=len(Y), s=len(Y) / 50.0, a=a_, b=b_, c=c_, d=d_, r2=r2, se=se[:4].tolist(),
                            ratio=-b_ / a_ if abs(a_) > 1e-9 else np.nan, cP=a_ * pred, cP_pred=pred,
                            cIcP=(c_ / a_) * K["cIcP"](40) if abs(a_) > 1e-9 else np.nan, cD=d_ * K["cD"],
                            se_ratio=(abs(b_ / a_) * math.sqrt((se[0] / a_) ** 2 + (se[1] / b_) ** 2)
                                      if abs(a_) > 1e-9 and abs(b_) > 1e-9 else np.nan),
                            G_mean=float(Gm.mean()), r2_replay=r2_of(Y, comp["T_replay"][idx]))
            allX.append(Xi)
            ally.append(Yf)
        if ally:
            b, r2, se = _ols(np.vstack(allX), np.concatenate(ally))
            pooled = dict(n=int(sum(len(y) for y in ally)), a=b[0], b=b[1], c=b[2], d=b[3], r2=r2,
                          ratio=-b[1] / b[0] if abs(b[0]) > 1e-9 else np.nan, cD=b[3] * K["cD"],
                          cIcP=(b[2] / b[0]) * K["cIcP"](40) if abs(b[0]) > 1e-9 else np.nan,
                          c_raw=b[0], c_meas=-b[1], se_ratio=_ratio_se(np.array([b[0], -b[1]]), se[:2]))
        else:
            pooled = dict(n=0)
        res_by[L] = dict(rows=rows, pooled=pooled, rail_frac=rail_frac)
        sc = pooled.get("r2", -np.inf) if pooled.get("n") else -np.inf
        if best is None or sc > best[0]:
            best = (sc, L)
    L = best[1]
    res = res_by[L]
    res["lag_frames"] = L
    res["kind"] = "structural"
    res["lag_r2"] = {k: (v["pooled"].get("r2") if v["pooled"].get("n") else None) for k, v in res_by.items()}
    return res


def _win_ids(n, w):
    """window index 0..k-1 for n consecutive samples cut into k = max(1, round(n / w)) equal windows."""
    k = max(1, int(round(n / w)))
    return np.minimum((np.arange(n) * k) // max(n, 1), k - 1)


def _demean_by(X, gid):
    """X minus its mean within each group (fixed effects); X (n, p), gid (n,) int."""
    X = np.asarray(X, float)
    u, inv = np.unique(gid, return_inverse=True)
    cnt = np.bincount(inv, minlength=len(u)).astype(float)
    M = np.zeros((len(u), X.shape[1]))
    for j in range(X.shape[1]):
        M[:, j] = np.bincount(inv, weights=X[:, j], minlength=len(u)) / cnt
    return X - M[inv]


def r2_of(y, yh):
    y = np.asarray(y, float)
    yh = np.asarray(yh, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else np.nan


def _replay_v295(th, cmd, tq, x, vws, eng):
    """_replay_v295_source's output, word for word, from drive_read_fastlane.v295_lane, cached like _replay_cand."""
    if _fast_lane_drift():
        return _replay_v295_source(th, cmd, tq, x, vws, eng)
    T = _cached(*_v295_job(th, cmd, tq, x, vws, np.asarray(eng, bool)))[0]
    return T.astype(float)


def _replay_v295_source(th, cmd, tq, x, vws, eng):
    """lane_mirror_v295.lane_tick (byte-exact V295) on the same wire inputs and the same slot-4 timing convention."""
    import lane_mirror_v295 as LM
    cal = LM.load_cal()
    ed = LM.Edits()
    st = LM.LaneState()
    n = len(th)
    T = np.zeros(n)
    ramp = 0
    last_eng = -10 ** 9
    for k in range(n):
        e = bool(eng[k])
        if e:
            last_eng = k
        elif ramp == 0 and k - last_eng > 300:
            continue
        kp = max(k - 1, 0)
        for s in range(10):
            ramp = min(0x8000, ramp + 33) if e else max(0, ramp - 16)
            kk = kp if s <= 4 else k
            Tk = LM.lane_tick(st, cal, ed, rate=int(x[kk]), angle=int(th[kk]), cmd69ae=int(cmd[k]), tq=int(tq[k]),
                              speed=int(vws[k]), ramp=ramp, act6806=1 if e else 0, req6805=1 if e else 0, pol=-1)
            if s == 4:
                T[k] = Tk
    return T


def _score_replay(W, T100, n):
    tt = W["T_t"]
    base = (W["eng"] & W["handsoff"] & (W["tse"] >= THR["settle_s"]))[:n]
    best = None
    for L in range(-2, 9):
        j = np.searchsorted(W["t"][:n], tt - L * DT, side="right") - 1
        ok = (j >= 0) & (j < n)
        jj = np.clip(j, 0, n - 1)
        m = ok & base[jj] & np.isfinite(W["T"])
        if m.sum() < 100:
            continue
        y = W["T"][m] / 8.0
        yh = np.sign(T100[jj[m]]) * (np.abs(T100[jj[m]]).astype(np.int64) >> 3)
        ss = np.sum((y - y.mean()) ** 2)
        r2 = 1 - np.sum((y - yh) ** 2) / ss if ss > 0 else np.nan
        gain = float(np.dot(yh, y) / max(np.dot(yh, yh), 1e-9))
        row = dict(lag=L, r2=float(r2), gain=gain, n=int(m.sum()),
                   rms_resid=float(np.sqrt(np.mean((y - yh) ** 2))), rms_tap=float(np.sqrt(np.mean(y ** 2))))
        if best is None or row["r2"] > best["r2"]:
            best = row
    return best or dict(n=0)


_ST = None


def load_score_time():
    """panel2/score_time.py, imported unchanged (the common time scorer's CandLane = the H1-validated lane)."""
    global _ST
    if _ST is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("p2_st_driveread", AL / "panel2" / "score_time.py")
        ST = importlib.util.module_from_spec(spec)
        sys.modules["p2_st_driveread"] = ST
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(ST)
        ST.OUT = SCR / "st"
        _ST = ST
    return _ST


def replay_cands(ST):
    """the image set the replay chooses between.  C3B-P = C3-rev2-P = the design's primary byte-for-byte (rev2 §1);
    its flight cave differs from the scored cave only on the invalid-rate path (op-skip), which valid wire never
    exercises (rev2 §1.2, EVIDENCE per the page)."""
    import rb_table as RT
    import json as _j
    gj = _j.loads((AL / "panel2" / "G-d-operand-and-margins" / "g_impls_frozen.json").read_text())
    GP48 = tuple(tuple(r) for r in gj["G-P48"]["rows"])
    flat = ((0, 256, 0), (0xFFFF, 256, 0))
    C = {}
    C["C3B-P"] = ST.Cand("C3B-P", "RBF", tuple(RT.GB_P), "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                         note="C3-rev2-P (V296 design)")
    C["C3-P56"] = ST.Cand("C3-P56", "C3", GP48, "fresh", 48, ki=56, icl=8192, arb=ST.ARB_A3, note="C3-P (Ki 56, G-P48)")
    C["SKIP"] = ST.Cand("SKIP", "X", flat, "fresh", 48, ki=40, icl=8192, note="in-place set, cave skipped: G = 256")
    C["C3B-P-kd34"] = ST.Cand("C3B-P-kd34", "X", tuple(RT.GB_P), "fresh", 34, ki=40, icl=8192, arb=ST.ARB_A3,
                              sgn_thr=300, note="D not re-sized (P2's Kd 34)")
    C["C3B-F"] = ST.Cand("C3B-F", "RBF", tuple(RT.GB_F), "held", 24, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                         note="C3-rev2-F")
    # V299 (DESIGN-V299-SYNTHESIS-rev3 section 1.3): C3B-P's lane with the V299 integral policy (freeze 1229, no
    # opposing clause, asymmetric bound, two-level cap).  FAST LANE ONLY (drive_read_fastlane.v299_cand); not in the
    # default replay() set, so every pre-V299 read is unchanged.  Rule identity: components(W, ref="V299", ...).
    C["V299"] = FL.v299_cand(ST, C["C3B-P"])
    return C


# =====================================================================================================================
# 2.  STOP BANDS
# =====================================================================================================================
def a2_r7(W):
    """after every request DROP (eng 1 -> 0): A2 LIVE iff |tap| < 20 LSB within 0.15 s; R7 iff the tap still pushes
    toward 0 deg (sign(T) == sign(theta): u = -T) with |tap| >= 20 LSB for > 0.2 s."""
    drops = [i for i in range(1, len(W["t"])) if W["req"][i - 1] and not W["req"][i] and W["have"][i]]
    rows = []
    for i in drops:
        t0 = W["t"][i]
        m = (W["T_t"] >= t0) & (W["T_t"] < t0 + 1.0)
        if m.sum() < 3:
            continue
        tt, T = W["T_t"][m] - t0, W["T"][m] / 8.0
        th = _zoh(W["t"], W["theta"], W["T_t"][m])
        quiet = np.abs(T) < THR["a2_tap"]
        # first time after which it stays quiet
        idx = np.flatnonzero(~quiet)
        t_quiet = float(tt[idx[-1] + 1]) if len(idx) and idx[-1] + 1 < len(tt) else (0.0 if not len(idx) else 9.9)
        push0 = (~quiet) & (np.sign(T) == np.sign(th)) & (np.abs(th) > 0.05)
        t_push = float(np.sum(push0) * 0.02)
        imp = float(np.sum(np.abs(T[push0])) * 0.02)               # LSB*s of push toward 0 in the first second
        rows.append(dict(t=float(t0), t_quiet=t_quiet, pass_a2=t_quiet <= THR["a2_t"], t_push0=t_push, imp0=imp,
                         r7=t_push > THR["r7_t"], tap0=float(T[0]), theta=float(th[0])))
    n = len(rows)
    return dict(n=n, n_pass=sum(r["pass_a2"] for r in rows), live=(all(r["pass_a2"] for r in rows) if n else None),
                r7=any(r["r7"] for r in rows), rows=rows[:30])


def r2_rail(W):
    m = W["eng"] & W["handsoff"] & (np.abs(W["T100"]) >= THR["r2_tap"])
    ev = [(W["t"][a], (b - a) * DT, float(np.nanmax(np.abs(W["T100"][a:b]))), float(np.nanmedian(W["vego"][a:b])))
          for a, b in runs(m, int(THR["r2_t"] * FS) + 1)]
    return dict(fire=bool(ev), n=len(ev), events=ev[:10])


def r6_err(W):
    err = W["theta"] - W["theta_sp"]
    m = W["eng"] & W["handsoff"] & (W["vego"] > THR["r6_v"]) & (np.abs(err) > THR["r6_deg"])
    ev = [(W["t"][a], (b - a) * DT, float(np.max(np.abs(err[a:b])))) for a, b in runs(m, int(THR["r6_t"] * FS) + 1)]
    return dict(fire=bool(ev), n=len(ev), events=ev[:10])


def r8_health(W):
    e = W["eng"]
    st, b4 = W["status"][e], W["b4"][e]
    have_st, have_b4 = bool(np.isfinite(st).any()), bool(np.isfinite(b4).any())
    bad_st = int(np.sum(np.isfinite(st) & (st != 0)))
    bad_b4 = int(np.sum(np.isfinite(b4) & ((b4.astype(int, copy=False) & 7) != 7))) if have_b4 else 0
    return dict(fire=bool(bad_st or bad_b4), bad_status=bad_st, bad_b4=bad_b4, have_status=have_st, have_b4=have_b4,
                n=int(e.sum()))


def _halfcycles(x):
    """zero crossings -> list of (i_start, i_end, peak_abs) per half-cycle."""
    s = np.signbit(x)
    zc = np.flatnonzero(s[1:] != s[:-1]) + 1
    return [(a, b, float(np.max(np.abs(x[a:b])))) for a, b in zip(zc[:-1], zc[1:]) if b > a]


def r3_ring(W, chans=("theta", "err", "w18"), mask=None, floor_scale=1.0, narrow_min=None, use_cmd=True):
    """R3*: a 0.25-5.5 Hz oscillation that GROWS, or >= 4 cycles with zeta < 0.25.  Per sub-band (0.25-0.9 / 0.9-2.5 /
    2.5-5.5 Hz), zero-phase band-pass, then sequences of >= 8 consecutive half-cycles that are (a) above the channel's
    amplitude floor, (b) periodic (half-periods within +-25 % of their median), (c) NARROWBAND -- the band-passed ring
    carries >= 60 % of the span's 0.1-10 Hz energy (road and path content is broadband; a ring is not).  zeta from the
    per-cycle amplitude ratio r = a(i+2)/a(i): zeta < 0.25 <=> geometric-mean r > 0.197; GROWING <=> r > 1.05."""
    floors = {k: floor_scale * v for k, v in
              dict(theta=THR["r3_amp_theta"], err=THR["r3_amp_err"], w18=THR["r3_amp_rate"]).items()}
    nmin = THR["r3_narrow"] if narrow_min is None else narrow_min
    sig = dict(theta=W["theta"], err=W["theta"] - W["theta_sp"], w18=W["w18"])
    # the COMMANDED counterpart of each channel: a ring the fork itself commands (road S-bends, an outer-loop cycle)
    # shows in theta_sp too; the inner loop's ring does not.  None for err (it IS the inner loop's residual).
    cmdsig = dict(theta=np.nan_to_num(W["theta_sp"]), w18=np.gradient(np.nan_to_num(W["theta_sp"])) * FS,
                  err=np.nan_to_num(W["theta_sp"]))
    # use_cmd=False on routes where 0xE4 is NOT an angle setpoint (every reference route: it is a torque/rate command
    # there, so "theta_sp" = -raw/10 is meaningless and would mask real rings as "commanded")
    have_cmd = use_cmd and (bool(np.nanstd(W["theta_sp"][W["eng"]]) > 0) if W["eng"].any() else False)
    base = W["eng"] if mask is None else (W["eng"] & mask)
    rmin = math.exp(-2 * math.pi * THR["r3_zeta"] / math.sqrt(1 - THR["r3_zeta"] ** 2))
    subs = ((0.25, 0.9), (0.9, 2.5), (2.5, 5.5))
    ev = []
    for ch in chans:
        x0 = np.nan_to_num(sig[ch])
        for a0, b0 in runs(base, 600):
            seg = x0[a0:b0]
            wide = signal.sosfiltfilt(signal.butter(2, [0.1, 10.0], "bandpass", fs=FS, output="sos"), seg - seg.mean())
            for lo, hi in subs:
                xb = signal.sosfiltfilt(signal.butter(2, [lo, hi], "bandpass", fs=FS, output="sos"), seg - seg.mean())
                hc = _halfcycles(xb)
                i = 0
                while i < len(hc):
                    j = i
                    while j < len(hc) and hc[j][2] >= floors[ch]:
                        j += 1
                    if j - i >= 2 * THR["r3_cycles"]:
                        seq = hc[i:j]
                        hp = np.array([b - a for a, b, _ in seq], float)
                        per_ok = np.abs(hp / np.median(hp) - 1.0) <= THR["r3_period_tol"]
                        # longest periodic sub-run
                        best = max(runs(per_ok, 1), key=lambda r: r[1] - r[0], default=(0, 0))
                        if best[1] - best[0] >= 2 * THR["r3_cycles"]:
                            sq = seq[best[0]:best[1]]
                            s0, s1 = sq[0][0], sq[-1][1]
                            narrow = float(np.sum(xb[s0:s1] ** 2) / max(np.sum(wide[s0:s1] ** 2), 1e-12))
                            amps = np.array([q[2] for q in sq])
                            r = amps[2:] / amps[:-2]
                            gm = float(np.exp(np.mean(np.log(np.maximum(r, 1e-6)))))
                            grow = gm > 1.05
                            if narrow >= nmin and (gm > rmin or grow):
                                f0 = FS / (2 * np.median(hp[best[0]:best[1]]))
                                # AMPLIFICATION over the command in the same band and span: a closed-loop ring
                                # (resonant peaking, a limit cycle, an instability) moves the wheel MORE than the
                                # setpoint asks; tracking lag and road geometry move it less or equal.
                                commanded, coh, amp_ratio = None, np.nan, np.inf
                                if have_cmd and ch != "_":
                                    cs = cmdsig[ch][a0:b0]
                                    cb = signal.sosfiltfilt(signal.butter(2, [lo, hi], "bandpass", fs=FS,
                                                                         output="sos"), cs - cs.mean())
                                    u, v_ = xb[s0:s1], cb[s0:s1]
                                    den = math.sqrt(float(np.sum(u * u) * np.sum(v_ * v_)))
                                    coh = float(np.sum(u * v_) / den) if den > 0 else 0.0
                                    amp_ratio = math.sqrt(float(np.sum(u * u)) / max(float(np.sum(v_ * v_)), 1e-12))
                                    commanded = bool(amp_ratio < (THR["r3_amp_ratio_err"] if ch == "err"
                                                                  else THR["r3_amp_ratio"]))
                                ev.append(dict(chan=ch, band="%.2f-%.1f" % (lo, hi), t=float(W["t"][a0 + s0]),
                                               dur=(s1 - s0) / FS, f0=float(f0), cycles=(best[1] - best[0]) / 2,
                                               amp_max=float(amps.max()), r_gm=gm, growing=bool(grow),
                                               narrow=narrow, v=float(np.nanmedian(W["vego"][a0 + s0:a0 + s1])),
                                               commanded=commanded, coh_cmd=coh, amp_ratio=amp_ratio))
                    i = max(j, i + 1)
    lf = [e for e in ev if e["f0"] >= THR["r3_flo"]]
    # FIRES on a qualifying ring (periodic, narrowband, >= 4 cycles, zeta < 0.25 or growing) that the wheel carries
    # with AMPLIFICATION over the setpoint in the same band and span (theta/theta_sp or w18/(d theta_sp/dt) >= 1.25;
    # err/theta_sp >= 1.25), or on ANY qualifying ring where no setpoint exists (the reference routes).  A ring the
    # setpoint carries at <= that ratio is REVIEW (road geometry, the fork's own path), reported, not R3* by itself.
    fire_ev = [e for e in lf if e.get("commanded") is not True]
    review = [e for e in lf if e not in fire_ev]
    return dict(fire=bool(fire_ev), n=len(fire_ev), n_review=len(review),
                events=sorted(fire_ev, key=lambda e: -e["amp_max"])[:12],
                review=sorted(review, key=lambda e: -e["amp_max"])[:6])


def line_census(W, mask=None, nperseg=256, lo=5.0, hi=30.0, chan="w18"):
    """Welch on the 0x18F rate (deg/s; chan 'w18') or the 0x18F driver-torque bar (chan 'bar') over the mask (default:
    ALL engaged frames -- the design's R4 reads 'the 0x18F rate or the torque bar'); lines = local maxima of the
    shoulder-fitted excess (+-2 Hz running median of log-PSD, the record's C88.excess_db) >= r4_excess_db in 5-30 Hz."""
    m = W["eng"] if mask is None else mask
    segs = [np.nan_to_num(W[chan][a:b]) for a, b in runs(m, nperseg)]
    P = []
    win = np.hanning(nperseg)
    U = (win ** 2).sum() * FS
    for x in segs:
        for s in range(0, len(x) - nperseg + 1, nperseg // 2):
            q = x[s:s + nperseg]
            q = q - q.mean()
            X = np.fft.rfft(q * win)
            p = np.abs(X) ** 2 / U
            p[1:-1] *= 2
            P.append(p)
    f = np.fft.rfftfreq(nperseg, 1 / FS)
    if len(P) < 8:
        return dict(n_seg=len(P), f=f, Pm=None, lines=[])
    Pm = np.mean(P, 0)
    L = 10 * np.log10(np.maximum(Pm, 1e-30))
    k = int(round(2.0 / (f[1] - f[0])))
    base = np.array([np.median(L[max(0, i - k):i + k + 1]) for i in range(len(L))])
    ex = L - base
    lines = []
    for i in range(1, len(f) - 1):
        if lo <= f[i] <= hi and ex[i] >= THR["r4_excess_db"] and ex[i] >= ex[i - 1] and ex[i] >= ex[i + 1]:
            sl = (f >= f[i] - 1.0) & (f <= f[i] + 1.0)
            lines.append(dict(f=float(f[i]), excess_db=float(ex[i]),
                              amp=float(np.sqrt(2.0 * Pm[sl].sum() * (f[1] - f[0])))))
    return dict(n_seg=len(P), f=f, Pm=Pm, ex=ex, lines=lines)


def r4_new_lines(cen, refs):
    """R4: a line present here and ABSENT on every reference (< 3 dB within +-0.75 Hz) and >= 1.5x every reference's
    +-1 Hz amplitude."""
    new = []
    for ln in cen.get("lines", []):
        absent, ampok, notes = True, True, []
        for nm, rc in refs.items():
            if rc.get("Pm") is None:
                continue
            f, ex, Pm = rc["f"], rc["ex"], rc["Pm"]
            sl = (f >= ln["f"] - 0.75) & (f <= ln["f"] + 0.75)
            rx = float(np.max(ex[sl])) if sl.any() else -99
            sl2 = (f >= ln["f"] - 1.0) & (f <= ln["f"] + 1.0)
            ra = float(np.sqrt(2.0 * Pm[sl2].sum() * (f[1] - f[0])))
            notes.append("%s %.1f dB %.3f" % (nm, rx, ra))
            if rx >= THR["r4_ref_db"]:
                absent = False
            if ln["amp"] < THR["r4_amp_ratio"] * ra:
                ampok = False
        if absent and ampok:
            new.append(dict(ln, refs=notes))
    return dict(fire=bool(new), new=new)


def ring_presence_f7(W, with_presence=True):
    """R5 + the goal: the record's own instruments UNCHANGED -- v293_flight_read.presence (18-22 Hz bar prominence >= 8
    AND amplitude >= 40, 2 s windows) and .strongturn (F7: fixed 103-wire 2-8 Hz episodes at |angle| >= 30, fdom >= 6).
    The angle loop has no demand index; idx is set to 255 so strongturn's rip-window idx >= 40 clause is inert."""
    FR = _fr()
    g = dict(bar=W["bar"], wire=W["wire"], eng=W["eng"], vego=W["vego"], t=W["t"])
    out = {}
    if with_presence:
        # FR.presence's predicate and aggregates, EXACT, via drive_read_fastpresence (the prominence median taken on
        # the 15-26 Hz rows locate reads; library-checked), cached per (bar, wire, masks) under SCR/presence
        import drive_read_fastpresence as FP
        m_ho, m_all = W["eng"] & W["handsoff"], W["eng"]
        fdrift = FP.drift(FR)
        key = FL.key_of(np.asarray(W["bar"], float), np.asarray(W["wire"], float), np.asarray(m_ho, bool),
                        np.asarray(m_all, bool), FP.VERSION, float(FR.FS), float(FR.CPD))
        pp = SCR / "presence" / ("%s.json" % key[:32])
        got = None
        if fdrift:                               # a mirrored library function changed: the library's own (slow) call
            _RT["fallback"].append("fast presence OFF (library changed: %s)" % ",".join(fdrift))
            with contextlib.redirect_stdout(io.StringIO()):
                got = dict(presence=FR.presence(g, m_ho, label="hands-off"),
                           presence_all=FR.presence(g, m_all, label="engaged"))
        elif pp.exists():
            try:
                got = json.loads(pp.read_text())
            except (OSError, ValueError):
                got = None
        if got is None:
            Pr = FP.Presence(FR)
            got = dict(presence=Pr(g, m_ho, label="hands-off"), presence_all=Pr(g, m_all, label="engaged"))
            try:
                pp.parent.mkdir(parents=True, exist_ok=True)
                pp.write_text(json.dumps(got))
            except OSError:
                pass
        out["presence"], out["presence_all"] = got["presence"], got["presence_all"]
    r = types.SimpleNamespace(eng=W["eng"], ang=W["theta"], wire=W["wire"], vego=W["vego"], bar=W["bar"],
                              T=W["T100"] * 8.0, idx=np.full(len(W["t"]), 255.0))
    with contextlib.redirect_stdout(io.StringIO()):
        out["strongturn"] = FR.strongturn(r)
    sp = None
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            g2 = dict(g, idx=np.full(len(W["t"]), 255.0))
            sp = FR.spectra(g2)
        except Exception as e:
            sp = dict(err=str(e)[:100])
    out["spectra"] = sp
    out["eng_over_dis"] = FR.eng_over_dis(sp) if isinstance(sp, dict) and "err" not in sp else None
    return out


# =====================================================================================================================
# 3.  THE GOAL CRITERIA
# =====================================================================================================================
def _goal_runs(W, lo, hi, min_s=15.0):
    m = W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi)
    ok = np.isfinite(W["pressed"])
    if ok.any():
        m = m & ~(np.nan_to_num(W["pressed"]) > 0.5)
    else:
        m = m & W["handsoff"]
    return runs(m, int(min_s * FS))


def tracking_and_hold(W, bands=BANDS_GOAL):
    """score_time.metrics('rr') verbatim in form: 0.5 Hz zero-phase LPF of theta and theta_sp, first 4 s of each run
    dropped; tracking = OLS slope (with intercept) pooled over the band's runs; turn-hold windows: |sp_LPF| >= 3 deg,
    |d sp_LPF/dt| <= max(1, 0.05|sp|) deg/s, >= 1.5 s -> mean(theta)/mean(sp)."""
    sos = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")
    out = {}
    for nm, lo, hi in bands:
        X, Y, holds, secs = [], [], [], 0.0
        for a, b in _goal_runs(W, lo, hi):
            x = signal.sosfiltfilt(sos, W["theta_sp"][a:b])
            y = signal.sosfiltfilt(sos, W["theta"][a:b])
            X.append(x[400:]); Y.append(y[400:])
            secs += (b - a - 400) / FS
            d = np.gradient(x) * FS
            msk = (np.abs(x) >= 3.0) & (np.abs(d) <= np.maximum(1.0, 0.05 * np.abs(x))) & (np.arange(b - a) >= 400)
            for p, q in runs(msk, 150):
                holds.append(float(y[p:q].mean() / x[p:q].mean()))
        if not X:
            out[nm] = dict(secs=0.0)
            continue
        # score_time.r71b_scores verbatim: the band's runs CONCATENATED (no per-run demeaning), one intercept
        Xa, Ya = np.concatenate(X), np.concatenate(Y)
        slope = float(np.linalg.lstsq(np.vstack([Xa, np.ones_like(Xa)]).T, Ya, rcond=None)[0][0])
        out[nm] = dict(secs=secs, track=slope, n_hold=len(holds),
                       hold_min=(min(holds) if holds else np.nan), hold_med=(float(np.median(holds)) if holds else np.nan),
                       track_pass=(THR["track_lo"] <= slope <= THR["track_hi"]),
                       hold_pass=(min(holds) >= THR["turnhold"]) if holds else None,
                       scored=secs >= THR["goal_min_s"])
    return out


def dwell_jump(W, bands=BANDS_CP + (("<5", 0.0, 5.0),)):
    """nl_sim.dwell_jump (the harness's own definition) on the 100 Hz wire: om = w18, th = theta, ref = theta_sp."""
    import nl_sim as NS
    out = {}
    for nm, lo, hi in bands:
        m = W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi)
        n_ev, secs, jmax = 0, 0.0, 0.0
        for a, b in runs(m, 200):
            ev, jm = NS.dwell_jump(W["w18"][a:b, None], W["theta"][a:b, None], W["theta_sp"][a:b, None])
            n_ev += int(ev[0]); secs += (b - a) / FS; jmax = max(jmax, float(jm[0]))
        out[nm] = dict(secs=secs, n=n_ev, per_min=(60.0 * n_ev / secs if secs > 0 else np.nan), jmax=jmax)
    return out


def symptom_dwells(W):
    """v293_symptom_instruments.dwells (the smoothed record detector) -- runs identically on the references."""
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_symptom_instruments as SI
    return SI.dwells(np.abs(W["wire"]) / 8.0, W["theta"], W["vego"], W["eng"])


# =====================================================================================================================
# 4.  FRICTION / BREAKAWAY per band (the sizing data for the next step; NOT a verdict)
# =====================================================================================================================
def friction(W, bands=BANDS_FRIC):
    """Two reads per band, hands-off engaged, on the tap (T counts; the motor torque on the wheel is u = -T):
       COULOMB  -T = k0 + k*theta + b*w + Fc*sign(w) on SLIDING frames (|w18| >= 2 deg/s, 0.1-s LP), OLS -> Fc.
       BREAKAWAY each stick (|w| 0.1-s mean < 0.25 deg/s for >= 0.2 s) that ends in a slip (|w| > 1 deg/s within
                 0.3 s): |(-T) - k0 - k*theta| at the first slipping frame, from the band's own sliding fit -> Fs.
    BELIEF: the tap is the LANE torque only; Honda's base assist and the hand are excluded by the hands-off mask."""
    T = -W["T100"] * 8.0
    w = W["w18"]
    ker = np.ones(10) / 10.0
    out = {}
    for nm, lo, hi in bands:
        m = W["eng"] & W["handsoff"] & (W["vego"] >= lo) & (W["vego"] < hi) & np.isfinite(T)
        if m.sum() < 500:
            out[nm] = dict(secs=float(m.sum() / FS), ok=False)
            continue
        wl = np.convolve(np.nan_to_num(w), ker, "same")
        sl = m & (np.abs(wl) >= 2.0)
        if sl.sum() < 200:
            out[nm] = dict(secs=float(m.sum() / FS), ok=False, n_slide=int(sl.sum()))
            continue
        X = np.c_[np.ones(sl.sum()), W["theta"][sl], wl[sl], np.sign(wl[sl])]
        b, r2, se = _ols(X, T[sl])
        k0, k, bb, Fc = b
        bk = []
        for a, c in runs(m & (np.abs(wl) < 0.25), 20):
            e = min(c + 30, len(w) - 1)
            nxt = np.flatnonzero(np.abs(w[c:e]) > 1.0)
            if len(nxt):
                i = c + int(nxt[0])
                bk.append(abs(T[i] - k0 - k * W["theta"][i]))
        out[nm] = dict(secs=float(m.sum() / FS), ok=True, Fc=float(Fc), se_Fc=float(se[3]), k=float(k), b=float(bb),
                       r2=float(r2), n_slide=int(sl.sum()), n_break=len(bk),
                       Fs_p50=float(np.median(bk)) if bk else np.nan, Fs_p90=float(np.percentile(bk, 90)) if bk else np.nan)
    return out


# =====================================================================================================================
# THE LIGHT-HOLD EPISODES (the opposing-hand freeze, N1) -- reported with the I component and the release overshoot
# =====================================================================================================================
def light_holds(W, R, comp=None):
    """the I component during light holds.  With the structural components (comp) it is EXACT up to the fit:
    I_comp = tap - (a P_raw + b P_meas + d D) (pooled a, b, d); without them it is the design's form
    tap - c_P e - c_D w (C3 §8).  Both 1 Hz low-passed; dI over the hold in T counts (x8)."""
    rows = {k: v for k, v in R["rows"].items() if v.get("ok")}
    if not rows:
        return dict(n=0)
    Pp = R["pooled"]
    if comp is not None and R.get("kind") == "structural":
        Ic = W["T100"] - (Pp["a"] * comp["Praw"] + Pp["b"] * comp["Pmeas"] + Pp["d"] * comp["D"])
    else:
        names = ("8-10", "10-12.5", "15-22", ">22")
        if all(k in rows for k in names):
            cP = np.interp(W["vego"], [9, 11.25, 18.5, 26], [rows[k]["cP"] for k in names])
        else:
            cP = np.full(len(W["t"]), np.nanmedian([v["cP"] for v in rows.values()]))
        Ic = W["T100"] - cP * W["ew"] - Pp.get("cD", 0.0) * W["w18"]
    Ic = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.nan_to_num(Ic))
    bar = np.abs(W["bar"])
    m = W["eng"] & (bar >= 300) & (bar < 512)
    out = []
    for a, b in runs(m, 100):
        dI8 = float(abs(Ic[b - 1] - Ic[a]) * 8.0)
        sp = W["theta_sp"][a]
        err = W["theta"][a:b] - W["theta_sp"][a:b]
        kind = "outward" if np.median(err) * np.sign(sp) > 0 else "inward"
        e2 = min(b + 300, len(W["t"]))
        # overshoot PAST the setpoint after release, away from where the hand held the wheel:
        #   inward hold (wheel held toward centre) -> past theta_sp outward ; outward hold -> past it toward centre
        d_ = (W["theta"][b:e2] - W["theta_sp"][b:e2]) * np.sign(sp)
        ovs = float(np.max(np.r_[0.0, d_ if kind == "inward" else -d_]))
        v = float(np.median(W["vego"][a:b]))
        bar_ = REL_S4["inward"] if kind == "inward" else (REL_S4["outward_lo"] if v < 12.5 else REL_S4["outward_hi"])
        out.append(dict(t=float(W["t"][a]), dur=(b - a) / FS, kind=kind, v=v, dI_T=dI8, flat=dI8 <= THR["i_flat_T"],
                        release_ovs=ovs, ovs_bar=bar_ + THR["rel_over_add"], ovs_pass=ovs <= bar_ + THR["rel_over_add"]))
    return dict(n=len(out), rows=out[:20])


# =====================================================================================================================
# REFERENCES (re-derived at run time, cached)
# =====================================================================================================================
CHANS = ("w18", "bar")


def census2(W, mask=None):
    return {ch: line_census(W, mask=mask, chan=ch) for ch in CHANS}


def r4_2(cen2, refs2):
    """R4 on both channels; refs2 = {ref tag: {chan: census}}."""
    out = dict(fire=False, new=[])
    for ch in CHANS:
        r = r4_new_lines(cen2[ch], {k: v[ch] for k, v in refs2.items() if ch in v})
        for n_ in r["new"]:
            out["new"].append(dict(n_, chan=ch))
        out["fire"] = out["fire"] or r["fire"]
    return out


def ref_summary(tag, with_presence=True, force=False):
    p = SCR / "refs" / ("%s.json" % tag)
    pz = SCR / "refs" / ("%s_census.npz" % tag)
    if p.exists() and pz.exists() and not force:
        J = json.loads(p.read_text())
        if with_presence and J.get("presence") is None:
            return ref_summary(tag, with_presence=True, force=True)
        Z = np.load(pz)
        J["census"] = {ch: dict(f=Z["f_" + ch], Pm=Z["Pm_" + ch], ex=Z["ex_" + ch], lines=J["census_lines"][ch])
                       for ch in CHANS}
        return J
    W = load_route(tag, with_extras=False)
    cen = census2(W)
    J = dict(tag=tag, build=REF_BUILD.get(tag, "?"), secs_eng=float(W["eng"].sum() / FS),
             dwells=symptom_dwells(W), census_lines={ch: cen[ch]["lines"] for ch in CHANS})
    rp = ring_presence_f7(W, with_presence=with_presence)
    J["presence"] = rp.get("presence")
    J["presence_all"] = rp.get("presence_all")
    J["strongturn"] = {k: v for k, v in rp["strongturn"].items() if not isinstance(v, list)}
    J["eng_over_dis"] = rp.get("eng_over_dis")
    J["r3"] = r3_ring(W, chans=("theta", "w18"), use_cmd=False)
    J["friction"] = friction(W)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(J, indent=1, default=_js))
    np.savez(pz, **{("%s_%s" % (k, ch)): cen[ch][k] for ch in CHANS for k in ("f", "Pm", "ex")})
    J["census"] = cen
    return J


def _js(x):
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return str(x)


# =====================================================================================================================
# THE WHOLE READ
# =====================================================================================================================
def read(W, refs=None, with_replay=True, with_presence=True):
    """the decision-bearing regression is the STRUCTURAL one (regress_struct on components, with the 2026-10-02 input
    corrections and the per-window I anchor -- docstring §1), and R1 additionally needs the 2-5 Hz literal fit to agree;
    the pre-correction structural form and the design's 0.3-3 Hz literal form are computed beside it and printed.  Why: on the synthetic positive control the literal form
    reads c_D 0.15-0.49 against the design's 0.566 (closed-loop collinearity of e and w plus the frozen-I
    misspecification) and fails its own pre-registered c_D clause on the correct build, while the structural form
    recovers a, b, c, d = 0.93-0.99 (angle_loop_controls.py, section A).  Both use the SAME pre-registered thresholds."""
    S = dict(meta=W["meta"])
    S["exposure"] = exposure(W)
    S["attrib"] = attribution(W)
    S["a2"] = a2_r7(W)
    # the pre-2026-10-02 structural form (direction-0 ramp, word on the 0x18F frame, one intercept): REPORTED ONLY
    comp0 = components(W)
    S["reg_struct_v0"] = regress_struct(W, comp0)
    # the decision-bearing structural form: the arm that ran, the word's lead, the I re-anchored per window
    si = struct_inputs(W)
    # the rule whose I the structural regression carries: V299's on an A16B wire (the V299 image), else C3B-P = V298
    ref = "V299" if (S["attrib"].get("image_letter") == "A16B" and "V299" in replay_cands(load_score_time())) else "C3B-P"
    if ref != "C3B-P":
        si["ref"] = ref
    try:
        comp = components(W, ref=ref, ramp_steps=tuple(si["ramp"]), q_lead=si["q_lead"])
    except NotImplementedError:
        si.update(ramp=[33, 16], note="fast lane off: the direction-0 ramp was used")
        _RT["fallback"].append("structural replay on the direction-0 ramp (fast lane off)")
        comp = components(W, q_lead=si["q_lead"])
    Rs = regress_struct(W, comp, anchor_s=si["anchor_s"])
    S["reg_struct"] = Rs
    S["struct_inputs"] = si
    S["replay"] = replay(W) if with_replay else None
    S["replay_corrected"] = _score_replay(W, np.round(comp["T_replay"] * 8.0), len(W["t"]))
    S["reg_r1b"] = regress(W, bp=(THR["r1b_lo"], THR["r1b_hi"]))
    S["verdict"] = verdict(Rs, W, S["a2"], S["replay"], r1b=S["reg_r1b"])
    R = regress(W)
    S["reg"] = R
    S["verdict_literal"] = verdict(R, W, S["a2"])
    S["r2"] = r2_rail(W)
    S["r3"] = r3_ring(W)
    S["r6"] = r6_err(W)
    S["r8"] = r8_health(W)
    cen = census2(W)
    S["census"] = {ch: dict(n_seg=cen[ch]["n_seg"], lines=cen[ch]["lines"]) for ch in CHANS}
    S["r4"] = r4_2(cen, {k: v["census"] for k, v in (refs or {}).items()})
    S["rp"] = ring_presence_f7(W, with_presence=with_presence)
    S["goal"] = tracking_and_hold(W)
    S["dj"] = dwell_jump(W)
    S["dwells"] = symptom_dwells(W)
    S["friction"] = friction(W)
    S["light"] = light_holds(W, Rs, comp)
    S["refs"] = {k: {kk: vv for kk, vv in v.items() if kk != "census"} for k, v in (refs or {}).items()}
    # ---- 6. the V299 / drive-2 blocks (drive_read_v299.py): additions only; nothing above reads them
    #      (DRIVE_READ_NO_V299=1 skips them: the pre-V299 read, for timing and identity checks)
    if os.environ.get("DRIVE_READ_NO_V299"):
        return S
    try:
        import drive_read_v299 as V2
        S["v299"] = V2.read(sys.modules[__name__], W, S, refs)
    except Exception as e:                          # a failure here must never hide sections 0-5 -- printed loudly
        import traceback
        S["v299_error"] = "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-1500:])
    return S


def exposure(W):
    out = {}
    for nm, lo, hi in BANDS_CP + (("<5", 0.0, 5.0),):
        m = W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi)
        out[nm] = dict(eng_s=float(m.sum() / FS), handsoff_s=float((m & W["handsoff"]).sum() / FS))
    out["engaged_s"] = float(W["eng"].sum() / FS)
    out["n_episodes"] = int(W["eid"].max())
    return out


def attribution(W):
    m = W["meta"]
    eps = [f for f in m.get("carfw", []) if "eps" in str(f.get("ecu", "")).lower()]
    fw = [f.get("fw", "").rstrip("\x00 ") for f in eps]
    params = m.get("params", {})
    keys = ("AccordEpsAngleLoop", "SteerDelay", "UseAutoSteerDelay", "AlwaysOnLateral", "SteerRatio",
            "AccordVariableSteerRatio", "ForceTorqueController", "SteerControlType", "GitCommit", "GitBranch",
            "AccordAngleBarFromEps", "AccordAngleMaxRate", "AccordAngleClipScale")        # the last three: V299 fork
    # the FORK's angle interface on the wire (SPEC C3): while lateral is allowed but NOT requested the fork sends
    # the measured angle verbatim (raw == the 0x14A field).  A torque fork sends ~0 there instead.
    ina = (~W["req"]) & W["have"] & np.isfinite(W["raw"])
    nz = ina & (np.abs(W["f14a"]) >= 20)                       # >= 2 deg off centre, so 0 cannot pass by accident
    match = float(np.mean(np.abs(W["raw"][nz] - W["f14a"][nz]) <= 2)) if nz.sum() >= 50 else np.nan
    act = W["req"] & W["have"]
    # the angle-loop image family (spec V299 rev 2 F9): 39990-TVA,A16A = V298, A16B = V299 (A160 = V294/V295: NOT live)
    letter = next((x for x in ("A16A", "A16B") if any(("39990-TVA," + x) in s for s in fw)), None)
    return dict(eps_fw=fw, live_image=(letter is not None) if fw else None, image_letter=letter,
                params={k: params.get(k) for k in keys if k in params}, cam=m.get("cam"), git=m.get("git"),
                fork_inactive_match=match, n_inactive=int(nz.sum()),
                raw_max=float(np.nanmax(np.abs(W["raw"][act]))) if act.any() else np.nan)


# =====================================================================================================================
# REPORT
# =====================================================================================================================
def f3(x, f="%.3f"):
    try:
        return f % x if x is not None and np.isfinite(x) else "  -  "
    except TypeError:
        return str(x)


def _clauses(L, V):
    for nm, ok, val in V["clauses"]:
        L.append("   [%s] %-66s %s" % ({True: "x", False: " ", None: "?"}[ok], nm, val))


def report(S):
    L = []
    P = L.append
    P("=" * 110)
    P("ANGLE-LOOP DRIVE READ -- %s" % S["meta"].get("tag", S["meta"].get("name", "?")))
    P("=" * 110)
    a = S["attrib"]
    P("0. ATTRIBUTION  EPS fw %s -> image %s" % (a["eps_fw"], {True: "%s (LIVE image)" % a.get("image_letter"),
                                                              False: "NOT A16A/A16B",
                                                              None: "unknown (no carFw)"}[a["live_image"]]))
    P("   fork params %s ; git %s" % (a["params"], a.get("git")))
    P("   fork angle interface (SPEC C3): inactive frames >= 2 deg with raw == 0x14A field: %s (n %d)  [angle fork ~1.0,"
      " torque fork ~0]; max |raw| engaged %s (SPEC C2 clip 4000)" % (f3(a["fork_inactive_match"]), a["n_inactive"],
                                                                        f3(a["raw_max"], "%.0f")))
    if a.get("cam"):
        P("   camera bus-2 0xE4: %d frames, %d with request=1, max |torque| %.0f  (%s)"
          % (a["cam"]["n"], a["cam"]["n_req"], a["cam"]["max_abs"],
             "PREREQUISITE VIOLATED: the camera LKAS is commanding" if a["cam"]["n_req"] else "camera LKAS silent"))
    e = S["exposure"]
    P("   engaged %.1f s in %d episodes; by band (engaged / hands-off s): %s" % (
        e["engaged_s"], e["n_episodes"], "  ".join("%s %.0f/%.0f" % (k, v["eng_s"], v["handsoff_s"])
                                                   for k, v in e.items() if isinstance(v, dict))))
    V = S["verdict"]
    P("")
    P("1. VERDICT (structural regression, decision-bearing; R1 also needs the %g-%g Hz fit): %s" % (
        THR["r1b_lo"], THR["r1b_hi"], V["verdict"]))
    _clauses(L, V)
    R = S["reg_struct"]
    si = S.get("struct_inputs") or {}
    if si:
        P("   structural inputs: C3-rev2-P lane replayed with the engage-ramp arm %d (+%d / -%d per tick, %s), the"
          " torque word %d frame(s) ahead of 0x18F, I re-anchored per ~%.0f s window%s" % (
              si["arm"], si["ramp"][0], si["ramp"][1], si["ramp_src"], si["q_lead"], si["anchor_s"],
              ("; " + si["note"]) if si.get("note") else ""))
        if si.get("ref"):
            P("   (A16B wire: the I component and C3B-P* below are the %s rule's replay -- section 6B decides which rule"
              " ran)" % si["ref"])
    P("   tap = a P_raw + b P_meas + c I + d D (+ one intercept per window); LIVE design: a = b = c = d = 1 (lag %d"
      " frames; R2 within-window)" % R["lag_frames"])
    P("   %-8s %6s %6s %6s %6s %6s %7s %7s %6s %7s %7s" % ("band", "s", "a", "b", "c", "d", "c_P", "pred", "c_I/P",
                                                        "R2", "R2rep"))
    for nm, v in R["rows"].items():
        if not v.get("ok"):
            P("   %-8s %6.1f   (too little hands-off exposure)" % (nm, v.get("n", 0) / 50.0))
            continue
        P("   %-8s %6.1f %6.3f %6.3f %6.3f %6.3f %7.3f %7.3f %6.2f %7.4f %7.4f" % (
            nm, v["s"], v["a"], v["b"], v["c"], v["d"], v["cP"], v["cP_pred"], v["cIcP"], v["r2"], v["r2_replay"]))
    Pp = R["pooled"]
    if Pp.get("n"):
        P("   pooled   a %.3f b %.3f c %.3f d %.3f  R2 %.4f" % (Pp["a"], Pp["b"], Pp["c"], Pp["d"], Pp["r2"]))
    Rb = S.get("reg_r1b")
    if Rb:
        P("   R1 SECOND METHOD -- the literal regression at %g-%g Hz (D is identified there), lag %d frames:" % (
            THR["r1b_lo"], THR["r1b_hi"], Rb["lag_frames"]))
        P("     %-8s %6s %7s %7s %7s %6s" % ("band", "s", "c_D", "se", "ratio", "R2"))
        for nm, v in Rb["rows"].items():
            if v.get("ok"):
                P("     %-8s %6.1f %7.3f %7.3f %7.3f %6.3f" % (nm, v["s"], v["cD"], v["se_cD"], v["ratio"], v["r2"]))
        P("     band median: c_D %s  ratio %s   (the design: c_D 0.566, ratio -1)" % (f3(V.get("r1b_cD")),
                                                                                    f3(V.get("r1b_ratio"))))
    R0 = S.get("reg_struct_v0")
    if R0 and R0["pooled"].get("n"):
        P0 = R0["pooled"]
        P("   SUPERSEDED structural form (pre-2026-10-02: direction-0 ramp, word on the 0x18F frame, one intercept),"
          " for comparison only:")
        P("     pooled ratio %s  c_I/c_P %s  c_D %s  (a %.3f b %.3f c %.3f d %.3f, lag %d); per band c_D %s" % (
            f3(P0["ratio"]), f3(P0["cIcP"], "%.2f"), f3(P0["cD"]), P0["a"], P0["b"], P0["c"], P0["d"],
            R0["lag_frames"], " ".join("%s %.3f" % (k, v["cD"]) for k, v in R0["rows"].items() if v.get("ok"))))
    VL = S["verdict_literal"]
    P("   the design's LITERAL regression (0.3-3 Hz, lag-matched), reported, not decision-bearing: %s" % VL["verdict"])
    P("     ratio %s  c_I/c_P %s  c_D %s  dip %s  hi %s" % (f3(VL["ratio"]), f3(VL["cIcP"], "%.2f"), f3(VL["cD"]),
                                                          f3(VL["dip"]), f3(VL["hi"])))
    if S.get("replay"):
        P("   REPLAY METHOD -- the lane replayed on the wire inputs (R2 of the tap vs each image's arithmetic):")
        for k, v in S["replay"].items():
            P("     %-12s R2 %s  gain %s  lag %s  n %s" % (k, f3(v.get("r2")), f3(v.get("gain")), v.get("lag"),
                                                        v.get("n")))
        rc = S.get("replay_corrected") or {}
        if rc.get("n"):
            P("     %-12s R2 %s  gain %s  lag %s  n %s   <- C3B-P with the structural inputs (arm %s ramp, word %s"
              " frame ahead)" % ("C3B-P*", f3(rc.get("r2")), f3(rc.get("gain")), rc.get("lag"), rc.get("n"),
                                 si.get("arm"), si.get("q_lead")))
    A2 = S["a2"]
    P("   A2: %d request drops, %d with |tap| < 20 LSB within 0.15 s; R7 (pushing toward 0 > 0.2 s): %s" % (
        A2["n"], A2["n_pass"], A2["r7"]))
    P("")
    P("2. STOP BANDS (any one -> REVERT)")
    P("   R1 INVERTED          %s" % (V["verdict"] == "INVERTED"))
    P("   R2 rail hands-off    %s  %s" % (S["r2"]["fire"], S["r2"]["events"][:3]))
    P("   R3* 0.25-5.5 Hz ring %s  %d events %s" % (S["r3"]["fire"], S["r3"]["n"], [
        (e_["chan"], round(e_["f0"], 2), round(e_["amp_max"], 2), round(e_["r_gm"], 2), e_["growing"], round(e_["t"], 1))
        for e_ in S["r3"]["events"][:4]]))
    P("   R4 new 5-30 Hz line  %s  %s" % (S["r4"]["fire"], [(n_["chan"], round(n_["f"], 2), round(n_["excess_db"], 1))
                                                          for n_ in S["r4"]["new"]]))
    st = S["rp"]["strongturn"]
    pres = S["rp"].get("presence") or {}
    P("   R5 ring presence %s %%  F7 %s /100 s (n %s, %.0f s at |angle| >= 30)" % (
        f3(pres.get("pres_pct"), "%.2f"), f3(st.get("f7_per100"), "%.2f"), st.get("n_f7"), st.get("hi_ang_s", 0)))
    P("   R6 |err| > 10 deg     %s  %s" % (S["r6"]["fire"], S["r6"]["events"][:3]))
    P("   R7 (see A2)          %s" % A2["r7"])
    P("   R8 health            %s  (status bad %d, b4 bad %d; have status %s b4 %s)" % (
        S["r8"]["fire"], S["r8"]["bad_status"], S["r8"]["bad_b4"], S["r8"]["have_status"], S["r8"]["have_b4"]))
    P("")
    P("3. THE GOAL (score bands; the operator scores symptoms)")
    for nm, v in S["goal"].items():
        if not v.get("secs"):
            P("   %-6s no hands-off run >= 15 s" % nm)
            continue
        P("   %-6s %5.0f s  tracking %s [%s]  turn-hold min %s med %s (n %d) [%s]%s" % (
            nm, v["secs"], f3(v["track"]), "pass" if v["track_pass"] else "FAIL", f3(v["hold_min"]), f3(v["hold_med"]),
            v["n_hold"], {True: "pass", False: "FAIL", None: "-"}[v["hold_pass"]],
            "" if v["scored"] else "  (under 60 s: reported, not a goal verdict)"))
    P("   dwell-then-jump (nl_sim.dwell_jump, ref = theta_sp), per min: %s" % "  ".join(
        "%s %s" % (k, f3(v["per_min"], "%.2f")) for k, v in S["dj"].items() if v["secs"] > 0))
    refs = S.get("refs") or {}
    P("   dwells/min @0.25 deg/s (symptom instrument):  this  %s" % _dw(S["dwells"]))
    for k, r in refs.items():
        P("        %-12s (%s)                       %s" % (k, r.get("build"), _dw(r.get("dwells", {}))))
    eod = S["rp"].get("eng_over_dis") or {}
    P("   18-22 Hz engaged/disengaged: this %s ; refs %s" % (
        f3(eod.get("18-22"), "%.2f"),
        {k: f3((r.get("eng_over_dis") or {}).get("18-22"), "%.2f") for k, r in refs.items()}))
    P("   ring presence (hands-off): this %s %% ; refs %s" % (
        f3(pres.get("pres_pct"), "%.2f"),
        {k: f3((r.get("presence") or {}).get("pres_pct"), "%.2f") for k, r in refs.items()}))
    P("   F7 /100 s: this %s ; refs %s" % (f3(st.get("f7_per100"), "%.2f"),
                                         {k: f3((r.get("strongturn") or {}).get("f7_per100"), "%.2f")
                                          for k, r in refs.items()}))
    for ch in CHANS:
        P("   5-30 Hz lines on %-4s (>= %.0f dB): %s" % (ch, THR["r4_excess_db"], [
            (round(n_["f"], 1), round(n_["excess_db"], 1)) for n_ in S["census"][ch]["lines"]]))
    P("")
    P("4. FRICTION per band (hands-off; T counts; next-step sizing, NOT a verdict)")
    for nm, v in S["friction"].items():
        if v.get("ok"):
            P("   %-7s %5.0f s  Coulomb Fc %6.1f +- %4.1f  breakaway p50/p90 %6.1f / %6.1f (n %d)  k %.1f T/deg  b %.2f" % (
                nm, v["secs"], v["Fc"], v["se_Fc"], v["Fs_p50"], v["Fs_p90"], v["n_break"], v["k"], v["b"]))
        else:
            P("   %-7s %5.0f s  (too little sliding/exposure)" % (nm, v.get("secs", 0)))
    lh = S["light"]
    P("")
    P("5. LIGHT-HOLD EPISODES (300 <= |bar| < 512 for >= 1 s): %d" % lh.get("n", 0))
    for r in lh.get("rows", []):
        P("   t %.1f %-7s %.1f s @ %.1f m/s  dI %.0f T [%s]  release overshoot %.2f deg (bar %.1f) [%s]" % (
            r["t"], r["kind"], r["dur"], r["v"], r["dI_T"], "flat" if r["flat"] else "RAMPS", r["release_ovs"],
            r["ovs_bar"], "pass" if r["ovs_pass"] else "FAIL"))
    if S.get("v299"):
        import drive_read_v299 as V2
        L.append(V2.report(S["v299"]))
    elif S.get("v299_error"):
        L.append("\n6. V299 / DRIVE-2 BLOCKS FAILED -- %s" % S["v299_error"])
    return "\n".join(L)


def _dw(d):
    return "  ".join("%s %s" % (k, f3(v.get("per_min_025"), "%.2f") if v.get("scored") else "-") for k, v in d.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("route")
    ap.add_argument("--refs", default=",".join(REFS_DEFAULT))
    ap.add_argument("--no-replay", action="store_true")
    ap.add_argument("--no-presence", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    refs = {}
    t_ref = _time.time()
    for r in [x for x in a.refs.split(",") if x]:
        pr("  reference %s ..." % r)
        refs[r] = ref_summary(r, with_presence=not a.no_presence)
    t_load = _time.time()
    W = load_route(a.route)
    t_read = _time.time()
    S = read(W, refs=refs, with_replay=not a.no_replay, with_presence=not a.no_presence)
    t_end = _time.time()
    txt = report(S)
    txt += ("\n\nRUNTIME %.1f s wall (imports %.1f, references %.1f, route load %.1f, read %.1f incl. lane replays %.1f;"
            " replay cache %d hit / %d computed, under %s)" % (
                t_end - _T0, t_ref - _T0, t_load - t_ref, t_read - t_load, t_end - t_read, _RT["replay_s"],
                _RT["hits"], _RT["misses"], SCR / "replay")) + "".join("; " + x for x in _RT["fallback"])
    pr(txt)
    out = Path(a.json) if a.json else SCR / ("read_%s.json" % W["meta"]["tag"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(S, indent=1, default=_js))
    (out.with_suffix(".txt")).write_text(txt, encoding="utf-8")
    pr("\nwrote %s (+ .txt)" % out)


if __name__ == "__main__":
    main()
