# -*- coding: utf-8 -*-
"""r71b_cache.py -- THE LOADER for route 75604b0a432fdc89_00000071--a7b8ba5d9d ("r71b", V294 + fork Dom 20d24ab79).

    import sys; sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
    import r71b_cache as R
    D = R.load()                 # dict of native-rate numpy arrays (+ D["meta"], D["can_raw"])
    G = R.grid100(D)             # every stream sampled onto the 0x18F frame axis (100 Hz, previous-value / ZOH)
    g = R.kit_grid()             # the kit's own creep20_loop_id.load('r71b_v294') grid (dejittered, as every census uses)
    python r71b_cache.py --selftest        # re-runs every positive control quoted below

🛑 ROUTE IDENTITY.  The dongle counter 0x71 names THREE routes on disk: --f2c9d073a3 (V293 rev 2, 2026-09-13),
   --ac50da2a6a, and THIS one, --a7b8ba5d9d (2026-09-30 03:10 UTC = 2026-09-29 20:10 PDT, 17 segments, 1020 s).
   Key everything on the full counter--hash.  Kit tag: r71b_v294.  Build it with ../extract_r71b.py.

TIME.  Every `*_t` array is ABSOLUTE logMonoTime in seconds (one boot, monotone across all 17 segments, contiguous:
   inter-segment gaps 4-6 ms).  Route t0 = D["t0"] = the first 0x18F frame.  Wall clock: D["meta"]["gps_anchor"]
   (unix_ms at a mono time); initData.wallTimeNanos is NOT synced on this device (reads 2026-07-28) -- do not use it.

======================================================================================================================
CAN (native rate; raw bytes also in D["can_raw"]["x<ADDR>_b<BUS>_{t,dat,dlen}"], dat is [N,8] uint8 zero-padded)
======================================================================================================================
 0xE4 STEERING_CONTROL, bus 129 (= panda TX-echo of openpilot's bus-1 send = what the EPS received), 100 Hz
   e4_t, e4_cmd      STEER_TORQUE, i16 big-endian bytes 0-1, raw counts.  + = steer RIGHT.
                     EVIDENCE: e4_cmd == carOutput.actuatorsOutput.torqueOutputCan (ratio 1.000, r = 0.99996) and
                     == -4091 x carOutput.actuatorsOutput.torque (openpilot torque + = LEFT).  Range on this route
                     -2130 .. +4096.
   e4_req            STEER_TORQUE_REQUEST, byte 2 bit 7
   e4_b2, e4_b3      bytes 2 and 3 whole.  e4_b2 & 0x7F == 0 on every frame (the override-taper arm field openpilot
                     sends as 0), e4_b3 == 0.
   (bus 2 = the camera's own stock LKAS 0xE4, req 3 %, blocked; bus 128/0/1/193 carry copies -- raw only)
 0x18F STEER_STATUS, bus 1, 100 Hz, dlen 7
   s18_t
   s18_tq_raw        STEER_TORQUE_SENSOR, i16 BE bytes 0-1, raw.  EVIDENCE: carState.steeringTorque = -1.0006 x raw.
                     The kit's `bar` (creep20_loop_id.load) = raw x 1.024 (sign RAW, i.e. = -steeringTorque x 1.024).
   s18_rate_raw      STEER_ANGLE_RATE, i16 BE bytes 2-3, raw -- THE KIT'S "wire" / v280 `rate` COLUMN.
                     EVIDENCE: raw = -7.997 x carState.steeringRateDeg (regression over the whole route).
                     🛑 SIGN HAZARD: it is the NEGATIVE of the wheel rate.  Prefer x_fw / wheel_rate_dps() or cs_rate.
   x_fw              = -s18_rate_raw = +8 x steeringRateDeg, COUNTS: the firmware operand x = gp-0x6a56 as the kit
                     models it (creep20_loop_id: x = -wire).  🛑 NOT the kit grid's g['rate_x'], which is -wire/8 in DEG/S --
                     same sign, different unit; wheel_rate_dps() gives deg/s.  x = 8.00 counts per deg/s: EVIDENCE twice over in
                     the record (0x55B48 bytes; 7.1-7.8 on the V292 wire) and here (-7.997).  The SIGN of gp-0x6a56 vs
                     the polarity flag is the record's (BELIEF here); every sign-bearing use must calibrate against
                     the feedforward on the same route (the instrument does).
   s18_sca           STEER_CONTROL_ACTIVE, byte 4 bit 3
   s18_status        STEER_STATUS nibble, byte 4 >> 4 (0 normal, 2/4 no_torque_alert, 3 low_speed_lockout, 5 fault_1,
                     6 tmp_fault).  EVIDENCE: 0 on every one of 101,868 frames of this route.
   s18_cfg           STEER_CONFIG_INDEX, byte 5 >> 4 (0 on every frame)
 0x14A STEERING_SENSORS, bus 1, 100 Hz
   s14_t
   s14_angle         i16 BE bytes 0-1 x -0.1 = deg, + = LEFT.  EVIDENCE: == carState.steeringAngleDeg (slope 1.0000).
   s14_rate          i16 BE bytes 2-3 x -1 = deg/s, + = LEFT.  EVIDENCE: == carState.steeringRateDeg (slope 1.0002).
                     The firmware writes (-x)>>3 here (0x55B48), so this is x/8 floored -- 1 deg/s resolution.
   s14_b4            byte 4 whole.  Bits 0-2 are STOCK Honda (== 7 on every frame); bits 3-7 are the V112-lineage
                     cave telemetry carried unchanged since V282 (see the 0x14A cave memory).
 0x1AB (427) the delivered-torque TAP, bus 1, 50 Hz
   tap_t
   tap_T             delivered LKAS lane torque gp-0x6b38 in firmware counts, quantised to 8:
                     fld = ((b0 & 3) << 8) | b1 ; T = (-1 if fld >= 512 else +1) * (fld & 511) * 8.
                     EVIDENCE: sign(tap_T) == +sign(e4_cmd) on 99.9 % of 17,659 frames with |cmd| > 200.
   tap_b0, tap_b2    raw bytes (b0 >> 2 == 32 on every frame = CONFIG_VALID set)
 0x158 ENGINE_DATA, bus 1, 100 Hz:   v158_t, v158 (XMISSION_SPEED, bytes 0-1 x 0.01 kph -> m/s).  EVIDENCE: v158 =
                     0.976 x carState.vEgo (median above 5 m/s) -- use cs_vego for speed bands (the kit does).
 NOT ON THE WIRE HERE: 0x18F carries no steering ANGLE (angle is 0x14A); carState.yawRate and steeringTorqueEps are 0 on
 every frame of this route (use pose_wz for yaw rate).
 KIT GRID NOTE: kit_grid() dejitters the 0x18F axis to 102,039 frames (171 dropped frames linearly filled) vs 101,868
 native frames here -- index-align nothing between the two grids; align by time.
 LATERAL DELAY (code-read, BELIEF): the torque controller's lat_delay = liveDelay.lateralDelay (0.326 s, constant on
 this route, status 'estimated') + LAT_SMOOTH_SECONDS 0.1 = 0.426 s (controlsd.py, modeld.py at Dom 20d24ab79).

======================================================================================================================
SERVICES (fork's own cereal; native rates; absolute mono seconds in <prefix>_t)
======================================================================================================================
 cs_*   carState 100 Hz: angle (deg, + left), rate (deg/s, + left), torque (driver torque, native, = -s18_tq_raw),
        torque_eps (0 -- not populated on this car), pressed (steeringPressed 0/1), vego, aego (m/s, m/s^2),
        vego_raw, yaw (carState.yawRate -- 0 on this car, use pose_wz), standstill, fault_tmp, fault_perm
        (steerFaultTemporary/Permanent), blink_l/blink_r, cruise_en, angle_off
 ctl_*  controlsState 100 Hz: which (0 pid, 1 angle, 2 debug, 3 TORQUE), and the torqueState fields active, error,
        error_rate, p, i, d, f, output, saturated, la_act, la_des (actual/desiredLateralAccel, m/s^2), jerk_des,
        version; curv, des_curv (controlsState.curvature / desiredCurvature, 1/m).  torqueState.output is in
        openpilot torque units (+ = left); the fork logs error = error_with_lsf, so p/error = the live Kp.
 cc_*   carControl 100 Hz: enabled, lat_active (latActive), torque (actuators.torque, + left, [-1,1]), angle, curv
        (actuators.curvature 1/m), torque_can
 co_*   carOutput 100 Hz: torque (actuatorsOutput.torque, after the rate limiter), torque_can (== e4_cmd), angle, curv
 sd_*   selfdriveState 100 Hz: enabled, active, state (enum raw: 0 disabled 1 preEnabled 2 enabled 3 softDisabling
        4 overriding), engageable
 spl_*  starpilotLateralState 100 Hz: active, fric_thr, fric_scale, ff (feedforward), fric_jerk, fric_jerk_dz, lsf
        (lowSpeedFactor), unwind, dob (accordObserverTorque), dob_frozen
 mdl_*  modelV2 20 Hz: des_curv (action.desiredCurvature, 1/m), frame
 dmd_*  drivingModelData 20 Hz: des_curv
 lpar_* liveParameters 20 Hz: sr (steerRatio), roll (rad), off / off_avg (angle offsets, deg), stiff, valid, sr_valid,
        sensor_valid, sr_std
 pose_* livePose 20 Hz: wz (yaw rate, rad/s, device frame z), wx, wy, ay, ax, roll, pitch, ok
 ltp_*  liveTorqueParameters 4 Hz: laf, off, fric (Filtered), laf_raw, off_raw, fric_raw, valid (liveValid), use
        (useParams), pts, cal
 ldel_* liveDelay 4 Hz: delay (lateralDelay s), est, est_std, blocks, status (0 unestimated 1 estimated 2 invalid), cal
 panda_* pandaStates[0] ~10 Hz: allowed (controlsAllowed), rx_inv, tx_blk, safety, nfaults, rxchk_inv, ign

======================================================================================================================
DERIVED MASKS (in load() and grid100())
======================================================================================================================
 "LATERALLY ENGAGED" = 0xE4 STEER_REQUEST (bus 129) AND 0x18F STEER_CONTROL_ACTIVE -- NOT longitudinal-only
 (feedback: "engaged" means lateral).  grid100 returns eng (that) and eng_ctl (carControl.latActive) side by side.

ANALYSIS ONLY.  Reads the cache; never sends, never flashes.
"""
import json
import os
import sys

