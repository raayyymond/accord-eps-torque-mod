# -*- coding: utf-8 -*-
r"""drive_read_v299.py -- THE DRIVE-2 (V299) BLOCKS of angle_loop_drive_read.py.

    imported by angle_loop_drive_read.read() / report();   standalone:  python drive_read_v299.py --selftest

ANALYSIS ONLY.  Reads the kit's route caches, the fork-side cache (r79_extract_fork.py) and the spec's own integer
mirror; writes only under _scratch/.  Sends nothing, flashes nothing, touches no fork file and no firmware.

WHAT IT ADDS -- ALIGNED 2026-10-02 to DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md §6 / §7 and the drive card
docs/scoring/DRIVE-CARD-V299-drive2-2026-10-02.md (the binding source of every criterion; every threshold is in THR2
with its source, none fitted on a flight).  The verifier's rejection of the rev-2 instrument is resolved item by item
(INSTRUMENT-V299.md §ALIGN).  DEFINITIONS (spec rev 3 §7.1, applied in EVERY block below):
  HANDS-OFF FRAME  latActive (the wire's req & SCA), |wire| < 300, not steeringPressed, and |bar| < 300 for the
                   preceding 0.5 s (handsoff_v3).  wire = carState.steeringTorque units = |bar| / 1.024; bar = the 0x18F
                   torque word x 1.024 (the reader's W["bar"]).  NB the reader's W["wire"] is the 0x18F RATE, not this.
  RELEASE EDGE     the first frame with |wire| < 150 after a hand episode (latActive, |wire| > 300 for >= 0.5 s); hand
                   side = the sign of the mean wire over the episode's last 0.3 s (ending at its last |wire| > 300
                   frame before the first |wire| < 150 crossing); a release whose next 1.5 s holds |wire| > 300
                   again (a re-grab) is EXCLUDED and counted; 6D prints every release with its release-instant gap.
  TURN-IN          a hands-off setpoint excursion >= 20 deg that settles (|d theta_sp/dt| < 5 deg/s for >= 1 s);
                   overshoot = max (theta - theta_sp_final) * sign(turn) in the FULL 3 s after theta first reaches
                   90 % of it (not cut where the setpoint moves again: that is flagged SP-MOVED).
  A  ATTRIBUTION   carFw EPS family `39990-TVA,A16<letter>` (A16A = V298, A16B = V299; A160 = V294/V295 excluded), the
                   V299 fork params, the fork commit the schema was pinned to, starpilotCarState.accordAngleStatus:
                   PRESENCE as a FRACTION of latActive frames (F1: >= 99 %), decoded with the FORK'S OWN bit values
                   (c6452361e values.py: 4 rate/jerk, 16 clip, 256 EPS-torque stale; every other bit reserved -- the
                   spec's §2.2 prose says 8 for the stale bit; the fork emits 256, see STATUS_BITS), and the O1-like
                   SETPOINT SNAP (F1): |d theta_sp| > 1.2 deg (literal, every config) in one frame TOWARD the wheel,
                   both frames latActive (the first frame and the rising edge excluded), on the fork's carOutput
                   setpoint (o1_snaps); CLIP-BOUND steps are NOT counted (orchestrator ruling 2026-10-02), both
                   counts printed (f1_snap_clause).
  B  RULE IDENTITY (F1)   the byte-exact lane (drive_read_fastlane.cand_lane) replayed under the V298 rule (C3B-P) and the
                   V299 rule (v299_cand), the drive read's structural inputs; R2 of the 0x1AB tap vs each on HANDS-OFF
                   tap frames, pooled (each at its own best lag) and per 30-s settled window with >= 200 hands-off tap
                   frames.  F1 on a V299 wire, in the orchestrator's order (f1_replay_clause): V299 does not beat V298
                   (pooled dR2 < +0.05 or < 2/3 of those windows) -> FAIL; else the winner's pooled R2 < 0.5 (the
                   ratified fit floor) -> NOT TESTABLE, loudly; else pass.  The positive control printed is what THIS
                   read measures on route 79, cached (SCR/refs/r79_v299_posctrl_*.json, keyed on a sha256 of the
                   canonical r79 wire cache's 0x1AB bytes) and written ONLY by a read whose scored tap hashes to it.
                   The V299 rule is checked every run against the spec mirror cave_rev2 (rev_h1.py, by ast).
  C  STUTTER READOUTS   stall-surges, ratchet trains, 4-8 Hz in-turn rms, dwells per band vs V282 r6c / r39 (the panel's
                   own detectors, unchanged); ENRICHMENT at |bar| 300 / 512 / 1229 crossings; HANDS-OFF |w| > 1229
                   onsets (the 0.5 s before = hands-off frames) per minute of turning (F6b); the 1.6-3 Hz hard-turn
                   wheel-rate (INFORMATION, ruling ii; m6_goal_scoring.spectral's own definition).
  D  RELEASES (F3 / F5)   F3 = the swing past theta_sp AWAY from the hand side within 1.5 s of the release; bars by
                   speed band: > 12 deg at 5-11 m/s, > 9 at 11-15, > 8 at >= 15, > 5 on a straight (|theta_sp| < 3
                   across the window, any speed).  F5 = (theta_sp - theta) toward centre at release + 1.5 s > 4 deg at
                   >= 5 m/s after ANY release.  The release-lurch null sentence (<= 6.1 / 6.5-12 / > 12 deg).
  E  F4a / F4b / F4c   hands-off turn-ins: F4a >= 45 deg at <= 10 m/s > 6 deg; F4b 20-45 deg at <= 4.5 m/s > 8.5 deg;
                   F4c 20-45 deg at 4.5-10 m/s > 6 deg (the 15 % clause is DELETED, spec §7.2).
  F  F10 RING      sustained hands-off curve holds at 10-13 m/s, |a_lat| >= 1.5 m/s^2, >= 3 s: theta - theta_sp
                   band-passed 0.4-0.8 Hz; fires on a half-peak > 1 deg or > 2 consecutive half-cycles >= 0.5 deg.
  G  CAP READ      hands-off curve holds at 8-12.5 m/s, |a_lat| >= 2 m/s^2, >= 3 s: per hold, the replayed V299 I AT
                   THE 6144 BOUND for >= 80 % of the LAST second AND the 0.5 Hz-LP |theta_sp - theta| > 3 deg there; the
                   card's three-way null sentence (>= 50 % of holds: ms_free-like, 7168 licensed for RE-SCORING only;
                   bound active but <= 3 deg: 6144 suffices; bound active in < 50 %: the cap is not the binder).
  H  HANDS / AUTHORITY   F7 (pressed + tap >= 50 % rail opposing > 0.5 s), F7b (OBSERVATION: |wire| > 600 > 0.3 s +
                   tap >= 40 % rail opposing, not pressed), F9 (hands-off tap > 250 LSB, or >= 230 for > 0.3 s).
  I  BAR CHECK (F8)  carState.steeringTorqueEps == -8 * tap on every frame with the EPS-stale bit (256) clear; that
                   bit's duty on latActive frames; canValid drops on EVERY angle-mode frame (steerControlType angle
                   and an A16x angle firmware; from the first valid frame), not only latActive; the drawn bar's sign.
  J  THE DRIVE-2 VERDICT   every pre-registered criterion PASS / FAIL / NOT TESTABLE (with why), F7b OBSERVATION,
                   X3 not applicable to config A, R9 the operator's, the three null sentences.

SIGNS (EVIDENCE, route 79, recomputed 2026-10-02 by chk_0x1ab_checksum.py): on the latest 0x18F frame at or before
  each carState row, the 0x18F torque word == -carState.steeringTorque EXACTLY on 100.00 % of 121 383 rows (corr
  -0.99999), so bar = -1.024 x steeringTorque: the 0x18F word is + = RIGHT, carState.steeringTorque + = LEFT, and the
  hand pushes the wheel toward sign(-bar) in the angle's +left convention.  The motor torque on the wheel is u = -T
  (0x1AB s10 is + = right, the fork's carstate.py).  The lane OPPOSES the hand iff T * bar < 0.

EVIDENCE vs BELIEF: every count, R2 and duty here is measured on the wire / the caches (EVIDENCE); a_lat is from the
setpoint angle through the fork's carParams bicycle model (BELIEF: roll and offsets ignored); the slot-4 bound test is a
frame-level reading of a 1 kHz condition (BELIEF at the tick, EVIDENCE at the frame); every "predicted" value is the
spec's sim (BELIEF).  Score bands; the operator scores symptoms.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import time
import types
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]
AL = KIT / "analysis-2020accord" / "studies" / "angle_loop"
V298F = AL / "v298_flight"
REV_H1 = AL / "v299_design" / "revise" / "rev_h1.py"
EXTRACTOR = V298F / "r79_extract_fork.py"
SPEC = "docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md"
CARD = "docs/scoring/DRIVE-CARD-V299-drive2-2026-10-02.md"
R79_PREFIX = "75604b0a432fdc89_00000079--a1f5d2a272"
for _q in (V298F, HERE):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
FS = 100.0
RAIL_T = 2461.0
RAIL_LSB = RAIL_T / 8.0                                    # 307.6 tap LSB

# =====================================================================================================================
# PRE-REGISTERED THRESHOLDS (spec rev 2 §6 / §7 + the orchestrator's V299-round brief, 2026-10-02).  None fitted.
# =====================================================================================================================
THR2 = dict(
    # ---- §7.1 definitions (spec rev 3), used by EVERY block
    ho_wire=300.0, ho_bar=300.0, ho_pre_s=0.5,    # hands-off: |wire| < 300, |bar| < 300 for the preceding 0.5 s, unpressed
    wire_per_bar=1.0 / 1.024,             # wire (carState.steeringTorque units) = bar / 1.024 (EVIDENCE r79, docstring)
    rel_on=300.0, rel_on_s=0.5, rel_off=150.0, rel_s=1.5, rel_min_s=0.5, rel_side_s=0.3,   # release edge (§7.1)
    ti_settle_rate=5.0, ti_settle_s=1.0, ti_rate_half=0.10, ti_min=20.0, ti_reach=0.90, ti_win_s=3.0,  # turn-in (§7.1)
    # ---- F1
    f1_dr2=0.05, f1_win_frac=2.0 / 3.0, f1_win_taps=200,   # pooled dR2 >= +0.05 AND V299 wins >= 2/3 of the 30-s
    win_frames=3000,                      # hands-off windows with >= 200 tap frames (30-s settled windows, d1_r79 D)
    man_frames=200, man_w=20.0, man_a=100.0,   # INFORMATION: manoeuvre windows (|8 Hz LP w18| >= 20 or |alpha| >= 100)
    f1_status=0.99,                       # accordAngleStatus present on >= 99 % of latActive frames
    f1_fit_floor=0.5,                     # INSTRUMENT GUARD (not in the card): the identity means nothing unless the
                                          # winning replay explains the tap (pooled R2 >= 0.5; r79's V298 fit 0.867)
    f1_snap=1.2, f1_snap_tol=1e-3, f1_o1_match=0.99,   # O1-like snap |d theta_sp| > 1.2 deg / frame toward the wheel
    # ---- F2
    f2_pres=0.5, f2_f7=0.0, f2_1822=2.5, f2_1317=3.5,
    # ---- F3 (bars by speed band, §7.2) / F5 / the lurch sentence
    f3_bands=((5.0, 11.0, 12.0), (11.0, 15.0, 9.0), (15.0, 999.0, 8.0)), f3_straight_deg=5.0, f3_straight_sp=3.0,
    f5_deg=4.0, f5_v=5.0,
    light_word=1229.0,                    # a "light" hold = peak |bar| < 1229 (below Honda's steeringPressed), unpressed
    lurch_vlo=5.0, lurch_vhi=10.0, lurch_nom=6.1, lurch_heavy_lo=6.5, lurch_heavy_hi=12.0,
    # ---- F4a / F4b / F4c (§7.2; the 15 % clause DELETED)
    f4a_min=45.0, f4a_vmax=10.0, f4a_deg=6.0,
    f4b_min=20.0, f4b_vmax=4.5, f4b_deg=8.5,
    f4c_min=20.0, f4c_vmax=10.0, f4c_deg=6.0,
    # ---- F6 / F6b
    f6_trains=4.7, f6_rms=7.09, f6_enrich=2.0,   # trains / min of turning at 5-10; in-turn 4-8 Hz rms there; 300|512
    f6b_enrich=2.0, f6b_onsets=20.0,      # near / free at 1229 crossings; HANDS-OFF |w| > 1229 onsets / min of turning
    near_frames=51,                       # +-0.25 s (d1_r79 section B: np.convolve(tog, ones(51), "same"))
    enrich_min_s=10.0, enrich_min_n=5,    # an enrichment ratio is scored only with >= 10 s near-turning and >= 5 events
    # ---- F7 / F7b / F8 / F9
    f7_frac=0.50, f7_t=0.5,
    f7b_wire=600.0, f7b_t=0.3, f7b_frac=0.40,   # F7b (OBSERVATION by ruling)
    f8_frac=0.001,
    f9_max=250.0, f9_hi=230.0, f9_t=0.3,
    # ---- F10
    f10_lo=0.4, f10_hi=0.8, f10_vlo=10.0, f10_vhi=13.0, f10_alat=1.5, f10_min_s=3.0, f10_half=1.0, f10_cyc=0.5,
    f10_ncyc=3,                           # "> 2 consecutive half-cycles >= 0.5 deg" = >= 3
    # ---- the cap null sentence (card §4 / spec §6.2)
    cap_vlo=8.0, cap_vhi=12.5, cap_alat=2.0, cap_min_s=3.0, cap_last_s=1.0, cap_at=0.80, cap_deg=3.0, cap_share=0.50,
    cap_level=6144, cap_d3_vlo=8.0, cap_d3_vhi=10.0, cap_d3_deg=3.0, cap_d3_min=60.0, cap_d3_max=90.0,  # D3 = 60-90 deg
    # ---- information: the 1.6-3 Hz hard-turn wheel-rate (m6_goal_scoring.spectral, its own definition)
    hard_lo=1.6, hard_hi=3.0, hard_theta=20.0, hard_run=200,
)
# the spec's sim predictions (rev 3 §7.2 / the card §4; BELIEF), printed beside each readout -- never used as a bar
PRED = dict(
    F1="V299 wins (spec §7.2)",
    F3="outward light holds: heavy 9.7-10.4 deg (5-10 m/s), 7.9 (12.5), 6.5 (15); nominal 4.4-6.1 / 5.4 / 4.8; "
       "straight <= 4.1 (rev 3 §7.2 F3)",
    F4a="<= 5.2 deg (45 deg, 3 m/s); <= 4.7 at 6.1 m/s; <= 3.3 at 7-10 m/s",
    F4b="7.0 deg heavy member (30 deg, 3 m/s), 5.8 at 4 m/s; nominal <= 4.2; V298 <= 3.0",
    F4c="<= 4.6 deg (5 m/s), <= 4.0 (6.1), <= 3.3 above",
    F5="<= 2.0 deg at <= 10 m/s; 3.2 at 12.5 m/s; 2.6 at 15; centre-ward / drags <= 0.1",
    F6="sim 0 stall-surges / turn (V298 1.75-6.1); 4-8 Hz 1.0-1.3 deg/s (V298 3.2-6.0, sim metric)",
    F7="no: longest 97 ms (S2) / 130 ms (RSN)",
    F9="tap peak <= 207 LSB (184-193 at 6-8 m/s); r79 replay max 205",
    F10="none on any member <= 12.4 m/s; 2.69 deg only on b_lo x ms_free at 12.6-13 m/s",
    F7b="EXPECTED on moderate drags at 5-8 m/s: 550-1560 ms at 800 words -- the ruling's declared cost",
    cap="shortfall <= 3.2 deg at 8 m/s and <= 0.9 deg from 9 m/s (nominal); 3-7 deg at 8-10 m/s if ms_free-like",
)
SYM_BANDS = (("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-20", 10.0, 20.0), (">20", 20.0, 99.0))
ENR_BANDS = (("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-20", 10.0, 20.0), ("0-20", 0.0, 20.0))
HARD_BANDS = (("<3", 0, 3), ("3-8", 3, 8), ("8-12", 8, 12), ("12-18", 12, 18), ("18-25", 18, 25), (">25", 25, 99),
              ("ALL", 0, 99))                                 # m6_goal_scoring.SB + its pooled row
# accordAngleStatus bit VALUES as the V299 fork emits them (EVIDENCE: fork c6452361e opendbc_repo/opendbc/car/honda/
# values.py ANGLE_STATUS_RATE = 4, ANGLE_STATUS_CLIP = 16, ANGLE_STATUS_EPS_STALE = 256; "Bits 1, 2, 8, 32, 64, 128 and
# 512+ are reserved (0)").  The spec's §2.2 F8 row says 8 for the stale bit: the fork commit says 256, the instrument
# decodes what the fork emits and counts any frame with 8 set as RESERVED.  "bit 8" in F8 = the value 256 (= 1 << 8).
STATUS_RATE, STATUS_CLIP, STATUS_STALE = 4, 16, 256
STATUS_BITS = {STATUS_RATE: "rate/jerk-bound", STATUS_STALE: "EPS-torque stale/bad", STATUS_CLIP: "clip-bound"}
STATUS_RESERVED = 0xFFFF & ~(STATUS_RATE | STATUS_CLIP | STATUS_STALE)
# the fork's error clip (identical at 2712e1336 = V298 and c6452361e = V299, values.py ANGLE_ERROR_MAX_*): tags a
# setpoint step as clip-bound on a route whose fork publishes no status word (route 79)
ERR_MAX_BP = (3.1, 8.0, 10.0, 11.75, 17.5, 26.9)
ERR_MAX_V = (17.0, 15.5, 19.5, 17.0, 8.5, 4.5)


def handsoff_v3(W):
    """spec rev 3 §7.1: latActive (the wire's req & SCA), |wire| < 300, not steeringPressed, and |bar| < 300 for the
    preceding 0.5 s (frames k-50 .. k).  wire = bar / 1.024 (carState.steeringTorque units).  An unknown bar (nan) is
    not hands-off.  -> bool (n,)."""
    bar = np.abs(np.where(np.isfinite(W["bar"]), W["bar"], np.inf))
    pressed = np.nan_to_num(W["pressed"]) > 0.5
    bad = (bar >= THR2["ho_bar"]) | pressed
    n = int(round(THR2["ho_pre_s"] * FS))
    cs = np.r_[0, np.cumsum(bad)]
    k = np.arange(len(bar))
    clean = (cs[k + 1] - cs[np.maximum(k - n, 0)]) == 0
    return np.asarray(W["eng"], bool) & (bar * THR2["wire_per_bar"] < THR2["ho_wire"]) & ~pressed & clean


def handsoff_before(W, idx, n=None):
    """True where the n frames BEFORE idx (idx-n .. idx-1) were all clean of a hand (|bar| < 300, unpressed) -- the
    hands-off test for an EVENT at idx whose own frame is not hands-off (an |w| > 1229 onset, F6b)."""
    bar = np.abs(np.where(np.isfinite(W["bar"]), W["bar"], np.inf))
    bad = (bar >= THR2["ho_bar"]) | (np.nan_to_num(W["pressed"]) > 0.5)
    n = int(round(THR2["ho_pre_s"] * FS)) if n is None else n
    cs = np.r_[0, np.cumsum(bad)]
    idx = np.asarray(idx, np.int64)
    return (idx >= n) & ((cs[idx] - cs[np.maximum(idx - n, 0)]) == 0)

def runs(mask, minlen=1):
    d = np.diff(np.r_[0, np.asarray(mask, np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    k = (b - a) >= minlen
    return np.c_[a[k], b[k]]


def _f(x, fmt="%.2f"):
    try:
        return fmt % x if x is not None and np.isfinite(x) else "-"
    except TypeError:
        return str(x)


# =====================================================================================================================
# B0. THE SPEC MIRROR cave_rev2, read verbatim from rev_h1.py (ast), and the rule validation
# =====================================================================================================================
FRZ, HOOK, SKIP = "FRZ", "HOOK", 0x2A164
_MIR = {}


def spec_mirror():
    """-> (cave_rev2, sha16 of its source).  The functions s16 / s32 / cave_rev2 are compiled from rev_h1.py's own
    text (no import of rev_h1: that pulls in d1_time and the panel engines); NC.FRZ_RET / HOOK_RET become labels."""
    if not _MIR:
        src = REV_H1.read_text(encoding="utf-8")
        tree = ast.parse(src)
        keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("s16", "s32", "cave_rev2")]
        assert sorted(n.name for n in keep) == ["cave_rev2", "s16", "s32"], [n.name for n in keep]
        mod = ast.Module(body=keep, type_ignores=[])
        ns = dict(NC=types.SimpleNamespace(FRZ_RET=FRZ, HOOK_RET=HOOK), SKIP=SKIP)
        exec(compile(mod, str(REV_H1), "exec"), ns)
        seg = ast.get_source_segment(src, [n for n in keep if n.name == "cave_rev2"][0])
        _MIR.update(fn=ns["cave_rev2"], sha=hashlib.sha256(seg.replace("\r\n", "\n").encode()).hexdigest()[:16])
    return _MIR["fn"], _MIR["sha"]


def _val_cases(N, seed, targeted=False):
    """random (rev_h1.cases' distributions, valid op and camera on) or targeted (the cap edit's regime: 1382 < v <=
    2880 and the 1381..1383 / 2879..2881 edges, a large angle either sign, |I8 >> 10| straddling 4096..6144, armed,
    hand below 1229).  I8 stays within ICL 8192 S (Honda's clamp: the lane cannot leave it)."""
    rng = np.random.default_rng(seed)
    if targeted:
        v = rng.choice(np.r_[rng.integers(1383, 2881, N), [1381, 1382, 1383, 2879, 2880, 2881]], N)
        sp = rng.integers(-16384, 16385, N)
        r26 = rng.integers(-65535, 65536, N)
        th = rng.integers(150, 1200, N) * rng.choice([-1, 1], N)
        I8 = (rng.integers(3000, 7500, N) * 1024 + rng.integers(0, 1024, N)) * rng.choice([-1, 1], N)
        tq = rng.integers(-1229, 1230, N)
        ramp = np.full(N, 0x8000)
    else:
        sp = rng.integers(-16384, 16385, N)
        sp[::40] = 32767
        r26 = rng.integers(-65535, 65536, N)
        knots = np.array([714, 1843, 2304, 2707, 4032, 6198, 1382, 2880])
        v = rng.integers(0, 12001, N)
        k5 = np.arange(N) % 5
        v[k5 == 0] = np.clip(rng.choice(knots, (k5 == 0).sum()) + rng.integers(-1, 2, (k5 == 0).sum()), 0, 12000)
        v[k5 == 1] = rng.choice([1381, 1382, 1383, 2879, 2880, 2881], (k5 == 1).sum())
        edges = np.array([-1230, -1229, -513, -512, -301, -300, 0, 300, 301, 512, 513, 1229, 1230, -32768, 32767])
        tq = np.where(rng.random(N) < 0.5, rng.integers(-3000, 3001, N), rng.choice(edges, N))
        ramp = rng.choice([0x8000, 0x8000, 0xFFFF, -1], N)
        ramp = np.where(ramp < 0, rng.integers(0, 0x8000, N), ramp)
        th = np.select([rng.random(N) < 1 / 3, rng.random(N) < 0.5], [rng.integers(-4000, 4001, N),
                                                                     rng.integers(-40, 41, N)],
                       rng.integers(-32768, 32768, N))
        I8 = np.select([rng.random(N) < 0.25, rng.random(N) < 1 / 3, rng.random(N) < 0.5],
                       [rng.integers(-8192 * 1024, 8192 * 1024, N), rng.integers(-2 ** 20, 2 ** 20, N),
                        np.zeros(N, np.int64)], rng.integers(-8192 * 1024, 8192 * 1024, N))
    return [np.asarray(a, np.int64) for a in (sp, r26, v, tq, ramp, th, I8)]


def _fast_freeze(FL, p, glut, sp, r26, v, tq, ramp, th, I8):
    """the fast lane's freeze decision for one tick, from the SAME helpers cand_lane calls (E' as cand_lane
    computes it; static_freeze; the I-vs-arb_bound test of its scalar loop with I = I8 >> 3)."""
    E = FL.s32((FL.s16(sp) << 2) - r26)
    G = np.asarray(glut, np.int64)[np.clip(v, 0, 12000)]
    Ep = FL.s32(E * G) >> 8
    fs = FL.static_freeze(p, tq, Ep, ramp)
    bd = FL.arb_bound(p["arb"], th, v & 0xFFFF, Ep)
    I = I8 >> 3
    wind = np.where(Ep >= 0, I >> 7, -(I >> 7)) >= bd
    return Ep, fs | wind, G


def rule_validation(FL, ST, C, n_rand=4000, n_targ=2000):
    """the fast lane's V299 rule vs the spec mirror cave_rev2 (camera on, op valid -- the paths the replay models)."""
    t0 = time.time()
    mir, sha = spec_mirror()
    pV = FL.cand_params(C["V299"])
    p8 = FL.cand_params(C["C3B-P"])
    glut = ST.glut(C["V299"].rows)
    out = dict(mirror_sha=sha, mirror_src=str(REV_H1.relative_to(KIT)).replace("\\", "/"))
    for nm, N, tg, seed in (("random", n_rand, False, 2991), ("targeted", n_targ, True, 2992)):
        sp, r26, v, tq, ramp, th, I8 = _val_cases(N, seed, tg)
        Ep, frzV, G = _fast_freeze(FL, pV, glut, sp, r26, v, tq, ramp, th, I8)
        _, frz8, _ = _fast_freeze(FL, p8, glut, sp, r26, v, tq, ramp, th, I8)
        m2 = np.zeros(N, bool)
        m1 = np.zeros(N, bool)
        epm = np.zeros(N, np.int64)
        for i in range(N):
            a = (int(sp[i]), int(r26[i]), int(ramp[i]), 1, 0, int(v[i]), min(abs(int(tq[i])), 0xFFFF), int(th[i]),
                 int(I8[i]), int(G[i]))
            ex, r16, _, _ = mir(*a)
            m2[i] = ex == FRZ
            epm[i] = r16
            m1[i] = mir(*a, caps=((1382, 4096), (None, None)))[0] == FRZ
        out[nm] = dict(n=int(N), mismatch=int(np.sum(frzV != m2)), ep_mismatch=int(np.sum(Ep != epm)),
                       n_frz=int(m2.sum()), n_run=int((~m2).sum()),
                       neg_rev1caps=int(np.sum(frzV != m1)), neg_v298=int(np.sum(frz8 != m2)))
    r, g = out["random"], out["targeted"]
    out["pass"] = (r["mismatch"] == 0 and g["mismatch"] == 0 and r["ep_mismatch"] == 0 and g["ep_mismatch"] == 0
                   and g["neg_rev1caps"] > 0 and (r["neg_v298"] + g["neg_v298"]) > 0)
    out["wall_s"] = time.time() - t0
    return out


# =====================================================================================================================
# A. ATTRIBUTION + the fork cache
# =====================================================================================================================
def route_tag(prefix):
    """the drive read's cache tag of a route: r<counter>_<hash6>_al (angle_loop_drive_read.load_route's formula; the
    counter alone is REUSED across drives, the hash is not)."""
    ctr = prefix.split("_")[1].split("--")[0].lstrip("0") or "0"
    return "r%s_%s_al" % (ctr, prefix.split("--")[1][:6])


def fork_cache_path(prefix, cache_dir):
    """THE fork-cache naming function, shared by this read (the lookup) and r79_extract_fork.py (the write: its
    default_out() calls this, and this read passes it as --out): <cache>/<route_tag(prefix)>_fork.npz, named from the
    route PREFIX, never from the wire cache's tag (a legacy tag such as r71b_v294 names the same route)."""
    return Path(cache_dir) / (route_tag(prefix) + "_fork.npz")


def fork_cache(W, FR, run_extractor=True):
    """-> (npz, meta, path) for THIS route's fork-side cache, or (None, reason, None).  The cache's own meta route
    must equal the wire's prefix (counters are reused).  The extractor runs ONLY when no cache file exists (never when
    one does, whatever it holds), writing to fork_cache_path(prefix) -- the path looked up here."""
    meta = W.get("meta") or {}
    prefix = meta.get("prefix")
    if meta.get("source") != "route" or not prefix:
        return None, "not a route (synthetic wire)", None
    main = fork_cache_path(prefix, FR.CACHE)
    cands = [main] + ([Path(FR.CACHE) / "r79_fork.npz"] if prefix == R79_PREFIX else [])   # the panel's legacy name
    seen = []
    for p in cands:
        if p.exists():
            Z = np.load(p, allow_pickle=False)
            m = json.loads(str(Z["meta_json"]))
            if m.get("route") == prefix:
                return Z, m, p
            seen.append("%s holds route %s" % (p.name, m.get("route")))
    if seen:
        return None, "fork cache present but for another route (%s); not re-extracted" % "; ".join(seen), None
    if not run_extractor:
        return None, "no fork cache %s" % main.name, None
    t0 = time.time()
    r = subprocess.run([sys.executable, str(EXTRACTOR), "--route", prefix, "--out", str(main)], capture_output=True,
                       text=True)
    meta["fork_extract_s"] = time.time() - t0
    if r.returncode != 0 or not main.exists():
        return None, "extractor failed (%s): %s" % (r.returncode, (r.stderr or r.stdout)[-300:]), None
    Z = np.load(main, allow_pickle=False)
    m = json.loads(str(Z["meta_json"]))
    if m.get("route") != prefix:
        return None, "the extractor wrote %s for route %s" % (main.name, m.get("route")), None
    return Z, m, main


def fw_family(fw_list):
    """spec F9: `39990-TVA,A16` + one capital letter (A16A V298, A16B V299; `39990-TVA,A160` = V294/V295 excluded)."""
    import re
    for s in fw_list:
        m = re.search(r"39990-TVA,(A16[A-Z])", s)
        if m:
            return m.group(1)
    for s in fw_list:
        m = re.search(r"39990-TVA[,-](A\d\d\w)", s)
        if m:
            return m.group(1)
    return None


IMAGE_OF = {"A16A": "V298", "A16B": "V299"}
V299_PARAMS = ("AccordAngleBarFromEps", "AccordAngleMaxRate", "AccordAngleClipScale")


def attribution(W, S, FK, fkmeta):
    a = S.get("attrib") or {}
    letter = fw_family(a.get("eps_fw") or [])
    params = dict((W.get("meta") or {}).get("params") or {})
    if FK is not None and not any(k in params for k in V299_PARAMS):
        try:
            params.update(json.loads(str(FK["initdata_params_json"]))["params"])
        except Exception:
            pass
    out = dict(fw_letter=letter, image=IMAGE_OF.get(letter, "unknown"),
               params={k: params.get(k) for k in V299_PARAMS}, angle_loop=params.get("AccordEpsAngleLoop"),
               git=(a.get("git") or {}).get("commit"))
    if FK is None:
        out.update(fork_cache=None, fork_reason=fkmeta, status=None)
        return out
    out.update(fork_cache=True, fork_commit=fkmeta.get("fork_commit_full", fkmeta.get("fork_commit")),
               fork_schema=fkmeta.get("schema"), has_status_field=bool(fkmeta.get("has_accordAngleStatus")))
    lat = _lat_on_cs(FK)
    n_lat = int(lat.sum())
    if "spcs_angstat" in FK.files and len(FK["spcs_angstat"]):
        st = _status_on_cs(FK).astype(np.int64)
        m = lat & (st >= 0)
        out["status"] = dict(n_lat=int(m.sum()), **{STATUS_BITS[b]: float(np.mean((st[m] & b) > 0)) if m.any() else
                                                    np.nan for b in STATUS_BITS},
                             reserved_frames=int(np.sum(m & ((st & STATUS_RESERVED) != 0))),
                             spec_bit8_frames=int(np.sum(m & ((st & 8) != 0))))
        present = float(m.sum() / n_lat) if n_lat else np.nan
    else:
        out["status"] = None
        present = 0.0 if n_lat else np.nan                  # the schema lacks the field: absent on every frame
    # F1: accordAngleStatus PRESENT on >= 99 % of latActive carState rows (a starpilotCarState row within 5 ms)
    out["status_present"] = present
    out["status_n_lat"] = n_lat
    return out


def _lat_on_cs(FK):
    """carControl.latActive ZOH'd onto the carState rows."""
    j = np.clip(np.searchsorted(FK["t_cc"], FK["t_cs"], side="right") - 1, 0, len(FK["t_cc"]) - 1)
    return FK["cc_latActive"][j].astype(bool)


def _status_on_cs(FK):
    """accordAngleStatus per carState row: the starpilotCarState row nearest in time (card publishes both per loop);
    -1 where none lies within 5 ms."""
    ts, tc, st = FK["t_spcs"], FK["t_cs"], FK["spcs_angstat"].astype(np.int64)
    j = np.clip(np.searchsorted(ts, tc), 1, len(ts) - 1)
    j = np.where(np.abs(ts[j - 1] - tc) <= np.abs(ts[j] - tc), j - 1, j)
    return np.where(np.abs(ts[j] - tc) <= 0.005, st[j], -1)


def o1_check(FK, params):
    """co_ang vs the fork's _update_angle limiter reconstructed WITHOUT the override (m4_common.limiter_reconstruct
    with OVR_ON = inf); F1's 'no O1-like setpoint snap'.  NOT TESTABLE when MaxRate / ClipScale are not config A's."""
    mr, cs = params.get("AccordAngleMaxRate"), params.get("AccordAngleClipScale")
    try:
        if (mr is not None and abs(float(mr) - 120.0) > 1e-6) or (cs is not None and abs(float(cs) - 1.0) > 1e-6):
            return dict(testable=False, why="MaxRate %s / ClipScale %s are not config A's (120 / 1.0)" % (mr, cs))
    except ValueError:
        return dict(testable=False, why="unreadable MaxRate / ClipScale %r / %r" % (mr, cs))
    with contextlib.redirect_stdout(io.StringIO()):
        import m4_common as C4
    keys = ("t_co", "t_cc", "cc_latActive", "cc_ang", "cs_ang", "cs_rate", "cs_tq", "cs_vegoraw", "co_ang",
            "carparams_json")
    F = {k: FK[k] for k in keys}
    on = C4.OVR_ON
    try:
        C4.OVR_ON = float("inf")
        L = C4.limiter_reconstruct(F)
    finally:
        C4.OVR_ON = on
    lat = L["lat"]
    res = np.abs(L["res"])
    n = int(lat.sum())
    if n == 0:
        return dict(testable=False, why="no latActive frame")
    match = float(np.mean(res[lat] <= 0.01))
    snaps = runs(lat & (res > 0.5), 1)
    L2 = C4.limiter_reconstruct(F)                            # CONTROL: the V298 fork's limiter, WITH the O1 override
    m2 = float(np.mean(np.abs(L2["res"])[L2["lat"]] <= 0.01)) if L2["lat"].any() else np.nan
    return dict(testable=True, n_lat=n, match=match, match_with_o1=m2, n_snap_runs=int(len(snaps)),
                snap_s=float(sum(b - a for a, b in snaps) / FS), passed=match >= THR2["f1_o1_match"])


def _zoh_idx(t_src, t_dst):
    j = np.searchsorted(t_src, t_dst, side="right") - 1
    return np.clip(j, 0, max(len(t_src) - 1, 0)), j >= 0


def o1_snaps(FK, params):
    """F1's O1-like SETPOINT SNAP, the spec's own definition (rev 3 §7.2 F1): |d theta_sp| > 1.2 deg in ONE frame
    TOWARD the wheel, outside the first frame and the latActive rising edge.  theta_sp = carOutput's setpoint (co_ang,
    the limiter's output the fork packed into 0xE4), theta = carState.steeringAngleDeg of the same frame, latActive =
    carControl's (ZOH).  A step counts only when BOTH its frames are latActive (so the rising edge and the first frame
    never count); "toward the wheel" = sign(d theta_sp) == sign(theta - theta_sp) at the step's start; "one frame" =
    the allowance scales with the 10-ms frames the step spans (a dropped log row is not a snap).  The allowance is the
    LITERAL 1.2 deg/frame on every config (orchestrator ruling 2026-10-02 -- NOT AccordAngleMaxRate / 100).  Each snap
    is tagged CLIP-BOUND when the fork's error clip bound that frame (status bit 16 when published, else |co - theta|
    at the error-clip table, values.py ANGLE_ERROR_MAX_*): the V299 fork KEEPS that clip, and it drags the setpoint
    faster than 1.2 deg/frame behind a wheel the hand turns fast, by design.  By the same ruling a clip-bound step is
    NOT an override snap: only the non-clip-bound count fails F1 (f1_snap_clause); both counts are printed."""
    t = np.asarray(FK["t_co"], float)
    if len(t) < 3:
        return dict(testable=False, why="no carOutput rows")
    co = np.asarray(FK["co_ang"], float)
    jc, okc = _zoh_idx(FK["t_cc"], t)
    lat = FK["cc_latActive"][jc].astype(bool) & okc
    js, oks = _zoh_idx(FK["t_cs"], t)
    th = np.asarray(FK["cs_ang"], float)[js]
    vk = "cs_vegoraw" if "cs_vegoraw" in FK.files else "cs_vego"
    v = np.asarray(FK[vk], float)[js]
    try:
        mr = float(params.get("AccordAngleMaxRate")) if params.get("AccordAngleMaxRate") is not None else 120.0
    except ValueError:
        mr = 120.0
    try:
        cscale = float(params.get("AccordAngleClipScale")) if params.get("AccordAngleClipScale") is not None else 1.0
    except ValueError:
        cscale = 1.0
    cap = THR2["f1_snap"]                                       # the literal 1.2 deg/frame (ruling), whatever MaxRate
    d = np.diff(co)
    nfr = np.maximum(1.0, np.rint(np.diff(t) / 0.01))
    both = lat[1:] & lat[:-1] & oks[1:] & oks[:-1]
    gap0 = th[:-1] - co[:-1]
    toward = (np.sign(d) == np.sign(gap0)) & (gap0 != 0)
    big = np.abs(d) > cap * nfr + THR2["f1_snap_tol"]
    snap = both & toward & big
    # clip-bound tag on the step's END frame
    vv = np.where(np.asarray(ERR_MAX_BP) <= 11.75, cscale, 1.0)
    emax = np.interp(v, ERR_MAX_BP, np.asarray(ERR_MAX_V) * vv)
    clip_rec = np.abs(co - th) >= emax - 0.05
    src = "reconstructed (|co - theta| at the fork's error clip)"
    clip = clip_rec
    if "spcs_angstat" in FK.files and len(FK["spcs_angstat"]):
        ts = np.asarray(FK["t_spcs"], float)
        j = np.clip(np.searchsorted(ts, t), 1, len(ts) - 1)
        j = np.where(np.abs(ts[j - 1] - t) <= np.abs(ts[j] - t), j - 1, j)
        st = np.where(np.abs(ts[j] - t) <= 0.005, FK["spcs_angstat"].astype(np.int64)[j], -1)
        clip = np.where(st >= 0, (st & STATUS_CLIP) > 0, clip_rec)
        src = "status bit 16 (reconstruction where no status row)"
    sc = snap & clip[1:]
    k = np.flatnonzero(snap)
    ev = [(float(t[i + 1] - t[0]), float(d[i]), float(gap0[i]), float(v[i + 1]), bool(clip[i + 1])) for i in k[:8]]
    return dict(testable=bool(both.any()), why="" if both.any() else "no latActive step", cap=cap, n_steps=int(both.sum()),
                n_snap=int(snap.sum()), n_snap_clip=int(sc.sum()), n_snap_noclip=int((snap & ~clip[1:]).sum()),
                max_toward=float(np.max(np.abs(d)[both & toward] / nfr[both & toward])) if (both & toward).any() else 0.0,
                clip_src=src, events=ev, max_rate_param=mr)


def f1_snap_clause(SN):
    """F1's O1-like snap clause under the orchestrator's ruling (2026-10-02): only NON-clip-bound steps > 1.2 deg /
    frame toward the wheel count (a clip-bound step = the fork's error clip dragging the setpoint behind a hand that
    turns faster than the rate cap, by design); the allowance is the literal 1.2 deg/frame on every config.  Both counts
    are printed.  -> (status, text)."""
    if not SN.get("testable"):
        return "NOT TESTABLE", "O1-snap check: %s" % SN.get("why")
    txt = ("O1-like snaps (|d theta_sp| > %.1f deg / frame toward the wheel, both frames latActive): %d NOT clip-bound "
           "(counted) + %d clip-bound (not counted, ruling) of %d steps" % (SN["cap"], SN["n_snap_noclip"],
                                                                          SN["n_snap_clip"], SN["n_steps"]))
    return ("FAIL" if SN["n_snap_noclip"] else "PASS"), txt


# =====================================================================================================================
# B. RULE IDENTITY (F1)
# =====================================================================================================================
def rule_identity(D, W, S):
    ST = D.load_score_time()
    C = D.replay_cands(ST)
    if "V299" not in C:
        return dict(ok=False, why="the drive read has no V299 candidate (drive_read_fastlane.v299_cand missing)")
    si = S.get("struct_inputs") or D.struct_inputs(W)
    ramp = tuple(int(x) for x in si["ramp"])
    ql = int(si["q_lead"])
    th, cmd, tq, x, abe, vws = D.wire_inputs(W)
    if ql:
        tq = np.r_[tq[ql:], np.repeat(tq[-1:], ql)]
    tag = "" if (ramp == (33, 16) and not ql) else "r%d_%d_q%d" % (ramp[0], ramp[1], ql)
    eng = np.asarray(W["eng"], bool)
    rep = {}
    for nm in ("C3B-P", "V299"):
        job = D._cand_job(ST, C[nm], th, cmd, tq, x, abe, vws, eng, ramp_steps=ramp, tag=tag)
        if job is None:
            return dict(ok=False, why="fast lane off (source drift): the V299 rule exists only in the fast lane")
        T, I = D._cached(*job)
        rep[nm] = dict(T=np.asarray(T, np.int64), I=np.asarray(I, np.int64), p=FL_params(C[nm]))
    n = len(W["t"])
    # hands-off (spec rev 3 §7.1) settled frames: the pooled score AND the windows use them
    base = handsoff_v3(W) & (W["tse"] >= D.THR["settle_s"])
    sc = {nm: score_replay_mask(W, r["T"], base) for nm, r in rep.items()}
    # windows: 30-s chunks of the settled runs (d1_r79 section D); scored when >= 200 HANDS-OFF tap frames
    settled = W["eng"] & (W["tse"] >= D.THR["settle_s"])
    wid = np.full(n, -1, np.int64)
    k = 0
    for a, b in runs(settled, 1):
        for s0 in range(a, b - THR2["win_frames"] + 1, THR2["win_frames"]):
            wid[s0:s0 + THR2["win_frames"]] = k
            k += 1
    w_lp = signal.filtfilt(*signal.butter(2, 8.0 / 50.0), np.nan_to_num(W["w18"]))
    alpha = np.gradient(w_lp) * FS
    nopress = ~(np.nan_to_num(W["pressed"]) > 0.5)
    hard = settled & nopress & ((np.abs(w_lp) >= THR2["man_w"]) | (np.abs(alpha) >= THR2["man_a"]))
    tt = W["T_t"]
    Y = {}
    for nm in rep:
        L = sc[nm].get("lag", 0) or 0
        jj = np.clip(np.searchsorted(W["t"], tt - L * 0.01, side="right") - 1, 0, n - 1)
        m = base[jj] & np.isfinite(W["T"])
        T = rep[nm]["T"][jj]
        yh = np.sign(T) * (np.abs(T) >> 3)
        Y[nm] = (jj, m, yh)
    rows = []
    for w in range(k):
        r2 = {}
        for nm, (jj, m, yh) in Y.items():
            q = m & (wid[jj] == w)
            if q.sum() < THR2["f1_win_taps"]:
                break
            y = W["T"][q] / 8.0
            ss = float(np.sum((y - y.mean()) ** 2))
            if ss <= 0:
                break
            r2[nm] = 1.0 - float(np.sum((y - yh[q]) ** 2)) / ss
        if len(r2) == 2:
            rows.append((w, r2["C3B-P"], r2["V299"], int(np.sum(hard & (wid == w))) >= THR2["man_frames"]))
    R = np.array([[r[1], r[2]] for r in rows]) if rows else np.zeros((0, 2))
    man = np.array([r[3] for r in rows], bool) if rows else np.zeros(0, bool)
    d = R[:, 1] - R[:, 0] if len(R) else np.zeros(0)                # + = V299 fits better
    pooled = (sc["V299"].get("r2", np.nan) - sc["C3B-P"].get("r2", np.nan))
    nw = int(len(d))
    w99, w98 = int(np.sum(d > 0)), int(np.sum(d < 0))
    F = f1_decide(pooled, w99, w98, nw, sc["V299"].get("r2", np.nan), sc["C3B-P"].get("r2", np.nan))
    diff = float(np.mean(rep["V299"]["T"][W["eng"]] != rep["C3B-P"]["T"][W["eng"]])) if W["eng"].any() else np.nan
    return dict(ok=True, ramp=list(ramp), q_lead=ql, tag=tag, pooled=dict(V298=sc["C3B-P"], V299=sc["V299"]),
                dR2_pooled=float(pooled), n_win=nw, n_man=int(man.sum()),
                wins_V299=w99, wins_V298=w98,
                man_wins_V299=int(np.sum(d[man] > 0)), man_wins_V298=int(np.sum(d[man] < 0)),
                d_p10=float(np.percentile(d, 10)) if len(d) else np.nan,
                d_p50=float(np.median(d)) if len(d) else np.nan,
                d_p90=float(np.percentile(d, 90)) if len(d) else np.nan,
                frames_differ=diff, _rep=rep, **F)


def f1_decide(pooled, w99, w98, nw, r2_99, r2_98):
    """the identity arithmetic (spec rev 3 §7.2 F1 + the ratified fit floor), from the pooled dR2 (V299 - V298), the
    window wins and each replay's pooled R2.  v299_beats = the card's literal clause (pooled dR2 >= +0.05 AND V299 wins
    >= 2/3 of the windows), decided BEFORE the fit floor; fit_ok = the winning (best) replay's pooled R2 >= 0.5."""
    need = THR2["f1_win_frac"] * nw
    v99 = bool(nw > 0 and np.isfinite(pooled) and pooled >= THR2["f1_dr2"] and w99 >= need - 1e-9)
    v98 = bool(nw > 0 and np.isfinite(pooled) and -pooled >= THR2["f1_dr2"] and w98 >= need - 1e-9)
    v299_beats = v99
    best = np.nanmax([r2_99, r2_98]) if np.isfinite([r2_99, r2_98]).any() else np.nan
    fit_ok = bool(np.isfinite(best) and best >= THR2["f1_fit_floor"])
    if not fit_ok:
        v99 = v98 = False                                       # neither rule's replay explains this tap
    ran = "V299" if v99 else ("V298" if v98 else ("undecided" if fit_ok else "neither fits"))
    return dict(need_wins=float(need), ran=ran, v299_wins=v99, v298_wins=v98, fit_ok=fit_ok, best_r2=float(best),
                v299_beats=v299_beats, v299_r2=float(r2_99))


def f1_replay_clause(RI):
    """F1's replay clause, in the ORCHESTRATOR'S ORDER (ruling 2026-10-02; the fit floor RATIFIED):
      (a) V299 does not beat V298 (pooled dR2 < +0.05, or V299 wins < 2/3 of the 30-s hands-off windows) -> FAIL;
      (b) else the winning (V299) replay's pooled R2 < 0.5 -> the replay clause is NOT TESTABLE (a loud note);
      (c) else the replay clause passes.
    No scored window at all -> NOT TESTABLE.  -> (status 'FAIL' | 'NOT TESTABLE' | 'PASS', text)."""
    if not RI.get("ok"):
        return "NOT TESTABLE", "rule identity: %s" % RI.get("why")
    if RI["n_win"] == 0:
        return "NOT TESTABLE", "no 30-s hands-off window with >= 200 tap frames"
    if not RI["v299_beats"]:
        return "FAIL", ("the V299-rule replay does not beat V298's (pooled dR2 %+.3f vs >= +0.05; V299 wins %d of %d "
                        "windows vs >= %.1f)" % (RI["dR2_pooled"], RI["wins_V299"], RI["n_win"], RI["need_wins"]))
    if not RI["fit_ok"]:
        return "NOT TESTABLE", ("!!! LOUD: the V299-rule replay BEATS V298's, but explains the tap poorly (V299 pooled R2 "
                                "%.3f < the ratified fit floor %.1f) -- the replay clause is NOT TESTABLE; do not read "
                                "the identity as V299 !!!" % (RI.get("v299_r2", np.nan), THR2["f1_fit_floor"]))
    return "PASS", "V299 replay beats V298's (pooled dR2 %+.3f, %d of %d windows) and fits (R2 %.3f)" % (
        RI["dR2_pooled"], RI["wins_V299"], RI["n_win"], RI.get("v299_r2", np.nan))


def score_replay_mask(W, T100, base):
    """angle_loop_drive_read._score_replay with the frame mask passed in (the spec rev 3 §7.1 hands-off frames instead
    of the reader's |bar| < 500): R2 of the 0x1AB tap vs the replay at its best lag in -2..8 frames."""
    tt = W["T_t"]
    n = len(W["t"])
    best = None
    for L in range(-2, 9):
        j = np.searchsorted(W["t"], tt - L * 0.01, side="right") - 1
        ok = (j >= 0) & (j < n)
        jj = np.clip(j, 0, n - 1)
        m = ok & base[jj] & np.isfinite(W["T"])
        if m.sum() < 100:
            continue
        y = W["T"][m] / 8.0
        yh = np.sign(T100[jj[m]]) * (np.abs(T100[jj[m]]).astype(np.int64) >> 3)
        ss = np.sum((y - y.mean()) ** 2)
        r2 = 1 - np.sum((y - yh) ** 2) / ss if ss > 0 else np.nan
        row = dict(lag=L, r2=float(r2), n=int(m.sum()))
        if best is None or row["r2"] > best["r2"]:
            best = row
    return best or dict(n=0)


POSCTRL_VER = "fix-2026-10-02b"
# the CANONICAL route-79 wire cache (the v280 cache the reader decodes route 79 from).  The positive-control cache is
# keyed on a sha256 of ITS raw 0x1AB bytes (t1ab / b0 / b1) and is written ONLY by a read whose scored tap is that
# file's tap (decoded the reader's way, creep20_loop_id.load): a wire that merely carries route 79's PREFIX (a
# re-synthesised tap, a selftest, a verifier's scratch cache) can never write or overwrite it.
R79_TAG = "r79_a1f5d2_al"
R79_WIRE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280" / (R79_TAG + ".npz")
_R79 = {}


def _tap_sha(T_t, T):
    """sha256 of a SCORED tap in the reader's decoded form: the 0x1AB frame times (float64) and words (float64)."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(T_t, np.float64)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(T, np.float64)).tobytes())
    return h.hexdigest()


def r79_identity(D=None, tap=False):
    """-> dict(wire_sha = sha256 over the canonical r79 cache's raw t1ab / b0 / b1 bytes [+ with tap=True: tap_sha =
    _tap_sha of that file's tap decoded exactly as creep20_loop_id.load decodes it (dejittered t1ab; 8 * s10 of
    b0 & 3 : b1) -- computed only when a route-79-prefixed wire asks, it costs a dejitter]).  Read from R79_WIRE by
    its fixed path, never from FR.CACHE / C20.CACHE (which a caller may have repointed)."""
    if "wire_sha" not in _R79 or (tap and "tap_sha" not in _R79):
        with np.load(R79_WIRE) as Z:
            Z = {k: np.asarray(Z[k]) for k in ("t1ab", "b0", "b1")}
        h = hashlib.sha256()
        for k in ("t1ab", "b0", "b1"):
            a = np.ascontiguousarray(Z[k])
            h.update(k.encode() + str(a.dtype).encode() + str(a.shape).encode())
            h.update(a.tobytes())
        _R79["wire_sha"] = h.hexdigest()
        if tap:
            if D is None:
                import angle_loop_drive_read as D
            # memo of the decoded tap's sha, NAMED by the canonical wire's sha (recomputed whenever that file changes)
            mp = D.SCR / "refs" / ("r79_tapsha_%s.json" % _R79["wire_sha"][:16])
            try:
                J = json.loads(mp.read_text())
                if J.get("wire_sha") == _R79["wire_sha"]:
                    _R79["tap_sha"] = J["tap_sha"]
            except (OSError, ValueError, KeyError):
                pass
            if "tap_sha" not in _R79:
                tn = D._c20().dejitter(Z["t1ab"], 0.02, 50)[2]
                fld = ((Z["b0"].astype(int) & 3) << 8) | Z["b1"].astype(int)
                Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
                _R79["tap_sha"] = _tap_sha(tn, Tm)
                try:
                    mp.parent.mkdir(parents=True, exist_ok=True)
                    mp.write_text(json.dumps(dict(wire_sha=_R79["wire_sha"], tap_sha=_R79["tap_sha"])))
                except OSError:
                    pass
    return _R79


def tap_is_r79(W, D=None):
    """True only when the tap this read scores IS the canonical route-79 tap (hash equality, not the prefix)."""
    try:
        return _tap_sha(W["T_t"], W["T"]) == r79_identity(D, tap=True)["tap_sha"]
    except Exception:
        return False


def _posctrl_path(D):
    keys = {k: THR2[k] for k in ("ho_wire", "ho_bar", "ho_pre_s", "f1_dr2", "f1_win_frac", "f1_win_taps", "win_frames",
                                 "f1_fit_floor")}
    keys["r79_wire_sha"] = r79_identity(D)["wire_sha"]
    h = hashlib.sha256((POSCTRL_VER + json.dumps(keys, sort_keys=True)).encode()).hexdigest()[:10]
    return D.SCR / "refs" / ("r79_v299_posctrl_%s.json" % h)


def _posctrl_of(RI):
    return {k: RI.get(k) for k in ("ran", "dR2_pooled", "n_win", "wins_V299", "wins_V298", "d_p50", "need_wins")}


def positive_control(D, W, RI):
    """F1's positive control = what THIS instrument measures on route 79 (V298 must win).  Live when the tap being
    scored IS route 79's real tap (tap_is_r79: a hash of the scored tap == the canonical r79 cache's), and only then
    written to the cache (keyed on the r79 wire sha + the F1 / hands-off thresholds).  Any other wire -- including one
    that carries route 79's PREFIX with another tap -- reads the cache, or computes it once from R79_WIRE itself (the
    loaded tap re-checked against the hash before it is written).  Never writes from a selftest tap."""
    p = _posctrl_path(D)
    meta = W.get("meta") or {}
    if meta.get("prefix") == R79_PREFIX and RI.get("ok"):
        if meta.get("selftest"):
            return dict(_posctrl_of(RI), source="this read (route 79 inputs, a SELFTEST tap: not cached)")
        if tap_is_r79(W, D):
            J = dict(_posctrl_of(RI), source="this read (route 79, the tap hashes to the canonical r79 wire)")
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(J, default=_js))
            except OSError:
                pass
            return J
        note = "; THIS wire carries route 79's prefix but NOT its tap (hash mismatch): not cached, not used"
    else:
        note = ""
    if p.exists():
        try:
            return dict(json.loads(p.read_text()), source="cached read of route 79 (%s)%s" % (p.name, note))
        except ValueError:
            pass
    try:
        FR, C20 = D._fr(), D._c20()
        keep = (FR.CACHE, C20.CACHE)
        FR.CACHE = C20.CACHE = str(R79_WIRE.parent)            # the canonical cache, whatever a caller repointed
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                W79 = D.load_route(R79_TAG)
        finally:
            FR.CACHE, C20.CACHE = keep
        if not tap_is_r79(W79, D):
            return dict(ran=None, source="unavailable (the canonical r79 cache's tap does not hash to itself)%s" % note)
        R = rule_identity(D, W79, {})
        R.pop("_rep", None)
        J = _posctrl_of(R)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(J, source="computed"), default=_js))
        return dict(J, source="computed now on route 79 (cached as %s)%s" % (p.name, note))
    except Exception as e:                                       # informational: never stops the read
        return dict(ran=None, source="unavailable (%s)%s" % (e, note))


def FL_params(c):
    import drive_read_fastlane as FL
    return FL.cand_params(c)


def bound_active(D, W, rep_entry, glut):
    """per frame: the replayed integrator AT its A3 bound at slot 4, s * (I >> 7) >= bound, s = sign(E'), with E'
    and the bound from the slot-4 inputs (gp-0x6a00 = frame k-1's angle, r26 = 16 * th[k-1], gp-0x69ae = cmd[k],
    the speed word of frame k) -- the frame-level reading of the cave's 1 kHz test (BELIEF at the tick)."""
    import drive_read_fastlane as FL
    th, cmd, tq, x, abe, vws = D.wire_inputs(W)
    thp = np.r_[th[:1], th[:-1]]
    E = FL.s32((FL.s16(cmd) << 2) - 16 * thp)
    G = np.asarray(glut, np.int64)[np.clip(vws, 0, 12000)]
    Ep = FL.s32(E * G) >> 8
    bd = FL.arb_bound(rep_entry["p"]["arb"], thp, vws & 0xFFFF, Ep)
    I4 = rep_entry["I"]
    s = np.where(Ep >= 0, I4, -I4)
    act = (s >= bd) & W["eng"] & (rep_entry["T"] != 0)
    # "I at the 6144 bound" (card §4 / spec §6.2): active AND the bound in force is the upper cap level itself
    return dict(active=act, at_cap=act & (bd == THR2["cap_level"]))


# =====================================================================================================================
# C. STUTTER READOUTS + ENRICHMENT
# =====================================================================================================================
def _ep():
    with contextlib.redirect_stdout(io.StringIO()):
        import m4_episodes as EP
    return EP


def stutter(W, dwells=None):
    EP = _ep()
    G = dict(w18=np.nan_to_num(W["w18"]), vego=W["vego"], t=W["t"])
    ss = EP.stall_surge(G, W["eng"])
    pb = EP.per_band(G, ss)
    tr, _ = EP.trains(G, ss)
    spec = {}
    for nm, lo, hi in SYM_BANDS:
        r = EP.rate_spectrum_in_turn(G, W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi))
        spec[nm] = None if r is None else dict(n=r["n"], rms_4_8=r["rms_4_8"], rms_2_10=r["rms_2_10"], fpk=r["fpk"])
    dw = {}
    for nm, v in (dwells or {}).items():
        dw[nm] = v.get("per_min_025") if v.get("scored") else None
    return dict(stall=pb, trains=tr, spec=spec, dwells=dw), ss


