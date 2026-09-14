# -*- coding: utf-8 -*-
"""v293_flight_read.py -- THE TURNKEY SCORER FOR THE FIRST V293 DRIVE.  ONE COMMAND.

    python rlog-tools/studies/grind/v293_flight_read.py <route id or cache tag> [--build V293|V282|V292]

It extracts the route into the v280-format cache if it is not there already (decode copied VERBATIM
from extract_v292_routes.py, so every census tool reads it with the same yardstick), then prints a
one-page scorecard against the PRE-REGISTERED read:

    docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md   "What PASS licenses" + the adjudication
    docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md  section 6

SECTIONS
  0  exposure, the fork toggles, and `epsTorqueMode` -- is this drive attributable at all?
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
#    is nine flag/byte fields from the V31P-V2 gate telemetry; the fork's is eight floats/bools plus
#    `epsTorqueMode @8 :Bool`).  So the kit's decoder reads the fork's lateral state as EpsTelemetry
#    and every field is garbage.  We do NOT edit the kit's schema; we build a patched COPY under
#    _scratch/ and load it with capnp.load().  Everything else in the schema is untouched, and nothing
#    on the extraction path (can / carState / userBookmark / initData) reads this struct.
FORK_STRUCT = """struct EpsTelemetry @0xc2243c65e0340384 {
  # PATCHED COPY for the V293 flight read -- the FORK repurposed this struct id as
  # StarPilotLateralState (cereal/custom.capnp on raayyymond-StarPilot/StarPilot @ Dom).  Field list
  # copied verbatim from the fork so `epsTorqueMode` decodes correctly.  The kit's own schema is NOT
  # modified by this file.
  active @0 :Bool;
  frictionThreshold @1 :Float32;
  frictionScale @2 :Float32;
  feedforward @3 :Float32;
  frictionJerk @4 :Float32;
  frictionJerkDeadzone @5 :Float32;
  lowSpeedFactor @6 :Float32;
  unwindDetected @7 :Bool;
  epsTorqueMode @8 :Bool;
}"""
# 🛑 A SECOND COLLISION, same shape.  The kit declares `modelDataV2SP @116 :Custom.ModelDataV2SP`
# (struct id 0xa1680744031fdb2d, one enum field); the FORK declares the same slot and the same struct
# id as `customReserved9 :Custom.CustomReserved9`, six Text/UInt64 fields carrying THE TESTING GROUND
# SELECTION.  That is where the torque-mode switch lives now, so it has to be patched too.
FORK_TG_STRUCT = """struct ModelDataV2SP @0xa1680744031fdb2d {
  # PATCHED COPY -- the FORK repurposed this struct id as CustomReserved9, which carries the Testing
  # Ground selection published by the_galaxy (slot 9 "Accord EPS Torque Mode", variant B = torque
  # mode).  Field list copied verbatim from the fork.
  slotId @0 :Text;
  slotName @1 :Text;
  variant @2 :Text;
  variantLabel @3 :Text;
  reason @4 :Text;
  wallTimeNanos @5 :UInt64;
}"""
TG_SLOT, TG_VARIANT = "9", "B"          # starpilot/common/testing_grounds.py: TESTING_GROUND_9 = "9"
_LOG = None


def fork_log_schema():
    """load a PATCHED copy of the kit's cereal so `epsTorqueMode` decodes.  Falls back to the kit's
    own schema (and says so) if anything goes wrong -- a missing toggle read must not stop the read."""
    global _LOG
    if _LOG is not None:
        return _LOG
    src = os.path.join(KIT, "rlog-tools", "cereal")
    dst = os.path.join(SCR, "cereal_fork")
    try:
        import capnp
        capnp.remove_import_hook()
        stamp = os.path.join(dst, ".patched")
        if not os.path.exists(stamp):
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
            io.open(stamp, "w").write("patched\n")
        _LOG = (capnp.load(os.path.join(dst, "log.capnp")), True)
    except Exception as e:
        pr("  ⚠ patched fork schema unavailable (%s) -- falling back to the KIT schema; "
           "`epsTorqueMode` cannot be read." % str(e)[:70])
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
    fD_ratio=0.75,             # torqueState median f / desiredLateralAccel.  Torque mode with the
                               # shipped friction 0 gives exactly 1.000; MEASURED on four routes that
                               # are not torque mode: pooled 0.24-0.40, worst |D| band 0.58.
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
               "AccordCurvatureLead", "AccordCurvatureLeadGain", "ForceAutoTune",
               "ForceTorqueController", "AccordEpsGainScale", "AccordEpsSpringScale",
               "AccordTurnFFTaper", "GitCommit", "GitBranch", "GitRemote", "GitCommitDate",
               "Version", "TermsVersion", "CarParams", "DongleId"]


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def extract(prefix, tag):
    """build <TAG>.npz / _b4.npz / _marks.json / _params.json exactly as extract_v292_routes.py does,
    plus the fork's `epsTorqueMode` duty, which needs the PATCHED schema."""
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
    tm_n = tm_true = 0
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
            elif w == "epsTelemetry" and patched:
                # PATCHED name -- this is the fork's starpilotLateralState
                try:
                    tm_n += 1
                    if evt.epsTelemetry.epsTorqueMode:
                        tm_true += 1
                except Exception:
                    pass
            elif w == "modelDataV2SP" and patched:
                # PATCHED name -- this is the fork's customReserved9, the Testing Ground selection
                _tg_collect(evt, tg)
            elif w == "controlsState":
                # the SECOND, INDEPENDENT source for the toggle (docs/guides/TORQUE-MODE-TOGGLE-
                # CHECKLIST section C): under torque mode f = desiredLateralAccel + friction and
                # friction ships at 0, so f tracks D one-for-one; under the rate-plant branch the
                # same point reads ~0.38 of it.  MEASURED on r6c seg 3 (V282): slope 0.3905.
                try:
                    ls = evt.controlsState.lateralControlState
                    if ls.which() == "torqueState":
                        t_ = ls.torqueState
                        tq_f.append((float(t_.f), float(t_.desiredLateralAccel), bool(t_.active)))
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
    pdump["_epsTorqueMode_frames"] = tm_n
    pdump["_epsTorqueMode_true"] = tm_true
    pdump["_epsTorqueMode_duty"] = (tm_true / tm_n) if tm_n else None
    pdump["_epsTorqueMode_readable"] = bool(patched)
    pdump["_written_by"] = "v293_flight_read.py"
    if tq_f:
        Q = np.asarray(tq_f, float)
        sel = (Q[:, 2] > 0.5) & (np.abs(Q[:, 1]) >= 0.3)
        pdump["_torqueState_n"] = int(len(Q))
        pdump["_torqueState_n_fit"] = int(sel.sum())
        if sel.sum() >= 50:
            sl, ic = np.polyfit(Q[sel, 1], Q[sel, 0], 1)
            pdump["_torqueState_slope_f_vs_D"] = float(sl)
            pdump["_torqueState_intercept"] = float(ic)
            pdump["_torqueState_fD_p50"] = float(np.median(Q[sel, 0] / Q[sel, 1]))
            pdump["_torqueState_fD_by_band"] = {}
            for lo, hi in ((0.3, 0.6), (0.6, 0.9), (0.9, 1.3), (1.3, 2.0)):
                s2 = (Q[:, 2] > 0.5) & (np.abs(Q[:, 1]) >= lo) & (np.abs(Q[:, 1]) < hi)
                pdump["_torqueState_fD_by_band"]["%.1f-%.1f" % (lo, hi)] = (
                    [float(np.median(Q[s2, 0] / Q[s2, 1])), int(s2.sum())] if s2.sum() > 50
                    else [None, int(s2.sum())])
        else:
            pdump["_torqueState_slope_f_vs_D"] = pdump["_torqueState_fD_p50"] = None
    else:
        pdump["_torqueState_n"] = 0
        pdump["_torqueState_slope_f_vs_D"] = pdump["_torqueState_fD_p50"] = None
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
    """read ONLY the three toggle sources from a route's rlogs: initData.params, the fork's
    starpilotLateralState.epsTorqueMode, and controlsState...torqueState (f, desiredLateralAccel).

    Written to the STUDY's own _scratch, never into the shared v280 cache -- a route the record
    already owns must not have its cache rewritten by this tool.
    """
    out = os.path.join(SCR, "fork_toggles_%s.json" % prefix)
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
    tm_n = tm_true = 0
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
            if w == "epsTelemetry" and patched:
                try:
                    tm_n += 1
                    if evt.epsTelemetry.epsTorqueMode:
                        tm_true += 1
                except Exception:
                    pass
            elif w == "modelDataV2SP" and patched:
                _tg_collect(evt, tg)
            elif w == "controlsState":
                try:
                    ls = evt.controlsState.lateralControlState
                    if ls.which() == "torqueState":
                        t_ = ls.torqueState
                        tq.append((float(t_.f), float(t_.desiredLateralAccel), bool(t_.active)))
                except Exception:
                    pass
            elif w == "initData" and params is None:
                try:
                    params = {e.key: bytes(e.value).decode("utf-8", "replace")
                              for e in evt.initData.params.entries if e.key in WANT_PARAMS}
                except Exception:
                    pass
    d = dict(params or {})
    d.update(_epsTorqueMode_frames=tm_n, _epsTorqueMode_true=tm_true,
             _epsTorqueMode_duty=((tm_true / tm_n) if tm_n else None),
             _epsTorqueMode_readable=bool(patched), _written_by="v293_flight_read.py")
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
    """majority (slot, variant) and whether it is Testing Ground 9 variant B."""
    d = dict(_tg_frames=acc.get("n", 0), _tg_slot=None, _tg_variant=None,
             _tg_slot_name=acc.get("slotName"), _tg_variant_label=acc.get("variantLabel"),
             _tg_pairs=None, _tg_is_torque_mode=None)
    pairs = acc.get("pairs") or {}
    if not pairs:
        return d
    d["_tg_pairs"] = {"%s/%s" % k: v for k, v in sorted(pairs.items(), key=lambda z: -z[1])}
    (sid, var), _ = max(pairs.items(), key=lambda z: z[1])
    d["_tg_slot"], d["_tg_variant"] = sid, var
    d["_tg_is_torque_mode"] = bool(sid == TG_SLOT and var == TG_VARIANT)
    return d