import numpy as np

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
ROUTE = "75604b0a432fdc89_00000071--a7b8ba5d9d"
TAG = "r71b_v294"
CACHE = os.path.join(KIT, "_scratch", "cache", ROUTE)
IMG_V294 = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
            "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
            "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
IMG_V294_SHA256 = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"


def _i16(dat, i):
    v = (dat[:, i].astype(np.int32) << 8) | dat[:, i + 1].astype(np.int32)
    return np.where(v >= 32768, v - 65536, v)


def load(with_raw=True):
    """dict of native-rate arrays; see the module docstring for every unit and sign."""
    if not os.path.exists(os.path.join(CACHE, "svc.npz")):
        raise SystemExit("no cache at %s -- run analysis-2020accord/studies/v295/extract_r71b.py first" % CACHE)
    C = dict(np.load(os.path.join(CACHE, "can.npz")))
    S = dict(np.load(os.path.join(CACHE, "svc.npz")))
    meta = json.load(open(os.path.join(CACHE, "meta.json")))
    D = dict(S)
    D["meta"] = meta
    # 0xE4, bus 129
    d = C["x0E4_b129_dat"]
    D["e4_t"] = C["x0E4_b129_t"]; D["e4_cmd"] = _i16(d, 0).astype(float)
    D["e4_req"] = ((d[:, 2] >> 7) & 1).astype(int); D["e4_b2"] = d[:, 2].astype(int); D["e4_b3"] = d[:, 3].astype(int)
    # 0x18F
    d = C["x18F_b1_dat"]
    D["s18_t"] = C["x18F_b1_t"]; D["s18_tq_raw"] = _i16(d, 0).astype(float); D["s18_rate_raw"] = _i16(d, 2).astype(float)
    D["x_fw"] = -D["s18_rate_raw"]
    D["s18_sca"] = ((d[:, 4] >> 3) & 1).astype(int); D["s18_status"] = (d[:, 4] >> 4).astype(int)
    D["s18_cfg"] = (d[:, 5] >> 4).astype(int); D["s18_b4"] = d[:, 4].astype(int)
    # 0x14A
    d = C["x14A_b1_dat"]
    D["s14_t"] = C["x14A_b1_t"]; D["s14_angle"] = _i16(d, 0) * -0.1; D["s14_rate"] = _i16(d, 2) * -1.0
    D["s14_b4"] = d[:, 4].astype(int)
    # 0x1AB tap
    d = C["x1AB_b1_dat"]
    fld = ((d[:, 0].astype(int) & 3) << 8) | d[:, 1].astype(int)
    D["tap_t"] = C["x1AB_b1_t"]; D["tap_T"] = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8.0
    D["tap_b0"] = d[:, 0].astype(int); D["tap_b2"] = d[:, 2].astype(int)
    # 0x158 speed
    d = C["x158_b1_dat"]
    D["v158_t"] = C["x158_b1_t"]
    D["v158"] = ((d[:, 0].astype(int) << 8) | d[:, 1].astype(int)) * 0.01 / 3.6
    D["t0"] = float(D["s18_t"][0])
    if with_raw:
        D["can_raw"] = C
    return D