def enrichment(W, ss, levels=((300,), (512,), (300, 512), (1229,)), onset_levels=(1229,)):
    """stall-surges per minute of turning within +-0.25 s of a |bar| event vs away from one.  The event at 300 / 512 is
    a CROSSING (both edges; F6, card §4 'at |bar| 300/512 crossings'); at 1229 it is the |w| > 1229 freeze ONSET only
    (the rising edge; F6b, card §4 'within +-0.25 s of |w| > 1229 freeze onsets') -- onset_levels."""
    bar = np.abs(np.nan_to_num(W["bar"]))
    eng = W["eng"]
    turn = ss["turn"]
    R = ss["R"]
    v = W["vego"]
    st = R[:, 0] if len(R) else np.zeros(0, np.int64)
    out = {}
    for lv in levels:
        tog = np.zeros(len(bar), bool)
        for L in lv:
            ab = bar > L
            if L in onset_levels:
                tog |= np.r_[False, ab[1:] & ~ab[:-1]]          # rising edges (onsets) only
            else:
                tog |= np.r_[False, ab[1:] != ab[:-1]]
        tog &= eng & np.r_[False, eng[:-1]]
        near = np.convolve(tog.astype(float), np.ones(THR2["near_frames"]), "same") > 0
        row = {}
        for nm, lo, hi in ENR_BANDS:
            tb = turn & (v >= lo) & (v < hi)
            sel = (v[st] >= lo) & (v[st] < hi)
            sn, sf = (tb & near).sum() / FS, (tb & ~near).sum() / FS
            nn, nf = int(np.sum(sel & near[st])), int(np.sum(sel & ~near[st]))
            rn = 60.0 * nn / sn if sn > 0 else np.nan
            rf = 60.0 * nf / sf if sf > 0 else np.nan
            scored = sn >= THR2["enrich_min_s"] and (nn + nf) >= THR2["enrich_min_n"]
            row[nm] = dict(near_s=float(sn), free_s=float(sf), n_near=nn, n_free=nf, rate_near=rn, rate_free=rf,
                           ratio=(rn / rf if (rf and np.isfinite(rf) and rf > 0) else (np.inf if nn else np.nan)),
                           scored=bool(scored))
        out["|".join(str(L) for L in lv)] = row
    # |w| > 1229 freeze ONSETS (rising edges) on engaged turning frames, per minute of turning (F6b).
    # HANDS-OFF onset (spec rev 3 §7.1, the one hands-off definition): the 0.5 s BEFORE the onset were hands-off frames
    # (|bar| < 300, so |wire| < 300, and unpressed): a twist or a relay from a free wheel, not a hand already on the rim.
    # (carState.steeringPressed cannot separate them: Honda's carstate sets it at |wire| > 1200 = word 1229 with no
    # debounce, so it is true on EVERY such exceedance.)
    ab = bar > 1229
    on = np.r_[False, ab[1:] & ~ab[:-1]] & eng & turn
    idx = np.flatnonzero(on)
    nxt = np.flatnonzero(~ab)
    ends = nxt[np.minimum(np.searchsorted(nxt, idx), max(len(nxt) - 1, 0))] if len(nxt) else idx
    lens = ends - idx
    ho = handsoff_before(W, idx)
    tsec = turn.sum() / FS
    pm = (lambda k: (60.0 * k / tsec) if tsec > 0 else np.nan)
    out["onsets1229"] = dict(n=int(len(idx)), per_min_turn=pm(len(idx)), n_short=int(np.sum(lens < 10)),
                             n_handsoff=int(ho.sum()), per_min_handsoff=pm(int(ho.sum())),
                             n_handsoff_short=int(np.sum(ho & (lens < 10))), turn_s=float(tsec))
    return out


