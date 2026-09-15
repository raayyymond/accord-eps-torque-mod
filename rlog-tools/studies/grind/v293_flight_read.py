# -*- coding: utf-8 -*-
"""v293_flight_read.py -- THE TURNKEY SCORER FOR THE FIRST V293 DRIVE.  ONE COMMAND.

    python rlog-tools/studies/grind/v293_flight_read.py <route id or cache tag> [--build V293|V282|V292]
                                                       [--config <a *.decoded.json toggle config>]

It extracts the route into the v280-format cache if it is not there already (decode copied VERBATIM
from extract_v292_routes.py, so every census tool reads it with the same yardstick), then prints a
one-page scorecard against the PRE-REGISTERED read:

    docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md   "What PASS licenses" + the adjudication
    docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md  section 6

SECTIONS
  0  exposure and the fork toggles -- initData.params plus the 100 Hz Kp read off torqueState -- is
     this drive attributable at all?  (The fork side is a TOGGLE CONFIG, not code, since 2026-09-13.)
  1  THE EDIT-LIVE IDENTITY -- the control that decides attribution.  |427 tap| regressed on
     f(cmd)*fade computed from the BUILT IMAGE's own cells.  Pre-registered: V293 R2 ~ +0.92 with a
     ~47-count residual; V282/V292 ~ -4.8 and ~349.  Carries its own NEGATIVE and POSITIVE controls.
  2  the 18-22 Hz ring by the DRIVE-CONTROLLED measure (engaged / same-route disengaged), the
     present-window amplitude, presence rate and f0.
  3  F7 and tap ripple/level at |angle| >= 30 (the record's fixed 103-wire detector), the ABSOLUTE
     6-8.5 Hz tap ripple, and the 5-9 Hz wheel band.
  4  the outer-loop signature -- a 1-4 Hz line in 0xE4 command and steering angle, per speed band.
  5  13-17 Hz vs V282 (V292's rejected x1.9-2.1) and any 22-30 Hz line.
  6  the 0x14A cave duties b4-b7 (b4 = sign(r24) = the NEGATIVE CONTROL; b7 = the pre-registered mover).
  7  THE OPERATOR'S FOUR SYMPTOMS -- ratchet, loose, oversteer, overshoot-then-correct -- as
     pre-registered instruments, with every reference column RE-DERIVED at run time by
     `v293_symptom_instruments.py` on the cached routes, never copied from a report.  Carries its own
     POSITIVE CONTROL: the same code must reproduce V293-PLANT-IDENT-2026-09-13.md on r70_v293.

WHAT CHANGED IN v2 (2026-09-13)
  * THE EXPECTED FORK CONFIG IS READ FROM A FILE (`--config`), not hard-coded, so a revised toggle
    config is scored against itself.  Default: the rev-2 file if it exists, else the rev-1 one.
  * THE `branch` GATE WAS REPLACED.  v1's `median f/desiredLateralAccel >= 0.75` was BROKEN AS
    WRITTEN and failed a correctly-attributed drive: `f` is the current command minus an offset and
    `desiredLateralAccel` is the 0.30 s delayed setpoint plus a jerk lead, so f/D = 1 - c/|D| by
    construction.  The replacement reads `torqueState.f` against
    `starpilotLateralState.feedforward` (bimodal: 0.000 in the else arm, 3.3 under plant FF) and
    re-derives the fork's own f-formula on the wire.  The gate's POLARITY FOLLOWS THE CONFIG.
  * A SECOND REVERT CLASS: a ratchet worse than the rev-1 flight reverts the TOGGLE CONFIG, not the
    firmware.

THE CONTROLS, and why they are the point
  * NEGATIVE CONTROL: `--controls` runs the SAME identity on r6c (V282) and r6d/r6e/r6f (V292) and
    must FAIL there.  An instrument that passes everywhere measures nothing.  It also computes every
    band reference and writes them to _scratch/v293_flight_refs.json, so the drive-day run is fast
    and its reference numbers are RE-DERIVED rather than copied out of prose.
  * POSITIVE CONTROL: a V293 tap synthesised from the route's own recorded command by the byte-exact
    1 kHz integer march (v292_replay_lib.Elec with the V293 cells), decimated to the tap's 50 Hz and
    quantised.  Regressed by the same estimator it must read R2 ~ 1.  It is NOT tautological: the
    predictor is the STEADY-STATE surface and the synthetic tap comes from the dynamic chain.

MARKED THROUGHOUT: EVIDENCE = measured from the wire or read from the image.  BELIEF = inherited or
modelled.  Score bands; the OPERATOR scores symptoms.  Nothing here licenses the word "fixed".

ANALYSIS ONLY.  Reads rlogs and images; writes only under _scratch/.  Flashes nothing, sends nothing.
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import sys
import types

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
PTRCACHE = os.path.join(KIT, "rlog-tools", "_scratch", "cache")
SCR = os.path.join(HERE, "_scratch")
REFS_JSON = os.path.join(SCR, "v293_flight_refs.json")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "osc-highangle"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
CPD = 8.0                       # raw 0x18F counts per deg/s
BANDS = (("5-9", 5, 9), ("9-13", 9, 13), ("13-17", 13, 17), ("18-22", 18, 22),
         ("22-26", 22, 26), ("26-30", 26, 30))
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ======================================================================================================
# 0.  THE CEREAL SCHEMA PATCH -- the kit CANNOT read the fork's lateral state without it
# ======================================================================================================
# 🛑 EVIDENCE (read from both schemas, 2026-09-13):  the kit declares
#       epsTelemetry @137 :Custom.EpsTelemetry            struct id 0xc2243c65e0340384
#    and the fork declares
#       starpilotLateralState @137 :Custom.StarPilotLateralState   struct id 0xc2243c65e0340384
#    -- the SAME union slot and the SAME struct id with a COMPLETELY DIFFERENT field layout (the kit's
#    is nine flag/byte fields from the V31P-V2 gate telemetry; the fork's is eight floats/bools).
#    So the kit's decoder reads the fork's lateral state as EpsTelemetry
#    and every field is garbage.  We do NOT edit the kit's schema; we build a patched COPY under
#    _scratch/ and load it with capnp.load().  Everything else in the schema is untouched, and nothing
#    on the extraction path (can / carState / userBookmark / initData) reads this struct.
FORK_STRUCT = """struct EpsTelemetry @0xc2243c65e0340384 {
  # PATCHED COPY for the V293 flight read -- the FORK repurposed this struct id as
  # StarPilotLateralState (cereal/custom.capnp on raayyymond-StarPilot/StarPilot @ Dom).  Field list
  # copied verbatim from the fork (Dom @ 4247cb09e -- the `epsTorqueMode @8` of the UNDONE commit
  # 3d1a3d0c7 never shipped).  The kit's own schema is NOT modified by this file.
  active @0 :Bool;
  frictionThreshold @1 :Float32;
  frictionScale @2 :Float32;
  feedforward @3 :Float32;
  frictionJerk @4 :Float32;
  frictionJerkDeadzone @5 :Float32;
  lowSpeedFactor @6 :Float32;
  unwindDetected @7 :Bool;
}"""
# 🛑 A SECOND COLLISION, same shape.  The kit declares `modelDataV2SP @116 :Custom.ModelDataV2SP`
# (struct id 0xa1680744031fdb2d, one enum field); the FORK declares the same slot and the same struct
# id as `customReserved9 :Custom.CustomReserved9`, six Text/UInt64 fields carrying THE TESTING GROUND
# SELECTION.  Decoded and REPORTED only: no Testing Ground slot is the torque mode (the operator
# undid the slot-9 rework on 2026-09-13; the fork side is a plain toggle config).
FORK_TG_STRUCT = """struct ModelDataV2SP @0xa1680744031fdb2d {
  # PATCHED COPY -- the FORK repurposed this struct id as CustomReserved9, which carries the Testing
  # Ground selection published by the_galaxy.  Informational on this scorecard.  Field list copied
  # verbatim from the fork.
  slotId @0 :Text;
  slotName @1 :Text;
  variant @2 :Text;
  variantLabel @3 :Text;
  reason @4 :Text;
  wallTimeNanos @5 :UInt64;
}"""
# ======================================================================================================
# 0b.  THE EXPECTED FORK CONFIG -- READ FROM A FILE, never hard-coded  [v2, 2026-09-13]
# ======================================================================================================
# 🛑 WHY THIS MOVED OUT OF THE SOURCE.  v1 hard-coded the rev-1 torque-mode config, so the very next
# drive -- which flies a REVISED config on the SAME firmware -- would have been scored against the
# wrong expectation and reported a bogus `toggle` FAIL.  The expectation now comes from the decoded
# Galaxy toggle config itself, which is the same artefact the operator restores on the device.
CONFIG_DIR = os.path.join(KIT, "analysis-2020accord", "reference")
CONFIG_R2 = os.path.join(CONFIG_DIR, "toggle-config_V293_torque_mode_r2.decoded.json")
CONFIG_R1 = os.path.join(CONFIG_DIR, "toggle-config_V293_torque_mode.decoded.json")

# params_keys.h DECLARED defaults, transcribed from FORK-LATERAL-PATH-V293-2026-09-13.md section 5
# (which read them out of `common/params_keys.h` at Dom 4247cb09e).  A params rebuild DROPS a key that
# sits at its declared default, so an ABSENT key in initData reads as the default -- MEASURED on r6f,
# where `AccordRatePlantFF` was absent and the rate-plant branch was demonstrably live.
# ⚠ `SteerKP` / `SteerFriction` / `SteerLatAccel` / `SteerDelay` / `SteerRatio` are deliberately NOT
# here: their declared defaults are platform-derived, so absence is genuinely ambiguous and must read
# as a MISMATCH rather than quietly resolve to a guess.
PARAMS_DEFAULTS = {
    "AccordRatePlantFF": "1", "AccordTorqueKi": "0.30", "AccordTurnFFTaper": "0",
    "AccordFFRateGain": "0.5", "AccordEpsGainScale": "1.0", "AccordEpsSpringScale": "1.0",
    "AccordVariableSteerRatio": "1", "ForceAutoTuneOff": "1", "ForceAutoTune": "0",
    "AdvancedLateralTune": "1", "KeepLearnedLatAccelOffset": "1", "UseAutoSteerDelay": "1",
    # rev-3 keys (fork 2026-09-14): the V293 torque-mode terms, declared defaults = the rev-3 flight values
    "AccordHoldMap": "1", "AccordFrictionHyst": "0.015", "AccordRateLoopGain": "0.0006",
    "AccordErrorNotchQ": "1.0", "AccordRefFilter": "0.12",
    # rev-4 key (fork f4e314da6, 2026-09-14): the integral gain from 18 m/s; declared default = the rev-4 flight value
    "AccordTorqueKiHigh": "2.5",
}
# keys we read but never gate on -- printed as context beneath the config table
CONTEXT_KEYS = ("SteerRatio", "SteerDelay", "UseAutoSteerDelay", "AccordVariableSteerRatio",
                "AccordFFRateGain", "AccordEpsGainScale", "AccordEpsSpringScale",
                "KeepLearnedLatAccelOffset", "ForceTorqueController", "ForceAutoTune",
                "AccordHoldMap", "AccordFrictionHyst", "AccordRateLoopGain", "AccordErrorNotchQ", "AccordRefFilter",
                "AccordTorqueKiHigh", "GitCommit", "GitBranch")

# 🛑 WHICH FORK COMMIT A CONFIG NEEDS.  The rev-2 config sets AccordEpsSpringScale 1.0 and
# AccordEpsGainScale 1.0 NOT because no correction is wanted, but because the correction moved INTO
# FORK CODE: `HONDA_ACCORD_EPS_G_V` -> [550, 271, 246, 205] and `_K_V` -> [0.93, 1.64, 2.15, 2.77,
# 3.15] were replaced on Dom at 9622aee9f.  Fly it on 4247cb09e and the scales are 1.0 against the
# OLD tables, i.e. the plant feedforward is the one the identification measured as 1.4-2.6x too
# small -- a silently wrong drive that every other gate would pass.  The rlog cannot read the tables,
# only the commit, so this gate is a COMMIT check and says so.
CONFIG_FORK_COMMIT = {
    "toggle-config_V293_torque_mode_r2.decoded.json": dict(
        want="9622aee9f", forbid="4247cb09e",
        why="the rev-2 config's spring/gain scales are 1.0 because the Accord plant tables were "
            "REPLACED IN FORK CODE at 9622aee9f; on 4247cb09e those scales multiply the OLD tables"),
    # rev 3 (2026-09-14): the five new Accord* keys are CONSUMED only by e8e62f0e1 and later; on 66cf4454a the
    # params library does not know them (Galaxy may refuse the restore, or the keys sit unread), the code path is
    # rev 2 with SteerFriction 0 and Ki 0.6 -- a silently different drive.
    "toggle-config_V293_torque_mode_r3.decoded.json": dict(
        want="e8e62f0e1", forbid="66cf4454a",
        why="the rev-3 config's AccordHoldMap / AccordFrictionHyst / AccordRateLoopGain / AccordErrorNotchQ / "
            "AccordRefFilter keys only exist in fork code from e8e62f0e1; on 66cf4454a they are unknown to the "
            "params library and the controller runs rev 2 with the relay off"),
    # rev 4 (2026-09-14, routes 72+73): AccordTorqueKiHigh is CONSUMED only from f4e314da6 (08a5a7064 = the same code
    # plus its test fix); on e8e62f0e1 the key is unknown (flat Ki 0.6), the SteerFriction relay is still live under
    # the hysteresis FF, and the stock-param sync can back-fill SteerFriction 0.0 with the stock 0.212 (route 73).
    "toggle-config_V293_torque_mode_r4.decoded.json": dict(
        want=("08a5a7064", "f4e314da6"), forbid="e8e62f0e1",
        why="the rev-4 config's AccordTorqueKiHigh (Ki 2.5 from 18 m/s) exists only in fork code from f4e314da6, "
            "which also gates the SteerFriction relay off under AccordFrictionHyst and stops the stock-param sync "
            "from back-filling an explicit SteerFriction 0.0 (route 73 ran 0.212 that way)"),
}


def load_config(path=None):
    """the expected config, from a `*.decoded.json` under analysis-2020accord/reference/.

    Returns (path, {key: (expected_string, default_or_None, kind)}) in the shape the v1 table used, so
    the gate code below is unchanged.  JSON bools become "1"/"0"; JSON numbers become their repr and
    are compared as floats, so 0.3 == "0.3" == "0.30".
    """
    if path is None:
        path = CONFIG_R2 if os.path.exists(CONFIG_R2) else CONFIG_R1
    if not os.path.exists(path):
        raise SystemExit("no expected-config file at %s\n"
                         "  -> pass --config <a *.decoded.json under analysis-2020accord/reference/>"
                         % path)
    raw = json.load(open(path))
    cfg = {}
    for k, v in raw.items():
        if isinstance(v, bool):
            cfg[k] = ("1" if v else "0", PARAMS_DEFAULTS.get(k), "bool")
        elif isinstance(v, (int, float)):
            cfg[k] = (repr(float(v)), PARAMS_DEFAULTS.get(k), "float")
        else:
            cfg[k] = (str(v), PARAMS_DEFAULTS.get(k), "str")
    return path, cfg


CONFIG_PATH, CONFIG = None, {}    # set by main() / set_config(); the EXPECTED fork toggle config
EXPECT_PLANT_FF = None            # True when the config asks for AccordRatePlantFF = 1


def set_config(path=None):
    """load the expected config and derive which feedforward ARM it asks for.

    🛑 THE BRANCH GATE'S POLARITY FOLLOWS THE CONFIG.  Rev 1 turned the rate-plant FF OFF (the else
    arm); the rev-2 config turns it ON.  A gate hard-wired to "the else arm must be live" would fail
    the very next drive for doing exactly what it was told to do.
    """
    global CONFIG_PATH, CONFIG, EXPECT_PLANT_FF
    CONFIG_PATH, CONFIG = load_config(path)
    v = CONFIG.get("AccordRatePlantFF")
    EXPECT_PLANT_FF = (v[0] == "1") if v else None
    for k in CONFIG:
        if k not in WANT_PARAMS:
            WANT_PARAMS.append(k)
    return CONFIG_PATH


INSTALLED_KP = 0.9                # the rate-servo tune's SteerKP (2026-09-10 backup; route 6f initData)
_LOG = None


def fork_log_schema():
    """load a PATCHED copy of the kit's cereal so the fork's lateral state and its Testing Ground
    heartbeat decode.  Falls back to the kit's own schema (and says so) if anything goes wrong -- a
    missing informational read must not stop the scorecard."""
    global _LOG
    if _LOG is not None:
        return _LOG
    src = os.path.join(KIT, "rlog-tools", "cereal")
    dst = os.path.join(SCR, "cereal_fork")
    try:
        import capnp
        capnp.remove_import_hook()
        import hashlib
        stamp = os.path.join(dst, ".patched")
        want = "patched " + hashlib.sha1((FORK_STRUCT + FORK_TG_STRUCT).encode("utf-8")).hexdigest()[:12] + "\n"
        have = io.open(stamp, encoding="utf-8").read() if os.path.exists(stamp) else ""
        if have != want:            # first run, or the patched structs changed -> rebuild the copy
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            os.makedirs(dst)
            for f in ("log.capnp", "car.capnp", "deprecated.capnp", "custom.capnp"):
                shutil.copy(os.path.join(src, f), os.path.join(dst, f))
            shutil.copytree(os.path.join(src, "include"), os.path.join(dst, "include"))
            p = os.path.join(dst, "custom.capnp")
            txt = io.open(p, encoding="utf-8").read()
            for pat, rep, nm in (
                    (r"struct EpsTelemetry @0xc2243c65e0340384 \{.*?\n\}", FORK_STRUCT, "EpsTelemetry"),
                    (r"struct ModelDataV2SP @0xa1680744031fdb2d \{.*?\n\}", FORK_TG_STRUCT,
                     "ModelDataV2SP")):
                txt, n = re.subn(pat, rep, txt, flags=re.S)
                if n != 1:
                    raise RuntimeError("%s struct not found in custom.capnp (n=%d)" % (nm, n))
            io.open(p, "w", encoding="utf-8").write(txt)
            io.open(stamp, "w", encoding="utf-8").write(want)
        _LOG = (capnp.load(os.path.join(dst, "log.capnp")), True)
    except Exception as e:
        pr("  ⚠ patched fork schema unavailable (%s) -- falling back to the KIT schema; "
           "the Testing Ground heartbeat cannot be read." % str(e)[:70])
        sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
        from cereal import log as clog
        _LOG = (clog, False)
    return _LOG


# ======================================================================================================
# 1.  IMAGES AND THE ROUTE -> BUILD MAP
# ======================================================================================================
import grind_incident_r35 as GI                 # noqa: E402
import grind1_census_v282 as CEN                # noqa: E402
import grind1_census_v288_r5e as C88            # noqa: E402
import creep20_loop_id as C20                   # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG     # noqa: E402
import strongturn_r32_r33 as ST                 # noqa: E402
import v292_replay_lib as RL                    # noqa: E402
import v293_lib as L                            # noqa: E402
import v293_symptom_instruments as SI           # noqa: E402

IMG = {
    "V282": L.IMG282,
    "V292": L.IMG292,
    "V293": LG.FW + ("_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-"
                     "KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"),
    "V281r3": CEN.IMG["V281r3"],
}
BUILD_OF = {"r6c": "V282", "r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3",
            "r6d_v292": "V292", "r6e_v292": "V292", "r6f_v292": "V292"}
CONTROL_ROUTES = ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292")
REF_V282 = "r6c"                                # nearest-in-time V282 reference; r39 printed beside it

# --- literals transcribed from the record, printed as a CROSS-CHECK on the recomputed refs ----------
# V292-FLIGHT-READ-2026-09-13.md section 4 (engaged / same-route disengaged, 18-22 Hz) and section 3.1
# (the present-window 18-22 Hz rate amplitude, ALL engaged, deg/s).  DESIGN section 6.2 for F7/rip.
RECORD = dict(
    engdis_1822={"r6c": 3.399, "r39": 3.920, "r35": 3.618,
                 "r6d_v292": 5.484, "r6e_v292": 6.795, "r6f_v292": 4.086},
    pres_amp_1822={"r6c": 2.630, "r39": 2.766, "r35": 3.487,
                   "r6d_v292": 3.638, "r6e_v292": 2.820, "r6f_v292": 3.277},
    pres_pct={"r6c": 9.8, "r39": 20.9, "r35": 16.2,
              "r6d_v292": 18.1, "r6e_v292": 18.7, "r6f_v292": 20.5},
    f7_per100={"r6c": None, "r39": 1.03, "r35": 0.00,
               "r6d_v292": 3.99, "r6e_v292": 2.22, "r6f_v292": 6.30},
    identity_r2_prereg=dict(V293=0.92, V282=-4.81),
    identity_resid_prereg=dict(V293=47.4, V282=348.8),
    b7_duty=dict(V282=0.996, V293=0.808),
    b4_duty=dict(V282=0.808, V293=0.808),
)

# --- pre-registered decision thresholds, each with its source ---------------------------------------
# --- what the controls actually MEASURED on 2026-09-13, so the yardstick is visible without a rerun --
# (`--controls`, whole-route, this file's own estimator; see _scratch/v293_flight_read_controls.txt)
CONTROL_FLOOR = {"r6c": -0.011, "r39": -0.840, "r35": -0.069,
                 "r6d_v292": -0.135, "r6e_v292": -1.225, "r6f_v292": -0.561}
CONTROL_CEILING = 0.9638       # the positive control on r6d_v292: a synthetic V293 tap, same estimator

THR = dict(
    identity_r2=0.50,          # prereg "the within-frame identity"; predicted +0.92.  MEASURED: the
                               # estimator's ceiling on real data is +0.96 and its floor across six
                               # non-V293 routes is -0.01, so the gate sits between them.
    identity_resid=150.0,      # absolute fallback only.  The LIVE gate is 2.5x the SAME ROUTE's own
                               # positive-control residual, which self-calibrates for exposure, the
                               # idx range and the 8-count quantiser.
    identity_resid_rel=2.5,
    ring_ratio=0.40,           # prereg "What PASS licenses" / DESIGN 6.3: <= 0.4x of V282's
    f7_per100=2.0,             # prereg "revert if"
    ripL=0.25,                 # prereg "revert if"
    rip_abs_ratio=1.5,         # DESIGN 6.3 symmetric sentence: absolute 6-8.5 Hz tap ripple >= 1.5x
    band_1317_ratio=1.5,       # prereg B7 gate (V292's rejected x1.9-2.1)
    coh_14=0.50,               # a GUARD, not the discriminator: coherence reads 0.88-1.00 at 1-4 Hz
                               # on every route in the corpus.  The angle AMPLITUDE discriminates.
    # --- v2, 2026-09-13: THE BRANCH IDENTITY.  `fD_ratio` is GONE -- see `branch_block` for why it
    #     could not work.  Both sides below are MEASURED, not assumed:
    #       median |f - starpilotLateralState.feedforward| / median |f|
    #         ELSE arm  (rate-plant FF OFF): r70_v293 0.0000 · r39 0.0000 · r35 0.0000
    #         PLANT arm (rate-plant FF ON) : r6f_v292 3.325 · r6c 3.371
    #     The statistic is BIMODAL with nothing between 0.00 and 3.3, so the gate sits far from both
    #     sides.  The absolute guard catches a route whose |f| is itself tiny.
    branch_rel=0.10,
    branch_abs=0.02,           # m/s^2
    branch_slope_tol=0.02,     # the f-on-D_future slope must be 1.000 +- this in the ELSE arm
    branch_r2=0.95,            # below this the three-term identity does not hold -> not the ELSE arm
    offset_tol=0.02,           # m/s^2: |effective latAccelOffset| when the config says KEEP = 0
    # --- v2: THE OPERATOR'S FOUR SYMPTOMS.  Every one is calibrated against at least one route that
    #     FAILS it (r70_v293, the rev-1 flight) and one that PASSES (a V282/V281r3 reference), and the
    #     section 7 printout names which is which beside the threshold.
    ratchet_vs_r6c=3.0,        # dwells/min at th 0.25 must be <= 3x r6c's in every populated band
    ratchet_min_s=60.0,        # a band under this much exposure is reported, not gated
    conc_q7590=0.40,           # rate concentration in the q75-90 rms bin.  r70 0.468 FAIL;
                               # r6c 0.345 / r39 0.325 / r35 0.351 PASS; sine 0.157, noise 0.278
    track_lo=0.95, track_hi=1.05,     # tracking gain.  r70 >22 1.123 FAIL; r6c 0.966-0.996 PASS
    track_min_s=60.0,
    hold_hi=1.04,              # turn-hold actual/desired above 20 m/s.  r70 1.093 FAIL
    overshoot=0.20,            # relative step overshoot at 10-20 and >20.  r70 0.437 / 0.341 FAIL
    prom_db=3.0,               # 1-4 Hz prominence.  r70 6.5-11.8 FAIL; r6c -2.3..+2.2 PASS
    rate14_vs_r6c=2.0,         # 1-4 Hz rate content against r6c's
    i_share=0.20,              # integrator share of |f|+|p|+|i|.  r70 0.35-0.39 FAIL
    deliver_lo=0.90, deliver_hi=1.10,   # straight-line delivery.  r70 0.800 FAIL
)

NULL_SENTENCE_PREREG = (
    "if the 18-22 Hz ring's amplitude and ring-down are unchanged with the LKAS loop open on every "
    "frame (identity holding), the 20 Hz object is not the LKAS loop's and the whole in-loop class "
    "- V38 -> V293 - is closed")
NULL_SENTENCE_DESIGN = (
    '"If the 18-22 Hz ring amplitude on hands-off creep does not fall to at most 0.4x of V282\'s - an '
    'effect three times the x1.22 the kit has ruled unreadable, and one the car\'s own '
    'engaged/disengaged ratio of 3.5-4.2 says must be there - with the LKAS rate loop FULLY OPEN '
    '(|R_servo| = 0 at every frequency, verified on the wire by the within-frame identity in 6.2), '
    'then the 18-22 Hz object is NOT the LKAS rate loop\'s, the engaged/disengaged ratio measures '
    'something other than the loop, and every in-loop class - shaping, notching, pole-moving and '
    'opening - is CLOSED."')


# ======================================================================================================
# 2.  EXTRACTION -- decode copied VERBATIM from extract_v292_routes.py
# ======================================================================================================
WANT_PARAMS = ["AccordEpsTorqueMode", "AccordRatePlantFF", "AccordFFRateGain", "AccordTorqueKi",
               "AccordVariableSteerRatio", "SteerRatio", "SteerLatAccel", "SteerFriction", "SteerKP",
               "AccordCurvatureLead", "AccordCurvatureLeadGain", "ForceAutoTune", "ForceAutoTuneOff",
               "AdvancedLateralTune", "KeepLearnedLatAccelOffset", "ForceTorqueController",
               "AccordEpsGainScale", "AccordEpsSpringScale", "AccordTurnFFTaper", "GitCommit",
               "GitBranch", "GitRemote", "GitCommitDate", "Version", "TermsVersion", "CarParams",
               "DongleId",
               # v2: the rev-2 config touches these, and a key that is not CAPTURED reads the same as
               # a key that is ABSENT from the store -- which is a silent wrong answer, not a null.
               "SteerDelay", "UseAutoSteerDelay"]
                                   # AccordEpsTorqueMode stays only as a STALE-FORK trap detector


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def extract(prefix, tag):
    """build <TAG>.npz / _b4.npz / _marks.json / _params.json exactly as extract_v292_routes.py does,
    plus the fork-side attribution reads: torqueState (f, D, p, error) and the Testing Ground
    heartbeat (which needs the PATCHED schema)."""
    clog, patched = fork_log_schema()
    import zstandard
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        raise SystemExit("no rlog segments on disk matching %s--*--rlog.zst in %s\n"
                         "  -> fetch them first (the `fetch-rlogs` skill), then re-run." % (prefix, RLOGS))
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    pr("  extracting %s -> %s : %d segments on disk %s" % (prefix, tag, len(segs), have))
    t18, tq, rate, sca, t14, ang, t1ab, b0, b1, te4, cmd, req, tcs, vego = ([] for _ in range(14))
    t14b, b4 = [], []
    cs_ang, cs_tq, cs_press, cs_sr = [], [], [], []
    marks, seg_span, failed = [], {}, []
    params_dump = None
    tq_f, tg = [], {}
    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo = hi = None
        n18_at_seg_start = len(t18)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                failed.append(dict(seg=sn, err=str(e)[:120])); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if lo is None:
                lo = tm
            hi = tm
            if w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    if m.src == 1:
                        if m.address == 0x18F and len(d) >= 5:
                            t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2))
                            sca.append((d[4] >> 3) & 1)
                        elif m.address == 0x14A and len(d) >= 4:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1)
                            if len(d) >= 5:
                                t14b.append(tm); b4.append(d[4])
                        elif m.address == 0x1AB and len(d) >= 2:
                            t1ab.append(tm); b0.append(d[0]); b1.append(d[1])
                    elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); cmd.append(i16be(d, 0)); req.append((d[2] >> 7) & 1)
            elif w == "carState":
                cs = evt.carState
                tcs.append(tm); vego.append(cs.vEgo)
                cs_ang.append(cs.steeringAngleDeg); cs_tq.append(cs.steeringTorque)
                cs_press.append(1 if cs.steeringPressed else 0)
                try:
                    cs_sr.append(cs.steeringRateDeg)
                except Exception:
                    cs_sr.append(float("nan"))
            elif w == "modelDataV2SP" and patched:
                # PATCHED name -- this is the fork's customReserved9, the Testing Ground selection
                _tg_collect(evt, tg)
            elif w == "controlsState":
                # THE CONTROL-PATH reads of the fork tune (docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST
                # section C).  (1) f/D: under the torque config f = desiredLateralAccel + friction
                # and friction is 0, so f tracks D one-for-one; under the rate-plant branch the same
                # point reads ~0.38 of it (MEASURED on r6c seg 3, V282: slope 0.3905).  (2) Kp at
                # 100 Hz: the fork logs pid_log.error = error_with_lsf and feeds THAT to pid.update,
                # whose p = k_p * error, so p / error == SteerKP on every active frame, exactly.
                try:
                    ls = evt.controlsState.lateralControlState
                    if ls.which() == "torqueState":
                        t_ = ls.torqueState
                        tq_f.append((float(t_.f), float(t_.desiredLateralAccel), bool(t_.active),
                                     float(t_.p), float(t_.error)))
                except Exception:
                    pass
            elif w == "userBookmark":
                marks.append(dict(seg=sn, mono=tm))
            elif w == "initData" and params_dump is None:
                try:
                    pd = {}
                    for e in evt.initData.params.entries:
                        if e.key in WANT_PARAMS:
                            try:
                                pd[e.key] = bytes(e.value).decode("utf-8", "replace")
                            except Exception:
                                pd[e.key] = repr(bytes(e.value)[:200])
                    pd["_all_keys_n"] = len(list(evt.initData.params.entries))
                    pd["_seg"] = sn
                    params_dump = pd
                except Exception:
                    pass
        seg_span[sn] = dict(lo=lo, hi=hi,
                            lo_can=(t18[n18_at_seg_start] if len(t18) > n18_at_seg_start else lo))
    if not t18:
        raise SystemExit("no 0x18F frames decoded from %s -- wrong bus or a bad cache" % prefix)
    A = lambda x, dt=float: np.asarray(x, dt)  # noqa: E731
    D = dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca, int), t14=A(t14), ang=A(ang),
             t1ab=A(t1ab), b0=A(b0, int), b1=A(b1, int), te4=A(te4), cmd=A(cmd), req=A(req, int),
             tcs=A(tcs), vego=A(vego), cs_ang=A(cs_ang), cs_tq=A(cs_tq),
             cs_press=A(cs_press, int), cs_rate=A(cs_sr))
    os.makedirs(CACHE, exist_ok=True)
    np.savez(os.path.join(CACHE, tag + ".npz"), **D)
    np.savez(os.path.join(CACHE, tag + "_b4.npz"), t14b=A(t14b), b4=A(b4, int))
    t0 = D["t18"][0]
    for m in marks:
        m["t_route"] = m["mono"] - t0
        m["t_in_seg"] = m["mono"] - seg_span[m["seg"]]["lo_can"]
    order = sorted(seg_span)
    out = dict(t0_mono=float(t0), route_prefix=prefix, tag=tag, marks=marks,
               present_segments=order, missing_segments=[], failed_segments=failed,
               gaps=[dict(after_seg=a_, before_seg=b_,
                          gap_s=round(seg_span[b_]["lo_can"] - seg_span[a_]["hi"], 3),
                          contiguous_index=(b_ == a_ + 1)) for a_, b_ in zip(order, order[1:])],
               segs={str(k): dict(lo_route=v["lo"] - t0, hi_route=v["hi"] - t0,
                                  lo_can_route=v["lo_can"] - t0) for k, v in seg_span.items()},
               lo_route_note="use lo_can_route; lo_route is initData's process-start stamp")
    json.dump(out, open(os.path.join(CACHE, tag + "_marks.json"), "w"), indent=1)
    pdump = params_dump or {}
    pdump["_tg_readable"] = bool(patched)
    pdump["_written_by"] = "v293_flight_read.py"
    pdump["_want_params"] = sorted(WANT_PARAMS)
    pdump.update(_torque_state_stats(tq_f))
    pdump.update(_tg_summary(tg))
    json.dump(pdump, open(os.path.join(CACHE, tag + "_params.json"), "w"), indent=1)
    pd_ = os.path.join(PTRCACHE, prefix)
    os.makedirs(pd_, exist_ok=True)
    json.dump(dict(route=prefix, tag=tag, v280_cache=os.path.join(CACHE, tag + ".npz"),
                   b4_cache=os.path.join(CACHE, tag + "_b4.npz"),
                   marks=os.path.join(CACHE, tag + "_marks.json"),
                   params=os.path.join(CACHE, tag + "_params.json"),
                   note="v280-format cache, decode identical to extract_v292_routes.py"),
              open(os.path.join(pd_, "CACHE-POINTER.json"), "w"), indent=1)
    pr("  wrote %s.npz (%.1f s route, %d bookmarks, %d segments)"
       % (tag, D["t18"][-1] - t0, len(marks), len(order)))


# ======================================================================================================
# 2b. THE CONTROL-PATH CACHE -- what SECTION 7 and the BRANCH IDENTITY need and the v280 cache lacks
# ======================================================================================================
# 🛑 The v280 cache is CAN + carState ONLY.  Three of the operator's four symptoms (loose, oversteer,
# overshoot) and the new branch-identity gate are all read off openpilot's own control path, which is
# not in it.  So this builds a SECOND, separate cache per route -- never touching the v280 one -- with
# the 100 Hz controlsState/torqueState series, the fork's starpilotLateralState (which needs the
# PATCHED schema), liveTorqueParameters at 4 Hz and liveParameters at 20 Hz.  Times are stored as
# ABSOLUTE mono seconds so they align onto the v280 cache's own grid (whose t18 is absolute too).
CS_FIELDS = ("la_des", "la_act", "f", "p", "i", "err", "out", "active", "sat", "version")


def tag_prefix(tag):
    """the route prefix on disk for a cache tag like 'r6c' / 'r70_v293' -- the tag's leading rXX is the
    route counter in hex, exactly as `resolve` built it."""
    mk = os.path.join(CACHE, tag + "_marks.json")
    if os.path.exists(mk):
        p = (json.load(open(mk)) or {}).get("route_prefix")
        if p:
            return p
    ctr = re.sub(r"_v\d+.*$", "", tag)
    ctr = ctr[1:] if ctr.startswith("r") else ctr
    cand = {}
    for p in glob.glob(os.path.join(RLOGS, "*_%s--*--rlog.zst" % ctr.rjust(8, "0"))):
        cand.setdefault("--".join(os.path.basename(p).split("--")[:2]), []).append(p)
    if len(cand) == 1:
        return list(cand)[0]
    if not cand:
        return None
    # 🛑 THE DONGLE COUNTER WAS RESET, so a counter can name two different routes (r35 and r6f both
    # do).  Disambiguate against the v280 cache's OWN duration -- segments are ~60 s, so the segment
    # count pins which route the cache was built from.  Never guess: a wrong prefix would silently
    # align a different drive's control path onto this drive's CAN grid.
    npz = os.path.join(CACHE, tag + ".npz")
    if not os.path.exists(npz):
        return None
    with np.load(npz) as D:
        want = float(D["t18"][-1] - D["t18"][0]) / 60.0
    best = min(cand, key=lambda k: abs(len(cand[k]) - want))
    if abs(len(cand[best]) - want) > 1.5:
        return None
    return best


def cs_cache_path(tag):
    return os.path.join(SCR, "cs_%s.npz" % tag)


def build_cs_cache(tag, prefix=None, force=False):
    """ONE rlog pass per route for the control path.  Returns the npz path, or None if no rlogs.

    Every field is read with getattr + a default, because the reference routes were logged by older
    fork builds and a missing field must degrade to NaN rather than kill the pass.  `epsTelemetry` is
    the KIT's name for union slot @137, which the fork publishes as `starpilotLateralState` -- readable
    only through the patched schema, so `sp_ff` is NaN-filled when the patch is unavailable.
    """
    out = cs_cache_path(tag)
    if os.path.exists(out) and not force:
        return out
    prefix = prefix or tag_prefix(tag)
    if not prefix:
        return None
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if not segs:
        return None
    clog, patched = fork_log_schema()
    import zstandard
    pr("  building the CONTROL-PATH cache for %s (%d segments, one pass; cached in _scratch/) ..."
       % (tag, len(segs)))
    C = {k: [] for k in ("t_cs",) + CS_FIELDS + ("des_curv", "curv")}
    C.update({k: [] for k in ("t_sp", "sp_ff", "sp_active", "sp_lsf")})
    C.update({k: [] for k in ("t_ltp", "ltp_off", "ltp_fac", "ltp_fric", "ltp_valid")})
    C.update({k: [] for k in ("t_lpar", "roll")})
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
            if w == "controlsState":
                try:
                    m = evt.controlsState
                    lcs = m.lateralControlState
                    st = getattr(lcs, lcs.which())
                except Exception:
                    continue
                C["t_cs"].append(tm)
                C["des_curv"].append(float(getattr(m, "desiredCurvature", np.nan)))
                C["curv"].append(float(getattr(m, "curvature", np.nan)))
                for nm, fld, cast in (("la_des", "desiredLateralAccel", float),
                                      ("la_act", "actualLateralAccel", float),
                                      ("f", "f", float), ("p", "p", float), ("i", "i", float),
                                      ("err", "error", float), ("out", "output", float),
                                      ("active", "active", lambda z: 1.0 if z else 0.0),
                                      ("sat", "saturated", lambda z: 1.0 if z else 0.0),
                                      ("version", "version", float)):
                    try:
                        C[nm].append(cast(getattr(st, fld)))
                    except Exception:
                        C[nm].append(np.nan)
            elif w == "epsTelemetry" and patched:
                # PATCHED name: this is the FORK's starpilotLateralState (same slot @137, same struct id)
                try:
                    s = evt.epsTelemetry
                    C["t_sp"].append(tm)
                    C["sp_ff"].append(float(s.feedforward))
                    C["sp_active"].append(1.0 if s.active else 0.0)
                    C["sp_lsf"].append(float(s.lowSpeedFactor))
                except Exception:
                    pass
            elif w == "liveTorqueParameters":
                try:
                    m = evt.liveTorqueParameters
                    C["t_ltp"].append(tm)
                    C["ltp_off"].append(float(getattr(m, "latAccelOffsetFiltered", np.nan)))
                    C["ltp_fac"].append(float(getattr(m, "latAccelFactorFiltered", np.nan)))
                    C["ltp_fric"].append(float(getattr(m, "frictionCoefficientFiltered", np.nan)))
                    C["ltp_valid"].append(1.0 if getattr(m, "liveValid", False) else 0.0)
                except Exception:
                    pass
            elif w == "liveParameters":
                try:
                    C["t_lpar"].append(tm)
                    C["roll"].append(float(getattr(evt.liveParameters, "roll", np.nan)))
                except Exception:
                    pass
    os.makedirs(SCR, exist_ok=True)
    np.savez(out, **{k: np.asarray(v, float) for k, v in C.items()},
             _patched=np.asarray([1.0 if patched else 0.0]))
    pr("    wrote %s : %d controlsState, %d starpilotLateralState, %d liveTorqueParameters frames"
       % (os.path.basename(out), len(C["t_cs"]), len(C["t_sp"]), len(C["t_ltp"])))
    return out


def resolve(arg, tag_override=None):
    """<arg> is a full route id, a route counter, or an existing cache tag.  Returns (tag, prefix)."""
    if os.path.exists(os.path.join(CACHE, arg + ".npz")):
        return arg, None
    m = re.match(r"^([0-9a-f]{16}_[0-9a-f]{8}--[0-9a-f]+)", arg)
    if m:
        prefix = m.group(1)
    else:
        hits = sorted(set(os.path.basename(p).split("--")[0] + "--" + os.path.basename(p).split("--")[1]
                          for p in glob.glob(os.path.join(RLOGS, "*%s*--rlog.zst" % arg))))
        if len(hits) != 1:
            raise SystemExit("cannot resolve %r: %d matching route prefixes on disk %s\n"
                             "  pass the full route id, or a cache tag that exists in %s"
                             % (arg, len(hits), hits[:4], CACHE))
        prefix = hits[0]
    ctr = prefix.split("_")[1].split("--")[0].lstrip("0") or "0"
    tag = tag_override or ("r%s_v293" % ctr)
    return tag, prefix


# ======================================================================================================
# 3.  LOADING
# ======================================================================================================
_CELLS = {}


def cells_for(build):
    """every cell read LITTLE-ENDIAN from the image itself -- never from a build script's constants."""
    if build not in _CELLS:
        c = L.read_cells(IMG[build])
        c["_build"] = build
        _CELLS[build] = c
    return _CELLS[build]


