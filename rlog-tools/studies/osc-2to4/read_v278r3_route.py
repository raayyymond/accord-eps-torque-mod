# -*- coding: utf-8 -*-
"""THE PRE-REGISTERED READ of V278 rev 3's delivered-torque tap -- route 75604b0a432fdc89_00000031 (r31).

Applies PREREG-V278R3-CLAMP-READ.md exactly as written (thresholds quoted, none moved):
  SAT  = P(|T| >= 2472)  i.e. tap reading >= 309          "high" >= 0.05, "low" < 0.02
  DAMP = P(sign(T) != sign(0x18F rate)), both nonzero      "high" >= 0.60 osc / >= 0.55 normal, "low" <= 0.50
  scored over OSCILLATING frames if the episode detector fires, else over all engaged frames.
Episode detector = prereg_v278r3_saturation.py's: 2.5-6 Hz band-pass of the 0x18F rate on a 100 Hz grid,
1 Hz-smoothed Hilbert envelope, threshold max(2.5 x p95(disengaged), 150), >= 1.0 s, gaps < 1 s merged.

SIGN CONVENTION NOTE (reported, not resolved here): the prereg simulation scores DAMP against the RAW 0x18F
bytes 2-3 (i16be, no negation: prereg_v278r3_saturation.py `wire = D["rate"]`), while
probe/decode_v278r3_torque_tap.py NEGATES the wire before comparing. The two are complements. This script
reports BOTH; the prereg (raw-wire) convention is the pre-registered one and is used for the decision table.

Own reader, tolerant of a torn last segment (seg 10 of r31 is truncated). Also writes per-segment IMU
caches in the house `_imu.npz` schema so the off-EPS grind metric (ratchet_in_the_imu_pooled.py) can run.

Run:  python rlog-tools/studies/osc-2to4/read_v278r3_route.py [--imu-only]
"""
import glob
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(KIT)
sys.path.insert(0, KIT)
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
SCRATCH = os.environ.get("R3READ_SCRATCH", os.path.join(HERE, "_r3read"))
os.makedirs(SCRATCH, exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = {
    "r31": ("75604b0a432fdc89_00000031--a680e9b2ac", "V278r3"),
    "r2e": ("75604b0a432fdc89_0000002e--855ecfcf30", "V276"),
}
FS = 100.0
COUNTS_PER_DEGS = 8.0
SAT_THR = 2472          # prereg §0.1: one LSB under the 2481 ceiling; tap reading >= 309
SAT_HIGH, SAT_LOW = 0.05, 0.02
DAMP_HIGH_OSC, DAMP_HIGH_NORM, DAMP_LOW = 0.60, 0.55, 0.50


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def decode_1ab(d):
    """DBC honda_accord: MOTOR_TORQUE : 1|10@0+  -> bits 1..0 of byte 0 (MSBs) + byte 1 = ((d0&3)<<8)|d1.
    NOTE probe/decode_v278r3_torque_tap.py uses ((d0&0x7F)<<3)|(d1>>5), which is the layout for START BIT 7,
    not 1 -- on this route that formula yields only 14 distinct values (d0 is 0x80 or 0x82) and throws away
    the low 5 bits of d1, which is where the torque magnitude actually lives. Bytes settle it; see the report."""
    val = ((d[0] & 3) << 8) | d[1]
    sign = -1 if (val >> 9) & 1 else 1
    return sign * ((val & 0x1FF) << 3), val


def segments(prefix):
    return sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))