def zoh(t_src, x_src, t_dst):
    """previous-value sample of (t_src, x_src) at t_dst; NaN before the first sample."""
    j = np.searchsorted(t_src, t_dst, side="right") - 1
    out = np.asarray(x_src, float)[np.clip(j, 0, len(x_src) - 1)].copy()
    out[j < 0] = np.nan
    return out


def grid100(D=None):
    """every stream on the 0x18F frame axis (native 100 Hz, absolute mono s in 't', route seconds in 'tr').

    ZOH semantics (the ECU holds a command between frames).  Service fields keep their names (cs_angle, ctl_p ...).
    eng = e4_req & s18_sca (LATERAL engagement on the wire); eng_ctl = carControl.latActive.
    """
    D = load(with_raw=False) if D is None else D
    t = D["s18_t"]
    G = dict(t=t, tr=t - D["t0"], x_fw=D["x_fw"], s18_rate_raw=D["s18_rate_raw"], s18_tq_raw=D["s18_tq_raw"],
             s18_sca=D["s18_sca"], s18_status=D["s18_status"])
    for k in ("e4_cmd", "e4_req", "e4_b2"):
        G[k] = zoh(D["e4_t"], D[k], t)
    for k in ("s14_angle", "s14_rate", "s14_b4"):
        G[k] = zoh(D["s14_t"], D[k], t)
    G["tap_T"] = zoh(D["tap_t"], D["tap_T"], t)
    G["v158"] = zoh(D["v158_t"], D["v158"], t)
    for pre in ("cs", "ctl", "cc", "co", "sd", "spl", "mdl", "lpar", "pose", "ltp", "ldel"):
        tk = pre + "_t"
        if tk not in D:
            continue
        for k in [k for k in D if k.startswith(pre + "_") and k != tk and isinstance(D[k], np.ndarray)]:
            G[k] = zoh(D[tk], D[k], t)
    G["eng"] = (np.nan_to_num(G["e4_req"]) > 0.5) & (G["s18_sca"] > 0)
    G["eng_ctl"] = np.nan_to_num(G.get("cc_lat_active", np.zeros(len(t)))) > 0.5
    return G