def ref_stutter(D, tag):
    """the same readouts on a reference route, cached (SCR/refs/<tag>_v299stutter.json)."""
    p = D.SCR / "refs" / ("%s_v299stutter.json" % tag)
    if p.exists():
        try:
            J = json.loads(p.read_text())
            if "hard" not in J or J.get("enrich_1229") != "onsets":   # a pre-ALIGN / pre-FIX cache: upgrade once
                Wr = D.load_route(tag, with_extras=False)
                if "hard" not in J:                          # the 1.6-3 Hz readout
                    J["hard"] = hard_turn(Wr)
                if J.get("enrich_1229") != "onsets":         # the 1229 enrichment on ONSETS (rising edges only)
                    J["enrich"] = enrichment(Wr, stutter(Wr)[1])
                    J["enrich_1229"] = "onsets"
                p.write_text(json.dumps(J, default=_js))
                J = json.loads(p.read_text())
            return J
        except ValueError:
            pass
    Wr = D.load_route(tag, with_extras=False)
    J, ss = stutter(Wr, D.symptom_dwells(Wr))
    J["enrich"] = enrichment(Wr, ss)
    J["enrich_1229"] = "onsets"
    J["hard"] = hard_turn(Wr)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(J, default=_js))
    return json.loads(p.read_text())


def hard_turn(W):
    """INFORMATION (ruling ii; spec rev 3 §6.1 item 10): the 1.6-3 Hz hard-turn wheel-rate, m6_goal_scoring.spectral's
    own definition mirrored: per speed band (m6's SB + pooled), engaged runs >= 2 s, w18 minus its run mean,
    band-passed 1.6-3 Hz (2nd-order Butterworth, zero-phase), rms over the FREE (unpressed; m6_common) frames with
    |theta| >= 20 deg; NaN under 1 s of such frames."""
    sos_h = signal.butter(2, (THR2["hard_lo"], THR2["hard_hi"]), btype="bandpass", fs=FS, output="sos")
    free = ~(np.nan_to_num(W["pressed"]) > 0.5) if np.isfinite(W["pressed"]).any() else np.asarray(W["handsoff"])
    out = {}
    for nm, lo, hi in HARD_BANDS:
        me = W["eng"] & (W["vego"] >= lo) & (W["vego"] < hi)
        num, ns = 0.0, 0
        for a, b in runs(me, THR2["hard_run"]):
            w = np.nan_to_num(W["w18"][a:b])
            yb = signal.sosfiltfilt(sos_h, w - w.mean())
            s_ = free[a:b] & (np.abs(W["theta"][a:b]) >= THR2["hard_theta"])
            num += float((yb[s_] ** 2).sum())
            ns += int(s_.sum())
        out[nm] = dict(s=ns / FS, rms=float(np.sqrt(num / ns)) if ns > 100 else np.nan)
    return out


def _js(x):
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.bool_):
        return bool(x)
    return str(x)


# =====================================================================================================================
# D. RELEASES (F3 / F5)
# =====================================================================================================================
def f3_bar(v, straight):
    """F3's bar (spec rev 3 §7.2): 5 deg on a straight (|theta_sp| < 3 across the window, any speed), else 12 at
    5-11 m/s, 9 at 11-15, 8 at >= 15; None (not scored) below 5 m/s off a straight."""
    if straight:
        return THR2["f3_straight_deg"]
    for lo, hi, bar in THR2["f3_bands"]:
        if lo <= v < hi:
            return bar
    return None


def releases(W):
    """spec rev 3 §7.1 RELEASE EDGE: a hand episode = latActive with |wire| > 300 for >= 0.5 s (contiguous); its
    release = the first frame after it with |wire| < 150 (a dip to 150-300 that rises again is the SAME episode); the
    hand side = sign of the mean wire (+left) over the 0.3 s before the release = sign(-bar).  A release whose next
    1.5 s holds |wire| > 300 again is a RE-GRAB: excluded and counted.  A disengage inside the window truncates it: F3
    is scored on >= 0.5 s, F5 only on the full 1.5 s.
      F3 = max over the window of the swing PAST theta_sp AWAY from the hand side, -(theta - theta_sp) * side,
           against f3_bar(speed, straight).
      F5 = (theta_sp - theta) * sign(theta_sp) at release + 1.5 s (toward centre; |theta - theta_sp| when |theta_sp|
           < 1 deg, where 'toward centre' has no sign) > 4 deg at >= 5 m/s, after ANY release."""
    bar = np.nan_to_num(W["bar"])
    wire = np.abs(bar) * THR2["wire_per_bar"]
    eng = np.asarray(W["eng"], bool)
    pressed = np.nan_to_num(W["pressed"]) > 0.5
    th, sp, v = W["theta"], W["theta_sp"], W["vego"]
    n = len(bar)
    hi = eng & (wire > THR2["rel_on"])
    lo_idx = np.flatnonzero(wire < THR2["rel_off"])
    hi_idx = np.flatnonzero(wire > THR2["rel_on"])
    nrel = int(round(THR2["rel_s"] * FS))
    nside = int(round(THR2["rel_side_s"] * FS))
    rows, trunc, regrab, dis = [], 0, 0, 0
    last = -1
    for a, b in runs(hi, int(round(THR2["rel_on_s"] * FS))):
        if b <= last:
            continue                                            # part of the episode already released
        i = np.searchsorted(lo_idx, b)
        if i >= len(lo_idx):
            continue
        r = int(lo_idx[i])                                      # the release edge
        last = r
        if not eng[a:r + 1].all():
            dis += 1                                            # the request dropped before the hand let go
            continue
        # re-grab: |wire| > 300 within the next 1.5 s
        j = np.searchsorted(hi_idx, r)
        if j < len(hi_idx) and hi_idx[j] <= r + nrel:
            regrab += 1
            continue
        c = r
        while c <= min(r + nrel, n - 1) and eng[c]:
            c += 1
        full = c > r + nrel
        if c - r < int(round(THR2["rel_min_s"] * FS)):
            trunc += 1
            continue
        e2 = c - 1
        # hand side (spec rev 3 §7.1): sign of the mean -bar over the episode's LAST 0.3 s, i.e. the 0.3 s ending at the
        # episode's last |wire| > 300 frame before the first |wire| < 150 crossing (the 300 -> 150 decay is not in it)
        eh = int(hi_idx[np.searchsorted(hi_idx, r) - 1]) + 1     # one past the last |wire| > 300 frame before r
        s_h = float(np.sign(np.mean(-bar[max(a, eh - nside):eh]))) or 1.0
        d = th[r:e2 + 1] - sp[r:e2 + 1]
        swing = float(max(0.0, np.max(-d * s_h)))
        straight = bool(np.max(np.abs(sp[r:e2 + 1])) < THR2["f3_straight_sp"])
        vr = float(np.median(v[r:e2 + 1]))
        fb = f3_bar(vr, straight)
        f3 = fb is not None and swing > fb
        k15 = r + nrel
        if full:
            spe = sp[k15]
            gap15 = float((spe - th[k15]) * np.sign(spe)) if abs(spe) >= 1.0 else float(abs(th[k15] - spe))
        else:
            gap15 = np.nan
        f5_scored = full and vr >= THR2["f5_v"]
        f5 = f5_scored and gap15 > THR2["f5_deg"]
        pk = float(np.max(np.abs(bar[a:r])))
        light = pk < THR2["light_word"] and not pressed[a:r].any()
        h0 = max(a, r - 50)
        dh = float(np.median(th[h0:r] - sp[h0:r]))
        kind = ("outward" if dh * np.sign(sp[r - 1]) > 0 else "inward") if abs(sp[r - 1]) >= 1.0 else "straight"
        rows.append(dict(t=float(W["t"][r]), dur=(r - a) / FS, win=(e2 - r) / FS, v=vr, peak_word=pk,
                         gap0=float(th[r] - sp[r]), side_end=(eh - a) / FS,
                         peak_wire=pk * THR2["wire_per_bar"], hand_side=int(s_h), kind=kind, hold_disp=dh,
                         swing=swing, f3_bar=fb, max_abs_err=float(np.max(np.abs(d))), straight=straight,
                         gap15=gap15, f5_scored=bool(f5_scored), light=bool(light), f3=bool(f3), f5=bool(f5)))
    sc5 = [r for r in rows if r["f5_scored"]]
    lur = [r for r in rows if r["kind"] == "outward" and r["light"] and THR2["lurch_vlo"] <= r["v"] < THR2["lurch_vhi"]]
    return dict(n=len(rows), n_trunc=trunc, n_regrab=regrab, n_disengaged=dis,
                n_f3_scored=int(sum(r["f3_bar"] is not None for r in rows)), n_f5_scored=len(sc5),
                f3=any(r["f3"] for r in rows), f5=any(r["f5"] for r in rows),
                n_f3=int(sum(r["f3"] for r in rows)), n_f5=int(sum(r["f5"] for r in rows)),
                swing_max=max([r["swing"] for r in rows], default=np.nan),
                swing_max_scored=max([r["swing"] for r in rows if r["f3_bar"] is not None], default=np.nan),
                gap15_max=max([r["gap15"] for r in sc5], default=np.nan),
                lurch=lurch_sentence(lur),
                rows=sorted(rows, key=lambda r: -r["swing"]))            # every scored release (6D prints each)