def read_segment(path):
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    out = {k: [] for k in ("t18", "tq", "rate", "sca", "t14", "ang", "t1ab", "T", "field", "b0", "b1",
                           "te4", "cmd", "req", "tcs", "vego", "csang", "tcc", "lat", "tco", "coreq",
                           "gt", "gtm", "gx", "gy", "gz", "at", "atm", "ax", "ay", "az")}
    n = 0
    torn = False
    it = clog.Event.read_multiple_bytes(data)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception as exc:          # capnp KjException on a torn tail
            torn = True
            print("    torn tail after %d events: %s" % (n, str(exc).splitlines()[0][:80]))
            break
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        tm = evt.logMonoTime * 1e-9
        if w == "can":
            for m in evt.can:
                d = bytes(m.dat)
                if m.src == 1:
                    if m.address == 0x18F and len(d) >= 5:
                        out["t18"].append(tm); out["tq"].append(i16be(d, 0)); out["rate"].append(i16be(d, 2))
                        out["sca"].append((d[4] >> 3) & 1)
                    elif m.address == 0x14A and len(d) >= 4:
                        out["t14"].append(tm); out["ang"].append(i16be(d, 0) * -0.1)
                    elif m.address == 0x1AB and len(d) >= 2:
                        T, fld = decode_1ab(d)
                        out["t1ab"].append(tm); out["T"].append(T); out["field"].append(fld)
                        out["b0"].append(d[0]); out["b1"].append(d[1])
                elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                    out["te4"].append(tm); out["cmd"].append(i16be(d, 0)); out["req"].append((d[2] >> 7) & 1)
        elif w == "carState":
            out["tcs"].append(tm); out["vego"].append(evt.carState.vEgo); out["csang"].append(evt.carState.steeringAngleDeg)
        elif w == "carControl":
            out["tcc"].append(tm); out["lat"].append(int(bool(evt.carControl.latActive)))
        elif w == "carOutput":
            out["tco"].append(tm); out["coreq"].append(float(evt.carOutput.actuatorsOutput.torque))
        elif w == "gyroscope":
            g = evt.gyroscope
            try:
                v = list(g.gyroUncalibrated.v)
            except Exception:
                try:
                    v = list(g.gyro.v)
                except Exception:
                    continue
            if len(v) >= 3:
                out["gt"].append(g.timestamp * 1e-9); out["gtm"].append(tm)
                out["gx"].append(v[0]); out["gy"].append(v[1]); out["gz"].append(v[2])
        elif w == "accelerometer":
            a = evt.accelerometer
            try:
                v = list(a.acceleration.v)
            except Exception:
                continue
            if len(v) >= 3:
                out["at"].append(a.timestamp * 1e-9); out["atm"].append(tm)
                out["ax"].append(v[0]); out["ay"].append(v[1]); out["az"].append(v[2])
    return {k: np.asarray(v, float) for k, v in out.items()}, torn


def read_route(tag):
    prefix, build = ROUTES[tag]
    cache = os.path.join(SCRATCH, "%s_direct.npz" % tag)
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return {k: z[k] for k in z.files}
    segs = segments(prefix)
    per = []
    for p in segs:
        print("  reading %s" % os.path.basename(p), flush=True)
        d, torn = read_segment(p)
        d["_torn"] = torn
        per.append(d)
    # t0 = the house cache's t0_mono if it exists (so IMU caches pair with the route CAN cache)
    house = os.path.join(ROOT, "analysis-2020accord", "_scratch", "cache", tag, "%s.npz" % tag)
    t0 = None
    if os.path.exists(house):
        hz = np.load(house, allow_pickle=True)
        if "t0_mono" in hz.files:
            t0 = float(np.asarray(hz["t0_mono"]).ravel()[0])
    if t0 is None:
        t0 = float(min(d["t18"][0] for d in per if len(d["t18"])))
    # IMU caches, house schema, one per segment
    imu_dir = os.path.join(ROOT, "_scratch", "cache", tag)
    os.makedirs(imu_dir, exist_ok=True)
    for i, d in enumerate(per):
        if len(d["gt"]) < 100:
            continue
        np.savez(os.path.join(imu_dir, "%ss%d_imu.npz" % (tag, i)),
                 gt=d["gt"] - t0, gt_mono=d["gtm"] - t0, gx=d["gx"], gy=d["gy"], gz=d["gz"],
                 at=d["at"] - t0, at_mono=d["atm"] - t0, ax=d["ax"], ay=d["ay"], az=d["az"],
                 g_status=np.ones_like(d["gt"]), a_status=np.ones_like(d["at"]),
                 t0_mono=np.array([t0]))
    D = {}
    for k in per[0]:
        if k.startswith("_"):
            continue
        D[k] = np.concatenate([d[k] for d in per])
    D["seg_of_1ab"] = np.concatenate([np.full(len(d["t1ab"]), i) for i, d in enumerate(per)])
    D["seg_of_18"] = np.concatenate([np.full(len(d["t18"]), i) for i, d in enumerate(per)])
    D["t0"] = np.array([t0])
    D["torn"] = np.array([int(d["_torn"]) for d in per])
    np.savez(cache, **D)
    return D


def hold(t_src, v_src, t_dst):
    idx = np.searchsorted(t_src, t_dst, side="right") - 1
    out = np.full(len(t_dst), np.nan)
    ok = idx >= 0
    out[ok] = v_src[idx[ok]]
    return out