def wheel_rate_dps(D_or_G):
    """the FINEST wheel-rate signal on the wire: 0x18F raw / -8 = +x/8 deg/s (+ = LEFT, same sign as carState rate),
    resolution 0.125 deg/s at 100 Hz.  (carState.steeringRateDeg / 0x14A is the same quantity floored to 1 deg/s;
    steeringAngleDeg is 0.1 deg.)  Works on load() output (native s18 axis) or grid100() output."""
    return np.asarray(D_or_G["x_fw"], float) / 8.0


def wheel_accel_dps2(rate_dps, fc_hz=None, fs=100.0):
    """d/dt of the wheel rate in deg/s^2 (central difference x fs).  fc_hz: optional ZERO-PHASE 2nd-order Butterworth
    low-pass first (filtfilt) -- for analysis only; the firmware's own operand is a CAUSAL 2.03 Hz one-pole (see the
    trim instrument in ../flight/r71b_attribution.py, which mirrors it)."""
    x = np.nan_to_num(np.asarray(rate_dps, float))
    if fc_hz:
        from scipy import signal
        b, a = signal.butter(2, fc_hz / (fs / 2.0))
        x = signal.filtfilt(b, a, x)
    return np.gradient(x) * fs


def kit_grid():
    """creep20_loop_id.load('r71b_v294') -- the kit's dejittered 100 Hz grid, exactly what every census tool reads.
    g['wire'] is the RAW 0x18F rate field (= -8 x steeringRateDeg); g['rate_x'] = -wire/8 in deg/s; g['bar'] = raw
    0x18F torque x 1.024; g['T_t'], g['T'] = the native 50 Hz tap; g['eng'] = sca & req & frame present."""
    sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
    import creep20_loop_id as C20
    return C20.load(TAG)