def lurch_sentence(lur):
    """the card's release-lurch null sentence: every light OUTWARD release at 5-10 m/s swings <= 6.1 deg -> nominal-like
    (the heavy-member cost did not materialise); 6.5-12 -> the heavy member as predicted (an OBSERVATION; the operator's
    report decides); > 12 -> beyond both members (F3 fires)."""
    if not lur:
        return dict(n=0, max=np.nan, cls="NOT TESTABLE (no light outward release at 5-10 m/s)")
    mx = max(r["swing"] for r in lur)
    if mx <= THR2["lurch_nom"]:
        cls = "NOMINAL-LIKE (every one <= 6.1 deg): the heavy-member cost did not materialise"
    elif mx > THR2["lurch_heavy_hi"]:
        cls = "BEYOND BOTH MEMBERS (> 12 deg): F3 fires"
    elif mx >= THR2["lurch_heavy_lo"]:
        cls = "HEAVY MEMBER as predicted (6.5-12 deg): an observation, the operator's report decides"
    else:
        cls = "BETWEEN THE MEMBERS (6.1-6.5 deg): neither sentence; the operator's report decides"
    return dict(n=len(lur), max=float(mx), cls=cls)


# =====================================================================================================================
# E. F4 TURN-INS
# =====================================================================================================================
_SOS05 = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")


def _lp_runs(x, mask, sos=_SOS05, minlen=60):
    y = np.array(x, float, copy=True)
    for a, b in runs(mask, minlen):
        y[a:b] = signal.sosfiltfilt(sos, np.nan_to_num(x[a:b]))
    return y


def f4_class(size, v0):
    """-> (criterion, bar) for a turn-in of setpoint excursion `size` deg starting at v0 m/s (spec rev 3 §7.2), or
    (None, None) when no F4 clause covers it (> 10 m/s, or < 20 deg)."""
    if size >= THR2["f4a_min"]:
        return ("F4a", THR2["f4a_deg"]) if v0 <= THR2["f4a_vmax"] else (None, None)
    if size >= THR2["f4b_min"]:
        if v0 <= THR2["f4b_vmax"]:
            return "F4b", THR2["f4b_deg"]
        if v0 <= THR2["f4c_vmax"]:
            return "F4c", THR2["f4c_deg"]
    return None, None


def turnins(W):
    """spec rev 3 §7.1 TURN-IN: a hands-off setpoint excursion >= 20 deg that settles (|d theta_sp/dt| < 5 deg/s for
    >= 1 s).  The setpoint's rate is a centred 0.2-s difference (0xE4's 0.1-deg LSB makes a one-frame slope 10 deg/s
    per count, so the 5 deg/s test cannot be read per frame).  Excursion = between two consecutive settled runs in one
    engaged episode: theta_sp_start = the median of the last 0.5 s of the earlier run, theta_sp_final = the median of
    the first 1 s of the later run; a TURN-IN moves away from centre (|final| > |start|), a RETURN (toward centre) is
    printed, not scored.  t90 = the first frame with sign(turn) (theta - start) >= 90 % of the excursion; overshoot =
    max (theta - theta_sp_final) * sign(turn) over the 3 s after it, cut where the later settled run ends (the setpoint
    moves again).  Hands-off (handsoff_v3) on every frame from the turn's start to the window's end.  Speed = v at the
    turn's start; F4a / F4b / F4c by f4_class."""
    eng = np.asarray(W["eng"], bool)
    sp, th, v = W["theta_sp"], W["theta"], W["vego"]
    ho = handsoff_v3(W)
    T = np.abs(np.nan_to_num(W["T100"]))
    n = len(sp)
    h = int(round(THR2["ti_rate_half"] * FS))
    dsp = np.full(n, np.inf)
    if n > 2 * h:
        dsp[h:n - h] = (sp[2 * h:] - sp[:n - 2 * h]) / (2 * h / FS)
    settled = eng & (np.abs(dsp) < THR2["ti_settle_rate"])
    eid = W["eid"]
    S = runs(settled, int(round(THR2["ti_settle_s"] * FS)))
    rows, rets, n_noho = [], [], 0
    nwin = int(round(THR2["ti_win_s"] * FS))
    for (a1, b1), (a2, b2) in zip(S[:-1], S[1:]):
        if eid[a1] != eid[a2] or eid[a1] == 0 or not eng[b1:a2].all():
            continue                                            # a disengage between: not one excursion
        sp0 = float(np.median(sp[max(a1, b1 - 50):b1]))
        spf = float(np.median(sp[a2:min(a2 + 100, b2)]))
        size = abs(spf - sp0)
        if size < THR2["ti_min"]:
            continue
        s = float(np.sign(spf - sp0))
        a0 = int(b1)
        reach = np.flatnonzero(s * (th[a0:b2] - sp0) >= THR2["ti_reach"] * size)
        k90 = a0 + int(reach[0]) if len(reach) else None
        # the overshoot window = the FULL 3 s after theta first reaches 90 % (NOT cut where the setpoint moves again --
        # that is FLAGGED, sp_moved); only a disengage inside it truncates it (flagged, truncated)
        trunc_ = sp_moved = False
        if k90 is not None:
            we = min(k90 + nwin, n)
            off = np.flatnonzero(~eng[k90:we])
            if len(off):
                we = k90 + int(off[0])
            trunc_ = we < k90 + nwin
            sp_moved = bool(we > b2)                            # the later settled run ended inside the window
        else:
            we = b2
        allho = bool(ho[a0:we].all())
        if abs(spf) <= abs(sp0):
            rets.append(dict(t=float(W["t"][a0]), v=float(v[a0]), size=size, start=sp0, final=spf, handsoff=allho,
                             past_centre=(float(max(0.0, np.max(-th[a2:b2] * np.sign(sp0)))) if abs(spf) <= 2.0
                                          else np.nan)))        # the unwind past centre (information)
            continue
        if not allho:
            n_noho += 1
            continue
        crit, bar = f4_class(size, float(v[a0]))
        ovs = float(np.max((th[k90:we] - spf) * s)) if k90 is not None and we > k90 else np.nan
        rows.append(dict(t=float(W["t"][a0]), v=float(v[a0]), size=size, start=sp0, final=spf, crit=crit, bar=bar,
                         ovs=ovs, t90=((k90 - a0) / FS) if k90 is not None else np.nan,
                         wheel_peak=float(np.max(th[a0:we] * s)), tap_peak=float(np.max(T[a0:we])),
                         fire=bool(crit is not None and np.isfinite(ovs) and ovs > bar),
                         reached=k90 is not None, sp_moved=sp_moved, truncated=trunc_))
    out = dict(n=len(rows), n_returns=len(rets), n_not_handsoff=n_noho, rows=sorted(rows, key=lambda r: -np.nan_to_num(
        r["ovs"], nan=-1e9))[:20], returns=rets[:10], n_sp_moved=int(sum(r["sp_moved"] for r in rows)),
               n_truncated=int(sum(r["truncated"] for r in rows)),
               _all=rows)                                       # the FULL list (cap_read's D3 filter); read() pops it
    for c in ("F4a", "F4b", "F4c"):
        rc = [r for r in rows if r["crit"] == c]
        out[c] = dict(n=len(rc), fire=any(r["fire"] for r in rc), n_fire=int(sum(r["fire"] for r in rc)),
                      ovs_max=max([r["ovs"] for r in rc if np.isfinite(r["ovs"])], default=np.nan),
                      n_unreached=int(sum(not r["reached"] for r in rc)))
    return out


# =====================================================================================================================
# F / G. CURVE HOLDS: F10 ring and the cap read
# =====================================================================================================================
VM_DEFAULT = dict(steerRatio=16.33, wheelbase=2.83, centerToFront=1.1037, mass=1623.33, tireStiffnessFront=183657.0,
                  tireStiffnessRear=185617.16)            # route 79's carParams (fallback when no fork cache)


def a_lat_of(W, FK, params):
    """lateral acceleration (m/s^2) the SETPOINT asks for: the fork's carParams bicycle model (opendbc
    vehicle_model: curv = steer / (sR l (1 - sf u^2))), steer = the 0.5 Hz LP of theta_sp, sR = the SteerRatio param
    when set (16.84 on r79) else carParams.  BELIEF (roll, offsets, the tyre model ignored)."""
    cp = dict(VM_DEFAULT)
    if FK is not None:
        try:
            cp.update({k: v for k, v in json.loads(str(FK["carparams_json"])).items() if k in cp})
        except Exception:
            pass
    try:
        sR = float(params.get("SteerRatio")) if params.get("SteerRatio") else cp["steerRatio"]
    except ValueError:
        sR = cp["steerRatio"]
    m, l, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    aR = l - aF
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    sf = m * (cF * aF - cR * aR) / (l ** 2 * cF * cR)
    u = np.maximum(W["vego"], 1.0)
    spl = _lp_runs(W["theta_sp"], W["eng"])
    curv = np.radians(spl) / (sR * l * (1.0 - sf * u ** 2))
    return curv * u ** 2, spl, dict(sR=sR, l=l, sf=sf)


def curve_holds(W, spl, alat, vlo, vhi, athr, min_s):
    settled = W["eng"] & (W["tse"] >= 1.2)
    nopress = ~(np.nan_to_num(W["pressed"]) > 0.5)
    d = np.gradient(spl) * FS
    m = (settled & handsoff_v3(W) & nopress & (W["vego"] >= vlo) & (W["vego"] < vhi) & (np.abs(alat) >= athr)
         & (np.abs(spl) >= 3.0) & (np.abs(d) <= np.maximum(1.0, 0.05 * np.abs(spl))))
    return runs(m, int(min_s * FS))


def f10_ring(W, spl, alat):
    H = curve_holds(W, spl, alat, THR2["f10_vlo"], THR2["f10_vhi"], THR2["f10_alat"], THR2["f10_min_s"])
    sos = signal.butter(2, [THR2["f10_lo"], THR2["f10_hi"]], "bandpass", fs=FS, output="sos")
    e = np.nan_to_num(W["theta"] - W["theta_sp"])
    eng = W["eng"]
    rows = []
    for a, b in H:
        a2, b2 = a, b                                            # extend by <= 2 s inside the engaged run (filter edges)
        while a2 > 0 and eng[a2 - 1] and a - a2 < 200:
            a2 -= 1
        while b2 < len(e) and eng[b2] and b2 - b < 200:
            b2 += 1
        y = signal.sosfiltfilt(sos, e[a2:b2] - np.mean(e[a2:b2]))
        sgn = np.signbit(y)
        zc = np.flatnonzero(sgn[1:] != sgn[:-1]) + 1
        hc = []
        for p, q in zip(zc[:-1], zc[1:]):
            i = p + int(np.argmax(np.abs(y[p:q])))
            if a <= a2 + i < b:
                hc.append(float(np.abs(y[i])))
        hc = np.array(hc)
        big = bool((hc > THR2["f10_half"]).any())
        cyc = runs(hc >= THR2["f10_cyc"], THR2["f10_ncyc"]) if len(hc) else np.zeros((0, 2))
        rows.append(dict(t=float(W["t"][a]), dur=(b - a) / FS, v=float(np.median(W["vego"][a:b])),
                         alat=float(np.median(np.abs(alat[a:b]))), half_max=float(hc.max()) if len(hc) else 0.0,
                         n_half=int(len(hc)), fire=big or len(cyc) > 0))
    return dict(n=len(rows), secs=float(sum(r["dur"] for r in rows)), fire=any(r["fire"] for r in rows),
                rows=rows[:20])


def cap_read(W, spl, alat, cap=None, turnins_=None):
    """the cap's null sentence (card §4 / spec §6.2).  Holds: hands-off curve holds at 8-12.5 m/s with |a_lat| >= 2
    m/s^2 for >= 3 s (curve_holds).  Per hold, over its LAST second: `at` = the share of frames the replayed V299 I
    sits AT the 6144 bound (cap["at_cap"]), `err` = the mean of |theta_sp - theta| low-passed at 0.5 Hz (4th-order,
    zero-phase, per engaged run).  A hold is BOUND when at >= 80 %; BOTH when also err > 3 deg.  Sentence:
      >= 50 % of holds BOTH         -> the car is ms_free-like; 7168 is licensed for RE-SCORING, not for flight (it
                                       flies only if drive 2's 8-10 m/s turn-ins showed < 3 deg overshoot -- printed);
      else >= 50 % BOUND             -> the bound is active but the error is <= 3 deg: 6144 suffices;
      else                           -> the bound is active in < 50 % of the holds: the cap is not the binder.
    Also printed per hold (the D7 readout): the median centre-ward shortfall (theta_sp - theta) * sign(theta_sp)."""
    H = curve_holds(W, spl, alat, THR2["cap_vlo"], THR2["cap_vhi"], THR2["cap_alat"], THR2["cap_min_s"])
    th, sp = W["theta"], W["theta_sp"]
    elp = np.abs(_lp_runs(sp - th, W["eng"]))
    last = int(round(THR2["cap_last_s"] * FS))
    rows = []
    for a, b in H:
        r = dict(t=float(W["t"][a]), dur=(b - a) / FS, v=float(np.median(W["vego"][a:b])),
                 alat=float(np.median(np.abs(alat[a:b]))), sp=float(np.median(np.abs(sp[a:b]))),
                 shortfall=float(np.median((sp[a:b] - th[a:b]) * np.sign(sp[a:b]))),
                 err_last=float(np.mean(elp[b - last:b])))
        if cap is not None:
            r["at_last"] = float(np.mean(cap["at_cap"][b - last:b]))
            r["active_last"] = float(np.mean(cap["active"][b - last:b]))
            r["bound"] = r["at_last"] >= THR2["cap_at"]
            r["both"] = r["bound"] and r["err_last"] > THR2["cap_deg"]
        rows.append(r)
    out = dict(n=len(rows), secs=float(sum(r["dur"] for r in rows)), rows=rows[:20],
               short_p50=float(np.median([r["shortfall"] for r in rows])) if rows else np.nan,
               short_max=float(np.max([r["shortfall"] for r in rows])) if rows else np.nan)
    # D3's 8-10 m/s turn-ins (card §4): the 60-90 deg hands-off turn-ins at 8-10 m/s, from the FULL turn-in list
    # (turnins()['_all'], never the top-20 overshoot cut)
    ti_all = (turnins_ or {}).get("_all")
    if ti_all is None:
        ti_all = (turnins_ or {}).get("rows") or []
    d3 = [r for r in ti_all if THR2["cap_d3_vlo"] <= r["v"] <= THR2["cap_d3_vhi"]
          and THR2["cap_d3_min"] <= r["size"] <= THR2["cap_d3_max"] and np.isfinite(r["ovs"])]
    out["d3_ovs_max"] = max([r["ovs"] for r in d3], default=np.nan)
    out["d3_n"] = len(d3)
    if cap is None:
        out.update(sentence="NOT TESTABLE (no V299 replay)", cls=None)
    elif not rows:
        out.update(sentence="NOT TESTABLE (no hands-off hold at 8-12.5 m/s with |a_lat| >= 2 m/s^2 for >= 3 s)",
                   cls=None)
    else:
        sb = float(np.mean([r["bound"] for r in rows]))
        sbo = float(np.mean([r["both"] for r in rows]))
        out.update(share_bound=sb, share_both=sbo)
        if sbo >= THR2["cap_share"]:
            gate = ("D3's 60-90 deg hands-off turn-ins at 8-10 m/s (full list): max overshoot %s deg over %d (flies only "
                    "if < 3 deg: %s)" % (
                _f(out["d3_ovs_max"]), out["d3_n"], "MET" if out["d3_n"] and out["d3_ovs_max"] < THR2["cap_d3_deg"]
                else "NOT MET" if out["d3_n"] else "NOT TESTABLE"))
            out.update(cls="ms_free", sentence="MS_FREE-LIKE: in %.0f %% of %d holds I sits at the 6144 bound and the "
                       "0.5 Hz error > 3 deg -> 7168 is licensed for RE-SCORING, not for flight; %s" % (
                           100 * sbo, len(rows), gate))
        elif sb >= THR2["cap_share"]:
            out.update(cls="suffices", sentence="6144 SUFFICES: the bound is active in %.0f %% of %d holds but the "
                       "error is <= 3 deg in %.0f %% of them" % (100 * sb, len(rows), 100 * (1 - sbo / sb)))
        else:
            out.update(cls="not_binder", sentence="THE CAP IS NOT THE BINDER: the bound is active in %.0f %% of %d "
                       "holds (< 50 %%); the shortfall belongs to the plant / outer loop" % (100 * sb, len(rows)))
    return out


# =====================================================================================================================
# H. HANDS / AUTHORITY: F7, F7b, F9
# =====================================================================================================================
def hands_authority(W):
    T = np.nan_to_num(W["T100"])                               # tap LSB (T / 8), ZOH of the 50 Hz frames
    bar = np.nan_to_num(W["bar"])
    eng = W["eng"]
    pressed = np.nan_to_num(W["pressed"]) > 0.5
    opp = (T * bar) < 0                                       # the lane opposes the hand (module docstring)
    f7m = eng & pressed & opp & (np.abs(T) >= THR2["f7_frac"] * RAIL_LSB)
    f7r = runs(f7m, int(THR2["f7_t"] * FS) + 1)
    f7bm = eng & ~pressed & (np.abs(bar) > THR2["f7b_wire"] * 1.024) & opp & (np.abs(T) >= THR2["f7b_frac"] * RAIL_LSB)
    f7br = runs(f7bm, int(THR2["f7b_t"] * FS) + 1)
    # F9 on the native 50 Hz tap instants
    j = np.clip(np.searchsorted(W["t"], W["T_t"], side="right") - 1, 0, len(W["t"]) - 1)
    ho = handsoff_v3(W)[j] & np.isfinite(W["T"])                # spec rev 3 §7.1 hands-off frames
    tap = np.abs(W["T"]) / 8.0
    tmax = float(np.max(tap[ho])) if ho.any() else np.nan
    hi = runs(ho & (tap >= THR2["f9_hi"]), int(THR2["f9_t"] * 50) + 1)
    f9 = bool((np.isfinite(tmax) and tmax > THR2["f9_max"]) or len(hi))
    lens = [(b - a) / FS for a, b in runs(f7bm, 1)]
    return dict(f7=bool(len(f7r)), n_f7=int(len(f7r)), f7_longest=float(max([(b - a) / FS for a, b in runs(f7m, 1)],
                                                                               default=0.0)),
                f7b=bool(len(f7br)), n_f7b=int(len(f7br)), f7b_longest=float(max(lens, default=0.0)),
                f7b_events=[(float(W["t"][a]), (b - a) / FS, float(np.median(W["vego"][a:b])),
                             float(np.max(np.abs(bar[a:b])) / 1.024)) for a, b in f7br[:8]],
                f9=f9, tap_max_handsoff=tmax, n_f9_hi=int(len(hi)),
                pressed_known=bool(np.isfinite(W["pressed"]).any()))


# =====================================================================================================================
# I. THE BAR CHECK (F8)
# =====================================================================================================================
def bar_check(W, FR, FK, fw_letter=None):
    if FK is None:
        return dict(testable=False, why="no fork cache")
    if "spcs_angstat" not in FK.files or not len(FK["spcs_angstat"]):
        cs = FK["cs_tqeps"]
        return dict(testable=False, why="accordAngleStatus absent (the fork's schema at this commit predates spec F8)",
                    tqeps_nonzero=float(np.mean(cs != 0)) if len(cs) else np.nan,
                    canvalid=_canvalid(FK, fw_letter))
    Z = np.load(os.path.join(FR.CACHE, W["meta"]["tag"] + ".npz"))
    t1, fld = Z["t1ab"], ((Z["b0"].astype(np.int64) & 3) << 8) | Z["b1"].astype(np.int64)
    Tn = np.where(fld >= 512, -1, 1) * (fld & 511) * 8                     # = 8 * s10 (the kit's tap decode)
    tc, eps = FK["t_cs"], FK["cs_tqeps"].astype(float)
    j = np.searchsorted(t1, tc, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, len(t1) - 1)
    st = _status_on_cs(FK)
    lat = _lat_on_cs(FK)
    have = ok & (st >= 0)
    clear = have & ((st & STATUS_STALE) == 0)                 # "bit 8" = the value 256 (STATUS_BITS)
    eq0 = eps == -Tn[jj]
    eq1 = eps == -Tn[np.clip(jj - 1, 0, len(t1) - 1)]
    mis = clear & ~eq0
    sgn_m = clear & (np.abs(Tn[jj]) >= 8)
    return dict(testable=bool(clear.any()), n_clear=int(clear.sum()),
                mismatch_frac=float(mis.sum() / max(clear.sum(), 1)),
                mismatch_frac_tolerant=float(np.sum(clear & ~eq0 & ~eq1) / max(clear.sum(), 1)),
                bit8_duty_lat=float(np.mean((st[lat & (st >= 0)] & STATUS_STALE) > 0)) if (lat & (st >= 0)).any()
                else np.nan,
                bar_sign_agree=float(np.mean(np.sign(-eps[sgn_m]) == np.sign(Tn[jj][sgn_m]))) if sgn_m.any() else np.nan,
                canvalid=_canvalid(FK, fw_letter))