def episodes_prereg(tg, wire, eng):
    """EXACTLY prereg_v278r3_saturation.py's detector."""
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")
    rb = signal.sosfiltfilt(sos, wire)
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    p95_dis = np.percentile(env[~eng], 95) if (~eng).any() else 0.0
    thr = max(2.5 * p95_dis, 150.0)
    on = (env > thr) & eng
    edges = np.diff(np.r_[0, on.astype(int), 0])
    eps = [(s, e) for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]) if (e - s) / FS >= 1.0]
    merged = []
    for s, e in eps:
        if merged and s - merged[-1][1] < FS:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    osc = np.zeros_like(eng)
    for s, e in merged:
        osc[s:e] = True
    return merged, osc, thr, env, rb


def stats(T, fld, wire_raw, cmd, m):
    """m = frame mask on the 0x1AB grid. Returns dict."""
    Te, fe, we, ce = T[m], fld[m], wire_raw[m], cmd[m]
    o = dict(n=int(m.sum()))
    if o["n"] == 0:
        return o
    mag = np.abs(Te)
    o["sat"] = float((mag >= SAT_THR).mean())
    o["sat2496"] = float((mag >= 2496).mean())
    o["max_field_mag"] = int((fe & 0x1FF).max())
    o["max_absT"] = int(mag.max())
    o["T_zero"] = float((Te == 0).mean())
    o["T_p50"], o["T_p90"], o["T_p99"] = [float(np.percentile(mag, q)) for q in (50, 90, 99)]
    both = (Te != 0) & (we != 0) & ~np.isnan(we)
    o["n_both"] = int(both.sum())
    if both.any():
        o["damp_raw"] = float((np.sign(Te[both]) != np.sign(we[both])).mean())     # PREREG convention
        o["damp_neg"] = float((np.sign(Te[both]) != -np.sign(we[both])).mean())    # decoder convention
    ok = ~np.isnan(ce)
    if ok.sum() > 5 and np.std(ce[ok]) > 0:
        slope, icpt = np.polyfit(ce[ok], Te[ok], 1)
        o["slope"], o["r"] = float(slope), float(np.corrcoef(ce[ok], Te[ok])[0, 1])
        bb = ok & (Te != 0) & (ce != 0)
        o["sign_T_eq_negcmd"] = float((np.sign(Te[bb]) == -np.sign(ce[bb])).mean()) if bb.any() else np.nan
    return o


def fmt(o):
    if o.get("n", 0) == 0:
        return "n=0"
    return ("n=%5d damp_raw %.3f damp_neg %.3f sat %.3f maxfld %3d max|T| %4d T0 %.3f p50/p90/p99 %4.0f/%4.0f/%4.0f "
            "slope %.3f r %+.3f sgn(T)=-sgn(cmd) %.3f"
            % (o["n"], o.get("damp_raw", np.nan), o.get("damp_neg", np.nan), o["sat"], o["max_field_mag"],
               o["max_absT"], o["T_zero"], o["T_p50"], o["T_p90"], o["T_p99"], o.get("slope", np.nan),
               o.get("r", np.nan), o.get("sign_T_eq_negcmd", np.nan)))


def label_sat(x):
    return "HIGH" if x >= SAT_HIGH else ("LOW" if x < SAT_LOW else "between")


def label_damp(x, osc):
    hi = DAMP_HIGH_OSC if osc else DAMP_HIGH_NORM
    return "HIGH" if x >= hi else ("LOW" if x <= DAMP_LOW else "between")