def load_route(tag, build):
    c = cells_for(build)
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["idx"], g["sgn"] = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    g["idx"] = np.round(g["idx"])
    bp = os.path.join(CACHE, tag + "_b4.npz")
    if os.path.exists(bp):
        B = np.load(bp)
        k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        g["_b4_t"], g["_b4"] = tn14, b4
        for bit in range(8):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
    r = types.SimpleNamespace(tag=tag, build=build, c=c, g=g, wire=g["wire"], eng=g["eng"],
                              ang=g["ang"], vego=g["vego"], bar=g["bar"], cmd=g["cmd"],
                              idx=g["idx"], T=g["T100"], t=g["tr"])
    return r


# ======================================================================================================
# 4.  SECTION 1 -- THE EDIT-LIVE IDENTITY
# ======================================================================================================
def tap_quantise(T):
    """the CAN-427 tap as the frame builder writes it: (sign(T)<<9) | (|T|>>3), 8 counts per LSB."""
    T = np.asarray(T, float)
    return np.sign(T) * (np.abs(T).astype(np.int64) >> 3).astype(float) * 8.0


def r2(y, yhat):
    y = np.asarray(y, float); yhat = np.asarray(yhat, float)
    ss = np.sum((y - y.mean()) ** 2)
    return float(1.0 - np.sum((y - yhat) ** 2) / ss) if ss > 0 else np.nan


def fade_multiplier(c, bar, vego, mode="bar"):
    """the ONE-STAGE post-PID taper at 0x2A13x:  factor = ((tapAB * tapCD) & 0xFFFF) >> 8.

    🛑 THE AXIS UNIT OF 0xCBBC4 IS OPEN.  The record's own mirror (grind_incident_r35 / v292_replay_lib
    prep_window) indexes it by |driver torque| >> 5; adversary A (ADV-V293-A) read it as SPEED IN KM/H
    and got a rail of 2151 at 10 m/s and 736 above 20 m/s.  Both readings are offered here and the
    drive itself discriminates: with the loop open the tap IS the surface, so whichever reading gives
    the higher R2 on a V293 route is EVIDENCE for the axis unit.  `const` is the at-rest value 254/256.
    """
    X, Y = c["fadeB"][0], c["fadeB"][1]
    if mode == "bar":
        u = np.abs(np.asarray(bar, float)) // 32.0
    elif mode == "speed":
        u = np.asarray(vego, float) * 3.6                    # km/h, adversary A's reading
    elif mode == "const":
        return np.full(len(np.atleast_1d(bar)), 254.0)
    else:
        raise ValueError(mode)
    B_ = np.interp(u, X, Y)
    return (((255.0 * B_).astype(np.int64)) & 0xFFFF) >> 8


def predict_tap(c, idx, sgn, m):
    """the delivered 427 tap predicted from the BUILT IMAGE's cells alone: T = f(cmd) * fade.

    `L.surface` marches the integer chain of FUN_00028ea6 with fb == 0 to its steady state.  With the
    feedback operand identically zero that steady state IS the delivered value on every frame, so no
    wheel-rate term enters -- which is precisely the claim being tested.
    """
    S = L.surface(c, np.asarray(idx, float), fb=0.0, fade=np.asarray(m, float))
    mag = np.abs(S["T"])
    signed = -np.asarray(sgn, float) * mag                   # sign(T) = -sign(sp), gain > 0
    return tap_quantise(signed), S