def angle_mode(FK, fw_letter):
    """F8's 'angle mode': carParams.steerControlType == angle (the fork's) AND the EPS runs an ANGLE firmware (carFw
    family A16A = V298 / A16B = V299).  Both hold for a whole route (carParams and carFw are per route), so in angle
    mode EVERY carState frame counts -- latActive or not.  -> (bool, why)."""
    try:
        sct = json.loads(str(FK["carparams_json"])).get("steerControlType")
    except Exception:
        sct = None
    ok = (str(sct) == "angle") and fw_letter in ("A16A", "A16B")
    return ok, "steerControlType %s, carFw %s" % (sct, fw_letter)


def _canvalid(FK, fw_letter=None):
    """canValid drops for F8: counted on EVERY angle-mode carState frame (angle_mode), not only latActive, from the
    first frame canValid is true (the boot rows before the first valid CAN parse are not drops: every route starts
    with 2-4 of them, r79 / r71); the latActive count is kept as information.  -> dict or None."""
    if "cs_canvalid" not in FK.files:
        return None
    cv = FK["cs_canvalid"].astype(bool)
    lat = _lat_on_cs(FK)
    am, why = angle_mode(FK, fw_letter)
    first = int(np.argmax(cv)) if cv.any() else len(cv)      # boot rows before the first valid CAN parse: not drops
    after = np.arange(len(cv)) >= first
    return dict(angle_mode=bool(am), why=why, n_frames=int(after.sum()) if am else 0, n_boot=first,
                drops=int(np.sum(after & ~cv)) if am else 0, drops_lat=int(np.sum(lat & after & ~cv)))


def _cv_s(c):
    if not c:
        return "n/a (no canValid field)"
    if not c["angle_mode"]:
        return "not angle mode (%s): 0 frames counted; latActive drops %d" % (c["why"], c["drops_lat"])
    return "%d of %d angle-mode frames after the first valid one (%s; %d boot rows before it; latActive %d)" % (
        c["drops"], c["n_frames"], c["why"], c.get("n_boot", 0), c["drops_lat"])


# =====================================================================================================================
# THE WHOLE V299 READ
# =====================================================================================================================
def read(D, W, S, refs=None):
    t0 = time.time()
    tm = {}
    V = {}
    FR = D._fr()
    FK, fkmeta, fkpath = fork_cache(W, FR)
    tm["fork_cache"] = time.time() - t0
    t1 = time.time()
    ST = D.load_score_time()
    C = D.replay_cands(ST)
    import drive_read_fastlane as FL
    V["rule_validation"] = rule_validation(FL, ST, C) if "V299" in C else dict(pass_=False, why="no V299 candidate")
    tm["rule_validation"] = time.time() - t1
    V["attrib"] = attribution(W, S, FK, fkmeta)
    V["attrib"]["fork_cache_path"] = str(fkpath) if fkpath else None
    params = dict(V["attrib"]["params"])
    params.update({k: (W["meta"].get("params") or {}).get(k) for k in ("SteerRatio",)})
    t1 = time.time()
    if FK is not None:
        try:                                                   # INFORMATION: the V298 limiter-reconstruction check
            V["o1"] = o1_check(FK, params)                     # (m4_common was written for route 79's arrays)
        except Exception as e:
            V["o1"] = dict(testable=False, why="the panel's limiter reconstruction failed on this route (%s: %s)" % (
                type(e).__name__, str(e)[:120]))
        V["snap"] = o1_snaps(FK, params)                       # F1's clause, the spec's own definition
    else:
        V["o1"] = dict(testable=False, why="no fork cache")
        V["snap"] = dict(testable=False, why="no fork cache")
    tm["o1"] = time.time() - t1
    t1 = time.time()
    RI = rule_identity(D, W, S)
    rep = RI.pop("_rep", None)
    V["rule_identity"] = RI
    V["posctrl"] = positive_control(D, W, RI)
    tm["rule_identity"] = time.time() - t1
    t1 = time.time()
    st, ss = stutter(W, S.get("dwells"))
    V["stutter"] = st
    V["enrich"] = enrichment(W, ss)
    V["hard"] = hard_turn(W)
    V["refs"] = {}
    for tag in (refs or {}):
        if str((refs[tag] or {}).get("build", "")).startswith("V282"):
            V["refs"][tag] = ref_stutter(D, tag)
    tm["stutter"] = time.time() - t1
    t1 = time.time()
    V["releases"] = releases(W)
    V["turnins"] = turnins(W)
    alat, spl, vm = a_lat_of(W, FK, params)
    V["vm"] = vm
    V["f10"] = f10_ring(W, spl, alat)
    cap = None
    if rep is not None:
        glut = ST.glut(C["V299"].rows)
        cap = bound_active(D, W, rep["V299"], glut)
    V["cap"] = cap_read(W, spl, alat, cap, V["turnins"])
    V["turnins"].pop("_all", None)                           # the full list served cap_read; not in the JSON
    V["hands"] = hands_authority(W)
    V["bar"] = bar_check(W, FR, FK, V["attrib"]["fw_letter"])
    tm["episodes"] = time.time() - t1
    V["verdict"] = verdict(V, S)
    tm["total"] = time.time() - t0
    V["timing"] = tm
    return V


# =====================================================================================================================
# J. THE DRIVE-2 VERDICT
# =====================================================================================================================
def score_f6(st, enrich):
    """F6 (spec rev 3 §7.2): ratchet trains >= 4.7 / min of turning at 5-10 m/s, OR in-turn 4-8 Hz wheel-rate rms
    >= 7.09 deg/s at 5-10 m/s (both = V298 on r79), OR stall-surges within +-0.25 s of |bar| 300/512 crossings >= 2x
    the free rate (0-20 m/s, scored when exposed).  -> (status, measured, note)."""
    tr = (st["trains"].get("5-10") or {}).get("per_min", np.nan)
    tr = np.nan if tr is None else tr
    rms = ((st["spec"].get("5-10") or {}) or {}).get("rms_4_8", np.nan)
    rms = np.nan if rms is None else rms
    u = enrich["300|512"]["0-20"]
    en = u["ratio"] if u["scored"] else np.nan
    vals = [x for x in (tr, rms, en) if np.isfinite(x)]
    if not vals:
        return "NOT TESTABLE", "no 5-10 m/s turning and no scored enrichment", ""
    why = []
    if np.isfinite(tr) and tr >= THR2["f6_trains"]:
        why.append("trains")
    if np.isfinite(rms) and rms >= THR2["f6_rms"]:
        why.append("4-8 Hz rms")
    if np.isfinite(en) and en >= THR2["f6_enrich"]:
        why.append("300|512 enrichment")
    meas = ("trains %s /min of turning at 5-10 m/s; in-turn 4-8 Hz rms %s deg/s at 5-10 m/s; surges near |bar| "
            "300|512 crossings %s x free (%s s near)" % (_f(tr), _f(rms, "%.3f"), _f(en), _f(u["near_s"], "%.0f")))
    notes = ([] if np.isfinite(en) else ["enrichment under-exposed"]) + ([] if np.isfinite(rms) else
                                                                         ["no 5-10 m/s in-turn spectrum"])
    return ("FAIL" if why else "PASS"), meas, "; ".join((["fires on: " + ", ".join(why)] if why else []) + notes)


def verdict(V, S):
    rows = []
    A = V["attrib"]
    RI = V["rule_identity"]
    RV = V["rule_validation"]

    def add(cid, status, measured, bar, note=""):
        rows.append(dict(id=cid, status=status, measured=measured, bar=bar, note=note))

    # ---- F1 (spec rev 3 §7.2): replay identity, carFw, status presence (a fraction), the O1-like snap
    parts, fails, nt = [], [], []
    if not RV.get("pass"):
        nt.append("the V299 rule failed its validation vs cave_rev2")
    if A["fw_letter"] is None:
        nt.append("no carFw")
    elif A["fw_letter"] != "A16B":
        fails.append("carFw %s != A16B" % A["fw_letter"])
    parts.append("carFw %s" % A["fw_letter"])
    if RI.get("ok"):
        parts.append("rule replay pooled dR2 (V299 - V298) %+.3f; 30-s hands-off windows (>= 200 tap frames) V299 wins "
                     "%d / V298 %d of %d (needs >= %.1f)" % (RI["dR2_pooled"], RI["wins_V299"], RI["wins_V298"],
                                                             RI["n_win"], RI["need_wins"]))
    rs, rtxt = f1_replay_clause(RI)                          # order: (a) not beating -> FAIL, (b) fit floor -> NT
    if rs == "FAIL":
        fails.append(rtxt)
    elif rs == "NOT TESTABLE":
        nt.append(rtxt)
    if A.get("fork_cache"):
        pr_ = A.get("status_present")
        parts.append("accordAngleStatus present on %s of %d latActive frames%s" % (
            _f(100 * pr_ if pr_ is not None and np.isfinite(pr_) else np.nan, "%.2f %%"), A.get("status_n_lat", 0),
            "" if A.get("has_status_field") else " (the pinned schema %s lacks the field)" % A.get("fork_schema")))
        if pr_ is None or not np.isfinite(pr_):
            nt.append("no latActive carState frame")
        elif pr_ < THR2["f1_status"]:
            fails.append("accordAngleStatus absent on %.2f %% (> 1 %%) of latActive frames" % (100 * (1 - pr_)))
    else:
        nt.append("no fork cache (%s)" % A.get("fork_reason"))
    SN = V.get("snap") or {}
    ss_, stxt = f1_snap_clause(SN)
    if SN.get("testable"):
        parts.append(stxt)
    if ss_ == "FAIL":
        fails.append("O1-like setpoint snaps (NOT clip-bound): %d" % SN["n_snap_noclip"])
    elif ss_ == "NOT TESTABLE":
        nt.append(stxt)
    st = "FAIL" if fails else ("NOT TESTABLE" if nt else "PASS")
    pc = V.get("posctrl") or {}
    pcs = ("positive control = THIS instrument on route 79 (%s): %s wins, V298 %s / V299 %s of %s windows, pooled dR2 "
           "%s" % (pc.get("source"), pc.get("ran"), pc.get("wins_V298"), pc.get("wins_V299"), pc.get("n_win"),
                   _f(pc.get("dR2_pooled"), "%+.3f"))) if pc.get("ran") else "positive control: %s" % pc.get("source")
    clipnote = ("; %d CLIP-BOUND steps > 1.2 deg/frame toward the wheel are NOT counted (orchestrator ruling "
                "2026-10-02: the V299 fork's error clip drags the setpoint behind a hand turning faster than the rate "
                "cap, by design -- not an override)" % SN["n_snap_clip"]) if SN.get("n_snap_clip") else ""
    add("F1", st, "; ".join(parts), "pooled dR2 >= +0.05 AND V299 wins >= 2/3 of the 30-s hands-off windows (>= 200 tap "
        "frames), then the winning replay's pooled R2 >= 0.5 (else NOT TESTABLE); A16B; accordAngleStatus on >= 99 % of "
        "latActive frames; no NON-clip-bound O1-like snap (> 1.2 deg/frame toward the wheel)",
        "; ".join(fails + nt + ["predicted (BELIEF): " + PRED["F1"], pcs]) + clipnote)
    # ---- F2
    rp = S.get("rp") or {}
    pres = (rp.get("presence") or {}).get("pres_pct", np.nan)
    f7 = (rp.get("strongturn") or {}).get("f7_per100", np.nan)
    eod = rp.get("eng_over_dis") or {}
    r4 = (S.get("r4") or {}).get("fire")
    vals = [pres, f7, eod.get("18-22", np.nan), eod.get("13-17", np.nan)]
    if all(np.isfinite(x) for x in vals) and r4 is not None:
        fail = (pres > THR2["f2_pres"] or f7 > THR2["f2_f7"] or r4 or eod["18-22"] > THR2["f2_1822"]
                or eod["13-17"] > THR2["f2_1317"])
        add("F2", "FAIL" if fail else "PASS", "presence %.2f %%, F7 %.2f /100 s, new 5-30 Hz line %s, 18-22 eng/dis "
            "%.2f, 13-17 %.2f" % (pres, f7, r4, eod["18-22"], eod["13-17"]),
            "presence <= 0.5 %, F7 0, no new line, 18-22 <= 2.5, 13-17 <= 3.5")
    else:
        add("F2", "NOT TESTABLE", "presence %s F7 %s eng/dis %s" % (pres, f7, eod), "", "a stop-band input missing")
    # ---- F3 / F5
    RL = V["releases"]
    cnt = "%d releases (%d re-grabs excluded, %d truncated, %d disengaged first)" % (
        RL["n"], RL["n_regrab"], RL["n_trunc"], RL["n_disengaged"])
    if RL["n_f3_scored"]:
        add("F3", "FAIL" if RL["f3"] else "PASS", "%s; %d scored (>= 5 m/s or a straight); max swing past theta_sp "
            "away from the hand %.1f deg (scored), %.1f (all); firing %d" % (
                cnt, RL["n_f3_scored"], RL["swing_max_scored"], RL["swing_max"], RL["n_f3"]),
            "> 12 deg at 5-11 m/s, > 9 at 11-15, > 8 at >= 15, > 5 on a straight; or a reported lurch",
            "predicted (BELIEF): " + PRED["F3"])
    else:
        add("F3", "NOT TESTABLE", "%s; none at >= 5 m/s or on a straight" % cnt, "", "card D5 / D6 / D8")
    if RL["n_f5_scored"]:
        add("F5", "FAIL" if RL["f5"] else "PASS", "%d releases at >= 5 m/s with the full 1.5 s; max centre-ward gap at "
            "+1.5 s %.1f deg; firing %d" % (RL["n_f5_scored"], RL["gap15_max"], RL["n_f5"]), "gap > 4 deg",
            "predicted (BELIEF): " + PRED["F5"])
    else:
        add("F5", "NOT TESTABLE", "no release at >= 5 m/s with a full 1.5-s window (%s)" % cnt, "", "card D5 / D8")
    # ---- F4a / F4b / F4c (the 15 % clause DELETED)
    TI = V["turnins"]
    for c, rng in (("F4a", ">= 45 deg at <= 10 m/s, > 6 deg"), ("F4b", "20-45 deg at <= 4.5 m/s, > 8.5 deg"),
                   ("F4c", "20-45 deg at 4.5-10 m/s, > 6 deg")):
        X = TI[c]
        if X["n"]:
            add(c, "FAIL" if X["fire"] else "PASS", "%d hands-off turn-ins; max overshoot vs theta_sp_final %s deg%s" % (
                X["n"], _f(X["ovs_max"]), (" (%d never reached 90 %%)" % X["n_unreached"]) if X["n_unreached"] else ""),
                rng, "predicted (BELIEF): " + PRED[c])
        else:
            add(c, "NOT TESTABLE", "no hands-off turn-in in its class (%d turn-ins found, %d not hands-off)" % (
                TI["n"], TI["n_not_handsoff"]), rng, "card D2 / D3")
    # ---- F6 / F6b
    E = V["enrich"]
    s6, m6, n6 = score_f6(V["stutter"], E)
    add("F6", s6, m6, "trains >= 4.7 /min, or 4-8 Hz rms >= 7.09 deg/s (both at 5-10 m/s), or near >= 2x free",
        "; ".join(x for x in (n6, "predicted (BELIEF): " + PRED["F6"]) if x))
    u9 = E["1229"]["0-20"]
    on = E["onsets1229"]
    f6b_en = u9["ratio"] if u9["scored"] else np.nan
    f6b_on = on["per_min_handsoff"]
    if np.isfinite(f6b_on):
        fail = (np.isfinite(f6b_en) and f6b_en >= THR2["f6b_enrich"]) or f6b_on > THR2["f6b_onsets"]
        add("F6b", "FAIL" if fail else "PASS", "HANDS-OFF |w| > 1229 onsets %.1f /min of turning (n %d, %d < 0.1 s; all "
            "onsets %d = %.1f /min); surges near |w| > 1229 ONSETS (rising edges) %s x free" % (
                f6b_on, on["n_handsoff"], on["n_handsoff_short"], on["n"], on["per_min_turn"], _f(f6b_en)),
            "near onsets >= 2x free, or > 20 hands-off onsets /min of turning", "" if np.isfinite(f6b_en) else
            "1229 enrichment under-exposed (%s s near)" % _f(u9["near_s"], "%.0f"))
    else:
        add("F6b", "NOT TESTABLE", "no turning time", "", "")
    # ---- F7 / F7b
    HA = V["hands"]
    if HA["pressed_known"]:
        add("F7", "FAIL" if HA["f7"] else "PASS", "pressed + tap >= 50 %% rail opposing: %d runs > 0.5 s (longest "
            "%.2f s)" % (HA["n_f7"], HA["f7_longest"]), "any > 0.5 s, or 'fights my hands'",
            "predicted (BELIEF): " + PRED["F7"])
    else:
        add("F7", "NOT TESTABLE", "no steeringPressed on this route", "", "")
    add("F7b", "OBSERVATION", "|wire| > 600 + tap >= 40 %% rail opposing, not pressed: %d runs > 0.3 s (longest "
        "%.2f s)" % (HA["n_f7b"], HA["f7b_longest"]), "by ruling an OBSERVATION; R9 (the operator) is the criterion",
        "predicted (BELIEF): " + PRED["F7b"])
    # ---- F8
    B = V["bar"]
    if B.get("testable"):
        fail = (B["mismatch_frac"] > THR2["f8_frac"] or (np.isfinite(B["bit8_duty_lat"]) and B["bit8_duty_lat"] >
                THR2["f8_frac"]) or ((B.get("canvalid") or {}).get("drops") or 0) > 0 or
                (np.isfinite(B["bar_sign_agree"]) and B["bar_sign_agree"] < 1.0))
        add("F8", "FAIL" if fail else "PASS", "cs_tqeps != -8 tap on %.3f %% of %d stale-bit-clear frames (tolerant "
            "%.3f %%); stale bit (256) on %.3f %% of latActive; canValid drops %s; bar sign agree %s" % (
                100 * B["mismatch_frac"], B["n_clear"], 100 * B["mismatch_frac_tolerant"], 100 * B["bit8_duty_lat"],
                _cv_s(B.get("canvalid")), _f(B["bar_sign_agree"], "%.4f")),
            "<= 0.1 %; bit 8 (value 256) <= 0.1 %; 0 canValid drops in angle mode; sign agrees")
    elif ((B.get("canvalid") or {}).get("drops") or 0) > 0:          # a fired clause fails F8 on its own
        add("F8", "FAIL", "canValid drops %s" % _cv_s(B.get("canvalid")), "0 canValid drops in angle mode",
            "the bar-equality clauses are NOT TESTABLE (%s)" % B.get("why", ""))
    else:
        add("F8", "NOT TESTABLE", B.get("why", ""), "", "canValid drops: %s" % _cv_s(B.get("canvalid")))
    # ---- F9
    if np.isfinite(HA["tap_max_handsoff"]):
        add("F9", "FAIL" if HA["f9"] else "PASS", "hands-off tap max %.0f LSB; >= 230 for > 0.3 s: %d" % (
            HA["tap_max_handsoff"], HA["n_f9_hi"]), "> 250, or >= 230 for > 0.3 s", "predicted (BELIEF): " + PRED["F9"])
    else:
        add("F9", "NOT TESTABLE", "no hands-off tap", "", "")
    # ---- F10
    F10 = V["f10"]
    if F10["n"]:
        add("F10", "FAIL" if F10["fire"] else "PASS", "%d holds (%.0f s) at 10-13 m/s, |a_lat| >= 1.5; max 0.4-0.8 Hz "
            "half-peak %.2f deg" % (F10["n"], F10["secs"], max(r["half_max"] for r in F10["rows"])),
            "half-peak > 1 deg or > 2 consecutive half-cycles >= 0.5 deg", "predicted (BELIEF): " + PRED["F10"])
    else:
        add("F10", "NOT TESTABLE", "no >= 3 s hands-off curve hold at 10-13 m/s with |a_lat| >= 1.5", "", "card D7 / D9")
    add("X3", "N/A", "config A (cap 120, clip x1.0)", "a later dose only", "")
    add("R9", "OPERATOR", "the operator's report (grinding, ratcheting, vibration, a lurch, 'fights my hands', anything "
        "new)", "his call; outranks every band", "")
    fails = [r["id"] for r in rows if r["status"] == "FAIL"]
    nts = [r["id"] for r in rows if r["status"] == "NOT TESTABLE"]
    return dict(rows=rows, fails=fails, not_testable=nts,
                headline=("FAIL: %s" % ", ".join(fails)) if fails else
                ("no pre-registered FAIL fired (NOT TESTABLE: %s)" % (", ".join(nts) or "none")))