def main():
    imu_only = "--imu-only" in sys.argv
    if imu_only:
        for tag in ROUTES:
            read_route(tag)
        return
    D = read_route("r31")
    t0 = float(D["t0"][0])
    print("\n=== ROUTE r31 = %s (%s) ===" % ROUTES["r31"])
    print("torn segments: %s" % [i for i, x in enumerate(D["torn"]) if x])
    t1ab = D["t1ab"]; T = D["T"].astype(int); fld = D["field"].astype(int)
    print("0x1AB %d  0x18F %d  0x0E4 %d  0x14A %d  carState %d  gyro %d  accel %d"
          % (len(t1ab), len(D["t18"]), len(D["te4"]), len(D["t14"]), len(D["tcs"]), len(D["gt"]), len(D["at"])))

    # ---- join onto the 0x1AB (50 Hz) grid, most-recent-value-held (as the decoder does) ----
    wire_raw = hold(D["t18"], D["rate"], t1ab)
    sca = hold(D["t18"], D["sca"], t1ab)
    cmd = hold(D["te4"], D["cmd"], t1ab)
    req = hold(D["te4"], D["req"], t1ab)
    eng = (sca > 0.5) & (req > 0.5)
    seg = D["seg_of_1ab"].astype(int)

    # ---- tap liveness ----
    b0v, b0c = np.unique(D["b0"].astype(int), return_counts=True)
    print("\nRAW 0x1AB byte0 histogram: %s" % ", ".join("0x%02X x%d" % (a, b) for a, b in zip(b0v, b0c)))
    print("byte1 distinct values: %d (engaged); decoder-formula ((b0&0x7F)<<3)|(b1>>5) would give %d distinct"
          % (len(np.unique(D["b1"][eng])), len(np.unique((((D["b0"].astype(int) & 0x7F) << 3) | (D["b1"].astype(int) >> 5))[eng]))))
    vals, cnt = np.unique(fld[eng], return_counts=True)
    top = sorted(zip(cnt, vals), reverse=True)[:6]
    print("\nTAP LIVENESS: engaged 0x1AB frames %d; distinct field values %d; top: %s"
          % (eng.sum(), len(vals), ", ".join("%d x%d" % (v, c) for c, v in top)))
    print("  field max anywhere (all frames) = %d; magnitude bits max = %d  (313 = ceiling arithmetic refuted)"
          % (fld.max(), (fld & 0x1FF).max()))

    # ---- 100 Hz grid for the episode detector (prereg criterion) ----
    T18 = D["t18"] - t0
    tg = np.arange(T18[0], T18[-1], 1 / FS)
    wire_g = np.interp(tg, T18, D["rate"])
    sca_g = np.interp(tg, T18, D["sca"]) > 0.5
    req_g = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    eng_g = sca_g & req_g
    vego_g = np.interp(tg, D["tcs"] - t0, D["vego"])
    ang_g = np.interp(tg, D["t14"] - t0, D["ang"])
    cmd_g = np.interp(tg, D["te4"] - t0, D["cmd"])
    merged, osc_g, thr, env, rb = episodes_prereg(tg, wire_g, eng_g)
    print("\nEPISODE DETECTOR (prereg criterion): threshold %.0f raw (p95 disengaged env %.0f); %d episodes, %.1f s"
          % (thr, np.percentile(env[~eng_g], 95) if (~eng_g).any() else np.nan, len(merged), osc_g.sum() / FS))
    for k, (s, e) in enumerate(merged):
        f, P = signal.welch(rb[s:e], fs=FS, nperseg=min(256, e - s))
        print("  ep %2d  t %.1f-%.1f s (%.1f s)  vego %.1f  |ang| p50 %.1f  |cmd| p50 %.0f  fdom %.2f Hz  pk|rate| %.0f raw"
              % (k, tg[s], tg[e - 1], (e - s) / FS, np.median(vego_g[s:e]), np.median(np.abs(ang_g[s:e])),
                 np.median(np.abs(cmd_g[s:e])), f[np.argmax(P)], np.abs(wire_g[s:e]).max()))
    osc_1ab = np.interp(t1ab - t0, tg, osc_g.astype(float)) > 0.5
    normal = eng & ~osc_1ab
    oscm = eng & osc_1ab

    # ---- task 1: per segment and pooled ----
    print("\nPER SEGMENT (engaged frames on the 0x1AB grid; damp_raw = prereg convention vs RAW wire, damp_neg = decoder's negated wire):")
    for i in range(seg.max() + 1):
        print("  seg %2d  %s" % (i, fmt(stats(T, fld, wire_raw, cmd, eng & (seg == i)))))
    P_all = stats(T, fld, wire_raw, cmd, eng)
    P_osc = stats(T, fld, wire_raw, cmd, oscm)
    P_nor = stats(T, fld, wire_raw, cmd, normal)
    print("  POOLED engaged  %s" % fmt(P_all))
    print("  OSC frames      %s" % fmt(P_osc))
    print("  NORMAL frames   %s" % fmt(P_nor))

    # ---- task 2: decision table ----
    print("\nDECISION TABLE (thresholds quoted from PREREG-V278R3-CLAMP-READ.md §3, none moved):")
    print("  SAT high >= %.2f / low < %.2f ; DAMP high >= %.2f osc, >= %.2f normal / low <= %.2f"
          % (SAT_HIGH, SAT_LOW, DAMP_HIGH_OSC, DAMP_HIGH_NORM, DAMP_LOW))
    rows = []
    if P_osc.get("n", 0) >= 20:
        rows.append(("OSC", P_osc, True))
    rows.append(("NORMAL" if merged else "ALL ENGAGED (no episodes)", P_nor if merged else P_all, False))
    for nm, o, is_osc in rows:
        for conv in ("damp_raw", "damp_neg"):
            d = o.get(conv, np.nan)
            print("  %-26s %-8s DAMP %.3f -> %-7s | SAT %.3f -> %-7s | predicted K=2: DAMP %s SAT %s"
                  % (nm, conv, d, label_damp(d, is_osc), o["sat"], label_sat(o["sat"]),
                     "0.68" if is_osc else "0.60", "0.000" if is_osc else "0.004"))

    # ---- task 5: route facts ----
    print("\nROUTE FACTS:")
    print("  engaged (sca & req) %.1f s of %.1f s; latActive %.1f%% of carControl rows"
          % (eng_g.sum() / FS, len(tg) / FS, 100 * D["lat"].mean()))
    v_e = vego_g[eng_g]
    print("  vEgo engaged: min %.1f p10 %.1f p50 %.1f p90 %.1f max %.1f m/s (route max %.1f)"
          % (v_e.min(), *np.percentile(v_e, [10, 50, 90]), v_e.max(), D["vego"].max()))
    print("  |steering angle| engaged (0x14A): p50 %.1f p95 %.1f p99 %.1f max %.1f deg"
          % (*np.percentile(np.abs(ang_g[eng_g]), [50, 95, 99]), np.abs(ang_g[eng_g]).max()))
    r_e = np.abs(wire_g[eng_g])
    print("  |0x18F rate| engaged RAW: p50 %.0f p95 %.0f p99 %.0f max %.0f  (deg/s at 8/deg/s: p95 %.1f p99 %.1f max %.1f)"
          % (*np.percentile(r_e, [50, 95, 99]), r_e.max(),
             np.percentile(r_e, 95) / 8, np.percentile(r_e, 99) / 8, r_e.max() / 8))
    print("  |0xE4 cmd| engaged: p50 %.0f p90 %.0f p99 %.0f max %.0f" % (*np.percentile(np.abs(cmd_g[eng_g]), [50, 90, 99]), np.abs(cmd_g[eng_g]).max()))
    aq = np.abs(np.interp(tg, T18, D["tq"]) * 1.024)
    print("  driver |torque| raw engaged: p50 %.0f p90 %.0f p99 %.0f" % tuple(np.percentile(aq[eng_g], [50, 90, 99])))

    # ---- T-vs-|angle| and T-vs-rate: where does T sit at high angle (operator: stutter far from centre) ----
    ang_1ab = np.interp(t1ab - t0, tg, ang_g)
    print("\n|T| BY |ANGLE| BIN (engaged):")
    for lo, hi in ((0, 10), (10, 30), (30, 60), (60, 120), (120, 400)):
        m = eng & (np.abs(ang_1ab) >= lo) & (np.abs(ang_1ab) < hi)
        if m.sum() < 50:
            continue
        o = stats(T, fld, wire_raw, cmd, m)
        print("  |ang| %3d-%3d  n=%5d  |T| p50 %4.0f p90 %4.0f max %4d  sat %.3f  damp_raw %.3f  |cmd| p50 %.0f"
              % (lo, hi, o["n"], o["T_p50"], o["T_p90"], o["max_absT"], o["sat"], o.get("damp_raw", np.nan),
                 np.median(np.abs(cmd[m][~np.isnan(cmd[m])]))))

    # ---- 2.5-6 Hz envelope summary (comparable to V276's read) ----
    print("\n2.5-6 Hz RATE ENVELOPE (raw counts): engaged p50 %.0f p95 %.0f max %.0f; disengaged p50 %.0f p95 %.0f"
          % (np.median(env[eng_g]), np.percentile(env[eng_g], 95), env[eng_g].max(),
             np.median(env[~eng_g]) if (~eng_g).any() else np.nan, np.percentile(env[~eng_g], 95) if (~eng_g).any() else np.nan))
    # engaged spectrum peak
    x = wire_g[eng_g] - wire_g[eng_g].mean()
    f, P = signal.welch(x, fs=FS, nperseg=512)
    b = (f >= 0.5) & (f <= 10)
    print("  all-engaged rate spectrum peak %.2f Hz; 2-4 Hz share of 0.5-10 Hz %.3f; 3.5-4.5 Hz share %.3f"
          % (f[b][np.argmax(P[b])], P[(f >= 2) & (f <= 4)].sum() / P[b].sum(), P[(f >= 3.5) & (f <= 4.5)].sum() / P[b].sum()))

    json.dump(dict(pooled=P_all, osc=P_osc, normal=P_nor, episodes=[(float(tg[s]), float(tg[e - 1])) for s, e in merged],
                   thr=float(thr)), open(os.path.join(SCRATCH, "r31_read.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