def identity_block(r, cellsets, lag_scan=(-4, 13)):
    """regress |427 tap| on f(cmd)*fade over every LATERALLY ENGAGED tap frame.

    The tap is sampled at its NATIVE 50 Hz (never up-sampled); the 100 Hz predictor is sampled onto it
    with previous-value (ZOH) semantics, which is how the ECU actually holds the command between frames.
    """
    g = r.g
    t_tap, T_tap = g["T_t"], g["T"]
    j = np.searchsorted(g["t"], t_tap, side="right") - 1
    ok = (j >= 0) & (j < len(g["t"]))
    res = dict(n_tap=int(ok.sum()))
    out = {}
    for name, c in cellsets:
        for fmode in ("bar", "speed", "const"):
            m100 = fade_multiplier(c, g["bar"], g["vego"], fmode)
            idx100, sgn100 = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
            idx100 = np.round(idx100)
            pred100, S = predict_tap(c, idx100, sgn100, m100)
            best = None
            for k in range(lag_scan[0], lag_scan[1]):
                jj = np.clip(j + k, 0, len(g["t"]) - 1)
                sel = ok & g["eng"][jj]
                if sel.sum() < 200:
                    continue
                y, yh = np.abs(T_tap[sel]), np.abs(pred100[jj[sel]])
                v = r2(y, yh)
                rs = float(np.sqrt(np.mean((y - yh) ** 2)))
                # the estimator has ZERO free parameters: no scale, no offset.  R2 near 1 therefore
                # means the BYTES PREDICT THE WIRE, not merely that the two correlate -- which is why
                # Pearson r is carried beside it.  A high r with a failing R2 is a SCALE error; a low
                # r is a structural one.
                cc = np.corrcoef(y, yh)[0, 1] if (y.std() > 0 and yh.std() > 0) else float("nan")
                sg = float(np.mean(np.sign(T_tap[sel]) == np.sign(pred100[jj[sel]])))
                sgc = float(np.mean(np.sign(T_tap[sel]) == -np.sign(g["cmd"][jj[sel]])))
                rms = float(np.sqrt(np.mean(y ** 2)))
                row = dict(lag_frames=k, lag_ms=k * 10.0, r2=v, resid=rs, n=int(sel.sum()),
                           pearson=float(cc), sign_pred=sg, sign_negcmd=sgc,
                           resid_norm=(rs / rms if rms > 0 else float("nan")))
                if best is None or v > best["r2"]:
                    best = row
                if k == 0:
                    res["%s/%s/lag0" % (name, fmode)] = row
            out["%s/%s" % (name, fmode)] = best
            if fmode == "bar":
                res["%s/_derate" % name] = dict(
                    n_speed_derate=int((fade_multiplier(c, g["bar"], g["vego"], "speed")[j[ok]] < 254).sum()),
                    n_bar_derate=int((m100[j[ok]] < 254).sum()),
                    n=int(ok.sum()),
                    m_bar_p50=float(np.median(m100[j[ok]])),
                    m_speed_p50=float(np.median(fade_multiplier(c, g["bar"], g["vego"], "speed")[j[ok]])))
    res["fits"] = out
    return res