# =====================================================================================================================
# REPORT
# =====================================================================================================================
def report(V):
    L = []
    P = L.append
    A = V["attrib"]
    RV = V["rule_validation"]
    RI = V["rule_identity"]
    P("")
    P("6. V299 / DRIVE-2 BLOCKS (drive_read_v299.py; criteria: %s §7, %s)" % (SPEC, CARD))
    P("   hands-off frame everywhere below (spec rev 3 §7.1): latActive, |wire| < 300, not pressed, |bar| < 300 for the "
      "preceding 0.5 s (wire = bar / 1.024 = carState.steeringTorque units)")
    P("6A ATTRIBUTION  EPS family %s -> image %s ; V299 fork params %s ; AccordEpsAngleLoop %s" % (
        A["fw_letter"], A["image"], A["params"], A["angle_loop"]))
    if A.get("fork_cache"):
        P("   fork cache %s ; schema pinned to %s (%s) ; accordAngleStatus field in schema: %s" % (
            Path(A["fork_cache_path"]).name, A["fork_commit"], A["fork_schema"], A["has_status_field"]))
        pr_ = A.get("status_present")
        P("   accordAngleStatus PRESENT on %s of %d latActive carState frames [F1 needs >= 99 %%]" % (
            _f(100 * pr_ if pr_ is not None and np.isfinite(pr_) else np.nan, "%.2f %%"), A.get("status_n_lat", 0)))
        s = A.get("status")
        if s:
            P("   decoded (the fork's values: 4 rate/jerk, 16 clip, 256 EPS stale): %s ; reserved bits set on %d frames "
              "(the spec's literal 8 on %d)" % ("  ".join("%s %.2f %%" % (k, 100 * s[k]) for k in STATUS_BITS.values()),
                                               s["reserved_frames"], s["spec_bit8_frames"]))
    else:
        P("   fork cache: none (%s)" % A.get("fork_reason"))
    SN = V.get("snap") or {}
    if SN.get("testable"):
        P("   O1-LIKE SNAPS (F1; |d theta_sp| > %.1f deg in one frame TOWARD the wheel -- the literal allowance on every "
          "config, AccordAngleMaxRate %s -- both frames latActive): %d of %d latActive steps -- %d NOT clip-bound "
          "(COUNTED by F1), %d clip-bound (%s; NOT counted, orchestrator ruling 2026-10-02); largest toward-wheel step "
          "%.2f deg/frame" % (SN["cap"], _f(SN.get("max_rate_param"), "%.0f"), SN["n_snap"], SN["n_steps"],
                              SN["n_snap_noclip"], SN["n_snap_clip"], SN["clip_src"], SN["max_toward"]))
        for e in SN["events"][:4]:
            P("     +%7.1f s  step %+6.2f deg toward a wheel %+6.2f deg away, @ %4.1f m/s%s" % (
                e[0], e[1], e[2], e[3], "  clip-bound" if e[4] else ""))
    else:
        P("   O1-like snaps: NOT TESTABLE (%s)" % SN.get("why"))
    O1 = V["o1"]
    if O1.get("testable"):
        P("   (information) co_ang vs the fork limiter WITHOUT the O1 override: equal (<= 0.01 deg) on %.2f %% of %d "
          "latActive frames, %d runs > 0.5 deg (%.1f s); control, the V298 limiter WITH O1: %.2f %%" % (
              100 * O1["match"], O1["n_lat"], O1["n_snap_runs"], O1["snap_s"], 100 * O1["match_with_o1"]))
    else:
        P("   (information) co_ang vs the no-O1 limiter: NOT TESTABLE (%s)" % O1.get("why"))
    P("6B RULE IDENTITY (F1's instrument; R2 of the tap on HANDS-OFF settled frames)")
    if RV.get("random"):
        r, g = RV["random"], RV["targeted"]
        P("   V299 rule (drive_read_fastlane.v299_cand: static_freeze + arb_bound + the loop's I test) vs the spec mirror"
          " cave_rev2 (%s, sha %s): random %d/%d mismatches (E' %d; %d freezes / %d runs), targeted %d/%d (E' %d) -> %s;"
          " negatives (must be > 0): mirror at rev-1 caps %d, the V298 rule %d (%.2f s)" % (
              RV["mirror_src"], RV["mirror_sha"], r["mismatch"], r["n"], r["ep_mismatch"], r["n_frz"], r["n_run"],
              g["mismatch"], g["n"], g["ep_mismatch"], "PASS" if RV["pass"] else "FAIL", g["neg_rev1caps"],
              r["neg_v298"] + g["neg_v298"], RV["wall_s"]))
    if RI.get("ok"):
        p8, p9 = RI["pooled"]["V298"], RI["pooled"]["V299"]
        P("   replays (arm ramp +%d/-%d, torque word %d frame ahead): pooled R2 vs the tap  V298 rule %.3f (lag %s)  "
          "V299 rule %.3f (lag %s)  -> dR2 (V299 - V298) %+.3f ; lanes differ on %.1f %% of engaged frames" % (
              RI["ramp"][0], RI["ramp"][1], RI["q_lead"], p8.get("r2", np.nan), p8.get("lag"), p9.get("r2", np.nan),
              p9.get("lag"), RI["dR2_pooled"], 100 * RI["frames_differ"]))
        P("   30-s hands-off windows (>= %d hands-off tap frames): %d (V299 wins %d, V298 wins %d; 2/3 = %.1f); dR2 "
          "p10/p50/p90 %+.3f / %+.3f / %+.3f ; (information) of them with >= 2 s manoeuvre %d (V299 %d, V298 %d)" % (
              THR2["f1_win_taps"], RI["n_win"], RI["wins_V299"], RI["wins_V298"], RI["need_wins"], RI["d_p10"],
              RI["d_p50"], RI["d_p90"], RI["n_man"], RI["man_wins_V299"], RI["man_wins_V298"]))
        marg = RI["dR2_pooled"]
        P("   RULE THAT RAN: %s  (F1 on a V299 wire: pooled dR2 >= +0.05 [margin %+.3f] AND V299 wins >= 2/3 of the "
          "windows; on a V298 wire the same test with the roles swapped: margin %+.3f; guard: the winner's pooled R2 "
          ">= %.1f, best here %.3f)" % (RI["ran"], marg - THR2["f1_dr2"], -marg - THR2["f1_dr2"], THR2["f1_fit_floor"],
                                       RI.get("best_r2", np.nan)))
        rs_, rt_ = f1_replay_clause(RI)
        P("   F1 REPLAY CLAUSE (order: not beating V298 -> FAIL; else the winner's R2 < %.1f -> NOT TESTABLE; else PASS): "
          "%s -- %s" % (THR2["f1_fit_floor"], rs_, rt_))
        pc = V.get("posctrl") or {}
        P("   POSITIVE CONTROL (what THIS instrument measures on route 79, %s): %s wins; V298 %s / V299 %s of %s windows; "
          "pooled dR2 %s; dR2 p50 %s" % (pc.get("source"), pc.get("ran"), pc.get("wins_V298"), pc.get("wins_V299"),
                                         pc.get("n_win"), _f(pc.get("dR2_pooled"), "%+.3f"),
                                         _f(pc.get("d_p50"), "%+.3f")))
    else:
        P("   rule identity NOT AVAILABLE: %s" % RI.get("why"))
    P("6C STUTTER READOUTS (the goal's criteria, ruling ii) -- per minute of TURNING time (|0.5 s mean rate| >= 10 deg/s)")
    st = V["stutter"]
    refs = V.get("refs") or {}
    hdr = "   %-34s %s" % ("readout / band", "".join("%-26s" % b for b, _, _ in SYM_BANDS))
    P(hdr)

    def line(name, getter):
        cells = []
        for b, _, _ in SYM_BANDS:
            x = getter(st, b)
            rr = [getter(refs[k], b) for k in refs]
            cells.append("%-26s" % ("%s [%s]" % (_f(x), "/".join(_f(y) for y in rr))))
        P("   %-34s %s" % (name, "".join(cells)))
    line("stall-surges /min [r6c/r39]", lambda d, b: (d["stall"].get(b) or {}).get("per_min"))
    line("ratchet trains /min [r6c/r39]", lambda d, b: (d["trains"].get(b) or {}).get("per_min"))
    line("4-8 Hz rate rms deg/s [r6c/r39]", lambda d, b: ((d["spec"].get(b) or {}) or {}).get("rms_4_8"))
    line("dwells /min @0.25 [r6c/r39]", lambda d, b: d["dwells"].get(b))
    P("   (refs: %s; V282 both)" % ", ".join(refs) if refs else "   (no V282 reference loaded)")
    E = V["enrich"]
    P("   ENRICHMENT: stall-surges /min within +-0.25 s of a |bar| crossing (300 / 512: both edges) or a |w| > 1229 "
      "ONSET (rising edge only, F6b) vs free [near/free = ratio; near s]")
    for lv in ("300", "512", "300|512", "1229"):
        P("     %-8s %s" % (lv + ("on" if lv == "1229" else ""),"  ".join("%s %s/%s=%s (%ss)" % (
            b, _f(E[lv][b]["rate_near"], "%.1f"), _f(E[lv][b]["rate_free"], "%.1f"), _f(E[lv][b]["ratio"]),
            _f(E[lv][b]["near_s"], "%.0f")) + ("" if E[lv][b]["scored"] else "*") for b, _, _ in ENR_BANDS)))
    for k in refs:
        e = (refs[k].get("enrich") or {}).get("300|512", {}).get("0-20")
        if e:
            P("     ref %-6s 300|512 0-20: %s/%s = %s" % (k, _f(e["rate_near"], "%.1f"), _f(e["rate_free"], "%.1f"),
                                                       _f(e["ratio"])))
    o = E["onsets1229"]
    P("   |w| > 1229 freeze onsets on engaged turning frames: %d (%.1f /min of %.0f s turning; %d shorter than 0.1 s); "
      "HANDS-OFF (the 0.5 s before = hands-off frames) %d = %.1f /min (%d short)   [* = under-exposed: < 10 s near or "
      "< 5 events]" % (o["n"], o["per_min_turn"], o["turn_s"], o["n_short"], o["n_handsoff"], o["per_min_handsoff"],
                       o["n_handsoff_short"]))
    H = V.get("hard") or {}
    P("   (information, ruling ii) 1.6-3 Hz HARD-TURN wheel-rate rms, deg/s (m6_goal_scoring's definition: |theta| >= 20,"
      " unpressed) [refs]: %s" % "  ".join("%s %s [%s]" % (b, _f((H.get(b) or {}).get("rms")), "/".join(
          _f(((refs[k].get("hard") or {}).get(b) or {}).get("rms")) for k in refs)) for b, _, _ in HARD_BANDS))
    RL = V["releases"]
    P("6D RELEASES (spec rev 3 §7.1: |wire| > 300 for >= 0.5 s, released at the first |wire| < 150; re-grab within 1.5 s "
      "excluded): %d scored, %d re-grabs excluded, %d truncated, %d disengaged first; F3 scored %d, F5 scored %d" % (
          RL["n"], RL["n_regrab"], RL["n_trunc"], RL["n_disengaged"], RL["n_f3_scored"], RL["n_f5_scored"]))
    for r in RL["rows"]:
        P("   t %7.1f %4.1f s @ %4.1f m/s peak wire %5.0f side %+d %-8s gap@release (theta - theta_sp) %+6.2f ; swing %5.2f "
          "[bar %s] over %.1f s (max|err| %5.2f%s) gap15 %s%s%s%s" % (
              r["t"], r["dur"], r["v"], r["peak_wire"], r["hand_side"], r["kind"], r["gap0"], r["swing"],
              _f(r["f3_bar"], "%.0f"), r["win"], r["max_abs_err"], ", straight" if r["straight"] else "",
              _f(r["gap15"]), " light" if r["light"] else "", " F3" if r["f3"] else "", " F5" if r["f5"] else ""))
    lu = RL["lurch"]
    P("   RELEASE-LURCH NULL SENTENCE (card §4: light outward releases at 5-10 m/s, <= 6.1 nominal / 6.5-12 heavy / > 12 "
      "F3): n %d, max swing %s deg -> %s" % (lu["n"], _f(lu["max"]), lu["cls"]))
    TI = V["turnins"]
    P("6E F4 HANDS-OFF TURN-INS (spec rev 3 §7.1; overshoot vs theta_sp_final in the 3 s after 90 %%): %d scored-class "
      "candidates, %d returns (information), %d excursions not hands-off; window NOT cut at the next setpoint move: "
      "%d had the setpoint move inside it (flagged SP-MOVED), %d truncated by a disengage" % (
          TI["n"], TI["n_returns"], TI["n_not_handsoff"], TI.get("n_sp_moved", 0), TI.get("n_truncated", 0)))
    for r in TI["rows"][:8]:
        P("   t %7.1f @ %4.1f m/s %+6.1f -> %+6.1f deg (%4.1f) %-4s overshoot %s [bar %s] t90 %s wheel %5.1f tap %5.1f%s"
          % (r["t"], r["v"], r["start"], r["final"], r["size"], r["crit"] or "-", _f(r["ovs"]), _f(r["bar"], "%.1f"),
             _f(r["t90"]), r["wheel_peak"], r["tap_peak"], " FIRES" if r["fire"] else "")
          + (" SP-MOVED" if r.get("sp_moved") else "") + (" TRUNCATED" if r.get("truncated") else ""))
    for r in TI["returns"][:4]:
        P("   return t %7.1f @ %4.1f m/s %+6.1f -> %+6.1f deg, unwind past centre %s deg%s" % (
            r["t"], r["v"], r["start"], r["final"], _f(r["past_centre"]), "" if r["handsoff"] else " (hands on)"))
    F10 = V["f10"]
    vm = V["vm"]
    P("6F F10 RING (curve holds 10-13 m/s, |a_lat| >= 1.5 m/s^2 from theta_sp via the carParams model sR %.2f, >= 3 s):"
      " %d holds, %.0f s" % (vm["sR"], F10["n"], F10["secs"]))
    for r in F10["rows"][:6]:
        P("   t %7.1f %4.1f s @ %4.1f m/s a_lat %.2f: 0.4-0.8 Hz half-peaks n %d max %.2f deg%s" % (
            r["t"], r["dur"], r["v"], r["alat"], r["n_half"], r["half_max"], " FIRES" if r["fire"] else ""))
    CP = V["cap"]
    P("6G CAP READ (hands-off curve holds 8-12.5 m/s, |a_lat| >= 2, >= 3 s; the replayed V299 I at the 6144 bound over the"
      " LAST second): %d holds, %.0f s; shortfall p50 %s max %s deg [predicted (BELIEF): %s]" % (
          CP["n"], CP["secs"], _f(CP["short_p50"]), _f(CP["short_max"]), PRED["cap"]))
    for r in CP["rows"][:6]:
        P("   t %7.1f %4.1f s @ %4.1f m/s a_lat %.2f |sp| %5.1f shortfall %5.2f ; last 1 s: at-6144 %s, bound-active %s, "
          "0.5 Hz |err| %5.2f%s" % (r["t"], r["dur"], r["v"], r["alat"], r["sp"], r["shortfall"],
                                   _f(r.get("at_last")), _f(r.get("active_last")), r["err_last"],
                                   "  BOUND+ERR" if r.get("both") else "  BOUND" if r.get("bound") else ""))
    P("   D3 gate input: %d hands-off 60-90 deg turn-ins at 8-10 m/s (full turn-in list), max overshoot %s deg" % (
        CP["d3_n"], _f(CP["d3_ovs_max"])))
    P("   CAP NULL SENTENCE (card §4 / spec §6.2): %s" % CP["sentence"])
    HA = V["hands"]
    P("6H HANDS / AUTHORITY  F7 runs %d (longest %.2f s) ; F7b runs %d (longest %.2f s) %s ; hands-off tap max %s LSB, "
      ">= 230 for > 0.3 s: %d" % (HA["n_f7"], HA["f7_longest"], HA["n_f7b"], HA["f7b_longest"],
                                  [(round(a, 1), round(b, 2), round(c, 1), round(d)) for a, b, c, d in HA["f7b_events"][:4]],
                                  _f(HA["tap_max_handsoff"], "%.0f"), HA["n_f9_hi"]))
    B = V["bar"]
    if B.get("testable"):
        P("6I BAR CHECK  cs_tqeps == -8 tap: mismatch %.3f %% of %d stale-bit-clear frames (vs the previous 0x1AB frame "
          "too: %.3f %%); stale bit (256) on %.3f %% of latActive; canValid drops %s; drawn-bar sign agrees %s" % (
              100 * B["mismatch_frac"], B["n_clear"], 100 * B["mismatch_frac_tolerant"], 100 * B["bit8_duty_lat"],
              _cv_s(B.get("canvalid")), _f(B["bar_sign_agree"], "%.4f")))
    else:
        P("6I BAR CHECK  NOT TESTABLE: %s (cs_tqeps nonzero on %s of frames); canValid drops (every angle-mode frame "
          "after the first valid one): %s" % (B.get("why"), _f(B.get("tqeps_nonzero"), "%.4f"), _cv_s(B.get("canvalid"))))
    VD = V["verdict"]
    P("")
    P("=" * 110)
    P("DRIVE-2 VERDICT (V299 config A; pre-registered: spec rev 3 §7 + the drive card) -- %s" % VD["headline"])
    if A["image"] != "V299":
        P("   NOTE: this route's EPS image is %s (%s), not V299 -- the block below is a CONTROL read (on route 79 F1 "
          "must FAIL: V298's rule wins)" % (A["image"], A["fw_letter"]))
    for r in VD["rows"]:
        P("   %-4s %-12s %s" % (r["id"], r["status"], r["measured"]))
        if r["bar"]:
            P("        %-12s bar: %s" % ("", r["bar"]))
        if r["note"]:
            P("        %-12s %s" % ("", r["note"]))
    rel = V["enrich"]["300|512"]["0-20"]
    P("   NULL SENTENCE, STUTTER (card §4): if F1 passes and surges are not enriched at 300/512 crossings, yet the "
      "operator still reports ratcheting or stutter, the freeze relay was not the mechanism -> stop iterating the integral"
      " policy; next is the small-correction stick (M1).  Now: F1 %s, 300|512 enrichment %s x (%s)." % (
          next(r["status"] for r in VD["rows"] if r["id"] == "F1"), _f(rel["ratio"]),
          "scored" if rel["scored"] else "under-exposed"))
    P("   NULL SENTENCE, CAP (card §4): %s" % CP["sentence"])
    P("   NULL SENTENCE, LURCH (card §4): n %d light outward releases at 5-10 m/s, max %s deg -> %s" % (
        lu["n"], _f(lu["max"]), lu["cls"]))
    P("=" * 110)
    tm = V.get("timing") or {}
    P("V299 blocks %.2f s (fork cache %.2f, rule validation %.2f, rule identity + positive control %.2f, O1 %.2f, "
      "stutter+refs %.2f, episodes %.2f)" % tuple(tm.get(k, 0.0) for k in (
          "total", "fork_cache", "rule_validation", "rule_identity", "o1", "stutter", "episodes")))
    return "\n".join(L)


# =====================================================================================================================
# SYNTHETIC CONTROLS  (python drive_read_v299.py --selftest)
# =====================================================================================================================
def _synth(n, v=8.0, seed=0):
    """a blank synthetic wire, all engaged, hands-off, on the reader's own constructor (make_wire)."""
    import angle_loop_drive_read as D
    t = np.arange(n) / FS
    z = np.zeros(n)
    W = dict(t=t, ang=z.copy(), raw=z.copy(), req=np.ones(n), sca=np.ones(n), bar=z.copy(), wire18=z.copy(),
             vego=np.full(n, v), T_t=np.arange(0, n / FS, 0.02), T=np.zeros(len(np.arange(0, n / FS, 0.02))),
             pressed=z.copy())
    return D, W


def _mk(D, W):
    return D.make_wire(W["t"], W["ang"], W["raw"], W["req"], W["sca"], W["bar"], W["wire18"], W["vego"], W["T_t"],
                       W["T"], pressed=W["pressed"], meta=dict(source="synthetic"))


def _rel_wire(v, sp_deg, bar_runs, th_fn, n=1200):
    """a synthetic release wire: constant setpoint, the bar set over bar_runs [(a, b, word)], theta = th_fn(k)."""
    D, S = _synth(n, v=v)
    k = np.arange(n)
    sp = np.full(n, float(sp_deg))
    bar = np.zeros(n)
    for a, b, wd in bar_runs:
        bar[a:b] = wd
    S.update(raw=-10.0 * sp, ang=th_fn(k, sp), bar=bar)
    return _mk(D, S)


def _turn_wire(turns, n=4000):
    """synthetic turn-ins: each (k0, start, final, ramp_frames, v, bump) = a setpoint ramp from start to final over
    ramp_frames starting at k0, held after; theta follows 30 frames late, plus a bump of `bump` deg (half-sine, 1.2 s)
    starting 40 frames after theta reaches 90 %."""
    D, S = _synth(n, v=6.0)
    k = np.arange(n)
    sp = np.zeros(n)
    vv = np.full(n, 6.0)
    for k0, s0, s1, rf, v, _ in turns:
        sp[k0 - 300:k0] = s0
        sp[k0:k0 + rf] = s0 + (s1 - s0) * (k[k0:k0 + rf] - k0) / rf
        sp[k0 + rf:k0 + rf + 500] = s1
        vv[k0 - 300:k0 + rf + 500] = v
    th = np.r_[np.full(30, sp[0]), sp[:-30]]
    for k0, s0, s1, rf, v, bump in turns:
        a = k0 + rf + 30 + 40
        th[a:a + 120] += np.sign(s1 - s0) * bump * np.sin(np.pi * np.arange(120) / 120.0)
    S.update(raw=-10.0 * sp, ang=th, vego=vv)
    return _mk(D, S)