def _torque_state_stats(tq):
    """the branch check: torque mode ships friction 0, so f = desiredLateralAccel exactly."""
    if not tq:
        return dict(_torqueState_n=0, _torqueState_slope_f_vs_D=None, _torqueState_fD_p50=None)
    Q = np.asarray(tq, float)
    sel = (Q[:, 2] > 0.5) & (np.abs(Q[:, 1]) >= 0.3)
    d = dict(_torqueState_n=int(len(Q)), _torqueState_n_fit=int(sel.sum()))
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
    if "_written_by" in d:
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
# 9.  SCORE ONE ROUTE -- everything above, into one dict
# ======================================================================================================
def score_route(tag, build, with_positive=True, prefix=None):
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
# 10. THE SCORECARD
# ======================================================================================================
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
    tm = P.get("AccordEpsTorqueMode")
    cl = P.get("AccordCurvatureLead")
    duty = P.get("_epsTorqueMode_duty")
    pr("   AccordEpsTorqueMode        = %-10s   INFORMATIONAL ONLY -- this key no longer exists."
       % ("absent" if tm is None else repr(tm)))
    pr("     The switch moved off the params family onto the fork's TESTING GROUND mechanism: slot 9")
    pr("     \"Accord EPS Torque Mode\", variant B.  `common/params_keys.h` now carries a comment where")
    pr("     the key used to be, so ABSENT here is EXPECTED under the Testing Ground gate and is not")
    pr("     evidence of anything.  A value would mean the device is running a PRE-REWORK fork.")
    pr("   AccordCurvatureLead        = %-10s   (still a real param; must be ABSENT or \"0\")"
       % ("ABSENT" if cl is None else repr(cl)))
    if P.get("_augmented_from_rlogs"):
        pr("   (this route's cache predates v293_flight_read.py; the two cereal-side readings below were")
        pr("    read straight from its rlogs into _scratch/ -- the shared cache was NOT rewritten)")
    elif "_written_by" not in P:
        pr("   ⚠ neither cereal-side toggle source could be read: no cache keys and no rlogs on disk.")
    pr("   starpilotLateralState.epsTorqueMode duty = %s  over %s frames%s"
       % (fmt(duty), P.get("_epsTorqueMode_frames", "-"),
          "" if P.get("_epsTorqueMode_readable", True) else "   [NOT READABLE -- schema patch failed]"))
    pr("     🛑 the kit's cereal calls union slot @137 `epsTelemetry` and the FORK calls it")
    pr("     `starpilotLateralState` -- same struct id 0xc2243c65e0340384, DIFFERENT fields.  This")
    pr("     tool loads a PATCHED COPY of the schema from _scratch/cereal_fork/; the kit's own")
    pr("     schema is untouched.  Any other kit script reading `epsTelemetry` from a 2026-09 rlog")
    pr("     is reading GARBAGE.  [EVIDENCE -- both schemas, read 2026-09-13]")
    # --- the Testing Ground selection, on a SECOND colliding slot -------------------------------
    tgs, tgv, tgn = P.get("_tg_slot"), P.get("_tg_variant"), P.get("_tg_frames", 0)
    if tgn:
        pr("   Testing Ground             = slot %s variant %s  (%s / %s)   over %d published frames"
           % (tgs, tgv, P.get("_tg_slot_name") or "?", P.get("_tg_variant_label") or "?", tgn))
        if (P.get("_tg_pairs") or {}) and len(P["_tg_pairs"]) > 1:
            pr("     ⚠ the selection CHANGED during the route: "
               + "  ".join("%s x%d" % (k, v) for k, v in P["_tg_pairs"].items()))
    else:
        pr("   Testing Ground             = no selection frames decoded on this route")
    pr("     the selection lives in /data/testing_grounds/slots.json, NOT in the params store -- but")
    pr("     it IS logged: the_galaxy publishes it as `customReserved9` (slotId / slotName / variant /")
    pr("     variantLabel / reason / wallTimeNanos), and that slot COLLIDES TOO -- the kit calls @116")
    pr("     `modelDataV2SP`, struct id 0xa1680744031fdb2d, one enum field.  The patched copy carries")
    pr("     the fork's field list, which is how the row above decodes.  Torque mode = slot %s / %s."
       % (TG_SLOT, TG_VARIANT))
    if build == "V293" and tgn:
        tg_on = bool(P.get("_tg_is_torque_mode"))
        duty_on = (duty is not None and duty > 0.9)
        if tg_on == duty_on:
            note = ("this AGREES with the epsTorqueMode duty (%s), so the two mechanisms are "
                    "consistent" % fmt(duty))
        else:
            note = ("🛑 this DISAGREES with the epsTorqueMode duty (%s): one of the two mechanisms "
                    "is wrong, and the drive cannot be attributed until that is resolved" % fmt(duty))
        verdicts.append(("REPORT", "testing ground",
                         "the Testing Ground published slot %s variant %s over %d frames (torque mode "
                         "is slot %s / %s).  %s.  Reported, not gated: the two toggle GATES are the "
                         "epsTorqueMode duty and the torqueState f/D ratio."
                         % (tgs, tgv, tgn, TG_SLOT, TG_VARIANT, note)))
    fd = P.get("_torqueState_fD_p50")
    sl_ = P.get("_torqueState_slope_f_vs_D")
    pr("   torqueState  median f / desiredLateralAccel = %s   (n %s of %s; whole-route regression "
       "slope %s)" % (fmt(fd, "%.4f"), P.get("_torqueState_n_fit", "-"),
                      P.get("_torqueState_n", "-"), fmt(sl_, "%.4f")))
    bb = P.get("_torqueState_fD_by_band") or {}
    if bb:
        pr("     by |D| band: " + "  ".join("%s %s (n%d)" % (k, fmt(v[0], "%.3f"), v[1])
                                            for k, v in sorted(bb.items())))
    pr("     THE SECOND, INDEPENDENT TOGGLE SOURCE, and the only one that reads the CONTROL PATH")
    pr("     rather than a parameter: friction ships at 0, so torque mode gives f = D exactly")
    pr("     (ratio 1.000) while the rate-plant branch scales it down.  MEASURED on four routes that")
    pr("     are NOT torque mode: %s -- pooled median %.2f-%.2f, worst band %.2f.  The gate is %.2f,"
       % ("r6c 0.32 / r6d 0.24 / r6e 0.40 / r6f 0.31", 0.24, 0.40, 0.58, 0.75))
    pr("     which sits 1.3x above the worst observation and 1.3x below the expected 1.000.")
    pr("     ⚠ the whole-route REGRESSION SLOPE is NOT usable as a gate: it reads 0.21-0.64 on the")
    pr("     same four routes, a spread that overlaps nothing useful.  The ratio is the statistic.")
    if build == "V293" and fd is not None:
        if fd >= THR["fD_ratio"]:
            verdicts.append(("PASS", "branch", "torqueState median f/D = %.3f (>= %.2f) -- the "
                                               "TORQUE-MODE branch is the one executing" % fd))
        else:
            verdicts.append(("FAIL", "branch",
                             "torqueState median f/D = %.3f -- that is the RATE-PLANT branch (measured "
                             "0.24-0.40 pooled on four non-torque-mode routes), not torque mode.  With "
                             "V293 in the ECU that is the FF-starved AND high-gain-feedback mismatch "
                             "(ADV-V293-D 4.4), which is NOT merely sluggish." % fd))
    for k in ("SteerLatAccel", "SteerFriction", "SteerKP", "AccordTorqueKi", "AccordRatePlantFF",
              "ForceTorqueController", "GitCommit"):
        if k in P:
            pr("   %-26s = %s" % (k, repr(P[k])[:70]))
    if build == "V293":
        # 🛑 TWO TOGGLE GATES, and the params key is NOT one of them.  The switch moved onto the
        # Testing Ground mechanism, so `AccordEpsTorqueMode` is absent by design and its absence
        # carries no information.  The gates are the cereal duty and the control-path ratio.
        if duty is not None and duty > 0.9:
            verdicts.append(("PASS", "toggle", "starpilotLateralState.epsTorqueMode duty %.3f over %s "
                                               "frames -- the mode is ON, engaged or not"
                             % (duty, P.get("_epsTorqueMode_frames", "?"))))
        elif duty is not None:
            verdicts.append(("FAIL", "toggle",
                             "starpilotLateralState.epsTorqueMode duty is %.3f -- the mode is OFF.  "
                             "V293 in the ECU with the mode off is the FF-starved AND "
                             "high-gain-feedback mismatch (ADV-V293-D 4.4), not merely sluggish, and "
                             "the band scores are NOT a build contrast.  Check Testing Ground slot %s "
                             "variant %s, and that params_pyx.so was rebuilt."
                             % (duty, TG_SLOT, TG_VARIANT)))
        else:
            verdicts.append(("FAIL", "toggle",
                             "starpilotLateralState.epsTorqueMode could not be read at all, so the "
                             "drive cannot be attributed to a torque-mode tune from the cereal side."))
        if tm is not None:
            verdicts.append(("REPORT", "toggle",
                             "AccordEpsTorqueMode = %r is PRESENT in the params store.  The key was "
                             "removed when the switch moved to the Testing Ground, so this device is "
                             "running a PRE-REWORK fork and the two mechanisms may disagree." % tm))
        if cl not in (None, "0"):
            verdicts.append(("FAIL", "toggle", "AccordCurvatureLead = %r -- V292's subject is live "
                                               "and confounds this drive" % cl))

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
                         "The fix is the FORK PRESET, not the firmware, but the drive stops."
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
    return verdicts


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
    pr("")
    if nrev:
        pr("  >>> %d REVERT trigger(s) fired.  The pre-registration's instruction is to STOP THE DRIVE "
           "and go back to V282." % nrev)
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
        S = score_route(tag, b, with_positive=False)
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
    ap.add_argument("--reextract", action="store_true", help="rebuild the cache even if it exists")
    a = ap.parse_args()
    os.makedirs(SCR, exist_ok=True)
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
    S = score_route(tag, build, with_positive=not a.no_positive, prefix=prefix)
    v = print_scorecard(S, refs)
    print_verdicts(S, v)
    json.dump(S, open(os.path.join(SCR, "v293_flight_read_%s.json" % tag), "w"), indent=1, default=float)
    io.open(os.path.join(SCR, "v293_flight_read_%s.txt" % tag), "w",
            encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_flight_read_%s.{txt,json}" % tag)


if __name__ == "__main__":
    main()