def v294_cells():
    """the LKAS rate-PID cells of the V294 image, read little-endian from the IMAGE (hash-checked), plus the two code
    edits decoded from their halfwords: e_shift (shl imm5 at 0x29D76) and fb_op (add/subr at 0x28FA4)."""
    import hashlib
    b = open(IMG_V294, "rb").read()
    h = hashlib.sha256(b).hexdigest()
    if h != IMG_V294_SHA256:
        raise RuntimeError("V294 image hash mismatch: %s" % h)
    sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
    import v293_lib as L
    c = L.read_cells(IMG_V294)
    hw = int.from_bytes(b[0x29D76:0x29D78], "little")
    assert (hw >> 5) & 0x3F == 0x16, "0x29D76 is not shl imm5"          # Format II shl imm5
    c["e_shift"] = hw & 0x1F
    hw2 = int.from_bytes(b[0x28FA4:0x28FA6], "little")
    op = (hw2 >> 5) & 0x3F
    c["fb_op"] = {0x0E: "sum", 0x0C: "diff"}[op]                         # add = 001110, subr = 001100
    c["_img_sha256"] = h
    return c


def _selftest():
    """re-derive every EVIDENCE claim in the docstring from the cache (and seg 0 through the KIT's patched schema)."""
    D = load()
    ok = True

    def fit(x, y):
        A = np.vstack([x, np.ones_like(x)]).T
        return np.linalg.lstsq(A, y, rcond=None)[0]

    ts = D["cs_t"]
    for nm, x, tx, y, want in (("s14_angle vs cs_angle", D["s14_angle"], D["s14_t"], D["cs_angle"], 1.0),
                               ("s14_rate vs cs_rate", D["s14_rate"], D["s14_t"], D["cs_rate"], 1.0),
                               ("s18_rate_raw vs cs_rate", D["s18_rate_raw"], D["s18_t"], D["cs_rate"], -0.125),
                               ("s18_tq_raw vs cs_torque", D["s18_tq_raw"], D["s18_t"], D["cs_torque"], -1.0),
                               ("e4_cmd vs co_torque_can", D["e4_cmd"], D["e4_t"], np.interp(D["e4_t"], D["co_t"], D["co_torque_can"]), 1.0)):
        xi = np.interp(ts, tx, x) if len(y) == len(ts) else x
        k = fit(xi, y)
        good = abs(k[0] / want - 1) < 0.01
        ok &= good
        print("  %-28s slope %+.5f (want %+.4f) offset %+.3f  %s" % (nm, k[0], want, k[1], "PASS" if good else "FAIL"))
    ci = np.interp(D["tap_t"], D["e4_t"], D["e4_cmd"])
    m = (np.abs(ci) > 200) & (D["tap_T"] != 0)
    fr = float(np.mean(np.sign(D["tap_T"][m]) == np.sign(ci[m])))
    ok &= fr > 0.99
    print("  sign(tap_T) == +sign(e4_cmd): %.4f of %d  %s" % (fr, m.sum(), "PASS" if fr > 0.99 else "FAIL"))
    print("  s18_status nonzero frames: %d ; s14_b4 & 7 != 7 frames: %d" % ((D["s18_status"] != 0).sum(),
                                                                          ((D["s14_b4"] & 7) != 7).sum()))
    # the KIT's patched schema on segment 0 must reproduce the native decode
    try:
        import io, contextlib, zstandard
        sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
        with contextlib.redirect_stdout(io.StringIO()):
            import v293_flight_read as FR
            clog, patched = FR.fork_log_schema()
        p = os.path.join(KIT, "analysis-2020accord", "rlogs", ROUTE + "--0--rlog.zst")
        data = zstandard.ZstdDecompressor().stream_reader(open(p, "rb")).read()
        n18, cs_a, tq_p, sp_ff = 0, [], [], []
        for evt in clog.Event.read_multiple_bytes(data):
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "can":
                n18 += sum(1 for m in evt.can if m.src == 1 and m.address == 0x18F)
            elif w == "carState":
                cs_a.append(evt.carState.steeringAngleDeg)
            elif w == "controlsState":
                try:
                    ls = evt.controlsState.lateralControlState
                    if ls.which() == "torqueState":
                        tq_p.append(ls.torqueState.p)
                except Exception:
                    tq_p.append(np.nan)
            elif w == "epsTelemetry" and patched:
                sp_ff.append(evt.epsTelemetry.feedforward)
        seg0 = D["meta"]["seg_spans"]["0"]
        lo, hi = seg0["lo_can"] - 1, seg0["hi"] + 1e-6
        m18 = (D["s18_t"] >= lo) & (D["s18_t"] <= hi)
        mcs = (D["cs_t"] <= hi); mctl = (D["ctl_t"] <= hi); msp = (D["spl_t"] <= hi)
        same = (n18 == m18.sum() and np.array_equal(np.asarray(cs_a, float), D["cs_angle"][mcs])
                and np.array_equal(np.asarray(tq_p, float), D["ctl_p"][mctl])
                and np.array_equal(np.asarray(sp_ff, float), D["spl_ff"][msp]))
        ok &= bool(same)
        print("  KIT patched schema, seg 0: 0x18F %d vs %d, carState %d, torqueState.p %d, lateralState.ff %d -> %s"
              % (n18, m18.sum(), len(cs_a), len(tq_p), len(sp_ff), "IDENTICAL" if same else "DIFFERENT"))
    except Exception as e:   # informational
        print("  kit-schema cross-check skipped: %s" % str(e)[:160])
    c = v294_cells()
    print("  V294 image cells: e_shift %d fb_op %s fb_a %d fb_b %d fb_clamp %d kp_Y %s kd_Y %s lag %d/%d gain %d map_Y %s"
          % (c["e_shift"], c["fb_op"], c["fb_a"], c["fb_b"], c["fb_clamp"], list(c["kp_Y"]), list(c["kd_Y"]),
             c["lag_a"], c["lag_b"], c["gain"], list(c["map_Y"])))
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        D = load(with_raw=False)
        print(sorted(k for k in D if k != "meta"))