def selftest():
    t0 = time.time()
    out = []
    P = lambda s: (out.append(s), print(s, flush=True))  # noqa: E731
    oks = {}
    # ---- HO. the hands-off definition (spec rev 3 §7.1): |bar| 400 (between the old 500 level and 300) is NOT
    #      hands-off; after it drops to 0, hands-off returns only once 0.5 s has passed
    D, S = _synth(600, v=6.0)
    S["bar"] = np.r_[np.zeros(100), np.full(100, 400.0), np.zeros(400)]
    W = _mk(D, S)
    ho = handsoff_v3(W)
    oks["HO"] = bool(ho[:100].all() and not ho[100:200].any() and not ho[200:250].any() and ho[251:].all()
                     and W["handsoff"][100:200].all())
    P("HO hands-off v3: |bar| 400 for 1 s -> hands-off %d of 100 frames (the reader's |bar| < 500 rule: %d); after it "
      "ends, hands-off at +0.50 s %s, +0.51 s %s -> %s" % (int(ho[100:200].sum()), int(W["handsoff"][100:200].sum()),
                                                          bool(ho[250]), bool(ho[251]), "PASS" if oks["HO"] else "FAIL"))
    # ---- C. stall-surge enrichment: a 20 deg/s turn with stalls placed AT |bar| 300 crossings, then randomly
    D, S = _synth(60000, v=7.0)
    w = np.full(60000, 20.0)
    rng = np.random.default_rng(5)
    bar = np.zeros(60000)
    cross = np.arange(500, 59000, 700)                        # a |bar| 300 crossing every 7 s
    for c in cross:
        bar[c:c + 120] = 400.0                                 # crosses 300 up at c and down at c + 120
    for c in cross[::2]:                                       # a stall-surge AT half the up-crossings
        w[c + 2:c + 6] = 0.0
        w[c + 6:c + 10] = 40.0
    rand = rng.choice(np.arange(1000, 58000), 20, replace=False)
    for c in rand:                                             # 20 stall-surges far from any crossing
        if np.min(np.abs(cross - c)) > 100 and np.min(np.abs(cross + 120 - c)) > 100:
            w[c:c + 4] = 0.0
            w[c + 4:c + 8] = 40.0
    S["wire18"] = -8.0 * w
    S["ang"] = np.cumsum(w) / FS
    S["raw"] = -10.0 * S["ang"]
    S["bar"] = bar
    W = _mk(D, S)
    st, ss = stutter(W)
    E = enrichment(W, ss)
    e = E["300|512"]["5-10"]
    oks["C1"] = e["ratio"] >= 2.0 and E["1229"]["5-10"]["n_near"] == 0
    P("C1 enrichment, stalls planted at |bar| 300 crossings: near %.1f / free %.1f per min = x%.1f (must be >= 2); 1229"
      " near events %d (must be 0) -> %s" % (e["rate_near"], e["rate_free"], e["ratio"], E["1229"]["5-10"]["n_near"],
                                            "PASS" if oks["C1"] else "FAIL"))
    S2 = dict(S)
    w2 = np.full(60000, 20.0)
    for c in rng.choice(np.arange(1000, 58000), 40, replace=False):
        w2[c:c + 4] = 0.0
        w2[c + 4:c + 8] = 40.0
    S2["wire18"] = -8.0 * w2
    W2 = _mk(D, S2)
    st2, ss2 = stutter(W2)
    E2 = enrichment(W2, ss2)
    e2 = E2["300|512"]["5-10"]
    oks["C2"] = (not e2["scored"]) or e2["ratio"] < 2.0
    P("C2 enrichment, 40 stalls at random times: near %s / free %s = x%s (must be < 2) ; stall-surges /min %.1f, trains "
      "/min %s -> %s" % (_f(e2["rate_near"], "%.1f"), _f(e2["rate_free"], "%.1f"), _f(e2["ratio"]),
                         st2["stall"]["5-10"]["per_min"], _f(st2["trains"]["5-10"]["per_min"]),
                         "PASS" if oks["C2"] else "FAIL"))
    # 1229 onsets: from a free wheel (hands-off), after a hand at 800, and after a hand at 400 (the F6b change: the
    # old |word| < 500 rule counted the last as hands-off; spec rev 3 §7.1 does not)
    S3 = dict(S2)
    b3 = np.zeros(60000)
    for c in np.arange(300, 59000, 250):                       # 24 onsets per minute, each 50 ms
        b3[c:c + 5] = 1500.0
    S3["bar"] = b3
    W3 = _mk(D, S3)
    _, ss3 = stutter(W3)
    o = enrichment(W3, ss3)["onsets1229"]
    res = {}
    for lvl in (800.0, 400.0):
        b4 = b3.copy()
        for c in np.arange(300, 59000, 250):
            b4[c - 60:c] = lvl
        S4 = dict(S3)
        S4["bar"] = b4
        W4 = _mk(D, S4)
        _, ss4 = stutter(W4)
        res[lvl] = enrichment(W4, ss4)["onsets1229"]
    oks["C3"] = (abs(o["per_min_handsoff"] - 24.0) < 1.0 and o["n_short"] == o["n"] == o["n_handsoff"]
                 and res[800.0]["n_handsoff"] == 0 and res[400.0]["n_handsoff"] == 0 and res[400.0]["n"] == o["n"])
    P("C3 |w| > 1229 onsets at 24 /min (50 ms each): from a free wheel hands-off %.1f /min (%d of %d); after a hand at "
      "800 for 0.6 s: %d; after a hand at 400 (hands-off under the old < 500 rule): %d of %d -> %s" % (
          o["per_min_handsoff"], o["n_handsoff"], o["n"], res[800.0]["n_handsoff"], res[400.0]["n_handsoff"],
          res[400.0]["n"], "PASS" if oks["C3"] else "FAIL"))
    # ---- C4. F6b's enrichment counts |w| > 1229 ONSETS (rising edges), not both edges: 1.5-s pulses above 1229 every
    #      7 s; stall-surges planted at the FALLING edges -> not enriched at onsets (the both-edge count WOULD call them
    #      enriched); planted at the RISING edges -> enriched
    c4 = {}
    for where in ("fall", "rise"):
        D, S = _synth(60000, v=7.0)
        w = np.full(60000, 20.0)
        bar = np.zeros(60000)
        for c in np.arange(500, 59000, 700):
            bar[c:c + 150] = 1500.0                            # onset at c, release at c + 150 (1.5 s later)
            e = c + 2 if where == "rise" else c + 152
            w[e:e + 4] = 0.0
            w[e + 4:e + 8] = 40.0
        S.update(wire18=-8.0 * w, ang=np.cumsum(w) / FS, bar=bar)
        S["raw"] = -10.0 * S["ang"]
        Wc = _mk(D, S)
        _, ssc = stutter(Wc)
        c4[where] = (enrichment(Wc, ssc)["1229"]["0-20"], enrichment(Wc, ssc, onset_levels=())["1229"]["0-20"])
    oks["C4"] = (c4["fall"][0]["scored"] and c4["fall"][0]["ratio"] < 2.0 and c4["fall"][1]["ratio"] >= 2.0
                 and c4["rise"][0]["scored"] and c4["rise"][0]["ratio"] >= 2.0)
    P("C4 F6b 1229 enrichment on ONSETS: surges at the falling edges -> onsets x%s (both-edge count would read x%s); at "
      "the rising edges -> onsets x%s -> %s" % (_f(c4["fall"][0]["ratio"]), c4["fall"][1]["ratio"],
                                                c4["rise"][0]["ratio"], "PASS" if oks["C4"] else "FAIL"))
    # ---- F6. the second clause (in-turn 4-8 Hz rms >= 7.09 deg/s at 5-10 m/s) is SCORED: a 30 deg/s turn at 7 m/s
    #      carrying a 6 Hz rate wobble of 14 deg/s (rms ~9.9) fires F6 on that clause alone; 3 deg/s does not
    f6 = []
    for amp in (14.0, 3.0):
        D, S = _synth(30000, v=7.0)
        kk = np.arange(30000)
        w = 30.0 + amp * np.sin(2 * np.pi * 6.0 * kk / FS)
        S["wire18"] = -8.0 * w
        S["ang"] = np.cumsum(w) / FS
        S["raw"] = -10.0 * S["ang"]
        W = _mk(D, S)
        stx, ssx = stutter(W)
        f6.append((score_f6(stx, enrichment(W, ssx)), ((stx["spec"].get("5-10") or {}) or {}).get("rms_4_8")))
    oks["F6"] = (f6[0][0][0] == "FAIL" and "4-8 Hz rms" in f6[0][0][2] and "trains" not in f6[0][0][2]
                 and f6[1][0][0] == "PASS")
    P("F6 4-8 Hz clause: 6 Hz wobble 14 deg/s -> rms %s, F6 %s (%s); 3 deg/s -> rms %s, F6 %s -> %s" % (
        _f(f6[0][1]), f6[0][0][0], f6[0][0][2], _f(f6[1][1]), f6[1][0][0], "PASS" if oks["F6"] else "FAIL"))
    # ---- HT. the 1.6-3 Hz hard-turn readout (information): a 30-deg hold with a 2 Hz rate component of 10 deg/s
    D, S = _synth(3000, v=6.0)
    kk = np.arange(3000)
    w = 10.0 * np.sin(2 * np.pi * 2.0 * kk / FS)
    S["wire18"] = -8.0 * w
    S["ang"] = 30.0 + np.cumsum(w) / FS
    S["raw"] = -10.0 * S["ang"]
    W = _mk(D, S)
    H = hard_turn(W)
    oks["HT"] = abs(H["3-8"]["rms"] - 10.0 / np.sqrt(2)) < 0.4 and not np.isfinite(H["8-12"]["rms"])
    P("HT 1.6-3 Hz hard-turn rms: a 2 Hz 10 deg/s rate at |theta| 30 deg, 6 m/s -> 3-8 band %.2f (expect %.2f); 8-12 %s "
      "-> %s" % (H["3-8"]["rms"], 10.0 / np.sqrt(2), _f(H["8-12"]["rms"]), "PASS" if oks["HT"] else "FAIL"))
    # ---- D. releases (spec rev 3 §7.1 edge + §7.2 F3 bars by band + F5 after ANY release)
    #   outward 800-word hold, released with a 10-deg swing past the setpoint: at 8 m/s (bar 12) no fire; at 12 m/s
    #   (bar 9) fires; a 6-deg swing on a straight (|sp| < 3) at 3 m/s fires (bar 5); a re-grab within 1.5 s is excluded;
    #   a dip to 200 (not < 150) that rises again is the SAME episode
    def swing_th(sw, a=700):
        return lambda k, sp: np.where((k >= 500) & (k < a), sp + 6.0, np.where((k >= a) & (k < a + 100),
                                      sp - sw * np.sin(np.pi * (k - a) / 100.0), sp))
    R1 = releases(_rel_wire(8.0, 20.0, [(500, 700, -800.0)], swing_th(10.0)))
    R2 = releases(_rel_wire(12.0, 20.0, [(500, 700, -800.0)], swing_th(10.0)))
    R3 = releases(_rel_wire(3.0, 1.0, [(500, 700, -800.0)], swing_th(6.0)))
    R4 = releases(_rel_wire(8.0, 20.0, [(500, 700, -800.0), (800, 900, -800.0)], swing_th(10.0)))
    R5 = releases(_rel_wire(8.0, 20.0, [(400, 600, -800.0), (600, 640, -200.0), (640, 700, -800.0)], swing_th(10.0)))
    oks["D1"] = (R1["n"] == 1 and not R1["f3"] and R1["rows"][0]["f3_bar"] == 12.0 and abs(R1["swing_max"] - 10) < 0.2
                 and R2["f3"] and R2["rows"][0]["f3_bar"] == 9.0 and R3["f3"] and R3["rows"][0]["f3_bar"] == 5.0
                 and R4["n_regrab"] == 1 and R4["n"] == 1 and abs(R4["rows"][0]["t"] - 9.0) < 0.02 and R5["n"] == 1 and abs(R5["rows"][0]["dur"] - 3.0) < 0.02)
    P("D1 F3 bars: 10-deg swing at 8 m/s -> %s (bar %s); at 12 m/s -> %s (bar %s); 6 deg on a straight at 3 m/s -> %s "
      "(bar %s); re-grab within 1.5 s -> %d excluded (the re-grab's own release scored: %d); a dip to 200 -> %d release, episode %.1f s -> %s" % (
          R1["f3"], R1["rows"][0]["f3_bar"] if R1["rows"] else "-", R2["f3"],
          R2["rows"][0]["f3_bar"] if R2["rows"] else "-", R3["f3"], R3["rows"][0]["f3_bar"] if R3["rows"] else "-",
          R4["n_regrab"], R4["n"], R5["n"], R5["rows"][0]["dur"] if R5["rows"] else -1,
          "PASS" if oks["D1"] else "FAIL"))
    #   F5 after ANY release: a FIRM 1500-word inward hold (not light) whose wheel is still 5 deg short toward centre
    #   at +1.5 s fires at 6 m/s; the same at 4 m/s is not scored
    def short_th(k, sp):
        return np.where((k >= 500) & (k < 700), sp - 6.0, np.where(k >= 700, sp - 5.0, sp))
    R6 = releases(_rel_wire(6.0, 20.0, [(500, 700, 1500.0)], short_th))
    R7 = releases(_rel_wire(4.0, 20.0, [(500, 700, 1500.0)], short_th))
    oks["D2"] = (R6["f5"] and R6["n_f5_scored"] == 1 and not R6["rows"][0]["light"] and abs(R6["gap15_max"] - 5) < 0.1
                 and R7["n_f5_scored"] == 0 and not R7["f5"])
    P("D2 F5 after any release: firm 1500-word hold, 5 deg short at +1.5 s, 6 m/s -> F5 %s (gap %s, light %s); 4 m/s -> "
      "scored %d -> %s" % (R6["f5"], _f(R6["gap15_max"]), R6["rows"][0]["light"] if R6["rows"] else "-",
                           R7["n_f5_scored"], "PASS" if oks["D2"] else "FAIL"))
    #   D4 the hand side = the episode's LAST 0.3 s of |wire| > 300 (ending before the first |wire| < 150 crossing), not
    #   the 0.3 s before the release frame: word -1500 for 1 s, +400 for 0.1 s, then a +200 decay for 0.5 s (150-300:
    #   the same episode) -> side +1 (the 0.3 s before the release frame, all +200, would say -1); the release-instant
    #   gap theta - theta_sp is carried per release (6D prints it): 3.0 deg here
    R8 = releases(_rel_wire(8.0, 20.0, [(500, 600, -1500.0), (600, 610, 400.0), (610, 660, 200.0)],
                            lambda k, sp: np.where(k == 660, sp + 3.0, sp)))
    oks["D4"] = (R8["n"] == 1 and R8["rows"][0]["hand_side"] == 1 and abs(R8["rows"][0]["gap0"] - 3.0) < 1e-9
                 and int(np.sign(np.mean(-np.r_[np.full(30, 200.0)]))) == -1)
    P("D4 hand side over the episode's last 0.3 s of |wire| > 300: side %s (the 0.3 s before the release frame would give "
      "-1); release-instant gap %s deg -> %s" % (R8["rows"][0]["hand_side"] if R8["rows"] else "-",
                                                 _f(R8["rows"][0]["gap0"]) if R8["rows"] else "-",
                                                 "PASS" if oks["D4"] else "FAIL"))
    #   the release-lurch sentence: light outward releases at 8 m/s with swings 5 / 9 / 13 deg
    cls = [releases(_rel_wire(8.0, 20.0, [(500, 700, -800.0)], swing_th(sw)))["lurch"]["cls"] for sw in (5.0, 9.0, 13.0)]
    oks["D3"] = cls[0].startswith("NOMINAL") and cls[1].startswith("HEAVY") and cls[2].startswith("BEYOND")
    P("D3 lurch sentence: swing 5 -> %s | 9 -> %s | 13 -> %s -> %s" % (cls[0][:12], cls[1][:12], cls[2][:12],
                                                                       "PASS" if oks["D3"] else "FAIL"))
    # ---- E. turn-ins (spec rev 3 §7.1; F4a / F4b / F4c): 50 deg at 6 m/s with an 8-deg bump (F4a fires); 30 deg at
    #      3 m/s with 7.5 (F4b: no, bar 8.5); 30 deg at 3 m/s with 9 (F4b fires); 30 deg at 6 m/s with 7 (F4c fires);
    #      50 deg at 6 m/s with 1 (no); 30 deg at 12 m/s (no clause); and the return of each (not scored)
    turns = [(400, 0.0, 50.0, 200, 6.0, 8.0), (1600, 0.0, 30.0, 150, 3.0, 7.5), (2800, 0.0, 30.0, 150, 3.0, 9.0),
             (4000, 0.0, 30.0, 150, 6.0, 7.0), (5200, 0.0, -50.0, 200, 6.0, 1.0), (6400, 0.0, 30.0, 150, 12.0, 9.0)]
    TI = turnins(_turn_wire(turns, n=7600))
    key_ = (lambda x: (str(x[0]), x[1]))
    got = sorted(((r["crit"], round(r["ovs"], 1), r["fire"]) for r in TI["rows"]), key=key_)
    want = sorted([("F4a", 8.0, True), ("F4b", 7.5, False), ("F4b", 9.0, True), ("F4c", 7.0, True),
                   ("F4a", 1.0, False), (None, 9.0, False)], key=key_)
    oks["E1"] = (len(got) == 6 and all(g[0] == w_[0] and abs(g[1] - w_[1]) < 0.35 and g[2] == w_[2]
                                        for g, w_ in zip(got, want))
                 and TI["F4a"]["n_fire"] == 1 and TI["F4b"]["n_fire"] == 1 and TI["F4c"]["n_fire"] == 1
                 and TI["n_returns"] >= 5)
    P("E1 turn-ins: %s ; returns %d -> %s" % (got, TI["n_returns"], "PASS" if oks["E1"] else "FAIL"))
    # ---- E2. the F4 window is the FULL 3 s after 90 %: a 50-deg turn-in at 6 m/s whose setpoint moves back 2 deg
    #      1.5 s after the ramp, with a 10-deg overshoot bump 2.0-3.2 s after 90 % -> scored (8 deg vs the moved-from
    #      final, F4a fires) and flagged SP-MOVED; the old cut at the setpoint move would have read ~0
    D, S = _synth(2400, v=6.0)
    k = np.arange(2400)
    k0, rf = 600, 200
    sp = np.zeros(2400)
    sp[k0:k0 + rf] = 50.0 * (k[k0:k0 + rf] - k0) / rf
    sp[k0 + rf:] = 50.0
    sp[k0 + rf + 150:] = 48.0                                  # the setpoint moves again 1.5 s after the ramp
    th = np.r_[np.zeros(30), sp[:-30]]
    k90 = int(np.flatnonzero(th >= 45.0)[0])
    th[k90 + 200:k90 + 320] += 10.0 * np.sin(np.pi * np.arange(120) / 120.0)
    S.update(raw=-10.0 * sp, ang=th)
    TI2 = turnins(_mk(D, S))
    r2_ = [r for r in TI2["_all"] if abs(r["size"] - 50.0) < 1.0]
    oks["E2"] = (len(r2_) == 1 and r2_[0]["sp_moved"] and not r2_[0]["truncated"] and abs(r2_[0]["ovs"] - 8.0) < 0.35
                 and r2_[0]["fire"] and TI2["n_sp_moved"] == 1)
    P("E2 full 3-s F4 window: 50-deg turn-in, setpoint moved 2 deg inside the window, 10-deg bump at +2.0 s -> overshoot "
      "%s (expect 8.0), SP-MOVED %s, fires %s -> %s" % (_f(r2_[0]["ovs"]) if r2_ else "-", r2_[0]["sp_moved"] if r2_
                                                         else "-", r2_[0]["fire"] if r2_ else "-",
                                                         "PASS" if oks["E2"] else "FAIL"))
    # ---- F. F10 ring: an 11 m/s curve hold with a 0.6 Hz ring 1.5 deg on theta; then 0.3 deg
    res = []
    for amp in (1.5, 0.3):
        D, S = _synth(2000, v=11.0)
        sp = np.full(2000, 40.0)                               # ~1.7 m/s^2 at 11 m/s through the r79 carParams model
        th = sp + amp * np.sin(2 * np.pi * 0.6 * np.arange(2000) / FS)
        S.update(raw=-10.0 * sp, ang=th)
        W = _mk(D, S)
        W["tse"] = np.full(len(W["t"]), 5.0)
        alat, spl, vm = a_lat_of(W, None, {})
        res.append(f10_ring(W, spl, alat))
    oks["F10"] = res[0]["n"] >= 1 and res[0]["fire"] and res[1]["n"] >= 1 and not res[1]["fire"]
    P("F10 (40-deg hold at 11 m/s, a_lat %.2f): 0.6 Hz ring 1.5 deg -> fire %s (max %.2f); 0.3 deg -> fire %s (max %.2f)"
      " -> %s" % (res[0]["rows"][0]["alat"] if res[0]["rows"] else -1, res[0]["fire"],
                  res[0]["rows"][0]["half_max"] if res[0]["rows"] else -1, res[1]["fire"],
                  res[1]["rows"][0]["half_max"] if res[1]["rows"] else -1, "PASS" if oks["F10"] else "FAIL"))
    # ---- G. the cap's three-way null sentence: a 15-s hold at 9 m/s (~2.2 m/s^2): I at 6144 over the last second
    #      and 4 deg short -> ms_free-like; at 6144 but 1 deg short -> 6144 suffices; 4 deg short, bound off -> not the
    #      binder; and a 2.5-s hold is not a hold (>= 3 s)
    cls = []
    for short, on, n in ((4.0, True, 1500), (1.0, True, 1500), (4.0, False, 1500), (4.0, True, 250)):
        D, S = _synth(n, v=9.0)
        sp = np.full(n, 75.0)
        S.update(raw=-10.0 * sp, ang=sp - short)
        W = _mk(D, S)
        W["tse"] = np.full(len(W["t"]), 5.0)
        alat, spl, vm = a_lat_of(W, None, {})
        at = np.zeros(n, bool)
        if on:
            at[-95:] = True
        cls.append(cap_read(W, spl, alat, dict(active=at, at_cap=at))["cls"])
    oks["G1"] = cls == ["ms_free", "suffices", "not_binder", None]
    P("G1 cap sentence: 4 deg + at 6144 -> %s; 1 deg + at 6144 -> %s; 4 deg, bound off -> %s; a 2.5-s hold -> %s -> %s"
      % (cls[0], cls[1], cls[2], cls[3], "PASS" if oks["G1"] else "FAIL"))
    # ---- G2. the cap sentence's D3 gate reads the FULL turn-in list, D3 = 60-90 deg at 8-10 m/s: 21 F4b turn-ins
    #      (30 deg, 3 m/s, overshoot 7.5) push a 70-deg 9 m/s turn-in (overshoot 2.0) out of the top-20 cut; a 40-deg
    #      9 m/s turn-in (overshoot 1.0) and a 70-deg 7 m/s one (0.5) are not D3.  The gate must see exactly the 70-deg
    #      9 m/s one (2.0 < 3 -> MET) -- the top-20 list alone would see none
    turns = ([(400 + 1200 * i, 0.0, 30.0, 150, 3.0, 7.5) for i in range(21)]
             + [(400 + 1200 * 21, 0.0, 70.0, 250, 9.0, 2.0), (400 + 1200 * 22, 0.0, 40.0, 150, 9.0, 1.0),
                (400 + 1200 * 23, 0.0, 70.0, 250, 7.0, 0.5)])
    TIg = turnins(_turn_wire(turns, n=400 + 1200 * 24 + 200))
    D, S = _synth(1500, v=9.0)
    sp = np.full(1500, 75.0)
    S.update(raw=-10.0 * sp, ang=sp - 4.0)
    Wg = _mk(D, S)
    Wg["tse"] = np.full(len(Wg["t"]), 5.0)
    alat, spl, vm = a_lat_of(Wg, None, {})
    at = np.zeros(1500, bool)
    at[-95:] = True
    CPg = cap_read(Wg, spl, alat, dict(active=at, at_cap=at), TIg)
    CPt = cap_read(Wg, spl, alat, dict(active=at, at_cap=at), dict(rows=TIg["rows"]))   # the top-20 cut alone
    oks["G2"] = (len(TIg["_all"]) == 24 and len(TIg["rows"]) == 20 and CPg["d3_n"] == 1
                 and abs(CPg["d3_ovs_max"] - 2.0) < 0.35 and "MET" in CPg["sentence"] and "NOT MET" not in
                 CPg["sentence"] and CPt["d3_n"] == 0)
    P("G2 cap D3 gate on the FULL list: %d turn-ins (top-20 cut %d); D3 (60-90 deg, 8-10 m/s) n %d, max overshoot %s -> "
      "'%s'; the top-20 list alone: n %d -> %s" % (len(TIg["_all"]), len(TIg["rows"]), CPg["d3_n"],
                                                   _f(CPg["d3_ovs_max"]), CPg["sentence"][-60:], CPt["d3_n"],
                                                   "PASS" if oks["G2"] else "FAIL"))
    # ---- H. F7b / F9: a 1.0 s 800-wire drag (word 819) against 45 % of rail opposing; a 0.6 s hands-off 240-LSB tap
    D, S = _synth(1500, v=6.0)
    bar = np.zeros(1500)
    bar[300:400] = 819.2
    Tt = np.arange(0, 15.0, 0.02)
    T = np.zeros(len(Tt))
    T[(Tt >= 3.0) & (Tt < 4.0)] = -0.45 * RAIL_T              # opposite sign to bar = opposing
    T[(Tt >= 8.0) & (Tt < 8.6)] = 240 * 8.0
    T[(Tt >= 4.0) & (Tt < 4.6)] = 240 * 8.0                   # NOT hands-off: within 0.5 s after the drag (spec §7.1)
    S.update(bar=bar, T_t=Tt, T=T)
    W = _mk(D, S)
    HA = hands_authority(W)
    oks["H1"] = HA["f7b"] and abs(HA["f7b_longest"] - 1.0) < 0.05 and HA["f9"] and HA["n_f9_hi"] == 1 and not HA["f7"]
    P("H1 F7b drag 1.0 s at 45 %% rail opposing -> F7b %s (longest %.2f s); hands-off 240 LSB for 0.6 s -> F9 %s (runs "
      "%d; the same tap right after the drag is not hands-off); F7 (not pressed) %s -> %s" % (
          HA["f7b"], HA["f7b_longest"], HA["f9"], HA["n_f9_hi"], HA["f7"], "PASS" if oks["H1"] else "FAIL"))
    # ---- I. bar check on a synthetic fork cache: cs_tqeps = -T exactly (0 mismatches), then sign-flipped (all); and
    #      the status word the V299 fork emits: 256 = EPS stale (F8's "bit 8") on 5 % of frames, one reserved 8
    oks_i = []
    for flip, stale in ((1, False), (-1, False), (1, True)):
        n = 2000
        t1 = np.arange(n) * 0.02 + 0.001
        fld = np.random.default_rng(1).integers(0, 1024, n)
        Tn = np.where(fld >= 512, -1, 1) * (fld & 511) * 8
        tc = np.arange(2 * n) * 0.01 + 0.005
        jj = np.searchsorted(t1, tc, side="right") - 1
        eps = flip * -Tn[np.clip(jj, 0, n - 1)].astype(float)
        sw = np.zeros(2 * n, np.int64)
        if stale:
            sw[::20] = STATUS_STALE
            eps[::20] = 0.0                                    # the fork zeroes the bar on a stale frame
            sw[7] = 8
        FK = _FakeNpz(t_cs=tc, cs_tqeps=eps, t_spcs=tc.copy(), spcs_angstat=sw, t_cc=tc.copy(),
                      cc_latActive=np.ones(2 * n, bool), cs_canvalid=np.ones(2 * n, bool))
        Wd = dict(meta=dict(tag="__synthetic__"))
        FRd = types.SimpleNamespace(CACHE=str(D.SCR))
        np.savez(D.SCR / "__synthetic__.npz", t1ab=t1, b0=(fld >> 8) & 3, b1=fld & 0xFF)
        oks_i.append(bar_check(Wd, FRd, FK))
    stA = attribution(dict(meta={}), dict(attrib={}), FK, dict(has_accordAngleStatus=True))
    oks["I1"] = (oks_i[0]["mismatch_frac"] == 0.0 and oks_i[1]["mismatch_frac"] > 0.9
                 and oks_i[2]["mismatch_frac"] == 0.0 and abs(oks_i[2]["bit8_duty_lat"] - 0.05) < 1e-9
                 and stA["status"]["reserved_frames"] == 1 and stA["status"]["spec_bit8_frames"] == 1)
    P("I1 bar check: exact -> mismatch %.4f; sign-flipped -> %.4f; stale (256) on 5 %% with the bar zeroed -> mismatch "
      "%.4f, stale-bit duty %.4f; reserved frames %d (the spec's literal 8: %d) -> %s" % (
          oks_i[0]["mismatch_frac"], oks_i[1]["mismatch_frac"], oks_i[2]["mismatch_frac"], oks_i[2]["bit8_duty_lat"],
          stA["status"]["reserved_frames"], stA["status"]["spec_bit8_frames"], "PASS" if oks["I1"] else "FAIL"))
    # ---- A1. accordAngleStatus presence as a FRACTION of latActive frames: rows on 98.5 % -> F1 clause fires; 100 %
    pres = []
    for keep in (0.985, 1.0):
        n = 4000
        tc = np.arange(n) * 0.01
        m = np.random.default_rng(3).random(n) < keep
        FK = _FakeNpz(t_cs=tc, t_spcs=tc[m], spcs_angstat=np.zeros(int(m.sum()), np.int64), t_cc=tc.copy(),
                      cc_latActive=np.ones(n, bool), cs_tqeps=np.zeros(n))
        pres.append(attribution(dict(meta={}), dict(attrib={}), FK, dict(has_accordAngleStatus=True))["status_present"])
    oks["A1"] = pres[0] < THR2["f1_status"] <= pres[1]
    P("A1 accordAngleStatus presence: rows on 98.5 %% of latActive frames -> %.4f (F1 fires below 0.99); all -> %.4f "
      "-> %s" % (pres[0], pres[1], "PASS" if oks["A1"] else "FAIL"))
    # ---- A2. the O1-like snap (spec rev 3 §7.2 F1): a 3-deg step toward the wheel fires; the same step away does not;
    #      a 1.2-deg / frame ramp toward the wheel does not; a 2.4-deg step over a dropped row (20 ms) does not; a 5-deg
    #      step at the latActive rising edge does not; a 2-deg step behind a wheel past the error clip is tagged CLIP
    n = 1000
    t = np.arange(n) * 0.01
    t[701:] += 0.01                                            # one dropped carOutput row before frame 701
    lat = np.zeros(n, bool)
    lat[100:950] = True
    th = np.full(n, 10.0)
    co = np.zeros(n)
    co[100:] = 5.0                                             # the rising edge: 0 -> 5 at frame 100 (excluded)
    co[110:114] = 5.0 + 1.2 * np.arange(1, 5)                  # 1.2 deg / frame toward the wheel (allowed)
    co[114:] = co[113]
    co[500:] = co[499] + 3.0 * np.sign(th[499] - co[499])      # a 3-deg snap toward the wheel (fires)
    co[600:] = co[599] - 3.0 * np.sign(th[599] - co[599])      # 3 deg away from the wheel (not a snap)
    co[701:] = co[700] + 2.4 * np.sign(th[700] - co[700])      # 2.4 deg over a 20-ms gap (not a snap)
    th[790:] = co[789] + 30.0                                  # the wheel jumps 30 deg away: the clip binds
    co[800:] = co[799] + 2.0                                   # a 2-deg step toward it: a snap, tagged clip-bound
    FK = _FakeNpz(t_co=t, co_ang=co, t_cc=t.copy(), cc_latActive=lat, t_cs=t.copy(), cs_ang=th,
                  cs_vegoraw=np.full(n, 8.0))
    SN = o1_snaps(FK, {})
    oks["A2"] = (SN["testable"] and SN["n_snap"] == 2 and SN["n_snap_clip"] == 1 and SN["n_snap_noclip"] == 1
                 and f1_snap_clause(SN)[0] == "FAIL")
    P("A2 O1-like snaps: %d (clip-bound %d, not %d) of %d latActive steps; expected 2 (1 clip-bound); F1 snap clause %s "
      "(the non-clip-bound one counts) -> %s" % (SN["n_snap"], SN["n_snap_clip"], SN["n_snap_noclip"], SN["n_steps"],
                                                 f1_snap_clause(SN)[0], "PASS" if oks["A2"] else "FAIL"))
    # ---- A3. the snap RULING (orchestrator 2026-10-02): (i) a wire whose ONLY snap is clip-bound PASSES the clause
    #      (both counts printed); (ii) the allowance is the LITERAL 1.2 deg/frame on every config: with
    #      AccordAngleMaxRate 250 (old allowance 2.5) a 2-deg non-clip step toward the wheel still counts
    coA = co.copy()
    coA[500:] = co[499]                                        # remove the 3-deg non-clip snap
    coA[600:] = coA[599] - 3.0 * np.sign(th[599] - coA[599])
    coA[701:] = coA[700] + 2.4 * np.sign(th[700] - coA[700])
    coA[800:] = coA[799] + 2.0                                 # the clip-bound step stays
    SNa = o1_snaps(_FakeNpz(t_co=t, co_ang=coA, t_cc=t.copy(), cc_latActive=lat, t_cs=t.copy(), cs_ang=th,
                            cs_vegoraw=np.full(n, 8.0)), {})
    coB = np.zeros(n)
    coB[100:] = 5.0
    coB[500:] = 7.0                                            # 2 deg toward a wheel at 10 deg (gap 5 -> 3; no clip)
    thB = np.full(n, 10.0)
    SNb = o1_snaps(_FakeNpz(t_co=t, co_ang=coB, t_cc=t.copy(), cc_latActive=lat, t_cs=t.copy(), cs_ang=thB,
                            cs_vegoraw=np.full(n, 8.0)), {"AccordAngleMaxRate": "250"})
    oks["A3"] = (SNa["n_snap"] == 1 and SNa["n_snap_clip"] == 1 and SNa["n_snap_noclip"] == 0
                 and f1_snap_clause(SNa)[0] == "PASS" and "1 clip-bound" in f1_snap_clause(SNa)[1]
                 and abs(SNb["cap"] - 1.2) < 1e-12 and SNb["n_snap_noclip"] == 1 and f1_snap_clause(SNb)[0] == "FAIL")
    P("A3 snap ruling: only a clip-bound step -> clause %s (%s); MaxRate 250, a 2-deg non-clip step toward the wheel -> "
      "allowance %.1f, counted %d, clause %s -> %s" % (f1_snap_clause(SNa)[0], f1_snap_clause(SNa)[1][-60:], SNb["cap"],
                                                       SNb["n_snap_noclip"], f1_snap_clause(SNb)[0],
                                                       "PASS" if oks["A3"] else "FAIL"))
    # ---- F1R. the replay clause in the ORCHESTRATOR'S ORDER through f1_decide + f1_replay_clause:
    #      (a) not beating -> FAIL, INCLUDING when the fit is also poor (the defect: the floor used to win -> NT);
    #      (b) beating but the winner's R2 < 0.5 -> NOT TESTABLE, loudly; (c) beating and fitting -> PASS
    cases = [("a: dR2 +0.02, 15/18", (0.02, 15, 3, 18, 0.80, 0.78), "FAIL"),
             ("a: dR2 +0.30, 10/18", (0.30, 10, 8, 18, 0.80, 0.50), "FAIL"),
             ("a: dR2 -1.0, poor fit (card-literal FAIL)", (-1.0, 0, 18, 18, -0.6, 0.40), "FAIL"),
             ("b: dR2 +0.20, 18/18, R2 0.30", (0.20, 18, 0, 18, 0.30, 0.10), "NOT TESTABLE"),
             ("c: dR2 +0.20, 18/18, R2 0.80", (0.20, 18, 0, 18, 0.80, 0.60), "PASS")]
    f1r = []
    for nm, (pl, w9, w8, nw_, r9, r8), _ in cases:
        RIc = dict(ok=True, dR2_pooled=pl, wins_V299=w9, wins_V298=w8, n_win=nw_, **f1_decide(pl, w9, w8, nw_, r9, r8))
        f1r.append((nm, f1_replay_clause(RIc)))
    oks["F1R"] = (all(c[1][0] == want for c, (_, _, want) in zip(f1r, cases)) and "LOUD" in f1r[3][1][1])
    P("F1R replay-clause order: %s -> %s" % ("; ".join("%s -> %s" % (nm, r[0]) for nm, r in f1r),
                                            "PASS" if oks["F1R"] else "FAIL"))
    # ---- K. the fork-cache naming: ONE function names the file the read looks up and the extractor writes; route 71's
    #      cache is FOUND under its legacy wire tag r71b_v294 without running the extractor
    import angle_loop_drive_read as D
    FR = D._fr()
    p71 = "75604b0a432fdc89_00000071--a7b8ba5d9d"
    Z, m, pth = fork_cache(dict(meta=dict(source="route", prefix=p71, tag="r71b_v294")), FR, run_extractor=False)
    r = subprocess.run([sys.executable, str(EXTRACTOR), "--route", p71, "--print-out"], capture_output=True, text=True)
    ext = (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""
    oks["K1"] = (Z is not None and pth == fork_cache_path(p71, FR.CACHE) and Path(ext) == pth
                 and pth.name == "r71_a7b8ba_al_fork.npz"
                 and fork_cache_path(R79_PREFIX, FR.CACHE).name == "r79_a1f5d2_al_fork.npz")
    P("K1 fork-cache naming: the read looks up %s (found %s, no extractor run); the extractor's default_out -> %s -> %s"
      % (fork_cache_path(p71, FR.CACHE).name, Z is not None, Path(ext).name if ext else r.stderr[-200:],
         "PASS" if oks["K1"] else "FAIL"))
    # ---- B. rule validation (+ negatives) and the rule identity on route 79 with the tap REPLACED by each replay
    import drive_read_fastlane as FL
    ST = D.load_score_time()
    C = D.replay_cands(ST)
    RV = rule_validation(FL, ST, C)
    oks["B1"] = RV["pass"]
    P("B1 V299 rule vs cave_rev2: random %d/%d, targeted %d/%d mismatches; negatives rev-1 caps %d, V298 %d -> %s" % (
        RV["random"]["mismatch"], RV["random"]["n"], RV["targeted"]["mismatch"], RV["targeted"]["n"],
        RV["targeted"]["neg_rev1caps"], RV["random"]["neg_v298"] + RV["targeted"]["neg_v298"],
        "PASS" if RV["pass"] else "FAIL"))
    W = D.load_route("r79_a1f5d2_al")
    S0 = dict(struct_inputs=D.struct_inputs(W))
    RI = rule_identity(D, W, S0)
    rep = RI.pop("_rep")
    res = []
    for nm, want in (("V299", "V299"), ("C3B-P", "V298")):
        Wx = dict(W)
        Tr = rep[nm]["T"]
        j = np.clip(np.searchsorted(W["t"], W["T_t"] + 0.01, side="right") - 1, 0, len(W["t"]) - 1)
        noise = np.random.default_rng(9).normal(0, 6.0 * 8, len(W["T_t"]))          # ~6 LSB, r79's residual scale
        Wx["T"] = np.round((Tr[j] + noise) / 8.0) * 8.0
        R2 = rule_identity(D, Wx, S0)
        R2.pop("_rep", None)
        res.append((nm, R2["ran"], R2["dR2_pooled"], R2["wins_V299"], R2["wins_V298"], R2["n_win"]))
    Wn = dict(W)                                               # the fit guard: a tap unrelated to either replay
    Wn["T"] = np.round(np.random.default_rng(11).normal(0, 40.0 * 8, len(W["T_t"])) / 8.0) * 8.0
    Rn = rule_identity(D, Wn, S0)
    Rn.pop("_rep", None)
    pc = positive_control(D, W, RI)
    oks["B2"] = (res[0][1] == "V299" and res[1][1] == "V298" and RI["ran"] == "V298" and Rn["ran"] == "neither fits"
                 and pc.get("ran") == "V298" and pc.get("n_win") == RI["n_win"] and pc.get("wins_V298") == RI["wins_V298"])
    P("B2 rule identity (pooled dR2 >= +0.05 AND >= 2/3 of the 30-s hands-off windows): real r79 tap -> %s (dR2 %+.3f, "
      "V298 wins %d of %d -- the positive control the read prints: %s %s/%s); tap := V299 replay + noise -> %s (dR2 "
      "%+.3f, V299 wins %d of %d); tap := V298 replay + noise -> %s (dR2 %+.3f, V298 wins %d of %d); tap := unrelated "
      "noise -> %s (best R2 %.2f) -> %s" % (
          RI["ran"], RI["dR2_pooled"], RI["wins_V298"], RI["n_win"], pc.get("ran"), pc.get("wins_V298"), pc.get("n_win"),
          res[0][1], res[0][2], res[0][3], res[0][5], res[1][1], res[1][2], res[1][4], res[1][5], Rn["ran"],
          Rn["best_r2"], "PASS" if oks["B2"] else "FAIL"))
    # ---- F1Rr. the replay-clause order on REAL replays: the unrelated-noise tap (neither fits) now FAILS F1 by branch
    #      (a) (V299 does not beat V298), where the old order read NOT TESTABLE; the V299-replay tap PASSES branch (c)
    Rv_T = np.round((rep["V299"]["T"][np.clip(np.searchsorted(W["t"], W["T_t"] + 0.01, side="right") - 1, 0,
                                              len(W["t"]) - 1)] + np.random.default_rng(9).normal(
        0, 48.0, len(W["T_t"]))) / 8.0) * 8.0
    Rv = rule_identity(D, dict(W, T=Rv_T), S0)
    Rv.pop("_rep", None)
    oks["F1Rr"] = (f1_replay_clause(Rn)[0] == "FAIL" and f1_replay_clause(Rv)[0] == "PASS"
                   and f1_replay_clause(RI)[0] == "FAIL")
    P("F1Rr replay clause on real replays: unrelated noise (best R2 %.2f) -> %s; tap := V299 replay -> %s; real r79 -> %s"
      " -> %s" % (Rn["best_r2"], f1_replay_clause(Rn)[0], f1_replay_clause(Rv)[0], f1_replay_clause(RI)[0],
                  "PASS" if oks["F1Rr"] else "FAIL"))
    # ---- PC1. the positive-control cache guard (DEFECT 1): a SYNTHETIC wire carrying route 79's prefix (meta NOT
    #      flagged selftest -- the verifier's vc_synth_wire construction) with the tap := the V299 replay + noise must
    #      NOT write or overwrite the cache; with the cache deleted, the control is recomputed from the canonical r79
    #      wire (V298 wins), never from the synthetic tap; the real r79 tap hashes to the canonical wire
    p_pc = _posctrl_path(D)
    real_bytes = p_pc.read_bytes() if p_pc.exists() else b""
    Ws = dict(W)
    Ws["meta"] = dict(W["meta"])                               # prefix == R79_PREFIX, no selftest flag
    jv = np.clip(np.searchsorted(W["t"], W["T_t"] + 0.01, side="right") - 1, 0, len(W["t"]) - 1)
    Ws["T"] = np.round((rep["V299"]["T"][jv] + np.random.default_rng(9).normal(0, 48.0, len(W["T_t"]))) / 8.0) * 8.0
    RIs = Rv                                                   # the same tap (F1Rr): its 6B identity
    assert np.array_equal(Ws["T"], Rv_T)
    pcs1 = positive_control(D, Ws, RIs)                        # the cache exists (B2 wrote it from the REAL tap)
    same = p_pc.read_bytes() == real_bytes
    p_pc.unlink()
    pcs2 = positive_control(D, Ws, RIs)                        # cache missing: recomputed from the canonical wire
    J2 = json.loads(p_pc.read_text()) if p_pc.exists() else {}
    oks["PC1"] = (bool(real_bytes) and json.loads(real_bytes).get("ran") == "V298" and RIs["ran"] == "V299"
                  and Ws["meta"].get("prefix") == R79_PREFIX and not tap_is_r79(Ws, D) and tap_is_r79(W, D)
                  and same and pcs1.get("ran") == "V298" and "NOT its tap" in pcs1.get("source", "")
                  and pcs2.get("ran") == "V298" and J2.get("ran") == "V298" and J2.get("n_win") == RI["n_win"]
                  and J2.get("wins_V298") == RI["wins_V298"])
    P("PC1 positive-control cache guard: a synthetic r79-prefixed wire (6B on it: %s) -> cache unchanged %s, printed %s "
      "(%s); cache deleted -> recomputed from the canonical r79 wire: %s %s/%s; real r79 tap hashes to the canonical wire "
      "%s, the synthetic %s (wire sha %s) -> %s" % (
          RIs["ran"], same, pcs1.get("ran"), pcs1.get("source", "")[-60:], J2.get("ran"), J2.get("wins_V298"),
          J2.get("n_win"), tap_is_r79(W, D), tap_is_r79(Ws, D), r79_identity(D)["wire_sha"][:12],
          "PASS" if oks["PC1"] else "FAIL"))
    # ---- B3 END TO END through the whole reader: route 79's inputs, carFw re-labelled A16B, the tap := the V299
    #      replay + noise.  The structural regression must carry V299's I (ref V299) and read LIVE; 6B must say V299;
    #      F1 must still FAIL on the fork side (route 79's fork has the override and no accordAngleStatus)
    Wx = dict(W)
    meta = dict(W["meta"])
    meta["carfw"] = [dict(f, fw=str(f.get("fw", "")).replace("A16A", "A16B")) for f in meta.get("carfw", [])]
    meta["selftest"] = True                                    # a synthetic tap: never cached as route 79's control
    Wx["meta"] = meta
    Tr = rep["V299"]["T"]
    j = np.clip(np.searchsorted(W["t"], W["T_t"] + 0.01, side="right") - 1, 0, len(W["t"]) - 1)
    Wx["T"] = np.round((Tr[j] + np.random.default_rng(9).normal(0, 48.0, len(W["T_t"]))) / 8.0) * 8.0
    Wx["T_lsb"] = Wx["T"] / 8.0
    Wx["T100"] = D._zoh(Wx["T_t"], Wx["T_lsb"], Wx["t"])
    with contextlib.redirect_stdout(io.StringIO()):
        SX = D.read(Wx, refs={}, with_replay=True, with_presence=True)
    VX = SX.get("v299") or {}
    f1 = next((r for r in (VX.get("verdict") or {}).get("rows", []) if r["id"] == "F1"), {})
    oks["B3"] = (SX["struct_inputs"].get("ref") == "V299" and SX["verdict"]["verdict"].startswith("LIVE")
                 and (VX.get("rule_identity") or {}).get("ran") == "V299"
                 and (VX.get("attrib") or {}).get("image") == "V299"
                 and f1.get("status") == "FAIL" and "rule replay does not beat" not in f1.get("note", "")
                 and "accordAngleStatus absent" in f1.get("note", "") and "O1-like setpoint snaps" in f1.get("note", ""))
    P("B3 end to end (r79 inputs, carFw A16B, tap := V299 replay + noise): structural ref %s, verdict %s, 6B ran %s, "
      "image %s, F1 %s on the fork side only (status absent + O1 snaps) -> %s" % (
          SX["struct_inputs"].get("ref"), SX["verdict"]["verdict"], (VX.get("rule_identity") or {}).get("ran"),
          (VX.get("attrib") or {}).get("image"), f1.get("status"), "PASS" if oks["B3"] else "FAIL"))
    allok = all(oks.values())
    P("SELFTEST %s  (%d controls: %s; %.1f s)" % ("ALL PASS" if allok else "FAILURES", len(oks),
                                                   " ".join(k for k in oks if not oks[k]) or "none failed",
                                                   time.time() - t0))
    p = D.SCR / "v299_selftest.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    try:
        os.remove(D.SCR / "__synthetic__.npz")
    except OSError:
        pass
    return allok


class _FakeNpz(dict):
    @property
    def files(self):
        return list(self.keys())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    print(__doc__)