def positive_control(r, c293, nwin=6, wlen=1500):
    """synthesise a V293 tap from the route's OWN recorded command, by the byte-exact 1 kHz march.

    NOT a tautology: the predictor regressed against is the STEADY-STATE surface; this synthetic tap
    comes from `v292_replay_lib.Elec`, which carries the feedback lag, the output lag and every floor.
    With c['fb_clamp'] == 0 the rate operand is clamped to +-0 -- the same identity the cell asserts.
    """
    g = r.g
    runs = [(a, b) for a, b in C20.runs(g["eng"], wlen)]
    if not runs:
        return None
    take = runs[:: max(1, len(runs) // nwin)][:nwin]
    acc = []
    for a, b in take:
        b = min(b, a + wlen)
        W = RL.prep_window(g, a, b, c293)
        el = RL.Elec(c293, fb=RL.V282_FB, ef=False, two_floor=True, kd=0.0)
        x1k = np.round(C20.up1k(np.asarray(g["wire"][W["seg"]], float))).astype(np.int64)
        x1k = -x1k                                          # the ECU's operand is -(wire rate)
        S = el.run(x1k, W["sp"], W["kp"], W["m"], W["eng"])
        sl = slice(800, None, 20)                           # settle, then decimate to the tap's 50 Hz
        tap = tap_quantise(S["T"][sl])
        pred, _ = predict_tap(c293, W["idx"][sl],
                              np.where(W["sp"][sl] < 0, -1.0, 1.0), W["m"][sl])
        e = W["eng"][sl]
        if e.sum() < 100:
            continue
        acc.append((r2(np.abs(tap[e]), np.abs(pred[e])),
                    float(np.sqrt(np.mean((np.abs(tap[e]) - np.abs(pred[e])) ** 2))),
                    int(e.sum())))
    if not acc:
        return None
    A_ = np.array(acc, float)
    return dict(n_win=len(acc), r2_p50=float(np.median(A_[:, 0])), resid_p50=float(np.median(A_[:, 1])),
                r2_min=float(A_[:, 0].min()), n=int(A_[:, 2].sum()))


# ======================================================================================================
# 5.  SECTIONS 2 / 5 -- THE BANDS, BY THE DRIVE-CONTROLLED MEASURE
# ======================================================================================================
STRATA = (
    ("hands-off creep 1-3 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)),
    ("hands-off 3-8 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 3) & (g["vego"] < 8)),
    ("hands-off 8-15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 8) & (g["vego"] < 15)),
    ("hands-off >=15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 15)),
    ("hands-off ALL speeds", lambda g: g["eng"] & (np.abs(g["bar"]) < 400)),
    ("ALL engaged", lambda g: g["eng"]),
    ("DISENGAGED (loop OPEN)", lambda g: ~g["eng"]),
)


def band_amp_of(f, P, lo, hi):
    sl = (f >= lo) & (f <= hi)
    return float(np.sqrt(2.0 * P.mean(0)[sl].sum() * (f[1] - f[0])) / CPD)


def spectra(g, nperseg=256):
    """pooled Welch on the 0x18F rate per stratum.  NO episode selection anywhere, so a change in
    presence rate cannot leak into an amplitude and vice versa.  Amplitudes in deg/s."""
    out = {}
    for lab, fn in STRATA:
        m = fn(g)
        runs = [g["wire"][a:b] for a, b in C20.runs(m, nperseg)]
        f, P = C88.seg_psds(runs, FS, nperseg)
        if P.shape[0] < 5:
            out[lab] = dict(t_s=float(m.sum() / FS), n_seg=int(P.shape[0]), amps=None)
            continue
        amps = {nm: band_amp_of(f, P, lo, hi) for nm, lo, hi in BANDS}
        ex = C88.excess_db(f, P.mean(0), half_hz=2.0)
        lines = {}
        for nm, lo, hi in (("10-17", 10, 17), ("17-24", 17, 24), ("22-30", 22, 30), ("5-9.5", 5, 9.5)):
            sl = (f >= lo) & (f <= hi)
            k = int(np.argmax(ex[sl]))
            lines[nm] = (float(f[sl][k]), float(ex[sl][k]))
        out[lab] = dict(t_s=float(m.sum() / FS), n_seg=int(P.shape[0]), amps=amps, lines=lines)
    return out


def eng_over_dis(sp):
    """the measure that survives the fork change: engaged band amplitude / the SAME route's
    lateral-DISENGAGED amplitude.  With STEER_REQUEST = 0 the rate loop is open, so this is how much
    the engaged loop adds over that route's own input.  [EVIDENCE, with one real limitation]
    the disengaged reference is mostly STATIONARY on every route (V292-FLIGHT-READ 4.1) -- it is
    like-for-like BETWEEN builds, but it is not a road-input normalisation."""
    e = sp.get("ALL engaged", {}).get("amps")
    d = sp.get("DISENGAGED (loop OPEN)", {}).get("amps")
    if not e or not d:
        return None
    return {k: (e[k] / d[k] if d[k] > 0 else float("nan")) for k in e}


def presence(g, mask, W=200, STEP=50, label=""):
    """the record's own predicate, unchanged: 2 s windows on a 0.5 s grid; PRESENT = 18-22 Hz
    prominence >= 8 on the DRIVER-TORQUE bar AND 18-22 Hz bar amplitude >= 40 (grind1_census_v282).
    The predicate reads the BAR, not the EPS torque, so the torque-map edit cannot move it directly.

    ⚠ SLOW ON PURPOSE: `line_of` runs the record's 4096-point prominence spectrum per window (~0.1 s).
    It is NOT optimised, because every published presence number in the corpus came out of this exact
    call and a faster floor would silently move the comparison.  ~1 s per 10 s of engaged time."""
    ra, npres, n, f0s = [], 0, 0, []
    import time as _time
    t0, nexp = _time.time(), max(1, int(mask.sum() / STEP))
    for a, b in C20.runs(mask, W):
        for s in range(a, b - W + 1, STEP):
            e = s + W
            f0, prom = CEN.line_of(g["bar"][s:e], FS)
            amp = CEN.band(g["bar"][s:e], 18, 22)
            n += 1
            if n % 500 == 0:
                print("      presence %s: %d/%d windows, %.0f s elapsed"
                      % (label, n, nexp, _time.time() - t0), flush=True)
            if prom >= 8 and amp >= 40:
                npres += 1
                ra.append(CEN.band(g["wire"][s:e], 18, 22) / CPD)
                f0s.append(f0)
    ra = np.asarray(ra, float)
    return dict(n_win=n, n_pres=npres, pres_pct=(100.0 * npres / n if n else float("nan")),
                amp_p50=(float(np.median(ra)) if len(ra) else float("nan")),
                amp_p90=(float(np.percentile(ra, 90)) if len(ra) else float("nan")),
                f0_p50=(float(np.median(f0s)) if f0s else float("nan")))


# ======================================================================================================
# 6.  SECTION 3 -- F7, THE TAP RIPPLE AND THE 5-9 Hz WHEEL BAND
# ======================================================================================================
def band_amp(x, lo, hi, fs=FS):
    x = np.asarray(x, float)
    if len(x) < 30:
        return float("nan")
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return float(np.sqrt(2.0) * signal.sosfiltfilt(sos, x - x.mean()).std())


def peak_in(x, lo, hi, fs=FS):
    x = np.asarray(x, float)
    if len(x) < 64:
        return float("nan"), float("nan")
    f, P = signal.welch(x - x.mean(), fs=fs, nperseg=min(len(x), 256))
    sl = (f >= lo) & (f <= hi)
    if not sl.any():
        return float("nan"), float("nan")
    k = int(np.argmax(P[sl]))
    return float(f[sl][k]), float(np.sqrt(2.0 * P[sl][k] * (f[1] - f[0])))


def strongturn(r):
    """the record's own instrument, thresholds unchanged.
    F7  : ST.fixed_thr_episodes(thr=103, band 2-8 Hz); |angle| >= 30 AND fdom >= 6; per 100 s of
          ENGAGED HIGH-ANGLE time.  REVERT at >= 2 / 100 s.
    rip : stutter_v283 SECTION C -- engaged, |angle| >= 30, v <= 10 m/s, |bar| < 2240, idx >= 40;
          1 s windows on a 0.5 s grid; rip/L = tap 6-8.5 Hz amplitude / median |T|.  REVERT at >= 0.25.
          The ABSOLUTE ripple is reported too, because torque mode grows the denominator x1.2-3.6 and
          a falling RATIO can hide a rising ripple (DESIGN 6.2)."""
    hs = float((r.eng & (np.abs(r.ang) >= 30)).sum() / FS)
    eps = ST.fixed_thr_episodes(r, thr=103.0)
    hi = [e for e in eps if e["ang"] >= 30]
    f7 = [e for e in hi if e["fdom"] >= 6]
    res = dict(hi_ang_s=hs, n_eps=len(eps), n_hi=len(hi), n_f7=len(f7),
               f7_per100=(100.0 * len(f7) / hs if hs > 1 else float("nan")),
               f7_fdom=[round(e["fdom"], 2) for e in f7[:10]])
    for thr in (80, 60, 40):
        e2 = ST.fixed_thr_episodes(r, thr=float(thr))
        n2 = len([e for e in e2 if e["ang"] >= 30 and e["fdom"] >= 6])
        res["f7_per100_thr%d" % thr] = (100.0 * n2 / hs if hs > 1 else float("nan"))
    W, STEP = int(FS), int(FS / 2)
    m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.bar) < 2240) & (r.idx >= 40)
    rows = []
    for a, b in C20.runs(m, W):
        for s in range(a, b - W + 1, STEP):
            e = s + W
            Tw = r.T[s:e]
            lvl = float(np.median(np.abs(Tw)))
            rip = band_amp(Tw, 6.0, 8.5)
            f0, _ = peak_in(r.wire[s:e], 5.5, 9.5)
            rows.append(dict(f0=f0, rip=rip, lvl=lvl,
                             ripL=(rip / lvl if lvl > 1 else float("nan")),
                             rate68=band_amp(r.wire[s:e], 6.0, 8.5) / CPD,
                             tq50=float(np.median(np.abs(r.bar[s:e])))))
    res["n_win"] = len(rows)
    for key, sub in (("all", lambda x: True), ("light", lambda x: x["tq50"] < 1216)):
        rr = [x for x in rows if sub(x)]
        res["n_win_" + key] = len(rr)
        if len(rr) < 3:
            continue
        res["ripL_p50_" + key] = float(np.nanmedian([x["ripL"] for x in rr]))
        res["ripL_p90_" + key] = float(np.nanpercentile([x["ripL"] for x in rr], 90))
        res["rip_abs_p50_" + key] = float(np.nanmedian([x["rip"] for x in rr]))
        res["lvl_p50_" + key] = float(np.nanmedian([x["lvl"] for x in rr]))
        res["rate68_p50_" + key] = float(np.nanmedian([x["rate68"] for x in rr]))
        res["f0_p50_" + key] = float(np.nanmedian([x["f0"] for x in rr]))
    for lab, fn in (("ang30_off", lambda: (np.abs(r.ang) >= 30) & (np.abs(r.bar) < 400)),
                    ("ang30_light", lambda: (np.abs(r.ang) >= 30) & (np.abs(r.bar) >= 400) & (np.abs(r.bar) < 1216))):
        mm = r.eng & fn()
        segs = [(a, b) for a, b in C20.runs(mm, 100)]
        res["t_s_" + lab] = float(mm.sum() / FS)
        if sum(b - a for a, b in segs) < 300:
            continue
        res["w59_" + lab] = float(np.nanmedian([band_amp(r.wire[a:b], 5, 9) / CPD for a, b in segs]))
        res["w1822_" + lab] = float(np.nanmedian([band_amp(r.wire[a:b], 18, 22) / CPD for a, b in segs]))
        res["T68_" + lab] = float(np.nanmedian([band_amp(r.T[a:b], 6, 8.5) for a, b in segs]))
    return res


# ======================================================================================================
# 7.  SECTION 4 -- THE OUTER LOOP (the V276 1-4 Hz signature)
# ======================================================================================================
SPEED_BANDS = (("0-5 m/s", 0.0, 5.0), ("5-10 m/s", 5.0, 10.0),
               ("10-20 m/s", 10.0, 20.0), (">=20 m/s", 20.0, 99.0))


def outer_loop(r, nperseg=512):
    """a 1-4 Hz line SHARED by the 0xE4 command and the steering angle is the V276 signature: the
    combined openpilot + EPS loop limit-cycling.  Scored per speed band, LOW SPEED FIRST -- the
    orchestrator's adjudication of B6 named the 5 m/s creep margin as the thinnest, on BOTH builds.
    Coherence is the discriminator: road input moves the angle without moving the command."""
    g = r.g
    res = {}
    for lab, lo, hi in SPEED_BANDS:
        m = g["eng"] & (g["vego"] >= lo) & (g["vego"] < hi)
        runs = [(a, b) for a, b in C20.runs(m, nperseg)]
        tt = sum(b - a for a, b in runs) / FS
        if tt < 20:
            res[lab] = dict(t_s=float(m.sum() / FS), n_run=len(runs), scored=False)
            continue
        Ca, Aa, Ka, Fa = [], [], [], []
        for a, b in runs:
            x = g["cmd"][a:b].astype(float)
            y = g["ang"][a:b].astype(float)
            f, Cxy = signal.coherence(x - x.mean(), y - y.mean(), fs=FS, nperseg=nperseg)
            _, Px = signal.welch(x - x.mean(), fs=FS, nperseg=nperseg)
            _, Py = signal.welch(y - y.mean(), fs=FS, nperseg=nperseg)
            sl = (f >= 1.0) & (f <= 4.0)
            k = int(np.argmax(Cxy[sl]))
            df = f[1] - f[0]
            Ca.append(float(Cxy[sl][k])); Fa.append(float(f[sl][k]))
            Aa.append(float(np.sqrt(2.0 * Px[sl].sum() * df)))
            Ka.append(float(np.sqrt(2.0 * Py[sl].sum() * df)))
        res[lab] = dict(t_s=float(m.sum() / FS), n_run=len(runs), scored=True,
                        coh_p90=float(np.percentile(Ca, 90)), coh_p50=float(np.median(Ca)),
                        f_at_coh=float(np.median(Fa)),
                        cmd14=float(np.median(Aa)), ang14_deg=float(np.median(Ka)))
    return res


# ======================================================================================================
# 8.  SECTION 6 -- THE 0x14A CAVE DUTIES
# ======================================================================================================
def cave_duties(r):
    """b4 = sign(r24) -- the NEGATIVE CONTROL, identical by construction (r24 does not depend on T).
    b7 = sign(gp-0x6b4c), the LKAS summand -- the pre-registered MOVER, 0.996 -> 0.808.
    b6 = |r24| >= |T| and b5 = |r24| >= |aggregator sum| -- NOT pre-registered (inside duty noise).
    b3 stays V282's aliased bit.  b0-b2 are stock Honda and must read 1.000 on every build."""
    g = r.g
    if "_b4" not in g:
        return None
    t14, b4 = g["_b4_t"], g["_b4"]
    sca14 = np.interp(t14, g["t"], g["sca"].astype(float)) > 0.5
    req14 = np.interp(t14, g["t"], g["req"].astype(float)) > 0.5
    eng14 = sca14 & req14
    v14 = np.interp(t14, g["t"], g["vego"])
    absr = np.abs(np.interp(t14, g["t"], g["wire"]))
    ker = np.ones(101) / 101.0
    still = (np.convolve(absr, ker, mode="same") < 1.0) & (absr < 1.0) & (v14 < 0.3)
    out = {}
    for lab, m in (("engaged", eng14), ("SCA=0", ~sca14), ("IDLE still", still)):
        out[lab] = {("b%d" % n): (float(((b4 >> n) & 1)[m].mean()) if m.sum() > 20 else float("nan"))
                    for n in range(8)}
        out[lab]["n"] = int(m.sum())
    return out


def fork_toggles(prefix, max_seg=None):
    """read ONLY the toggle sources from a route's rlogs: initData.params, controlsState...torqueState
    (f, desiredLateralAccel, p, error) and the Testing Ground heartbeat.

    Written to the STUDY's own _scratch, never into the shared v280 cache -- a route the record
    already owns must not have its cache rewritten by this tool.
    """
    # 🛑 THE CACHE KEY CARRIES THE KEY SET.  v1 keyed only on the route, so adding a param to
    # WANT_PARAMS would have silently kept serving a dump that never captured it -- and a key that was
    # never CAPTURED is indistinguishable from a key that is ABSENT from the store, which is the exact
    # shape of a silent wrong answer.  The hash forces a re-read when the list changes.
    import hashlib
    kh = hashlib.sha1(("|".join(sorted(WANT_PARAMS))).encode("utf-8")).hexdigest()[:8]
    out = os.path.join(SCR, "fork_toggles3_%s_%s.json" % (prefix, kh))
    if os.path.exists(out):
        return json.load(open(out))
    clog, patched = fork_log_schema()
    import zstandard
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    if max_seg:
        segs = segs[:max_seg]
    if not segs:
        return {}
    pr("  reading the fork toggles from %d rlog segments (once; cached in _scratch) ..." % len(segs))
    tq, params, tg = [], None, {}
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
            if w == "modelDataV2SP" and patched:
                _tg_collect(evt, tg)
            elif w == "controlsState":
                try:
                    ls = evt.controlsState.lateralControlState
                    if ls.which() == "torqueState":
                        t_ = ls.torqueState
                        tq.append((float(t_.f), float(t_.desiredLateralAccel), bool(t_.active),
                                   float(t_.p), float(t_.error)))
                except Exception:
                    pass
            elif w == "initData" and params is None:
                try:
                    params = {e.key: bytes(e.value).decode("utf-8", "replace")
                              for e in evt.initData.params.entries if e.key in WANT_PARAMS}
                except Exception:
                    pass
    d = dict(params or {})
    d.update(_tg_readable=bool(patched), _written_by="v293_flight_read.py",
             _want_params=sorted(WANT_PARAMS))
    d.update(_torque_state_stats(tq))
    d.update(_tg_summary(tg))
    json.dump(d, open(out, "w"), indent=1, default=float)
    return d


def _tg_collect(evt, acc):
    """the Testing Ground selection, off the PATCHED `modelDataV2SP` (= the fork's customReserved9).

    Guarded: a pre-rework rlog carries the genuine ModelDataV2SP on this slot, whose Text pointers are
    absent, so every field decodes empty.  Only a non-empty slotId is treated as a real reading.
    """
    try:
        c = evt.modelDataV2SP
        sid = str(c.slotId or "").strip()
        if not sid:
            return
        key = (sid, str(c.variant or "").strip().upper())
        acc["n"] = acc.get("n", 0) + 1
        acc.setdefault("pairs", {})
        acc["pairs"][key] = acc["pairs"].get(key, 0) + 1
        acc["slotName"] = str(c.slotName or "")
        acc["variantLabel"] = str(c.variantLabel or "")
    except Exception:
        pass


def _tg_summary(acc):
    """majority (slot, variant) -- informational; no slot is the torque mode."""
    d = dict(_tg_frames=acc.get("n", 0), _tg_slot=None, _tg_variant=None,
             _tg_slot_name=acc.get("slotName"), _tg_variant_label=acc.get("variantLabel"),
             _tg_pairs=None)
    pairs = acc.get("pairs") or {}
    if not pairs:
        return d
    d["_tg_pairs"] = {"%s/%s" % k: v for k, v in sorted(pairs.items(), key=lambda z: -z[1])}
    (sid, var), _ = max(pairs.items(), key=lambda z: z[1])
    d["_tg_slot"], d["_tg_variant"] = sid, var
    return d


def _torque_state_stats(tq):
    """the two CONTROL-PATH reads of the fork tune.  f/D: the torque config ships friction 0, so
    f = desiredLateralAccel exactly (the rate-plant branch reads ~0.3).  Kp: p / error == SteerKP on
    every active frame (the fork logs the LSF-inflated error and feeds the same number to the PID)."""
    if not tq:
        return dict(_torqueState_n=0, _torqueState_slope_f_vs_D=None, _torqueState_fD_p50=None,
                    _kp_hat=None, _kp_n=0)
    Q = np.asarray(tq, float)
    sel = (Q[:, 2] > 0.5) & (np.abs(Q[:, 1]) >= 0.3)
    d = dict(_torqueState_n=int(len(Q)), _torqueState_n_fit=int(sel.sum()), _kp_hat=None, _kp_n=0)
    if Q.shape[1] >= 5:
        k = (Q[:, 2] > 0.5) & (np.abs(Q[:, 4]) >= 0.02)
        d["_kp_n"] = int(k.sum())
        if k.sum() >= 50:
            r = Q[k, 3] / Q[k, 4]
            med = float(np.median(r))
            d.update(_kp_hat=med, _kp_iqr=[float(np.percentile(r, 25)), float(np.percentile(r, 75))],
                     _kp_within5pct=(float(np.mean(np.abs(r - med) <= 0.05 * abs(med))) if med else None))
    if sel.sum() < 50:
        d.update(_torqueState_slope_f_vs_D=None, _torqueState_fD_p50=None)
        return d
    sl, ic = np.polyfit(Q[sel, 1], Q[sel, 0], 1)
    d.update(_torqueState_slope_f_vs_D=float(sl), _torqueState_intercept=float(ic),
             _torqueState_fD_p50=float(np.median(Q[sel, 0] / Q[sel, 1])), _torqueState_fD_by_band={})
    for lo, hi in ((0.3, 0.6), (0.6, 0.9), (0.9, 1.3), (1.3, 2.0)):
        s2 = (Q[:, 2] > 0.5) & (np.abs(Q[:, 1]) >= lo) & (np.abs(Q[:, 1]) < hi)
        d["_torqueState_fD_by_band"]["%.1f-%.1f" % (lo, hi)] = (
            [float(np.median(Q[s2, 0] / Q[s2, 1])), int(s2.sum())] if s2.sum() > 50
            else [None, int(s2.sum())])
    return d


def read_params(tag, prefix=None):
    """the route's params, augmented with the toggle sources if its cache predates this tool.

    🛑 Never rewrites the shared cache: the augmentation lands in the study's own _scratch.
    """
    p = os.path.join(CACHE, tag + "_params.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    # 🛑 A cache written before a key joined WANT_PARAMS does not CARRY that key, and "not captured"
    # would then read as "absent from the store = its default".  Re-read the rlogs in that case.
    covered = set(d.get("_want_params") or []) >= set(WANT_PARAMS)
    if "_written_by" in d and "_kp_hat" in d and covered:
        return d
    mk = json.load(open(os.path.join(CACHE, tag + "_marks.json"))) \
        if os.path.exists(os.path.join(CACHE, tag + "_marks.json")) else {}
    pref = prefix or mk.get("route_prefix")
    if not pref:
        return d
    try:
        extra = fork_toggles(pref)
    except Exception as e:
        pr("  ⚠ could not read the fork toggles from the rlogs (%s)" % str(e)[:70])
        return d
    merged = dict(extra)
    merged.update({k: v for k, v in d.items() if not k.startswith("_")})
    merged["_augmented_from_rlogs"] = True
    return merged


# ======================================================================================================
# 8b. SECTION 7 -- THE OPERATOR'S FOUR SYMPTOMS, and the BRANCH IDENTITY   [v2, 2026-09-13]
# ======================================================================================================
SYM_REFS_JSON = os.path.join(SCR, "v293_symptom_refs.json")
# r70_v293 is a REFERENCE COLUMN, not just the route under test: every future drive is read against
# the rev-1 flight the operator scored those four symptoms on.
SYM_REF_ROUTES = ("r70_v293", "r6c", "r39", "r35")
SYM_REF_V282 = "r6c"
SYM_GRID_VERSION = "sym-grid-1"     # bump when sym_grid's masks or resampling change


def sym_code_hash():
    """the reference cache is keyed by the INSTRUMENT CODE, so a change to any definition invalidates
    every cached reference instead of silently comparing this drive against numbers from an older
    estimator.  That is the failure the kit has hit before with hand-copied reference literals."""
    import hashlib
    h = hashlib.sha1()
    h.update(io.open(SI.__file__, "rb").read())
    h.update(SYM_GRID_VERSION.encode("utf-8"))
    return h.hexdigest()[:16]


def sym_grid(tag, prefix=None):
    """ONE 100 Hz grid, built the way the identification built its own, so every instrument here
    reproduces its published number exactly (checked on r70_v293 -- see the positive control).

      t0 = the first 0x18F frame; t1 = the earliest last frame of 0x18F / 0x14A / 0xE4 / carState.
      Every channel is ZOH-sampled onto it: previous value held, which is what the consumer sees.

    🛑 TWO HANDS-OFF MASKS, and they are NOT interchangeable:
      `ho_buf`  engaged & not pressed with a +-0.5 s buffer -- the RATCHET stratum (v293_ident_k.py).
      `ho`      engaged & not pressed, NO buffer, plus finite control-path fields -- the stratum every
                CONTROL-PATH instrument uses (v293_ident_i.py / _c.py).
    Using one for the other moves the step count 29 -> 23 and the 8-15 m/s tracking gain 0.884 ->
    0.808.  MEASURED, 2026-09-13; the split is deliberate and both sides reproduce their source.
    """
    d = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = float(d["t18"][0])
    t1 = float(min(d["t18"][-1], d["t14"][-1], d["te4"][-1], d["tcs"][-1]))
    ta = np.arange(0.0, t1 - t0, 1.0 / FS) + t0

    def zoh(ts, ys):
        j = np.searchsorted(ts, ta, side="right") - 1
        o = np.full(len(ta), np.nan)
        ok = j >= 0
        o[ok] = np.asarray(ys, float)[j[ok]]
        return o

    g = dict(tag=tag, t=ta - t0, rate=zoh(d["t18"], d["rate"]) / CPD, ang=zoh(d["t14"], d["ang"]),
             cmd=zoh(d["te4"], d["cmd"]), v=zoh(d["tcs"], d["vego"]))
    g["eng"] = (zoh(d["te4"], d["req"]) > 0.5) & (zoh(d["t18"], d["sca"]) > 0.5)
    if "cs_press" in d:
        p = zoh(d["tcs"], d["cs_press"]) > 0.5
        w = int(0.5 * FS)
        g["ho_buf"] = g["eng"] & ~(np.convolve(p.astype(float), np.ones(2 * w + 1), "same") > 0)
        g["ho_raw"] = g["eng"] & ~p
        g["has_press"] = True
    else:
        g["ho_buf"] = g["ho_raw"] = None
        g["has_press"] = False
    csp = build_cs_cache(tag, prefix)
    g["has_cs"] = bool(csp)
    if csp:
        C = dict(np.load(csp))
        for k in CS_FIELDS + ("des_curv", "curv"):
            g[k] = zoh(C["t_cs"], C[k])
        for nm, tk, vk in (("sp_ff", "t_sp", "sp_ff"), ("sp_lsf", "t_sp", "sp_lsf"),
                           ("roll", "t_lpar", "roll")):
            g[nm] = zoh(C[tk], C[vk]) if len(C[tk]) else np.full(len(ta), np.nan)
        g["ltp_off"] = np.asarray(C["ltp_off"], float)
        g["ltp_valid"] = np.asarray(C["ltp_valid"], float)
        fin = np.isfinite(g["la_des"]) & np.isfinite(g["la_act"])
        base = g["ho_raw"] if g["ho_raw"] is not None else g["eng"]
        g["ho"] = base & fin
        g["ho_is_proxy"] = not g["has_press"]
    return g


def symptom_block(tag, prefix=None):
    """every pre-registered symptom instrument, on one route.  Returns a plain dict (JSON-safe)."""
    g = sym_grid(tag, prefix)
    S = dict(tag=tag, has_cs=g["has_cs"], has_press=g["has_press"],
             eng_s=float(g["eng"].sum()) / FS)
    # --- 1. ratchet ---------------------------------------------------------------------------------
    S["dwell_eng"] = SI.dwells(g["rate"], g["ang"], g["v"], g["eng"])
    S["dwell_ho"] = (SI.dwells(g["rate"], g["ang"], g["v"], g["ho_buf"])
                     if g["ho_buf"] is not None else None)
    S["conc"] = SI.rate_concentration(g["rate"], g["cmd"], g["v"], g["eng"])
    # --- 2. loose (the wander half is CAN-only, so it exists on every route) -------------------------
    S["wander"] = SI.angle_wander(g["ang"], g["rate"], g["v"], g["eng"])
    # --- report row: 1-4 Hz, CAN-only -----------------------------------------------------------------
    S["prom"] = SI.prominence_1_4(g["ang"], g["cmd"], g["rate"], g["v"], g["eng"])
    if not g["has_cs"]:
        return S
    ho = g["ho"]
    S["ho_s"] = float(ho.sum()) / FS
    S["stiff"] = SI.loop_stiffness(g["cmd"], g["ang"], g["la_des"], g["la_act"], g["out"], g["v"], ho)
    S["hold"] = SI.turn_hold(g["la_des"], g["la_act"], g["v"], ho)
    S["track"] = SI.tracking_gain(g["la_des"], g["la_act"], g["v"], ho)
    S["step"] = SI.step_overshoot(g["la_des"], g["la_act"], g["i"], g["v"], ho)
    S["shares"] = SI.pid_shares(g["f"], g["p"], g["i"], g["v"], ho)
    S["regime"] = SI.regime_delivery(g["la_des"], g["la_act"], g["v"], ho)
    S["branch"] = SI.branch_identity(g["f"], g["sp_ff"], g["la_des"], g["des_curv"], g["v"],
                                     g["roll"], g["active"])
    S["laf"] = SI.laf_identity(g["p"], g["i"], g["f"], g["out"], g["active"])
    fade = np.interp(g["v"], [0.5, 2.5], [0.0, 1.0])
    act = g["active"] > 0.5
    if act.any() and np.isfinite(g["roll"]).any():
        m = act & np.isfinite(g["roll"])
        S["branch"]["roll_term_p50"] = float(np.median(9.81 * g["roll"][m] * fade[m]))
    if len(g["ltp_off"]):
        S["branch"]["ltp_off_published_p50"] = float(np.median(g["ltp_off"]))
        S["branch"]["ltp_valid_frac"] = float(np.mean(g["ltp_valid"]))
    if np.isfinite(g["roll"]).any():
        S["branch"]["roll_p50_rad"] = float(np.nanmedian(g["roll"][ho])) if ho.any() else None
    return S


def symptom_refs(routes=SYM_REF_ROUTES, force=False):
    """the reference numbers for section 7, RE-DERIVED by this code on the cached routes and cached
    under _scratch/ keyed by `sym_code_hash()`.  🛑 They are never copied from
    V293-PLANT-IDENT-2026-09-13.md -- that is what keeps the comparison honest when a definition
    changes."""
    key = sym_code_hash()
    blob = {}
    if os.path.exists(SYM_REFS_JSON) and not force:
        try:
            blob = json.load(open(SYM_REFS_JSON))
        except Exception:
            blob = {}
    if blob.get("_code") == key and all(r in blob.get("routes", {}) for r in routes):
        return blob["routes"]
    pr("  computing the section 7 reference numbers on %s (code %s; cached in _scratch/) ..."
       % (", ".join(routes), key))
    out = {}
    for rt in routes:
        if not os.path.exists(os.path.join(CACHE, rt + ".npz")):
            pr("    %s: no v280 cache -- skipped" % rt)
            continue
        try:
            out[rt] = symptom_block(rt)
        except Exception as e:
            pr("    %s: %s" % (rt, str(e)[:90]))
    json.dump(dict(_code=key, _built="v293_flight_read.py", routes=out),
              open(SYM_REFS_JSON, "w"), indent=1, default=float)
    return out


# --- the identification's OWN published numbers, used ONLY as the POSITIVE CONTROL on r70_v293 -------
# 🛑 These are NOT used as references anywhere.  They exist so the scorecard can show that this code,
# run on the cached route, reproduces V293-PLANT-IDENT-2026-09-13.md -- and so a future edit that
# silently moves an estimator is caught.  Tolerance is stated with the check.
IDENT_R70 = {
    "dwell025_eng": (15.23, 7.66, 4.56, 1.24),          # H2, all-engaged
    "dwell025_ho": (20.97, 8.08, 5.26, 1.27),           # H2, hands-off
    "conc": (0.371, 0.438, 0.454, 0.468, 0.361),        # H9, rate-magnitude concentration
    "stiff": (0.0032, 0.0065, 0.0128, 0.0227),          # G2, torque per degree
    "hold": (None, None, 0.937, 1.093),                 # G3
    "track": (None, 0.884, 1.020, 1.123),               # C1, on the IDENT band grid
    "step": (None, 0.166, 0.437, 0.341),                # G4, relative overshoot
    "prom": (6.51, 11.78, 7.65, 3.08),                  # E5, dB
    "rate14": (59.1, 23.0, 8.2, 2.3),                   # E5, deg/s
    "i_share": (0.350, 0.348, 0.382, 0.384),            # C2, on the IDENT band grid
    "straight": 0.800,                                  # C4
}
IDENT_TOL = 0.02          # relative; absolute floor below


def _within(got, want, rel=IDENT_TOL, absf=0.003):
    if got is None or want is None:
        return None
    return abs(got - want) <= max(absf, rel * abs(want))


# ======================================================================================================
# 9.  SCORE ONE ROUTE -- everything above, into one dict
# ======================================================================================================
def score_route(tag, build, with_positive=True, prefix=None, with_symptoms=True):
    r = load_route(tag, build)
    g = r.g
    S = dict(tag=tag, build=build, image=os.path.basename(IMG[build]),
             route_s=float(g["t"][-1] - g["t"][0]),
             engaged_s=float(g["eng"].sum() / FS),
             disengaged_s=float((~g["eng"]).sum() / FS),
             handsoff_s=float((g["eng"] & (np.abs(g["bar"]) < 400)).sum() / FS),
             hiang_s=float((g["eng"] & (np.abs(g["ang"]) >= 30)).sum() / FS),
             creep_s=float((g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)).sum() / FS),
             cells={k: (int(r.c[k]) if np.isscalar(r.c[k]) else None)
                    for k in ("fb_clamp", "d_clamp", "p_clamp", "sum_clamp", "t_clamp", "ki",
                              "r24_arm", "gain")},
             kp_Y=np.asarray(r.c["kp_Y"]).astype(int).tolist(),
             kd_Y=np.asarray(r.c["kd_Y"]).astype(int).tolist())
    # --- 1. identity, scored under BOTH cell sets so the comparison is inside the same frames -------
    cs = [(build, r.c)]
    if build != "V282":
        cs.append(("V282", cells_for("V282")))
    S["identity"] = identity_block(r, cs)
    if with_positive:
        S["positive"] = positive_control(r, cells_for("V293"))
    # --- 2 / 5. bands --------------------------------------------------------------------------------
    S["spectra"] = spectra(g)
    S["engdis"] = eng_over_dis(S["spectra"])
    S["presence"] = dict(
        all_engaged=presence(g, g["eng"], label=tag + " ALL engaged"),
        handsoff_creep=presence(g, g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3),
                                label=tag + " hands-off creep"))
    # --- 3. strong turn ------------------------------------------------------------------------------
    S["strongturn"] = strongturn(r)
    # --- 4. outer loop -------------------------------------------------------------------------------
    S["outer"] = outer_loop(r)
    # --- 6. cave + params ----------------------------------------------------------------------------
    S["cave"] = cave_duties(r)
    S["params"] = read_params(tag, prefix)
    # --- 7. the operator's four symptoms, and the branch identity  [v2] ------------------------------
    if with_symptoms:
        try:
            S["symptom"] = symptom_block(tag, prefix)
        except Exception as e:
            pr("  ⚠ section 7 could not be computed (%s)" % str(e)[:90])
            S["symptom"] = None
    return S


def load_refs():
    return json.load(open(REFS_JSON)) if os.path.exists(REFS_JSON) else {}


def ref_get(refs, route, *path, default=None):
    d = refs.get(route)
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d if d is not None else default


# ======================================================================================================
# 9b. THE BRANCH IDENTITY BLOCK -- what replaced the broken f/D gate
# ======================================================================================================
def branch_block(S, refs):
    """print the branch read and return its verdicts.

    🛑 WHY THE v1 `f/desiredLateralAccel >= 0.75` GATE WAS WRONG, and it is worth stating in full
    because it FAILED a correctly-attributed drive.  It asserted "friction 0 => f = desiredLateralAccel
    exactly".  The fork does not compute those two from each other:

        pid_log.desiredLateralAccel = setpoint = expected_lateral_accel + jerk * lat_delay
        pid_log.f                   = ff       = D_future - roll*9.81*fade - latAccelOffset*fade
        D_future                               = desiredCurvature * vEgo**2

    one is the 0.30 s DELAYED reference plus a jerk lead, the other is the CURRENT command minus a
    constant.  So f/D = 1 - c/|D| BY CONSTRUCTION, and the whole 0.56 -> 0.87 ramp across |D| bins
    that v1 reported is that one additive constant.  A ratio rising with magnitude is the signature of
    an ADDITIVE term; a branch change is MULTIPLICATIVE and would show a FLAT ratio.

    WHAT IS PRINTED INSTEAD -- two independent reads, neither touching the delayed setpoint:
      (a) median |f - starpilotLateralState.feedforward|, normalised by median |f|.
      (b) the three-term regression  f ~ D_future + roll*fade + fade, whose coefficients in the ELSE
          arm are EXACTLY (1.000, -9.81, -latAccelOffset).
    Both were MEASURED on five routes before either became a gate; the numbers are printed below.
    """
    out = []
    sym = S.get("symptom") or {}
    b = sym.get("branch")
    pr("   THE FEEDFORWARD BRANCH -- which arm of `LatControlTorque.update` actually executed")
    pr("     [EVIDENCE -- the control path at 100 Hz.  This REPLACES v1's `f/desiredLateralAccel`")
    pr("      gate, which was BROKEN AS WRITTEN: `f` and `desiredLateralAccel` are different")
    pr("      quantities (the current command minus an offset, vs the 0.30 s delayed setpoint plus a")
    pr("      jerk lead), so f/D = 1 - c/|D| by construction and v1 was gating on a learned offset.]")
    if not b:
        pr("     ⚠ no control-path cache for this route -- the branch is UNSCOREABLE.")
        out.append(("REPORT", "branch", "no control-path cache (no rlogs on disk for this route) -- "
                                        "the feedforward branch could not be read"))
        return out
    want_plant = EXPECT_PLANT_FF
    rel, dabs = b.get("d_ff_rel"), b.get("d_ff_p50")
    pr("     (a) median |torqueState.f - starpilotLateralState.feedforward| = %s m/s^2  "
       "(p90 %s; |f| %s)" % (fmt(dabs, "%.4f"), fmt(b.get("d_ff_p90"), "%.4f"),
                             fmt(b.get("f_level"), "%.4f")))
    pr("         relative to |f| = %s   over %s active frames.  Both are published in the SAME"
       % (fmt(rel, "%.4f"), b.get("n_ff", "-")))
    pr("         `Controls.publish` call, so they align index-for-index.")
    pr("         [EVIDENCE] they are the SAME NUMBER in the else arm and differ by ~3.3x relative")
    pr("           under the plant-FF arm.  That is the whole of what the gate needs, and it is")
    pr("           measured on five routes.")
    pr("         [BELIEF] WHICH field holds which quantity under the plant-FF arm.  The sizes are")
    pr("           consistent with `feedforward` carrying the generic lat-accel term (|.| 0.372 on")
    pr("           r6f, against 0.366 on r70 where the two agree) and `f` carrying the live branch's")
    pr("           output (|.| 0.113, the size the fork's own hold-torque table predicts) -- but that")
    pr("           mapping was NOT read out of the fork source and nothing here depends on it.")
    pr("         MEASURED CALIBRATION, 2026-09-13, this estimator on five cached routes:")
    pr("           ELSE arm  (AccordRatePlantFF = 0): r70_v293 0.0000 · r39 0.0000 · r35 0.0000")
    pr("           PLANT arm (AccordRatePlantFF = 1): r6f_v292 3.3246 · r6c 3.3706")
    pr("         BIMODAL, with nothing between.  The gate is %.2f relative (or %.3f m/s^2 absolute),"
       % (THR["branch_rel"], THR["branch_abs"]))
    pr("         which is 30x above the ELSE side and 33x below the PLANT side.")
    pr("     (b) the f-identity, regressed on ACTIVE frames:")
    pr("           two-term   f = %s * D_future %+s            R2 %s"
       % (fmt(b.get("slope"), "%.4f"), fmt(b.get("intercept"), "%.4f"), fmt(b.get("r2"), "%.4f")))
    pr("           three-term f = %s * D_future %+s * roll*fade %+s * fade   R2 %s"
       % (fmt(b.get("slope_roll"), "%.5f"), fmt(b.get("coef_roll"), "%.4f"),
          fmt(-b["offset_roll"] if b.get("offset_roll") is not None else None, "%.5f"),
          fmt(b.get("r2_roll"), "%.6f")))
    pr("         In the ELSE arm the three coefficients must be EXACTLY (1.000, -9.81, "
       "-latAccelOffset).")
    pr("         MEASURED on r70_v293: 0.99992 / -9.8091 / -0.06865 at R2 0.999979 -- the fork's own")
    pr("         formula, confirmed to machine precision.  On r6f_v292 (plant arm): 0.5337 / -0.803 /")
    pr("         +0.0196 at R2 0.192.  [EVIDENCE]")
    pr("     THE LEARNED LATERAL-ACCEL OFFSET -- two DIFFERENT numbers, and only one of them acts:")
    pr("       published  liveTorqueParameters.latAccelOffsetFiltered (4 Hz) median = %s m/s^2 "
       "(liveValid on %s of frames)"
       % (fmt(b.get("ltp_off_published_p50"), "%+.5f"), fmt(b.get("ltp_valid_frac"), "%.2f")))
    pr("       EFFECTIVE  the fade coefficient of the three-term fit          = %s m/s^2"
       % fmt(b.get("offset_roll"), "%+.5f"))
    pr("       `torqued` publishes the first whatever the toggle says; `KeepLearnedLatAccelOffset`")
    pr("       decides whether controlsd TAKES it.  The EFFECTIVE one is the gate.")
    if b.get("roll_p50_rad") is not None:
        rr = b["roll_p50_rad"]
        pr("     ⚠ ROLL, and a CORRECTION TO THE RECORD.  liveParameters.roll reads a median %+.5f rad"
           % rr)
        pr("       = %+.2f deg on this route, so the roll term alone subtracts a median %+.4f m/s^2"
           % (np.degrees(rr), 9.81 * rr))
        pr("       from the feedforward.  V293-PLANT-IDENT section G1 read the ~0.30 m/s^2 subtraction")
        pr("       as a STALE LEARNED OFFSET; on r70 the three-term fit splits it +0.408 (roll) and")
        pr("       only -0.069 (learned offset).  [EVIDENCE -- R2 0.999979, residual rms 0.0024 m/s^2,")
        pr("       and the fitted offset matches the PUBLISHED one to 4 decimals.]  So clearing the")
        pr("       learned offset removes about a FIFTH of that subtraction, not all of it; a")
        pr("       persistent multi-degree roll is a device-levelling or camber question.  [BELIEF as")
        pr("       to which of those it is -- this drive cannot separate them.]")
    pr("     the OLD, BROKEN statistic, printed once so the change is visible and never gated on:")
    pr("       median f / desiredLateralAccel = %s" % fmt(b.get("fD_p50_OLD"), "%.4f"))
    # the two subtracted terms as their own REPORT rows, so the next drive carries them forward
    rt, ot = b.get("roll_term_p50"), b.get("offset_roll")
    rr = b.get("roll_p50_rad")
    out.append(("REPORT", "roll term",
                "roll*g*fade subtracts a median %s m/s^2 from the feedforward; liveParameters.roll "
                "median %s rad = %s deg.  No toggle touches this term."
                % (fmt(rt, "%+.4f"), fmt(rr, "%+.5f"),
                   fmt(np.degrees(rr) if rr is not None else None, "%+.2f"))))
    out.append(("REPORT", "learned offset",
                "latAccelOffset*fade subtracts a median %s m/s^2 (published latAccelOffsetFiltered "
                "%s, liveValid on %s of frames).  V293-PLANT-IDENT G1 read the whole ~0.30 m/s^2 "
                "subtraction as this term; the three-term fit says it is mostly the ROLL row above."
                % (fmt(ot, "%+.5f"), fmt(b.get("ltp_off_published_p50"), "%+.5f"),
                   fmt(b.get("ltp_valid_frac"), "%.2f"))))
    if want_plant is None or rel is None:
        out.append(("REPORT", "branch", "the config does not name AccordRatePlantFF, or too few "
                                        "active frames -- the branch is reported, not gated"))
        return out
    # EITHER a large relative difference OR a large absolute one means the two feedforwards are not
    # the same number.  The absolute guard exists for a drive whose |f| is itself tiny, where a
    # relative statistic is unstable.
    live_plant = (rel >= THR["branch_rel"]) or (dabs is not None and dabs >= THR["branch_abs"])
    armnm = "PLANT-FF" if live_plant else "ELSE (lat-accel FF)"
    wantnm = "PLANT-FF" if want_plant else "ELSE (lat-accel FF)"
    if live_plant == want_plant:
        out.append(("PASS", "branch",
                    "the %s arm is the one executing (|f - feedforward|/|f| = %.4f against a gate of "
                    "%.2f) -- which is the arm %s asks for"
                    % (armnm, rel, THR["branch_rel"], os.path.basename(CONFIG_PATH))))
    else:
        out.append(("FAIL", "branch",
                    "the %s arm executed but %s asks for the %s arm (|f - feedforward|/|f| = %.4f, "
                    "gate %.2f).  The band and symptom scores are NOT the contrast they were designed "
                    "to be until this is fixed."
                    % (armnm, os.path.basename(CONFIG_PATH), wantnm, rel, THR["branch_rel"])))
    # the f-identity is only meaningful in the ELSE arm -- say so rather than scoring a nonsense fit
    if not live_plant:
        sl, r2r = b.get("slope_roll"), b.get("r2_roll")
        if sl is not None and abs(sl - 1.0) <= THR["branch_slope_tol"] and (r2r or 0) >= THR["branch_r2"]:
            out.append(("PASS", "f identity",
                        "f = %.5f*D_future %+.4f*roll*fade %+.5f*fade at R2 %.6f -- the fork's own "
                        "formula, confirmed on the wire" % (sl, b["coef_roll"], -b["offset_roll"], r2r)))
        else:
            out.append(("REPORT", "f identity",
                        "the ELSE-arm f identity does not close: slope %s, R2 %s (wants 1.000 +- %.2f "
                        "at R2 >= %.2f) -- read the branch row with that in mind"
                        % (fmt(sl, "%.4f"), fmt(r2r, "%.4f"), THR["branch_slope_tol"], THR["branch_r2"])))
    keep = CONFIG.get("KeepLearnedLatAccelOffset")
    if keep is not None and keep[0] == "0":
        eff = b.get("offset_roll")
        if live_plant or (b.get("r2_roll") or 0) < THR["branch_r2"]:
            out.append(("REPORT", "lat-accel offset",
                        "the config asks for KeepLearnedLatAccelOffset = 0, but the EFFECTIVE offset "
                        "is only identifiable in the ELSE arm; published latAccelOffsetFiltered "
                        "median = %s.  Reported, not gated."
                        % fmt(b.get("ltp_off_published_p50"), "%+.5f")))
        elif eff is not None and abs(eff) <= THR["offset_tol"]:
            out.append(("PASS", "lat-accel offset",
                        "the effective learned offset reads %+.5f m/s^2 (|.| <= %.2f) -- "
                        "KeepLearnedLatAccelOffset = 0 took" % (eff, THR["offset_tol"])))
        else:
            out.append(("FAIL", "lat-accel offset",
                        "the config asks for KeepLearnedLatAccelOffset = 0 but the effective offset "
                        "still reads %+.5f m/s^2 (gate %.2f) -- the toggle did not take, or openpilot "
                        "was not restarted after it" % (eff, THR["offset_tol"])))
    return out


# ======================================================================================================
# 10. THE SCORECARD
# ======================================================================================================
def fmt_pair(p, f="%.3f"):
    return "-" if not p else "[%s, %s]" % (f % p[0], f % p[1])


def fmt(v, f="%.3f"):
    try:
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            return "  n/a"
        return f % v
    except Exception:
        return "  n/a"


def print_scorecard(S, refs):
    tag, build = S["tag"], S["build"]
    verdicts = []          # (level, clause, text)   level in PASS / FAIL / REVERT / REPORT / OPERATOR

    pr("=" * 124)
    pr("V293 FLIGHT READ -- %s   build %s   [image %s]" % (tag, build, S["image"]))
    pr("pre-registered read: docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md 'What PASS licenses'")
    pr("                     docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md section 6")
    pr("=" * 124)
    pr("cells read from the image: fb_clamp %s  d_clamp %s  Kd %s  Kp %s  r24 arm %s  gain %s"
       % (S["cells"]["fb_clamp"], S["cells"]["d_clamp"], S["kd_Y"], S["kp_Y"],
          S["cells"]["r24_arm"], S["cells"]["gain"]))

    # ---------------------------------------------------------------- 0. exposure and toggles
    pr("")
    pr("0. EXPOSURE AND THE FORK TOGGLES  [EVIDENCE -- the wire and initData]")
    pr("-" * 124)
    pr("   route %.0f s | engaged-lateral %.0f s | disengaged %.0f s | hands-off %.0f s | "
       "|ang|>=30 %.0f s | hands-off creep 1-3 m/s %.0f s"
       % (S["route_s"], S["engaged_s"], S["disengaged_s"], S["handsoff_s"], S["hiang_s"], S["creep_s"]))
    P = S["params"]
    cl = P.get("AccordCurvatureLead")
    pr("   THE FORK SIDE IS A TOGGLE CONFIG, not code: params that already exist on Dom.  The EXPECTED")
    pr("   config is READ FROM A FILE -- %s" % os.path.relpath(CONFIG_PATH, KIT))
    pr("   -- so a revised config is scored against itself, not against a constant baked into this")
    pr("   script.  Read here from initData.params (logged ONCE, at process start) and, independently,")
    pr("   from the CONTROL PATH at 100 Hz (torqueState p/error = SteerKP exactly; and the BRANCH")
    pr("   IDENTITY in section 7).  Accord* keys are ABSENT from initData when they sit at their")
    pr("   params_keys.h default (measured on r6f), so absence reads as the declared default; a key")
    pr("   this cache never CAPTURED reads as NOT CAPTURED, which is a different thing and is a FAIL.")
    cfg_ok, cfg_rows = True, []
    captured = set(P.get("_want_params") or WANT_PARAMS)
    for k, (want, dflt, kind) in sorted(CONFIG.items()):
        raw = P.get(k)
        if raw is None and k not in captured:
            ok, shown, eff = False, "NOT CAPTURED by this cache", None
        else:
            eff = raw if raw is not None else dflt
            if eff is None:
                ok, shown = False, "ABSENT (no declared default)"
            else:
                try:
                    ok = ((abs(float(eff) - float(want)) < 1e-6) if kind == "float"
                          else (str(eff).strip() == want))
                except ValueError:
                    ok = False
                shown = repr(raw) if raw is not None else "absent = default %r" % dflt
        cfg_ok &= ok
        cfg_rows.append((k, shown, want, ok))
        pr("   %-26s = %-30s config wants %-6s %s" % (k, shown, want, "ok" if ok else "MISMATCH"))
    ctx = [k for k in CONTEXT_KEYS if k in P and k not in CONFIG]
    if ctx:
        pr("   -- context, read but NOT gated (the config file does not name them) --")
        for k in ctx:
            pr("   %-26s = %s" % (k, repr(P[k])[:70]))
    pr("   AccordCurvatureLead        = %-10s   (must be ABSENT or \"0\"; the key does not exist on Dom)"
       % ("ABSENT" if cl is None else repr(cl)))
    if P.get("_augmented_from_rlogs"):
        pr("   (this route's cache predates this read; the cereal-side readings were read straight from")
        pr("    its rlogs into _scratch/ -- the shared cache was NOT rewritten)")
    elif "_written_by" not in P:
        pr("   ⚠ no toggle source could be read: no cache keys and no rlogs on disk.")
    kp, kpn = P.get("_kp_hat"), P.get("_kp_n", 0)
    pr("   torqueState  Kp at 100 Hz = median(p / error) = %s   (n %s; IQR %s; %s of frames within 5%%)"
       % (fmt(kp, "%.4f"), kpn, fmt_pair(P.get("_kp_iqr"), "%.4f"), fmt(P.get("_kp_within5pct"), "%.3f")))
    pr("     the fork logs pid_log.error = error_with_lsf and calls pid.update(pid_log.error, ...), whose")
    pr("     p = k_p * error, so the ratio IS the SteerKP toggle on every active frame -- a wire read of")
    pr("     the tune that survives a mid-route toggle change, which initData (logged once) does not.")
    pr("     Expected %s under %s; the installed rate-servo tune reads %.2f."
       % (CONFIG.get("SteerKP", ("(unspecified)",))[0], os.path.basename(CONFIG_PATH), INSTALLED_KP))
    # --- the Testing Ground heartbeat, informational ---------------------------------------------
    tgs, tgv, tgn = P.get("_tg_slot"), P.get("_tg_variant"), P.get("_tg_frames", 0)
    if tgn:
        pr("   Testing Ground             = slot %s variant %s  (%s / %s)   over %d published frames"
           % (tgs, tgv, P.get("_tg_slot_name") or "?", P.get("_tg_variant_label") or "?", tgn))
        if (P.get("_tg_pairs") or {}) and len(P["_tg_pairs"]) > 1:
            pr("     ⚠ the selection CHANGED during the route: "
               + "  ".join("%s x%d" % (k, v) for k, v in P["_tg_pairs"].items()))
    else:
        pr("   Testing Ground             = no selection frames decoded on this route%s"
           % ("" if P.get("_tg_readable", True) else "   [schema patch failed]"))
    pr("     informational only -- no Testing Ground slot is the torque mode (the slot-9 rework was undone")
    pr("     on 2026-09-13).  Decoded off the PATCHED @116 struct (the kit calls it `modelDataV2SP`, the")
    pr("     fork `customReserved9`; same struct id 0xa1680744031fdb2d, different fields).  The @137")
    pr("     collision (`epsTelemetry` vs the fork's `starpilotLateralState`, id 0xc2243c65e0340384) is")
    pr("     patched the same way; any other kit script reading either from a 2026-09 rlog reads GARBAGE.")
    # --- the latAccelFactor identity: the SECOND exact 100 Hz read, valid in BOTH arms ------------
    LA = (S.get("symptom") or {}).get("laf") or {}
    want_laf = None
    if "SteerLatAccel" in CONFIG:
        try:
            want_laf = float(CONFIG["SteerLatAccel"][0])
        except ValueError:
            want_laf = None
    pr("   torqueState  latAccelFactor at 100 Hz = median -(p + i + f) / output = %s"
       % fmt(LA.get("laf"), "%.4f"))
    pr("     (n %s active frames with |output| >= 1e-3; IQR %s; %s within 1%%, %s within 5%%)"
       % (LA.get("n", "-"), fmt_pair(LA.get("iqr"), "%.4f"), fmt(LA.get("within1"), "%.3f"),
          fmt(LA.get("within5"), "%.3f")))
    pr("     `output_torque = output_lataccel / latAccelFactor`, `output_lataccel = f + p + i + d`")
    pr("     with d structurally 0 on this car, and `torqueState.output = -output_torque`.  So the")
    pr("     ratio IS the SteerLatAccel toggle on every active frame, EXACTLY -- and unlike the")
    pr("     branch read it holds in BOTH feedforward arms, because `pid_log.f = pid.f` in each.")
    pr("     VERIFIED on r70_v293: median 6.0000, IQR [6.0000, 6.0000], 99.2% of frames within 1%.")
    if LA.get("laf") is None:
        verdicts.append(("FAIL", "latAccelFactor", "-(p+i+f)/output could not be read (%s usable "
                                                   "frames) -- the live authority scalar is unknown"
                         % LA.get("n", 0)))
    elif want_laf is None:
        verdicts.append(("REPORT", "latAccelFactor", "latAccelFactor = %.3f at 100 Hz; the config "
                                                     "names no SteerLatAccel, so this is reported, "
                                                     "not gated" % LA["laf"]))
    else:
        ok = abs(LA["laf"] - want_laf) <= 0.02 * want_laf and (LA.get("within5") or 0) >= 0.95
        if ok:
            verdicts.append(("PASS", "latAccelFactor",
                             "latAccelFactor = %.4f at 100 Hz over %d frames (config wants %.2f, "
                             "within 2%%), %.3f of frames within 5%% -- the authority scalar was LIVE"
                             % (LA["laf"], LA["n"], want_laf, LA.get("within5") or 0)))
        else:
            verdicts.append(("FAIL", "latAccelFactor",
                             "latAccelFactor = %.4f at 100 Hz but %s wants %.2f (gate: within 2%% and "
                             ">= 95%% of frames within 5%%; measured %.3f) -- P, I and the feedforward "
                             "are ALL divided by this, so the whole authority is wrong"
                             % (LA["laf"], os.path.basename(CONFIG_PATH), want_laf,
                                LA.get("within5") or 0)))
    # --- the FORK COMMIT: the config's scales only mean what they say on the right code -----------
    fc = CONFIG_FORK_COMMIT.get(os.path.basename(CONFIG_PATH))
    gc = str(P.get("GitCommit") or "")
    pr("   fork GitCommit             = %s   branch %s"
       % (gc[:12] or "ABSENT", P.get("GitBranch") or "?"))
    if fc:
        pr("     🛑 %s." % fc["why"])
        pr("     The rlog CANNOT read the tables, only the commit, so this is a COMMIT check: it")
        pr("     wants %s and must NOT be %s." % (" or ".join(fc["want"]) if isinstance(fc["want"], (tuple, list)) else fc["want"], fc["forbid"]))
        if not gc:
            verdicts.append(("FAIL", "fork commit", "initData carries no GitCommit -- the fork build "
                                                    "cannot be attributed, and %s" % fc["why"]))
        elif gc.startswith(fc["forbid"]):
            verdicts.append(("FAIL", "fork commit",
                             "GitCommit %s is the PRE-TABLE commit -- %s.  The plant feedforward is "
                             "then the one the identification measured as 1.4-2.6x too small, and "
                             "every other gate would pass a silently wrong drive."
                             % (gc[:9], fc["why"])))
        elif gc.startswith(tuple(fc["want"]) if isinstance(fc["want"], (tuple, list)) else fc["want"]):
            verdicts.append(("PASS", "fork commit", "GitCommit %s -- the commit carrying the replaced "
                                                    "Accord plant tables" % gc[:9]))
        else:
            verdicts.append(("REPORT", "fork commit",
                             "GitCommit %s is neither the expected %s nor the forbidden %s -- the "
                             "tables cannot be verified from the rlog; check the fork tree before "
                             "reading the plant-FF rows" % (gc[:9], " or ".join(fc["want"]) if isinstance(fc["want"], (tuple, list)) else fc["want"], fc["forbid"])))
    verdicts += branch_block(S, refs)
    if build == "V293":
        # THREE ATTRIBUTION GATES on the fork side, none of them a code flag: the initData config
        # read, the 100 Hz Kp read, and the f/D branch read above.
        cfgname = os.path.basename(CONFIG_PATH).replace(".decoded.json", ".json")
        if cfg_ok:
            verdicts.append(("PASS", "toggle", "initData.params carries %s: " % cfgname +
                             ", ".join("%s=%s" % (k, w) for k, (w, _, _) in sorted(CONFIG.items()))))
        else:
            bad = ["%s=%s (wants %s)" % (k, sh, w) for k, sh, w, ok in cfg_rows if not ok]
            verdicts.append(("FAIL", "toggle",
                             "initData.params does NOT carry %s -- " % cfgname + "; ".join(bad) +
                             ".  V293 in the ECU with a tune it was not designed against is the "
                             "FF-starved AND high-gain-feedback mismatch (ADV-V293-D 4.4), not merely "
                             "sluggish, and the band scores are NOT a build contrast.  Restore %s in "
                             "Galaxy and restart openpilot." % cfgname))
        # 🛑 THE EXPECTED Kp COMES FROM THE CONFIG FILE.  v1 hard-coded 0.3, which would have failed the
        # rev-2 drive for carrying the Kp its own config asked for.
        want_kp = None
        if "SteerKP" in CONFIG:
            try:
                want_kp = float(CONFIG["SteerKP"][0])
            except ValueError:
                want_kp = None
        if kp is None:
            verdicts.append(("FAIL", "kp", "torqueState p/error could not be read (%s active frames with "
                                           "|error| >= 0.02) -- the live Kp is unknown" % kpn))
        elif want_kp is None:
            verdicts.append(("REPORT", "kp", "Kp = %.3f at 100 Hz over %d frames; the config names no "
                                             "SteerKP, so this is reported, not gated" % (kp, kpn)))
        elif abs(kp - want_kp) <= max(0.03, 0.05 * want_kp):
            verdicts.append(("PASS", "kp", "Kp = %.3f at 100 Hz over %d frames -- the config's %.2f was "
                                           "LIVE on the control path" % (kp, kpn, want_kp)))
        elif abs(kp - INSTALLED_KP) <= 0.05:
            verdicts.append(("FAIL", "kp", "Kp = %.3f at 100 Hz -- that is the INSTALLED rate-servo tune "
                                           "(%.2f), not the config's %.2f: the restore did not take, or "
                                           "openpilot was not restarted after it"
                                           % (kp, INSTALLED_KP, want_kp)))
        else:
            verdicts.append(("FAIL", "kp", "Kp = %.3f at 100 Hz -- neither the config's %.2f nor the "
                                           "installed tune (%.2f); attribute before scoring"
                                           % (kp, want_kp, INSTALLED_KP)))
        if P.get("AccordEpsTorqueMode") is not None:
            verdicts.append(("REPORT", "toggle",
                             "AccordEpsTorqueMode = %r is PRESENT in the params store -- that key existed "
                             "only on the pre-rework preset patch, so this device runs a STALE fork build"
                             % P.get("AccordEpsTorqueMode")))
        if cl not in (None, "0"):
            verdicts.append(("FAIL", "toggle", "AccordCurvatureLead = %r -- a separate, undriven fork "
                                               "experiment is live and confounds this drive" % cl))

    # ---------------------------------------------------------------- 1. the identity
    pr("")
    pr("1. THE EDIT-LIVE IDENTITY -- |427 tap| vs f(cmd)*fade, on every laterally engaged frame")
    pr("   [EVIDENCE -- the wire, against cells read from the BUILT IMAGE.  This is the control that")
    pr("    decides ATTRIBUTION: with 0xC62E6 = 0 the tap is an exact function of demand and fade and")
    pr("    carries NO wheel-rate term.  Pre-registered V293 R2 +0.92 resid 47 ; V282/V292 -4.81 / 349.]")
    pr("-" * 124)
    I = S["identity"]
    pr("   %d tap frames.  The predictor is ZOH-sampled onto the tap's NATIVE 50 Hz (the tap is never"
       % I["n_tap"])
    pr("   up-sampled); the transport lag is scanned -40..+120 ms and the best row is reported.")
    pos = S.get("positive")
    rlim = (THR["identity_resid_rel"] * pos["resid_p50"]) if pos else THR["identity_resid"]
    pr("   gate: R2 >= %.2f AND residual <= %s.  MEASURED yardstick: this estimator's ceiling on real"
       % (THR["identity_r2"],
          ("%.0f = %.1fx this route's own positive control" % (rlim, THR["identity_resid_rel"]))
          if pos else "%.0f counts (absolute fallback -- no positive control ran)" % rlim))
    pr("   data is R2 %+.3f (a synthetic V293 tap) and its floor across six non-V293 routes is %+.3f."
       % (CONTROL_CEILING, max(CONTROL_FLOOR.values())))
    pr("   %-22s %-7s %8s %10s %8s %7s %8s %10s %10s %7s" %
       ("cells / fade axis", "lag ms", "n", "R2", "resid", "res/rms", "pearson", "sgn=sgn(pred)",
        "sgn=-sgn(cmd)", "verdict"))
    for key in sorted(I["fits"]):
        b = I["fits"][key]
        if b is None:
            pr("   %-22s  -- too few engaged frames --" % key)
            continue
        okk = (b["r2"] >= THR["identity_r2"] and b["resid"] <= rlim)
        pr("   %-22s %-7.0f %8d %10.4f %8.1f %7.3f %8.3f %10.3f %10.3f %7s" %
           (key, b["lag_ms"], b["n"], b["r2"], b["resid"], b["resid_norm"], b["pearson"],
            b["sign_pred"], b["sign_negcmd"], "HOLDS" if okk else "-"))
    pr("   ⚠ POLARITY, measured: the delivered tap follows sign(T) = +sign(cmd), so the column that")
    pr("     must go to ~1.00 is sign(T)=sign(pred).  The prereg's phrase 'sign(T) = -sign(cmd)' is the")
    pr("     opposite convention -- on the wire that column reads ~0.15 on V282.  Both are printed so")
    pr("     the reading cannot be taken the wrong way round.")
    pr("   The estimator has ZERO free parameters (no fitted scale, no offset): R2 -> 1 means the BYTES")
    pr("   PREDICT THE WIRE.  Pearson r beside it separates a SCALE error (high r, failing R2) from a")
    pr("   STRUCTURAL one (low r).")
    dr = I.get("%s/_derate" % build)
    if dr:
        pr("   fade axis is OPEN (ADV-V293-A erratum): the record reads 0xCBBC4 by |bar|>>5, adversary A")
        pr("   reads it as km/h.  On this route the bar reading derates on %d/%d frames (median m %.0f)"
           % (dr["n_bar_derate"], dr["n"], dr["m_bar_p50"]))
        pr("   and the speed reading would derate on %d/%d (median m %.0f).  The winning R2 row above IS"
           % (dr["n_speed_derate"], dr["n"], dr["m_speed_p50"]))
        pr("   the evidence for which axis is right -- with the loop open the tap IS the surface.")
    best_own = I["fits"].get("%s/bar" % build)
    for fm in ("speed", "const"):
        alt = I["fits"].get("%s/%s" % (build, fm))
        if alt and best_own and alt["r2"] > best_own["r2"]:
            best_own = alt
    if pos:
        pr("   POSITIVE CONTROL -- a V293 tap synthesised from THIS route's own command by the byte-exact")
        pr("     1 kHz march (Elec, fb clamped to +-0), decimated to 50 Hz, quantised, regressed by the")
        pr("     SAME estimator: R2 p50 %.4f (min %.4f) resid %.1f over %d windows / %d frames."
           % (pos["r2_p50"], pos["r2_min"], pos["resid_p50"], pos["n_win"], pos["n"]))
        pr("     Not a tautology: the predictor is the STEADY-STATE surface, the synthetic tap is dynamic.")
        if pos["r2_p50"] < 0.8:
            verdicts.append(("REPORT", "positive control",
                             "the positive control reads R2 %.3f, not ~1 -- the ESTIMATOR is impaired on "
                             "this route (exposure, idx range or tap quantisation), so read the identity "
                             "row with that in mind" % pos["r2_p50"]))
    pr("   NEGATIVE CONTROL, measured 2026-09-13 by `--controls` (the same estimator, V293's cells, on")
    pr("     routes that are NOT V293): " + "  ".join("%s %+.3f" % (k, v) for k, v in CONTROL_FLOOR.items()))
    pr("     -- every one FAILS, which is what makes a PASS here attributable.")
    if best_own is not None:
        hold = (best_own["r2"] >= THR["identity_r2"] and best_own["resid"] <= rlim)
        lvl = "PASS" if hold else ("FAIL" if build == "V293" else "PASS")
        note = ("identity HOLDS: R2 %.3f (>= %.2f), resid %.1f counts (<= %.0f), sign(T)=sign(pred) "
                "%.3f -- the LKAS rate feedback is DEAD on the wire"
                % (best_own["r2"], THR["identity_r2"], best_own["resid"], rlim,
                   best_own["sign_pred"]))
        if not hold:
            note = ("identity DOES NOT hold: R2 %.3f, resid %.1f counts -- %s"
                    % (best_own["r2"], best_own["resid"],
                       "the cal did not take, or the drive is not V293"
                       if build == "V293" else
                       "EXPECTED on this build; the residual IS the feedback leg (the negative control)"))
        verdicts.append((lvl, "identity", note))
        S["_identity_holds"] = bool(hold)
    else:
        S["_identity_holds"] = False
        verdicts.append(("FAIL", "identity", "no engaged tap frames -- the identity is unscoreable"))

    # ---------------------------------------------------------------- 2. the ring
    pr("")
    pr("2. THE 18-22 Hz RING -- the DRIVE-CONTROLLED measure (V292 flight read section 4)")
    pr("   [EVIDENCE.  engaged band amplitude / the SAME route's lateral-DISENGAGED amplitude.  The")
    pr("    disengaged reference is mostly STATIONARY on every route -- like-for-like between builds,")
    pr("    not a road-input normalisation.]")
    pr("-" * 124)
    ed = S["engdis"]
    hdr = "   %-24s " % "route" + " ".join("%-9s" % b[0] for b in BANDS)
    pr(hdr)
    if ed:
        pr("   %-24s " % (tag + " (%s)" % build) + " ".join("%-9.3f" % ed[b[0]] for b in BANDS))
    else:
        pr("   %-24s  -- no disengaged spectrum on this route --" % tag)
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        if rt == tag:
            continue
        e = ref_get(refs, rt, "engdis")
        if e:
            pr("   %-24s " % ("%s (%s)" % (rt, BUILD_OF.get(rt, "?")))
               + " ".join("%-9.3f" % e[b[0]] for b in BANDS))
    pr("   record literals, 18-22 Hz (V292-FLIGHT-READ section 4): "
       + "  ".join("%s %.2f" % (k, v) for k, v in RECORD["engdis_1822"].items()))
    ref_ed = ref_get(refs, REF_V282, "engdis", "18-22", default=RECORD["engdis_1822"][REF_V282])
    if ed and ref_ed:
        pr("   >>> this route's 18-22 Hz engaged/disengaged = %.3f   = x%.3f of %s's %.3f"
           % (ed["18-22"], ed["18-22"] / ref_ed, REF_V282, ref_ed))
    pr("")
    pr("   PRESENT-WINDOW RING AMPLITUDE -- the record's predicate (2 s windows, 0.5 s step; 18-22 Hz")
    pr("   prominence >= 8 on the DRIVER-TORQUE bar AND bar amplitude >= 40), 18-22 Hz on the 0x18F")
    pr("   rate, deg/s.  THIS is the clause: <= 0.40x of V282's.")
    pr("   %-24s %-10s %8s %8s %8s %9s %9s %8s" %
       ("route / stratum", "build", "n_win", "n_pres", "pres %", "amp p50", "amp p90", "f0"))
    def presline(nm, bld, pz):
        if not pz or pz["n_win"] < 5:
            pr("   %-24s %-10s %8s  -- under 5 windows in this stratum --"
               % (nm, bld, (pz or {}).get("n_win", 0)))
            return
        pr("   %-24s %-10s %8d %8d %7.1f%% %9.3f %9.3f %8.2f" %
           (nm, bld, pz["n_win"], pz["n_pres"], pz["pres_pct"], pz["amp_p50"], pz["amp_p90"],
            pz["f0_p50"]))
    for lab, key in (("ALL engaged", "all_engaged"), ("hands-off creep 1-3", "handsoff_creep")):
        presline(tag + "  " + lab, build, S["presence"][key])
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        if rt == tag:
            continue
        pz = ref_get(refs, rt, "presence", "all_engaged")
        if pz:
            presline(rt + "  ALL engaged", BUILD_OF.get(rt, "?"), pz)
    pr("   record literals, present-window amp p50 (V292-FLIGHT-READ section 3.1): "
       + "  ".join("%s %.2f" % (k, v) for k, v in RECORD["pres_amp_1822"].items()))
    ref_amp = ref_get(refs, REF_V282, "presence", "all_engaged", "amp_p50",
                      default=RECORD["pres_amp_1822"][REF_V282])
    ref_amp39 = ref_get(refs, "r39", "presence", "all_engaged", "amp_p50",
                        default=RECORD["pres_amp_1822"]["r39"])
    got = S["presence"]["all_engaged"]["amp_p50"]
    npres = S["presence"]["all_engaged"]["n_pres"]
    if np.isfinite(got) and ref_amp:
        rat = got / ref_amp
        pr("   >>> present-window ring x%.3f of %s (%.3f)   and x%.3f of r39 (%.3f)   [n_pres %d]"
           % (rat, REF_V282, ref_amp, got / ref_amp39, ref_amp39, npres))
        if npres < 10:
            verdicts.append(("REPORT", "ring",
                             "only %d present windows -- the ring ratio x%.2f is not decisive; the "
                             "exposure, not the build, is the limit" % (npres, rat)))
        elif rat <= THR["ring_ratio"]:
            verdicts.append(("PASS", "ring", "present-window 18-22 Hz ring x%.3f of %s's (<= %.2f)"
                             % (rat, REF_V282, THR["ring_ratio"])))
        else:
            verdicts.append(("FAIL", "ring",
                             "present-window 18-22 Hz ring x%.3f of %s's -- the pre-registered success "
                             "is <= %.2fx.  A band did not move; the OPERATOR scores the symptom."
                             % (rat, REF_V282, THR["ring_ratio"])))
        S["_ring_ratio"] = float(rat)
    else:
        S["_ring_ratio"] = None
        verdicts.append(("REPORT", "ring", "no present windows on this route -- the ring is unscoreable"))

    # ---------------------------------------------------------------- 3. strong turn
    pr("")
    pr("3. THE 6-9 Hz STRONG-TURN RIPPLE -- the operator's 'stutter' channel  [EVIDENCE]")
    pr("   F7: the record's FIXED 103-wire detector, |angle| >= 30 AND fdom >= 6, per 100 s of engaged")
    pr("   high-angle time.  REVERT at >= 2/100 s.  rip/L: stutter_v283 section C.  REVERT at >= 0.25.")
    pr("   The ABSOLUTE 6-8.5 Hz tap ripple is scored too -- torque mode grows the DENOMINATOR x1.2-3.6.")
    pr("-" * 124)
    T = S["strongturn"]
    pr("   %-24s %-9s %8s %7s %9s %9s %9s %9s %9s" %
       ("route", "build", "hi-ang s", "n F7", "F7/100 s", "rip/L p50", "rip/L p90", "rip ABS",
        "|T| p50"))

    def stline(nm, bld, t):
        pr("   %-24s %-9s %8.1f %7d %9.2f %9.3f %9.3f %9.1f %9.0f" %
           (nm, bld, t.get("hi_ang_s", float("nan")), t.get("n_f7", 0),
            t.get("f7_per100", float("nan")), t.get("ripL_p50_all", float("nan")),
            t.get("ripL_p90_all", float("nan")), t.get("rip_abs_p50_all", float("nan")),
            t.get("lvl_p50_all", float("nan"))))
    stline(tag, build, T)
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        t = None if rt == tag else ref_get(refs, rt, "strongturn")
        if t:
            stline(rt, BUILD_OF.get(rt, "?"), t)
    pr("   record literals, F7/100 s (DESIGN 6.2): "
       + "  ".join("%s %s" % (k, v) for k, v in RECORD["f7_per100"].items() if v is not None))
    pr("   THE 5-9 Hz WHEEL BAND (B5's channel).  A BROADBAND x1.5 rise is PREDICTED -- the servo's")
    pr("   disturbance rejection is what V293 removes; a resonant LINE is not predicted and is the")
    pr("   thing to look for.  'rate 6-8.5 loaded' is the 0x18F rate on the SAME loaded-turn windows")
    pr("   as rip/L above, and is the only one of these that is populated on every route.")
    pr("   %-24s %-9s | %11s %8s %8s | %11s" %
       ("route", "build", "|ang|>=30 off", "5-9 off", "18-22 off", "rate 6-8.5 loaded"))

    def w59line(nm, bld, t):
        pr("   %-24s %-9s | %11.1f %8.3f %8.3f | %11.3f" %
           (nm, bld, t.get("t_s_ang30_off", float("nan")), t.get("w59_ang30_off", float("nan")),
            t.get("w1822_ang30_off", float("nan")), t.get("rate68_p50_all", float("nan"))))
    w59line(tag, build, T)
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        t = None if rt == tag else ref_get(refs, rt, "strongturn")
        if t:
            w59line(rt, BUILD_OF.get(rt, "?"), t)
    pr("   ⚠ the |angle| >= 30 hands-LIGHT (bar 400-1216) stratum is EMPTY on all six reference routes")
    pr("     (under 3 s of runs >= 1 s), so B5's literal window does not exist in the corpus.  The")
    pr("     hands-OFF column exists only on r6c and r39.  Read the loaded-turn column as the populated")
    pr("     one.  [EVIDENCE -- exposure counted from the caches]")
    f7 = T.get("f7_per100", float("nan"))
    if T.get("hi_ang_s", 0) < 20:
        verdicts.append(("REPORT", "F7", "only %.0f s of engaged high-angle time -- F7 %.2f/100 s is "
                                         "not decisive" % (T.get("hi_ang_s", 0), f7)))
    elif np.isfinite(f7) and f7 >= THR["f7_per100"]:
        verdicts.append(("REVERT", "F7", "F7 = %.2f per 100 s of high-angle engaged time (>= %.1f) -- "
                                         "the pre-registered revert trigger" % (f7, THR["f7_per100"])))
    elif np.isfinite(f7):
        verdicts.append(("PASS", "F7", "F7 = %.2f per 100 s (< %.1f)" % (f7, THR["f7_per100"])))
    rl = T.get("ripL_p50_all", float("nan"))
    if np.isfinite(rl):
        if rl >= THR["ripL"]:
            verdicts.append(("REVERT", "rip/L", "tap ripple/level p50 = %.3f (>= %.2f) on loaded turns"
                             % (rl, THR["ripL"])))
        else:
            verdicts.append(("PASS", "rip/L", "tap ripple/level p50 = %.3f (< %.2f)" % (rl, THR["ripL"])))
    ra = T.get("rip_abs_p50_all", float("nan"))
    ra_ref = ref_get(refs, REF_V282, "strongturn", "rip_abs_p50_all")
    ra_ref39 = ref_get(refs, "r39", "strongturn", "rip_abs_p50_all")
    base = ra_ref if ra_ref else ra_ref39
    if np.isfinite(ra) and base:
        rr = ra / base
        pr("   >>> ABSOLUTE 6-8.5 Hz tap ripple %.1f counts = x%.3f of %s's %.1f"
           % (ra, rr, REF_V282 if ra_ref else "r39", base))
        if rr >= THR["rip_abs_ratio"]:
            verdicts.append(("REVERT", "rip ABS", "absolute 6-8.5 Hz tap ripple x%.2f of V282's "
                                                  "(>= %.1f) -- DESIGN 6.3's symmetric sentence"
                             % (rr, THR["rip_abs_ratio"])))
        else:
            verdicts.append(("PASS", "rip ABS", "absolute 6-8.5 Hz tap ripple x%.2f of V282's (< %.1f)"
                             % (rr, THR["rip_abs_ratio"])))

    # ---------------------------------------------------------------- 4. outer loop
    pr("")
    pr("4. THE OUTER LOOP -- a coherent 1-4 Hz line in 0xE4 COMMAND and STEERING ANGLE  [EVIDENCE]")
    pr("   The V276 signature, and the orchestrator's first revert trigger: watch LOW SPEED FIRST.")
    pr("   🛑 COHERENCE IS NOT THE DISCRIMINATOR -- it reads 0.88-1.00 at 1-4 Hz on EVERY route in the")
    pr("   corpus, V282 and V292 alike, because openpilot commands there and the car follows.  What")
    pr("   separates a limit cycle from ordinary tracking is the ANGLE AMPLITUDE at 1-4 Hz, against")
    pr("   the V282/V281r3 references in the same speed band.  Coherence is kept only as a guard: a")
    pr("   rise with LOW coherence is road input, not the loop.  [EVIDENCE -- measured on six routes]")
    pr("-" * 124)
    pr("   %-24s %-9s %8s %8s %9s %9s %10s %10s" %
       ("route", "band", "t s", "n_run", "coh p50", "coh p90", "f at coh", "ang 1-4 deg"))
    flagged = []
    for lab, _, _ in SPEED_BANDS:
        o = S["outer"].get(lab, {})
        if not o.get("scored"):
            pr("   %-24s %-9s %8.1f %8d  -- under 20 s of runs >= 5.12 s --"
               % (tag, lab, o.get("t_s", 0.0), o.get("n_run", 0)))
            continue
        refang = [ref_get(refs, rt, "outer", lab, "ang14_deg") for rt in ("r6c", "r39", "r35")]
        refang = [x for x in refang if x]
        hot = (o["coh_p90"] >= THR["coh_14"] and refang and o["ang14_deg"] > 1.5 * max(refang))
        pr("   %-24s %-9s %8.1f %8d %9.3f %9.3f %10.2f %10.4f%s"
           % (tag, lab, o["t_s"], o["n_run"], o["coh_p50"], o["coh_p90"], o["f_at_coh"],
              o["ang14_deg"], "   <-- ELEVATED" if hot else ""))
        if hot:
            flagged.append((lab, o))
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        if rt == tag:
            continue
        for lab, _, _ in SPEED_BANDS:
            o = ref_get(refs, rt, "outer", lab)
            if o and o.get("scored"):
                pr("   %-24s %-9s %8.1f %8d %9.3f %9.3f %10.2f %10.4f"
                   % (rt + " (%s)" % BUILD_OF.get(rt, "?"), lab, o["t_s"], o["n_run"],
                      o["coh_p50"], o["coh_p90"], o["f_at_coh"], o["ang14_deg"]))
    if flagged:
        verdicts.append(("REVERT", "outer loop",
                         "a coherent 1-4 Hz line in command AND angle at %s (coherence p90 %.2f, angle "
                         "1-4 Hz %.3f deg, >1.5x every V282/V281r3 reference) -- the V276 signature.  "
                         "The fix is the FORK TOGGLE CONFIG (the outer-loop tune), not the firmware, but the drive stops."
                         % (flagged[0][0], flagged[0][1]["coh_p90"], flagged[0][1]["ang14_deg"])))
    else:
        verdicts.append(("PASS", "outer loop",
                         "no 1-4 Hz line in command and angle above the V282/V281r3 references "
                         "in any scored speed band  [screening flag, not a numeric pre-registration]"))

    # ---------------------------------------------------------------- 5. the other bands
    pr("")
    pr("5. THE OTHER BANDS -- 13-17 Hz (V292's rejected x1.9-2.1) and any 22-30 Hz line  [EVIDENCE]")
    pr("-" * 124)
    pr("   pooled Welch on the 0x18F rate, deg/s, no episode selection.  BOTH strata: 'hands-off 8-15")
    pr("   m/s' is the one the record headlined V292's 13-17 Hz x1.81-1.85 on, so it carries the gate;")
    pr("   'hands-off ALL speeds' is beside it because the 8-15 band can be thin on a short drive.")
    ratios = {}
    for strat in ("hands-off 8-15 m/s", "hands-off ALL speeds"):
        pr("   --- %s ---" % strat)
        pr("   %-24s %-9s %8s " % ("route", "build", "t s") + " ".join("%-9s" % b[0] for b in BANDS))

        def bline(nm, bld, sp, st=strat):
            d = sp.get(st, {})
            if not d or not d.get("amps"):
                pr("   %-24s %-9s %8.1f  -- under 5 Welch segments --"
                   % (nm, bld, (d or {}).get("t_s", 0.0)))
                return
            pr("   %-24s %-9s %8.1f " % (nm, bld, d["t_s"])
               + " ".join("%-9.3f" % d["amps"][b[0]] for b in BANDS))
        bline(tag, build, S["spectra"])
        for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
            sp = None if rt == tag else ref_get(refs, rt, "spectra")
            if sp:
                bline(rt, BUILD_OF.get(rt, "?"), sp)
        own = S["spectra"].get(strat, {}).get("amps")
        ref_sp = ref_get(refs, REF_V282, "spectra", strat, "amps")
        if own and ref_sp:
            ratios[strat] = {b[0]: own[b[0]] / ref_sp[b[0]] for b in BANDS}
            pr("   ratios to %s: " % REF_V282
               + "  ".join("%s x%.2f" % (b[0], ratios[strat][b[0]]) for b in BANDS))
    gate_strat = "hands-off 8-15 m/s" if "hands-off 8-15 m/s" in ratios else "hands-off ALL speeds"
    if gate_strat in ratios:
        r1317 = ratios[gate_strat]["13-17"]
        if r1317 >= THR["band_1317_ratio"]:
            verdicts.append(("REVERT", "13-17 Hz",
                             "13-17 Hz x%.2f of %s's on %s (>= %.1f) -- the prereg's B7 gate and the "
                             "'a 10-18 Hz line' revert trigger.  V292's rejected value was x1.81-1.85 "
                             "on this stratum." % (r1317, REF_V282, gate_strat, THR["band_1317_ratio"])))
        else:
            verdicts.append(("PASS", "13-17 Hz", "13-17 Hz x%.2f of %s's on %s (< %.1f)"
                             % (r1317, REF_V282, gate_strat, THR["band_1317_ratio"])))
        verdicts.append(("REPORT", "5-9 Hz",
                         "5-9 Hz hands-off x%.2f of %s's on %s -- a BROADBAND rise ~x1.5 is PREDICTED "
                         "(the servo's disturbance rejection removed, B5); a resonant LINE is not.  "
                         "Read it against the line table."
                         % (ratios[gate_strat]["5-9"], REF_V282, gate_strat)))
        r2230 = max(ratios[gate_strat]["22-26"], ratios[gate_strat]["26-30"])
        verdicts.append(("REPORT", "22-30 Hz", "22-30 Hz at most x%.2f of %s's -- reported, not gated"
                         % (r2230, REF_V282)))
    pr("   line locations (peak of the excess-dB spectrum), hands-off ALL speeds.  A LINE is a narrow")
    pr("   excess; a broadband rise shows as a band amplitude change with no dB excess moving:")
    dd = S["spectra"].get("hands-off ALL speeds", {}).get("lines")
    if dd:
        pr("   %-24s %s" % (tag, "  ".join("%s: %5.2f Hz %+5.2f dB" % (k, v[0], v[1])
                                           for k, v in dd.items())))
    for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
        ll = None if rt == tag else ref_get(refs, rt, "spectra", "hands-off ALL speeds", "lines")
        if ll:
            pr("   %-24s %s" % (rt, "  ".join("%s: %5.2f Hz %+5.2f dB" % (k, v[0], v[1])
                                              for k, v in ll.items())))

    # ---------------------------------------------------------------- 6. the cave
    pr("")
    pr("6. THE 0x14A CAVE DUTIES -- b4 = sign(r24) is the NEGATIVE CONTROL; b7 is the pre-registered")
    pr("   MOVER (0.996 -> 0.808).  b5/b6 are NOT pre-registered.  b0-b2 are stock Honda (1.000).")
    pr("-" * 124)
    C = S["cave"]
    if C is None:
        pr("   no 0x14A byte-4 cache for this route")
    else:
        pr("   %-24s %-18s %s %9s" % ("route", "stratum",
                                      " ".join("b%d   " % n for n in range(7, -1, -1)), "n"))
        for lab in ("engaged", "SCA=0", "IDLE still"):
            d = C[lab]
            pr("   %-24s %-18s %s %9d" % (tag, lab,
                                          " ".join("%.3f" % d["b%d" % n] for n in range(7, -1, -1)),
                                          d["n"]))
        for rt in ("r6c", "r39", "r35", "r6d_v292", "r6e_v292", "r6f_v292"):
            d = None if rt == tag else ref_get(refs, rt, "cave", "engaged")
            if d:
                pr("   %-24s %-18s %s %9d" % (rt + " (%s)" % BUILD_OF.get(rt, "?"), "engaged",
                                              " ".join("%.3f" % d["b%d" % n] for n in range(7, -1, -1)),
                                              d["n"]))
        pr("   pre-registered (DESIGN 6.2): b7 V282 0.996 -> V293 0.808 (the MOVER); "
           "b4 0.808 -> 0.808 (the NEGATIVE CONTROL, identical by construction).")
        pr("   🛑 DO NOT COMPARE THOSE TWO NUMBERS WITH THE ROWS ABOVE.  0.996 and 0.808 were computed")
        pr("   on r39's TEN LOUDEST ONE-DIRECTION TURN WINDOWS, where the summand's sign is pinned by")
        pr("   the turn.  Whole-route, V282 measures b7 0.507-0.548 and b4 0.394-0.404 (the rows")
        pr("   above).  The comparison that means anything is THIS ROUTE against the MEASURED V282")
        pr("   rows, which is what the b4 clause below uses.  [EVIDENCE -- --controls, 2026-09-13]")
        e = C["engaged"]
        b4ref = ref_get(refs, REF_V282, "cave", "engaged", "b4", default=RECORD["b4_duty"]["V282"])
        if build == "V293" and np.isfinite(e["b4"]) and b4ref:
            if abs(e["b4"] - b4ref) > 0.10:
                verdicts.append(("REPORT", "b4 control",
                                 "b4 (sign r24) reads %.3f against %s's %.3f -- b4 cannot depend on T, "
                                 "so a move this large means the DRIVING changed (or something other "
                                 "than the intended cal did)" % (e["b4"], REF_V282, b4ref)))
            else:
                verdicts.append(("PASS", "b4 control", "b4 (sign r24) %.3f vs %s's %.3f -- unchanged, "
                                                       "as the negative control requires"
                                 % (e["b4"], REF_V282, b4ref)))
        if build == "V293" and np.isfinite(e["b7"]):
            verdicts.append(("REPORT", "b7 mover",
                             "b7 (sign of the LKAS summand) reads %.3f; pre-registered 0.996 -> 0.808.  "
                             "It is a direction-of-turn statistic, so read it beside b4, not alone."
                             % e["b7"]))
        if np.isfinite(e["b0"]) and min(e["b0"], e["b1"], e["b2"]) < 0.999:
            verdicts.append(("REPORT", "b0-b2",
                             "b0/b1/b2 read %.3f/%.3f/%.3f -- these are STOCK Honda bits and read 1.000 "
                             "on every build; a departure means the decode or the frame changed"
                             % (e["b0"], e["b1"], e["b2"])))

    # ---------------------------------------------------------------- 7. the operator's symptoms
    verdicts += print_section7(S)
    return verdicts


# ======================================================================================================
# 10b. SECTION 7 -- THE OPERATOR'S FOUR SYMPTOMS
# ======================================================================================================
def _g(d, *path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def print_section7(S):
    """the four symptoms the operator reported on the rev-1 flight, each as a pre-registered
    instrument with its references RE-COMPUTED by this run."""
    v = []
    tag = S["tag"]
    own = S.get("symptom")
    pr("")
    pr("7. THE OPERATOR'S FOUR SYMPTOMS -- pre-registered instruments  [EVIDENCE]")
    pr("   route 70's verbatim score: \"steering felt RATCHETY, like the wheel did not move smoothly")
    pr("   but only SNAPPED BETWEEN ANGLES\" · \"sometimes LOOSE and then sometimes OVERSTEER and other")
    pr("   times on hard transients it would OVERSHOOT THEN CORRECT slightly\".  Definitions in")
    pr("   v293_symptom_instruments.py, ported from the identification's own scripts.")
    pr("   🛑 EVERY REFERENCE COLUMN IS RE-DERIVED BY THIS CODE AT RUN TIME on the cached routes --")
    pr("   none is copied from V293-PLANT-IDENT-2026-09-13.md.  The cache is keyed by a hash of the")
    pr("   instrument source (%s), so changing a definition invalidates every reference." % sym_code_hash())
    pr("   EVIDENCE vs BELIEF on the thresholds themselves:")
    pr("     [EVIDENCE] every NUMBER in every table -- measured from the cached wire by the code named.")
    pr("     [EVIDENCE] which routes pass and which fail each gate -- computed in the census at 7.7.")
    pr("     [BELIEF]   that any of these statistics is what the operator FELT.  The instruments were")
    pr("                chosen to match his words; the match is a judgement, not a measurement, and a")
    pr("                statistic moving is not the car feeling right.")
    pr("     [BELIEF]   the plant-spring column in 7.2 -- fitted on r70 and assumed to transfer, on the")
    pr("                grounds that the firmware does not change between drives.")
    pr("-" * 124)
    if not own:
        pr("   ⚠ section 7 is UNAVAILABLE on this route (no symptom block could be built).")
        return v
    R = symptom_refs()
    cols = [c for c in SYM_REF_ROUTES if c in R]

    def table(title, get, fmt_="%9.3f", rows=SI.SBNAME, note=None):
        pr("   %s" % title)
        pr("     %-9s %11s " % ("band", "THIS ROUTE")
           + " ".join("%9s" % c.replace("_v293", "").replace("_v292", "") for c in cols))
        for b in rows:
            mine = get(own, b)
            pr("     %-9s %11s " % (b, (fmt_ % mine) if mine is not None else "      n/a")
               + " ".join((fmt_ % get(R[c], b)) if get(R[c], b) is not None else "      n/a"
                          for c in cols))
        if note:
            pr("     %s" % note)

    # ---------------------------------------------------------------- 7.1 ratchet
    pr("")
    pr("   7.1 RATCHET -- \"snapped between angles rather than smoothly moving between them\"")
    pr("       dwell = the 0.10 s MOVING MEAN of |0x18F rate| below a threshold for >= 0.20 s.  The")
    pr("       raw-threshold detector is a DOCUMENTED ARTEFACT: it finds 13 dwells on r70 and ZERO on")
    pr("       r6c.  All-engaged on every route (the driver-torque bar cannot stand in for")
    pr("       steeringPressed on this car); r70's hands-off stratum is printed beside it.")
    table("dwells per minute at threshold 0.25 deg/s -- ALL ENGAGED",
          lambda s, b: _g(s, "dwell_eng", b, "per_min_025"), "%9.2f")
    table("dwells per minute at threshold 0.50 deg/s -- ALL ENGAGED",
          lambda s, b: _g(s, "dwell_eng", b, "per_min_050"), "%9.2f")
    table("dwell duration p90, s (th 0.50)   -- how long the wheel sits still before it moves",
          lambda s, b: _g(s, "dwell_eng", b, "dwell_p90"), "%9.3f")
    table("snap p90, deg (th 0.50)           -- how far it then jumps",
          lambda s, b: _g(s, "dwell_eng", b, "snap_p90"), "%9.2f")
    if own.get("dwell_ho"):
        pr("     hands-off stratum, this route, th 0.25: "
           + "  ".join("%s %s" % (b, fmt(_g(own, "dwell_ho", b, "per_min_025"), "%.2f"))
                       for b in SI.SBNAME))
    ref6c = R.get(SYM_REF_V282, {})
    bad, exposed = [], []
    for b in SI.SBNAME:
        mine = _g(own, "dwell_eng", b, "per_min_025")
        base = _g(ref6c, "dwell_eng", b, "per_min_025")
        sec = _g(own, "dwell_eng", b, "sec") or 0.0
        if mine is None or base is None:
            continue
        if sec < THR["ratchet_min_s"]:
            continue
        exposed.append(b)
        if mine > THR["ratchet_vs_r6c"] * base:
            bad.append("%s %.2f vs %.2f" % (b, mine, base))
    pr("     PRE-REGISTERED: dwells/min at th 0.25 must fall toward the V282 rows -- PASS if <= %.0fx"
       % THR["ratchet_vs_r6c"])
    pr("     r6c's in every band with >= %.0f s of exposure.  CALIBRATION: r70_v293 FAILS this in all"
       % THR["ratchet_min_s"])
    pr("     four bands (15.23/7.66/4.56/1.24 against r6c 0.39/0.64/0.44/0.20); r39 and r35 PASS it.")
    if not exposed:
        v.append(("REPORT", "ratchet", "no speed band carries %.0f s of exposure -- the dwell "
                                       "statistic is not decisive on this drive" % THR["ratchet_min_s"]))
    elif bad:
        v.append(("FAIL", "ratchet", "dwells/min at th 0.25 above %.0fx r6c's in %d of %d exposed "
                                     "bands: %s" % (THR["ratchet_vs_r6c"], len(bad), len(exposed),
                                                    "; ".join(bad))))
    else:
        v.append(("PASS", "ratchet", "dwells/min at th 0.25 within %.0fx r6c's in every exposed band "
                                     "(%s)" % (THR["ratchet_vs_r6c"], ", ".join(exposed))))
    # 🛑 THE SECOND REVERT TRIGGER, added 2026-09-13.  The rev-1 flight was driveable and the operator
    # scored it; a config that makes the ratchet WORSE than that is a step backwards, and the drive
    # stops.  Two bands, not one, so a single thin band cannot fire it.
    worse = []
    r70r = R.get("r70_v293", {})
    if tag != "r70_v293":
        for b in SI.SBNAME:
            mine = _g(own, "dwell_eng", b, "per_min_025")
            base = _g(r70r, "dwell_eng", b, "per_min_025")
            sec = _g(own, "dwell_eng", b, "sec") or 0.0
            if mine is None or base is None or sec < THR["ratchet_min_s"]:
                continue
            if mine > base:
                worse.append("%s %.2f vs %.2f" % (b, mine, base))
    pr("     REVERT TRIGGER: dwells/min at th 0.25 ABOVE r70_v293's in TWO OR MORE exposed bands --")
    pr("     the rev-1 flight was driveable and scored; a config that ratchets harder than it is a")
    pr("     step backwards and the drive stops.  Revert to the PREVIOUS config, not to V282.")
    if len(worse) >= 2:
        v.append(("REVERT", "ratchet", "the ratchet is WORSE than the rev-1 flight in %d bands (%s) -- "
                                       "go back to the previous toggle config"
                  % (len(worse), "; ".join(worse))))
    pr("")
    cal = SI.conc_calibration()
    pr("     RATE-MAGNITUDE CONCENTRATION -- of all the wheel travel in a 4 s window, the share")
    pr("     delivered in the fastest 10 % of its frames, binned by the window's OWN rms rate so the")
    pr("     comparison is activity-matched.  CALIBRATION, recomputed now: a pure sine %.3f, 0-2 Hz"
       % cal["sine"])
    pr("     band-limited noise %.3f, a 10-step staircase %.3f.  Bin edges are FROZEN at the pooled"
       % (cal["noise"], cal["staircase"]))
    pr("     four-route percentiles %s deg/s." % ", ".join("%.3f" % x for x in SI.CONC_EDGES[1:5]))
    table("", lambda s, b: _g(s, "conc", "rate", b, "med"), "%9.3f", rows=SI.CONC_LABELS)
    pr("     and the 0xE4 COMMAND on the same windows -- the control that says whether the snappiness")
    pr("     is INHERITED from openpilot or GENERATED by the car:")
    table("", lambda s, b: _g(s, "conc", "cmd", b, "med"), "%9.3f", rows=SI.CONC_LABELS)
    q = _g(own, "conc", "rate", "q75-90", "med")
    pr("     PRE-REGISTERED: the q75-90 bin must fall from 0.468 toward the references' 0.33-0.35 --")
    pr("     PASS if <= %.2f.  CALIBRATION: r70_v293 0.468 FAILS; r6c 0.345, r39 0.325, r35 0.351 PASS."
       % THR["conc_q7590"])
    if q is None:
        v.append(("REPORT", "concentration", "the q75-90 rms bin is empty on this drive"))
    elif q <= THR["conc_q7590"]:
        v.append(("PASS", "concentration", "rate concentration in the q75-90 bin %.3f (<= %.2f)"
                  % (q, THR["conc_q7590"])))
    else:
        v.append(("FAIL", "concentration", "rate concentration in the q75-90 bin %.3f (> %.2f) -- the "
                                           "wheel still delivers its travel in bursts" % (q, THR["conc_q7590"])))

    # ---------------------------------------------------------------- 7.2 loose
    pr("")
    pr("   7.2 LOOSE -- \"sometimes steering felt loose\"")
    pr("       ⚠ NOT WANDER.  r70's 0.1-1 Hz angle wander on straights was LOWER than V282's, so the")
    pr("       obvious reading is a measured NULL.  What is low is the outer loop's STIFFNESS against")
    pr("       the plant's own return spring.  Wander is REPORT-only; stiffness carries the reading.")
    table("0.1-1 Hz angle wander on straight-ish stretches, deg rms  [REPORT]",
          lambda s, b: _g(s, "wander", b, "rms"), "%9.4f")
    pr("")
    pr("     OUTER-LOOP STIFFNESS, openpilot torque units per degree of angle, on straights, beside")
    pr("     the plant's own return spring (identification F1/D1 joint fit).  A loop barely stiffer")
    pr("     than the spring cannot hold the wheel against it, and on a straight the feedforward is")
    pr("     nearly zero, so almost nothing else is.  [REPORT -- no numeric pre-registration]")
    pr("     %-9s %11s %12s %7s " % ("band", "THIS ROUTE", "plant spring", "ratio")
       + " ".join("%9s" % c.replace("_v293", "") for c in cols))
    for b in SI.SBNAME:
        mine = _g(own, "stiff", b, "tq_per_deg")
        spr = SI.PLANT_SPRING_TQ_PER_DEG[b]
        pr("     %-9s %11s %12.5f %7s " % (b, fmt(mine, "%.5f"), spr,
                                           fmt(mine / spr if mine else None, "%.2f"))
           + " ".join("%9s" % fmt(_g(R[c], "stiff", b, "tq_per_deg"), "%.5f") for c in cols))

    # ---------------------------------------------------------------- 7.3 oversteer
    pr("")
    pr("   7.3 OVERSTEER -- \"sometimes there was oversteer\"")
    table("turn-hold windows >= 1.5 s: mean|actual| / mean|desired| lateral accel",
          lambda s, b: _g(s, "hold", "bands", b, "ratio"))
    pr("     by DEMAND size, all speeds (the plant gain is amplitude-dependent):")
    dl = sorted((_g(own, "hold", "demand") or {}).keys())
    if dl:
        pr("     %-9s %11s " % ("|D|", "THIS ROUTE")
           + " ".join("%9s" % c.replace("_v293", "") for c in cols))
        for b in dl:
            pr("     %-9s %11s " % (b, fmt(_g(own, "hold", "demand", b, "ratio")))
               + " ".join("%9s" % fmt(_g(R[c], "hold", "demand", b, "ratio")) for c in cols))
    pr("")
    pr("     TRACKING GAIN -- slope of actual on desired lateral accel, both low-passed at 0.5 Hz,")
    pr("     over engaged runs >= 10 s.  🛑 ON THE IDENTIFICATION'S BAND GRID (<8 / 8-15 / 15-22 /")
    pr("     >22 m/s), because that is where the reference lives.  r70 rose 0.884 -> 1.020 -> 1.123:")
    pr("     UNDER-turning below 15 m/s, OVER-turning above 22 -- the feedforward's missing speed law,")
    pr("     seen directly in the closed loop.")
    table("", lambda s, b: _g(s, "track", b, "slope"), "%9.3f", rows=SI.IBNAME)
    pr("     exposure, s: " + "  ".join("%s %s" % (b, fmt(_g(own, "track", b, "sec"), "%.0f"))
                                        for b in SI.IBNAME))
    bad = []
    for b in SI.IBNAME:
        sl = _g(own, "track", b, "slope")
        sec = _g(own, "track", b, "sec") or 0.0
        if sl is None or sec < THR["track_min_s"]:
            continue
        if not (THR["track_lo"] <= sl <= THR["track_hi"]):
            bad.append("%s %.3f" % (b, sl))
    pr("     PRE-REGISTERED: tracking gain within %.2f-%.2f in every band with >= %.0f s -> PASS."
       % (THR["track_lo"], THR["track_hi"], THR["track_min_s"]))
    pr("     CALIBRATION: r70_v293 FAILS (>22 reads 1.123); r6c PASSES (0.966/0.968/0.996/0.989).")
    if bad:
        v.append(("FAIL", "tracking gain", "outside %.2f-%.2f in %s -- the loop does not deliver what "
                                           "the planner asks at those speeds"
                  % (THR["track_lo"], THR["track_hi"], ", ".join(bad))))
    else:
        v.append(("PASS", "tracking gain", "within %.2f-%.2f in every band with >= %.0f s"
                  % (THR["track_lo"], THR["track_hi"], THR["track_min_s"])))
    hr = _g(own, "hold", "bands", ">20", "ratio")
    pr("     PRE-REGISTERED: the >20 m/s turn-hold ratio 1.093 -> <= %.2f.  CALIBRATION: r70_v293 1.093"
       % THR["hold_hi"])
    pr("     FAILS and r6c 0.995 PASSES -- bracketed on both sides by real data.")
    if hr is None:
        v.append(("REPORT", "turn hold", "no turn-hold runs >= 1.5 s above 20 m/s on this drive"))
    elif hr <= THR["hold_hi"]:
        v.append(("PASS", "turn hold", "turn-hold actual/desired above 20 m/s = %.3f (<= %.2f)"
                  % (hr, THR["hold_hi"])))
    else:
        v.append(("FAIL", "turn hold", "turn-hold actual/desired above 20 m/s = %.3f (> %.2f) -- the "
                                       "car still turns more than the planner asks" % (hr, THR["hold_hi"])))

    # ---------------------------------------------------------------- 7.4 overshoot
    pr("")
    pr("   7.4 OVERSHOOT-THEN-CORRECT -- \"on hard transients it would overshoot then correct slightly\"")
    pr("       steps: |d(desiredLateralAccel)| >= 0.30 m/s^2 over 0.5 s, hands-off, >= 2.5 s apart,")
    pr("       with the demand settling for 1.5 s.  Overshoot is relative to the final demand.")
    table("relative overshoot (median over the band's step events)",
          lambda s, b: _g(s, "step", "bands", b, "ov"))
    table("absolute overshoot, m/s^2", lambda s, b: _g(s, "step", "bands", b, "ov_abs"), "%9.3f")
    table("time to peak, s", lambda s, b: _g(s, "step", "bands", b, "tpk"), "%9.2f")
    pr("     step events: this route %s  |  " % fmt(_g(own, "step", "n"), "%.0f")
       + "  ".join("%s %s" % (c.replace("_v293", ""), fmt(_g(R[c], "step", "n"), "%.0f"))
                   for c in cols))
    d = _g(own, "step", "discriminator") or {}
    pr("     THE DISCRIMINATOR, carried with it: absolute overshoot regressed on STEP SIZE reads")
    pr("       slope %s, intercept %s, R2 %s over %s events; correlation with the integrator at the"
       % (fmt(d.get("slope"), "%.4f"), fmt(d.get("intercept"), "%+.4f"), fmt(d.get("r2"), "%.3f"),
          d.get("n", "-")))
    pr("       peak %s.  An UNDER-DAMPED LINEAR LOOP gives a positive slope and ~0 intercept; a"
       % fmt(d.get("corr_i"), "%+.3f"))
    pr("       STICTION RELEASE or a fixed feedforward offset gives slope ~0 and a positive intercept.")
    pr("       On r70 that read -0.456 / +0.571 / R2 0.027 -- a roughly FIXED excursion that does not")
    pr("       scale, which RULES OUT an under-damped linear loop.  [EVIDENCE]")
    bad = []
    for b in ("10-20", ">20"):
        ov = _g(own, "step", "bands", b, "ov")
        if ov is not None and ov > THR["overshoot"]:
            bad.append("%s %.3f" % (b, ov))
    pr("     PRE-REGISTERED: relative overshoot <= %.2f at 10-20 and >20 m/s -> PASS.  CALIBRATION:"
       % THR["overshoot"])
    pr("     r70_v293 FAILS both (0.437 and 0.341).  🛑 NO route in the corpus passes this at 10-20 m/s")
    pr("     (r6c 0.226 is the closest), so it is a TARGET, not a bracketed threshold -- see the")
    pr("     census in 7.7.  A FAIL here means \"not yet at the target\", not \"worse than V282\".")
    if bad:
        v.append(("FAIL", "overshoot", "relative step overshoot above %.2f at %s"
                  % (THR["overshoot"], ", ".join(bad))))
    elif any(_g(own, "step", "bands", b, "ov") is not None for b in ("10-20", ">20")):
        v.append(("PASS", "overshoot", "relative step overshoot <= %.2f at every scored band >= 10 m/s"
                  % THR["overshoot"]))
    else:
        v.append(("REPORT", "overshoot", "no step events above 10 m/s on this drive"))

    # ---------------------------------------------------------------- 7.5 the report rows
    pr("")
    pr("   7.5 REPORT ROWS -- the outer loop, the integrator and the delivery")
    table("1-4 Hz PROMINENCE above the shoulder-fitted baseline, dB (a line, or just the road?)",
          lambda s, b: _g(s, "prom", b, "prom"), "%9.2f")
    table("1-4 Hz content on the 0x18F RATE, deg/s (quantiser-free)",
          lambda s, b: _g(s, "prom", b, "rate"), "%9.2f")
    pr("     ⚠ the FLAT-baseline prominence estimator returns 16-21 dB on EVERY route and is not used.")
    badp = [b for b in SI.SBNAME
            if (_g(own, "prom", b, "prom") or -99) >= THR["prom_db"]]
    badr = []
    for b in SI.SBNAME:
        mine = _g(own, "prom", b, "rate")
        base = _g(ref6c, "prom", b, "rate")
        if mine is not None and base and mine > THR["rate14_vs_r6c"] * base:
            badr.append("%s %.1f vs %.1f" % (b, mine, base))
    pr("     PRE-REGISTERED: prominence < %.0f dB in every band AND 1-4 Hz rate content <= %.0fx r6c's."
       % (THR["prom_db"], THR["rate14_vs_r6c"]))
    pr("     CALIBRATION: r70_v293 FAILS both (6.5-11.8 dB; 4.8-11.6x).  r6c, r39 and r35 all PASS the")
    pr("     prominence clause (max 2.21 dB), so that one is bracketed; the rate-content clause is")
    pr("     against r6c itself, so only r6c passes it trivially -- read the census in 7.7.")
    if badp or badr:
        v.append(("FAIL", "1-4 Hz", ("prominence >= %.0f dB in %s" % (THR["prom_db"], ", ".join(badp))
                                     if badp else "")
                  + ("; " if badp and badr else "")
                  + ("rate content above %.0fx r6c's at %s" % (THR["rate14_vs_r6c"], "; ".join(badr))
                     if badr else "")))
    else:
        v.append(("PASS", "1-4 Hz", "no 1-4 Hz line (prominence < %.0f dB everywhere) and rate content "
                                    "within %.0fx r6c's" % (THR["prom_db"], THR["rate14_vs_r6c"])))
    pr("")
    table("INTEGRATOR SHARE of |f|+|p|+|i|  [IDENT band grid]",
          lambda s, b: _g(s, "shares", b, "i"), "%9.3f", rows=SI.IBNAME)
    ish = [x for x in (_g(own, "shares", b, "i") for b in SI.IBNAME) if x is not None]
    pr("     PRE-REGISTERED: < %.2f.  r70_v293 read 0.35-0.38 and FAILS; a feedforward that is right"
       % THR["i_share"])
    pr("     should not need the integrator to carry a third of the command.  🛑 NO route in the")
    pr("     corpus passes this either (r6c 0.30-0.40) -- a TARGET, not a bracketed threshold.  It is")
    pr("     the number a feedforward fix should move furthest, which is why it is scored at all.")
    if not ish:
        v.append(("REPORT", "integrator", "no control-path frames -- the integrator share is unread"))
    elif max(ish) < THR["i_share"]:
        v.append(("PASS", "integrator", "integrator share %.3f at its worst band (< %.2f)"
                  % (max(ish), THR["i_share"])))
    else:
        v.append(("FAIL", "integrator", "integrator share %.3f at its worst band (>= %.2f) -- the "
                                        "feedforward is still persistently wrong at DC"
                  % (max(ish), THR["i_share"])))
    pr("")
    pr("     DELIVERY BY REGIME, mean|actual| / mean|desired| (demand-defined regimes):")
    regs = ("straight", "turn entry", "turn hold", "turn exit", "low-speed manoeuvre")
    pr("     %-22s %11s " % ("regime", "THIS ROUTE")
       + " ".join("%9s" % c.replace("_v293", "") for c in cols))
    for rg in regs:
        mine = _g(own, "regime", rg, "deliver")
        pr("     %-22s %11s " % (rg, fmt(mine * 100 if mine else None, "%.1f"))
           + " ".join("%9s" % fmt((_g(R[c], "regime", rg, "deliver") or 0) * 100 or None, "%.1f")
                      for c in cols))
    st = _g(own, "regime", "straight", "deliver")
    pr("     PRE-REGISTERED: straight-line delivery %.0f-%.0f %%.  r70_v293 read 80.0 %% and FAILS --"
       % (100 * THR["deliver_lo"], 100 * THR["deliver_hi"]))
    pr("     under-delivering on straights is the friction error, and straights are where the")
    pr("     feedforward is nearly zero and the friction is nearly all of it.  🛑 NO reference route")
    pr("     passes this band either -- r6c UNDER-delivers at 86 % and r39/r35 OVER-deliver at")
    pr("     111/117 % -- so it is a TARGET.  What it does measure cleanly is the DIRECTION and size")
    pr("     of the straight-line error, which is the friction term's own signature.")
    if st is None:
        v.append(("REPORT", "straight delivery", "no straight regime on this drive"))
    elif THR["deliver_lo"] <= st <= THR["deliver_hi"]:
        v.append(("PASS", "straight delivery", "straight-line delivery %.1f %% (%.0f-%.0f %%)"
                  % (100 * st, 100 * THR["deliver_lo"], 100 * THR["deliver_hi"])))
    else:
        v.append(("FAIL", "straight delivery", "straight-line delivery %.1f %% (wants %.0f-%.0f %%)"
                  % (100 * st, 100 * THR["deliver_lo"], 100 * THR["deliver_hi"])))

    # ---------------------------------------------------------------- 7.6 the POSITIVE CONTROL
    pr("")
    pr("   7.6 POSITIVE CONTROL -- does this code reproduce the identification on r70_v293?")
    pr("       Tolerance: %.0f %% relative or %.3f absolute, whichever is larger.  A FAIL here means an"
       % (100 * IDENT_TOL, 0.003))
    pr("       instrument moved, and every number in section 7 must be re-read before it is trusted.")
    r70 = R.get("r70_v293")
    if not r70:
        pr("       ⚠ r70_v293 is not in the reference set -- the positive control could not run.")
        v.append(("REPORT", "positive control", "r70_v293 has no symptom block; section 7's "
                                                "instruments are UNVALIDATED on this run"))
    else:
        checks = [
            ("dwells/min th 0.25, all-engaged", IDENT_R70["dwell025_eng"],
             [_g(r70, "dwell_eng", b, "per_min_025") for b in SI.SBNAME]),
            ("dwells/min th 0.25, hands-off", IDENT_R70["dwell025_ho"],
             [_g(r70, "dwell_ho", b, "per_min_025") for b in SI.SBNAME]),
            ("rate concentration", IDENT_R70["conc"],
             [_g(r70, "conc", "rate", b, "med") for b in SI.CONC_LABELS]),
            ("loop stiffness, torque/deg", IDENT_R70["stiff"],
             [_g(r70, "stiff", b, "tq_per_deg") for b in SI.SBNAME]),
            ("turn-hold ratio", IDENT_R70["hold"],
             [_g(r70, "hold", "bands", b, "ratio") for b in SI.SBNAME]),
            ("tracking gain", IDENT_R70["track"], [_g(r70, "track", b, "slope") for b in SI.IBNAME]),
            ("relative overshoot", IDENT_R70["step"],
             [_g(r70, "step", "bands", b, "ov") for b in SI.SBNAME]),
            ("1-4 Hz prominence, dB", IDENT_R70["prom"], [_g(r70, "prom", b, "prom") for b in SI.SBNAME]),
            ("1-4 Hz rate content", IDENT_R70["rate14"], [_g(r70, "prom", b, "rate") for b in SI.SBNAME]),
            ("integrator share", IDENT_R70["i_share"], [_g(r70, "shares", b, "i") for b in SI.IBNAME]),
            ("straight delivery", (IDENT_R70["straight"],), [_g(r70, "regime", "straight", "deliver")]),
        ]
        nfail = 0
        pr("       %-34s %-42s %s" % ("instrument", "recomputed", "published / verdict"))
        for nm, want, got in checks:
            oks = [_within(g_, w_) for g_, w_ in zip(got, want)]
            ok = all(o is not False for o in oks)
            nfail += 0 if ok else 1
            pr("       %-34s %-42s %-30s %s"
               % (nm, " ".join("%8s" % fmt(x, "%.4f") for x in got),
                  " ".join("%8s" % (("%.4f" % w) if w is not None else "  -") for w in want),
                  "ok" if ok else "🛑 MOVED"))
        if nfail:
            v.append(("FAIL", "positive control",
                      "%d of %d instruments no longer reproduce the identification on r70_v293 -- "
                      "section 7 is not trustworthy until that is resolved" % (nfail, len(checks))))
        else:
            v.append(("PASS", "positive control",
                      "all %d instruments reproduce V293-PLANT-IDENT-2026-09-13.md on r70_v293 within "
                      "%.0f %%" % (len(checks), 100 * IDENT_TOL)))
    # ---------------------------------------------------------------- 7.7 the CALIBRATION CENSUS
    pr("")
    pr("   7.7 THRESHOLD CALIBRATION CENSUS -- every gate, run on every reference route")
    pr("       🛑 A GATE NOTHING FAILS IS THEATRE.  A GATE NOTHING PASSES IS A TARGET, NOT A")
    pr("       CALIBRATION -- and this table says which is which, by RUNNING each gate's own")
    pr("       predicate on each cached route rather than asserting it in prose.  A gate marked")
    pr("       TARGET ONLY is still worth scoring, but a FAIL on it does not mean the drive is worse")
    pr("       than the corpus; it means nothing in the corpus has ever met it.")
    pr("       %-24s %-16s " % ("gate", "threshold")
       + " ".join("%9s" % c.replace("_v293", "") for c in cols) + "   %s" % "verdict")
    for nm, thtxt, fn, selfref in _gate_predicates():
        res = []
        for c in cols:
            try:
                res.append(fn(R[c]))
            except Exception:
                res.append(None)
        # 🛑 A gate stated AS A RATIO TO r6c makes r6c's own PASS tautological (1 <= 2), so it does
        # not count as evidence that the gate is reachable.  Judge those on the other routes only.
        judged = [x for c, x in zip(cols, res) if not (selfref and c == SYM_REF_V282)]
        nP = sum(1 for x in judged if x is True)
        nF = sum(1 for x in judged if x is False)
        if nP and nF:
            verd = "bracketed"
        elif nF and not nP:
            verd = ("🛑 TARGET ONLY -- only %s passes, and it does so by construction" % SYM_REF_V282
                    if selfref else "🛑 TARGET ONLY -- no reference route passes")
        elif nP and not nF:
            verd = "🛑 NOTHING FAILS -- this gate does not discriminate"
        else:
            verd = "unscoreable on the corpus"
        pr("       %-24s %-16s " % (nm + (" *" if selfref else ""), thtxt)
           + " ".join("%9s" % ("PASS" if x is True else ("FAIL" if x is False else "n/a"))
                      for x in res) + "   %s" % verd)
    pr("       * stated as a RATIO TO %s, so that column passes by construction and is excluded from"
       % SYM_REF_V282)
    pr("         the bracketing judgement.")
    pr("")
    pr("   🛑 THESE ARE INSTRUMENTS, NOT A VERDICT ON THE FEEL.  The operator scores the symptoms.")
    pr("   A PASS here licenses \"the statistic the operator's words pointed at has moved\", nothing")
    pr("   more -- and a statistic moving is not the same as the car feeling right.")
    return v


def _gate_predicates():
    """each section 7 gate as a predicate over a symptom block, so the census below RUNS them rather
    than quoting them.  Returns (name, threshold text, fn -> True/False/None)."""
    def mk_ratchet(refs):
        def f(s):
            bad = exposed = 0
            for b in SI.SBNAME:
                mine = _g(s, "dwell_eng", b, "per_min_025")
                base = _g(refs.get(SYM_REF_V282, {}), "dwell_eng", b, "per_min_025")
                sec = _g(s, "dwell_eng", b, "sec") or 0.0
                if mine is None or base is None or sec < THR["ratchet_min_s"]:
                    continue
                exposed += 1
                bad += 1 if mine > THR["ratchet_vs_r6c"] * base else 0
            return None if not exposed else (bad == 0)
        return f

    def conc(s):
        q = _g(s, "conc", "rate", "q75-90", "med")
        return None if q is None else (q <= THR["conc_q7590"])

    def track(s):
        seen = False
        for b in SI.IBNAME:
            sl = _g(s, "track", b, "slope")
            sec = _g(s, "track", b, "sec") or 0.0
            if sl is None or sec < THR["track_min_s"]:
                continue
            seen = True
            if not (THR["track_lo"] <= sl <= THR["track_hi"]):
                return False
        return True if seen else None

    def hold(s):
        r = _g(s, "hold", "bands", ">20", "ratio")
        return None if r is None else (r <= THR["hold_hi"])

    def over(s):
        seen = False
        for b in ("10-20", ">20"):
            ov = _g(s, "step", "bands", b, "ov")
            if ov is None:
                continue
            seen = True
            if ov > THR["overshoot"]:
                return False
        return True if seen else None

    def prom(s):
        vals = [_g(s, "prom", b, "prom") for b in SI.SBNAME]
        vals = [x for x in vals if x is not None]
        return None if not vals else (max(vals) < THR["prom_db"])

    def mk_rate14(refs):
        def f(s):
            seen = False
            for b in SI.SBNAME:
                mine = _g(s, "prom", b, "rate")
                base = _g(refs.get(SYM_REF_V282, {}), "prom", b, "rate")
                if mine is None or not base:
                    continue
                seen = True
                if mine > THR["rate14_vs_r6c"] * base:
                    return False
            return True if seen else None
        return f

    def ish(s):
        vals = [_g(s, "shares", b, "i") for b in SI.IBNAME]
        vals = [x for x in vals if x is not None]
        return None if not vals else (max(vals) < THR["i_share"])

    def deliv(s):
        d = _g(s, "regime", "straight", "deliver")
        return None if d is None else (THR["deliver_lo"] <= d <= THR["deliver_hi"])

    refs = symptom_refs()
    return [
        ("ratchet dwells th0.25", "<= %.0fx r6c" % THR["ratchet_vs_r6c"], mk_ratchet(refs), True),
        ("concentration q75-90", "<= %.2f" % THR["conc_q7590"], conc, False),
        ("tracking gain", "%.2f-%.2f" % (THR["track_lo"], THR["track_hi"]), track, False),
        ("turn hold >20 m/s", "<= %.2f" % THR["hold_hi"], hold, False),
        ("step overshoot", "<= %.2f" % THR["overshoot"], over, False),
        ("1-4 Hz prominence", "< %.0f dB" % THR["prom_db"], prom, False),
        ("1-4 Hz rate content", "<= %.0fx r6c" % THR["rate14_vs_r6c"], mk_rate14(refs), True),
        ("integrator share", "< %.2f" % THR["i_share"], ish, False),
        ("straight delivery", "%.0f-%.0f %%" % (100 * THR["deliver_lo"], 100 * THR["deliver_hi"]),
         deliv, False),
    ]


def print_verdicts(S, verdicts):
    pr("")
    pr("=" * 124)
    pr("PRE-REGISTERED CLAUSES -- %s" % S["tag"])
    pr("=" * 124)
    pr("EVERY GATE BELOW IS CALIBRATED BY V292 -- the build the operator drove and rejected on")
    pr("2026-09-13.  Measured by `--controls` against r6c (V282): V292 read the ring at x1.38/x1.07/")
    pr("x1.25 (gate <= 0.40), F7 at 3.99/2.22/6.30 per 100 s (gate < 2), rip/L at 0.214/0.327/0.339")
    pr("(gate < 0.25) and the ABSOLUTE 6-8.5 Hz tap ripple at x2.23/x2.02/x2.23 (gate < 1.5).  A gate")
    pr("that a rejected build passes is theatre; none of these does.  [EVIDENCE]")
    pr("-" * 124)
    order = {"REVERT": 0, "FAIL": 1, "PASS": 2, "REPORT": 3}
    for lvl, clause, txt in sorted(verdicts, key=lambda z: order.get(z[0], 9)):
        pr("  [%-6s] %-14s %s" % (lvl, clause, txt))
    nrev = sum(1 for l, _, _ in verdicts if l == "REVERT")
    nfail = sum(1 for l, _, _ in verdicts if l == "FAIL")
    ratrev = any(c == "ratchet" for l, c, _ in verdicts if l == "REVERT")
    pr("")
    pr("  TWO CLASSES OF REVERT TRIGGER, and they point at DIFFERENT things:")
    pr("    * the BAND triggers (outer loop, F7, rip/L, absolute ripple, 13-17 Hz) say STOP THE DRIVE")
    pr("      and go back to V282 -- the FIRMWARE is the suspect.")
    pr("    * the RATCHET trigger (section 7.1: dwells/min at th 0.25 above r70_v293's in two or more")
    pr("      exposed bands) says go back to the PREVIOUS TOGGLE CONFIG -- the fork tune is the")
    pr("      suspect, the firmware is not, and r70_v293 was a driveable, scored baseline.")
    if nrev:
        pr("  >>> %d REVERT trigger(s) fired.  %s" % (
            nrev, ("Revert the TOGGLE CONFIG (the ratchet trigger fired); if a band trigger fired too, "
                   "go back to V282 as well." if ratrev
                   else "The pre-registration's instruction is to STOP THE DRIVE and go back to V282.")))
    elif nfail:
        pr("  >>> %d clause(s) FAILED and no revert trigger fired." % nfail)
    else:
        pr("  >>> no revert trigger fired and no clause failed.")
    pr("")
    pr("  🛑 THE OPERATOR SCORES THE SYMPTOMS.  Nothing above licenses the word 'fixed' for grinding,")
    pr("     vibrating, micro-ratcheting, ratcheting or excess friction.  These are BANDS.")
    pr("  🛑 Operator-only revert triggers, not scoreable here: grinding unchanged; a darty or loose")
    pr("     feel; a one-sided pull at rest; any EME warning or DTC.")
    if S.get("_identity_holds") and S.get("_ring_ratio") is not None \
            and S["_ring_ratio"] > THR["ring_ratio"]:
        pr("")
        pr("=" * 124)
        pr("THE TERMINAL NULL SENTENCE -- the identity HOLDS and the ring did NOT fall.  Verbatim:")
        pr("=" * 124)
        pr("  ADVERSARIAL-V293-PREREG 'What PASS licenses':")
        for ln in _wrap(NULL_SENTENCE_PREREG, 116):
            pr("    %s" % ln)
        pr("")
        pr("  DESIGN-V293-TORQUE-MODE section 6.3:")
        for ln in _wrap(NULL_SENTENCE_DESIGN, 116):
            pr("    %s" % ln)


def _wrap(s, w):
    words, line, out = s.split(), "", []
    for x in words:
        if len(line) + len(x) + 1 > w:
            out.append(line); line = x
        else:
            line = (line + " " + x).strip()
    if line:
        out.append(line)
    return out


# ======================================================================================================
# 11. THE CONTROLS -- the negative control AND the reference table, in one pass
# ======================================================================================================
def run_controls(routes=CONTROL_ROUTES):
    pr("=" * 124)
    pr("V293 FLIGHT READ -- CONTROLS.  The SAME identity estimator on routes that are NOT V293.")
    pr("An instrument that passes everywhere measures nothing: the identity MUST FAIL on r6c (V282)")
    pr("and on r6d/r6e/r6f (V292).  This pass also recomputes every band reference the drive-day read")
    pr("cites, and writes them to %s." % os.path.relpath(REFS_JSON, KIT))
    pr("=" * 124)
    refs, rows = load_refs(), []
    for tag in routes:
        b = BUILD_OF.get(tag)
        if b is None:
            pr("  %s: no build mapping -- skipped" % tag); continue
        if not os.path.exists(os.path.join(CACHE, tag + ".npz")):
            pr("  %s: no cache -- skipped" % tag); continue
        pr("")
        pr("  scoring %s (%s) ..." % (tag, b))
        # the symptom block has its OWN cache (keyed by the instrument code) and its own rlog pass;
        # running it here would do a full control-path extraction on routes the section never cites.
        S = score_route(tag, b, with_positive=False, with_symptoms=False)
        refs[tag] = dict(build=b, engdis=S["engdis"], spectra=S["spectra"],
                         presence=S["presence"], strongturn=S["strongturn"],
                         outer=S["outer"], cave=S["cave"],
                         identity={k: v for k, v in S["identity"]["fits"].items()},
                         exposure=dict(engaged_s=S["engaged_s"], disengaged_s=S["disengaged_s"],
                                       hiang_s=S["hiang_s"], creep_s=S["creep_s"]))
        # the identity under V293's OWN cells -- the number that must FAIL on a non-V293 route
        r = load_route(tag, b)
        I293 = identity_block(r, [("V293", cells_for("V293"))])
        refs[tag]["identity_as_V293"] = I293["fits"]
        best = None
        for k, v in I293["fits"].items():
            if v and (best is None or v["r2"] > best["r2"]):
                best = v
        own = None
        for k, v in S["identity"]["fits"].items():
            if k.startswith(b + "/") and v and (own is None or v["r2"] > own["r2"]):
                own = v
        rows.append((tag, b, best, own))
        pr("    identity scored with V293's cells : R2 %s  resid %s  (n %s, lag %s ms)"
           % (fmt(best and best["r2"], "%+.4f"), fmt(best and best["resid"], "%.1f"),
              best and best["n"], best and int(best["lag_ms"])))
        pr("    identity scored with %s's own cells: R2 %s  resid %s"
           % (b, fmt(own and own["r2"], "%+.4f"), fmt(own and own["resid"], "%.1f")))
    os.makedirs(SCR, exist_ok=True)
    json.dump(refs, open(REFS_JSON, "w"), indent=1, default=float)
    pr("")
    pr("=" * 124)
    pr("NEGATIVE CONTROL -- the identity on routes that are NOT V293.  Every row must FAIL the")
    pr("R2 >= %.2f / resid <= %.0f gate, or the instrument does not discriminate." % (THR["identity_r2"], THR["identity_resid"]))
    pr("=" * 124)
    pr("  %-12s %-8s %10s %10s %10s %10s %9s   %s" %
       ("route", "build", "R2 (V293)", "resid", "R2 (own)", "resid", "lag ms", "verdict"))
    allfail = True
    for tag, b, best, own in rows:
        okk = bool(best) and best["r2"] >= THR["identity_r2"] and best["resid"] <= THR["identity_resid"]
        allfail &= not okk
        pr("  %-12s %-8s %10s %10s %10s %10s %9s   %s" %
           (tag, b, fmt(best and best["r2"], "%+.4f"), fmt(best and best["resid"], "%.1f"),
            fmt(own and own["r2"], "%+.4f"), fmt(own and own["resid"], "%.1f"),
            fmt(best and best["lag_ms"], "%.0f"),
            "🛑 PASSES -- INSTRUMENT IS BROKEN" if okk else "FAILS, as required"))
    pr("")
    pr("  >>> %s" % ("the identity FAILS on every non-V293 route -- the instrument DISCRIMINATES. "
                     "[EVIDENCE]" if allfail else
                     "🛑 the identity PASSED on a non-V293 route.  It cannot attribute a V293 drive. "
                     "DO NOT use section 1 to attribute the build until this is resolved."))
    pr("  Pre-registered comparison: V282/V292 R2 ~ -4.81, residual ~349 counts (DESIGN 6.2, on r39's")
    pr("  ten loudest windows).  These rows are whole-route, so they are not expected to match exactly;")
    pr("  what must hold is the SIGN and the order of magnitude.")
    pr("")
    pr("  wrote %s" % REFS_JSON)
    return refs


# ======================================================================================================
# 12. MAIN
# ======================================================================================================
def main():
    ap = argparse.ArgumentParser(description="the turnkey scorer for the first V293 drive")
    ap.add_argument("route", nargs="?", help="route id (75604b0a...--xxxx), route counter, or cache tag")
    ap.add_argument("--build", default=None, choices=["V293", "V282", "V292", "V281r3"],
                    help="which image's cells to score against (default: V293, or the route's known build)")
    ap.add_argument("--tag", default=None, help="cache tag to write/read (default rNN_v293)")
    ap.add_argument("--controls", action="store_true",
                    help="run the negative control + recompute every band reference")
    ap.add_argument("--no-positive", action="store_true", help="skip the positive control (faster)")
    ap.add_argument("--no-symptoms", action="store_true", help="skip section 7 (faster)")
    ap.add_argument("--reextract", action="store_true", help="rebuild the cache even if it exists")
    ap.add_argument("--config", default=None,
                    help="the EXPECTED fork toggle config: a *.decoded.json under "
                         "analysis-2020accord/reference/.  Default: the rev-2 file if it exists, "
                         "else the rev-1 torque-mode file.")
    ap.add_argument("--refresh-symptom-refs", action="store_true",
                    help="recompute section 7's reference routes even if the cache is current")
    a = ap.parse_args()
    os.makedirs(SCR, exist_ok=True)
    set_config(a.config)
    if a.refresh_symptom_refs:
        symptom_refs(force=True)
    if a.controls:
        run_controls()
        io.open(os.path.join(SCR, "v293_flight_read_controls.txt"), "w",
                encoding="utf-8").write("\n".join(OUT) + "\n")
        pr("wrote _scratch/v293_flight_read_controls.txt")
        return
    if not a.route:
        ap.error("give a route id / cache tag, or --controls")
    tag, prefix = resolve(a.route, a.tag)
    if prefix and (a.reextract or not os.path.exists(os.path.join(CACHE, tag + ".npz"))):
        pr("=" * 124)
        extract(prefix, tag)
    if not os.path.exists(os.path.join(CACHE, tag + ".npz")):
        raise SystemExit("no cache for %s and no rlogs to build it from" % tag)
    build = a.build or BUILD_OF.get(tag, "V293")
    refs = load_refs()
    if not refs:
        pr("  ⚠ no reference table at %s -- run `--controls` once to build it.  Falling back to the"
           % os.path.relpath(REFS_JSON, KIT))
        pr("    literals transcribed from V292-FLIGHT-READ-2026-09-13.md (printed beside every number).")
    S = score_route(tag, build, with_positive=not a.no_positive, prefix=prefix,
                    with_symptoms=not a.no_symptoms)
    v = print_scorecard(S, refs)
    print_verdicts(S, v)
    json.dump(S, open(os.path.join(SCR, "v293_flight_read_%s.json" % tag), "w"), indent=1, default=float)
    io.open(os.path.join(SCR, "v293_flight_read_%s.txt" % tag), "w",
            encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_flight_read_%s.{txt,json}" % tag)


if __name__ == "__main__":
    main()
