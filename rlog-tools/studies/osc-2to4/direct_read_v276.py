# -*- coding: utf-8 -*-
"""DIRECT rlog read of the V276 drive -- the INDEPENDENT method for the 2-4 Hz oscillation.

Route 75604b0a432fdc89_0000002e--855ecfcf30 (16 segments), V276 on the car.
Reads the raw CAN frames from the rlog with its own decoder; shares NO code with the cache
pipeline or `score/`.  Three questions, each decided by a number:

  1. PEAK column rate in RAW counts during the oscillation, and whether 0x18F bytes 2-3 flat-top.
  2. The VARIANT SELECTOR on CAN 427 (V276 repointed the packer to gp-0x674e).
  3. Is openpilot's COMMAND (0xE4) oscillating, or only the RESPONSE (0x18F rate / 0x14A angle)?
     Plus the driver-torque level at which the oscillation dies (the grip threshold).

Frame layouts (Honda, big-endian; kit convention, see rlog-tools/lib/loop_op_lib.py header):
  0x18F src1  b0-1 i16be STEER_TORQUE_SENSOR (wire; raw = wire*1.024)   b2-3 i16be STEER_ANGLE_RATE
              (gp-0x6a56, RAW counts, no deg/s conversion applied)      b4 bit3 STEER_CONTROL_ACTIVE
  0x14A src1  b0-1 i16be STEER_ANGLE * -0.1 deg
  0x1AB src1  10-bit field  ((b0 & 3) << 8) | b1   -- V276: clamp(|gp-0x674e| * 5, 1, 1023)
  0x0E4 src129 b0-1 i16be STEER_TORQUE (openpilot's request)  b2 bit7 STEER_REQUEST
"""
import glob
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))            # rlog-tools
ROOT = os.path.dirname(KIT)
sys.path.insert(0, KIT)
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
PREFIX = "75604b0a432fdc89_0000002e--855ecfcf30"
RATE_CLAMP_BELIEF = 12000        # V276 docstring: channel believed magnitude-clamped here
FS = 100.0


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def segments(prefix):
    return sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))


def read_route(prefix):
    import zstandard
    from cereal import log as clog
    t18, tq, rate, sca = [], [], [], []
    t14, ang = [], []
    t1ab, sel, b0raw = [], [], []
    te4, cmd, req = [], [], []
    tcs, vego, lat = [], [], []
    for p in segments(prefix):
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        for evt in clog.Event.read_multiple_bytes(data):
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
                            t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2))
                            sca.append((d[4] >> 3) & 1)
                        elif m.address == 0x14A and len(d) >= 4:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1)
                        elif m.address == 0x1AB and len(d) >= 2:
                            t1ab.append(tm); sel.append(((d[0] & 3) << 8) | d[1]); b0raw.append(d[0])
                    elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); cmd.append(i16be(d, 0)); req.append((d[2] >> 7) & 1)
            elif w == "carState":
                tcs.append(tm); vego.append(evt.carState.vEgo)
            elif w == "carControl":
                lat.append((tm, bool(evt.carControl.latActive)))
        print("  read %s" % os.path.basename(p), flush=True)
    A = lambda x, dt=float: np.asarray(x, dt)
    return dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca, int),
                t14=A(t14), ang=A(ang), t1ab=A(t1ab), sel=A(sel, int), b0=A(b0raw, int),
                te4=A(te4), cmd=A(cmd), req=A(req, int), tcs=A(tcs), vego=A(vego),
                tlat=A([x[0] for x in lat]), lat=A([x[1] for x in lat], int))


def main():
    cache = os.path.join(HERE, "_direct_read_v276.npz")
    if os.path.exists(cache):
        D = dict(np.load(cache))
    else:
        D = read_route(PREFIX)
        np.savez(cache, **D)
    t0 = D["t18"][0]
    T = D["t18"] - t0
    rate, tq = D["rate"], D["tq"]
    tq_raw = tq * 1.024
    print("\n=== ROUTE %s ===" % PREFIX)
    print("0x18F frames %d over %.1f s (%.2f Hz);  0x14A %d;  0x1AB %d;  0xE4(src129) %d"
          % (len(T), T[-1], len(T) / T[-1], len(D["t14"]), len(D["t1ab"]), len(D["te4"])))

    # ---------------- uniform 100 Hz grid ----------------
    tg = np.arange(0.0, T[-1], 1 / FS)
    rg = np.interp(tg, T, rate)
    tqg = np.interp(tg, T, tq_raw)
    scag = np.interp(tg, T, D["sca"]) > 0.5
    reqg = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5 if len(D["te4"]) else np.zeros_like(scag)
    cmdg = np.interp(tg, D["te4"] - t0, D["cmd"]) if len(D["te4"]) else np.zeros_like(rg)
    angg = np.interp(tg, D["t14"] - t0, D["ang"])
    vg = np.interp(tg, D["tcs"] - t0, D["vego"]) if len(D["tcs"]) else np.zeros_like(rg)
    eng = scag & reqg
    dis = ~eng
    print("engaged (0x18F b4.3 AND 0xE4 STEER_REQUEST): %.1f s of %.1f s;  sca-only %.1f s; req-only %.1f s"
          % (eng.sum() / FS, len(tg) / FS, scag.sum() / FS, reqg.sum() / FS))

    # ---------------- Q1: flat-top check on the rate channel ----------------
    print("\n=== Q1: 0x18F STEER_ANGLE_RATE, RAW counts (gp-0x6a56) ===")
    amax = np.abs(rate).max()
    vals, cnt = np.unique(rate, return_counts=True)
    top = sorted(zip(cnt, vals), reverse=True)[:8]
    print("global |rate| max = %d   (min %d, max %d)" % (amax, rate.min(), rate.max()))
    print("most frequent values: %s" % ", ".join("%d x%d" % (v, c) for c, v in top))
    at_max = (np.abs(rate) >= amax - 1).sum()
    print("samples at |max| (within 1 count): %d of %d (%.3f%%)" % (at_max, len(rate), 100 * at_max / len(rate)))
    print("samples at |rate| >= %d (the believed clamp): %d" % (RATE_CLAMP_BELIEF, (np.abs(rate) >= RATE_CLAMP_BELIEF).sum()))
    for thr in (5504, 6668, 8256, 11008, 12000, 13760, 16512, 33024):
        print("  engaged samples with |rate| >= %5d: %6d (%.2f%% of engaged)"
              % (thr, (np.abs(rg[eng]) >= thr).sum(), 100 * (np.abs(rg[eng]) >= thr).mean()))

    # ---------------- engaged intervals: spectral character of each ----------------
    ed = np.diff(np.r_[0, eng.astype(int), 0])
    es, ee = np.where(ed == 1)[0], np.where(ed == -1)[0]
    print("\n=== ENGAGED INTERVALS (%d) -- 2-4 Hz share of rate power, peak freq ===" % len(es))
    print("%4s %8s %6s %6s %7s %7s %6s %6s %7s %7s" % ("#", "start", "dur", "v_mps", "pk|r|", "p95|r|", "f_pk", "sh24", "|cmd|50", "|tq|50"))
    for k, (s, e) in enumerate(zip(es, ee)):
        if e - s < 100:
            continue
        x = rg[s:e] - rg[s:e].mean()
        f, P = signal.welch(x, fs=FS, nperseg=min(256, e - s))
        b = (f >= 0.5) & (f <= 10)
        fpk = f[b][np.argmax(P[b])]
        sh = P[(f >= 2) & (f <= 4)].sum() / max(P[b].sum(), 1e-9)
        print("%4d %8.1f %6.1f %6.1f %7.0f %7.0f %6.2f %6.2f %7.0f %7.0f" % (
            k, tg[s], (e - s) / FS, vg[s:e].mean(), np.abs(rg[s:e]).max(), np.percentile(np.abs(rg[s:e]), 95), fpk, sh,
            np.median(np.abs(cmdg[s:e])), np.median(np.abs(tqg[s:e]))))
    x = rg[eng] - rg[eng].mean()
    f, P = signal.welch(x, fs=FS, nperseg=512)
    b = (f >= 0.5) & (f <= 10)
    print("ALL-ENGAGED rate spectrum peak: %.2f Hz; 2-4 Hz share %.2f" % (f[b][np.argmax(P[b])], P[(f >= 2) & (f <= 4)].sum() / P[b].sum()))
    x = rg[dis] - rg[dis].mean()
    f, P = signal.welch(x, fs=FS, nperseg=512)
    print("ALL-DISENGAGED rate spectrum peak: %.2f Hz; 2-4 Hz share %.2f" % (f[b][np.argmax(P[b])], P[(f >= 2) & (f <= 4)].sum() / P[b].sum()))

    # ---------------- oscillation episodes ----------------
    sos = signal.butter(4, [1.5, 5.0], btype="bandpass", fs=FS, output="sos")
    rb = signal.sosfiltfilt(sos, rg)
    env = np.abs(signal.hilbert(rb))
    env_s = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), env)
    dis = ~eng
    p95_dis = np.percentile(env_s[dis], 95) if dis.any() else np.nan
    p95_eng = np.percentile(env_s[eng], 95)
    print("\n2-4 Hz band envelope of rate: disengaged p50/p95 = %.0f/%.0f ; engaged p50/p95 = %.0f/%.0f"
          % (np.median(env_s[dis]), p95_dis, np.median(env_s[eng]), p95_eng))
    thr = max(2.5 * p95_dis, 150.0)
    print("episode threshold: envelope > %.0f wire counts, sustained >= 1.5 s, engaged" % thr)
    on = (env_s > thr) & eng
    # run-length
    edges = np.diff(np.r_[0, on.astype(int), 0])
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    eps = [(s, e) for s, e in zip(starts, ends) if (e - s) / FS >= 1.5]
    # merge gaps < 1 s
    merged = []
    for s, e in eps:
        if merged and s - merged[-1][1] < 1.0 * FS:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    eps = merged
    print("\n%d oscillation episodes" % len(eps))
    hdr = "%4s %8s %8s %6s %7s %7s %6s %6s %9s %9s %7s %6s %6s"
    print(hdr % ("#", "start", "end", "dur", "pk|rate|", "p95|r|", "f_dom", "v_mps", "cmd_amp", "rate_amp", "coh", "phase", "tq_p50"))
    osc_mask = np.zeros_like(eng)
    ep_rows = []
    for k, (s, e) in enumerate(eps):
        osc_mask[s:e] = True
        seg_r, seg_c, seg_q = rg[s:e], cmdg[s:e], tqg[s:e]
        n = e - s
        nps = min(512, n)
        f, P = signal.welch(seg_r - seg_r.mean(), fs=FS, nperseg=nps)
        band = (f >= 1.0) & (f <= 8.0)
        fdom = f[band][np.argmax(P[band])]
        # amplitude of the 2-4 Hz component of command vs rate: band-passed RMS * sqrt(2)
        cb = signal.sosfiltfilt(sos, seg_c - seg_c.mean()) if n > 30 else seg_c
        rbb = rb[s:e]
        c_amp, r_amp = np.sqrt(2) * cb.std(), np.sqrt(2) * rbb.std()
        # coherence and phase at fdom
        f2, Cxy = signal.coherence(seg_c, seg_r, fs=FS, nperseg=nps)
        f3, Pxy = signal.csd(seg_c, seg_r, fs=FS, nperseg=nps)
        j = np.argmin(np.abs(f2 - fdom))
        ph = np.degrees(np.angle(Pxy[j]))
        row = (k, tg[s], tg[e - 1], n / FS, np.abs(seg_r).max(), np.percentile(np.abs(seg_r), 95), fdom,
               vg[s:e].mean(), c_amp, r_amp, Cxy[j], ph, np.median(np.abs(seg_q)))
        ep_rows.append(row)
        print("%4d %8.1f %8.1f %6.1f %7.0f %7.0f %6.2f %6.1f %9.0f %9.0f %7.2f %6.0f %6.0f" % row)
    if ep_rows:
        R = np.array(ep_rows)
        print("\nEPISODE SUMMARY: total %.1f s oscillating; peak |rate| over all episodes = %.0f raw; "
              "median episode p95 = %.0f; f_dom median %.2f Hz"
              % (R[:, 3].sum(), R[:, 4].max(), np.median(R[:, 5]), np.median(R[:, 6])))
        print("  command 2-4 Hz amp: median %.0f (0xE4 counts);  rate 2-4 Hz amp: median %.0f raw;  coherence median %.2f; phase median %.0f deg"
              % (np.median(R[:, 8]), np.median(R[:, 9]), np.median(R[:, 10]), np.median(R[:, 11])))
        print("  0xE4 full-scale for reference: %d..%d on this route; engaged non-osc |cmd| p50/p95 = %.0f/%.0f"
              % (D["cmd"].min(), D["cmd"].max(),
                 np.median(np.abs(cmdg[eng & ~osc_mask])), np.percentile(np.abs(cmdg[eng & ~osc_mask]), 95)))

    # non-oscillating engaged rate distribution
    q = eng & ~osc_mask
    pct = np.percentile(np.abs(rg[q]), [50, 75, 90, 95, 99, 99.9])
    print("\nNON-oscillating ENGAGED |rate| raw: p50 %.0f p75 %.0f p90 %.0f p95 %.0f p99 %.0f p99.9 %.0f max %.0f  (n=%d, %.1f s)"
          % (*pct, np.abs(rg[q]).max(), q.sum(), q.sum() / FS))
    pctd = np.percentile(np.abs(rg[dis]), [50, 90, 95, 99])
    print("DISENGAGED |rate| raw: p50 %.0f p90 %.0f p95 %.0f p99 %.0f max %.0f" % (*pctd, np.abs(rg[dis]).max()))
    if osc_mask.any():
        pcto = np.percentile(np.abs(rg[osc_mask]), [50, 90, 95, 99])
        print("OSCILLATING |rate| raw:  p50 %.0f p90 %.0f p95 %.0f p99 %.0f max %.0f" % (*pcto, np.abs(rg[osc_mask]).max()))
        # per-cycle peaks: local maxima of |rate| in episodes
        pk, _ = signal.find_peaks(np.abs(rg) * osc_mask, distance=int(0.12 * FS), height=thr / 2)
        print("per-half-cycle peaks in episodes: n=%d  p50 %.0f p90 %.0f max %.0f"
              % (len(pk), np.median(np.abs(rg[pk])), np.percentile(np.abs(rg[pk]), 90), np.abs(rg[pk]).max()))
        # angle swing
        ab = signal.sosfiltfilt(sos, angg)
        print("angle 2-4 Hz swing (peak-to-peak proxy 2*sqrt2*std) in episodes: %.2f deg; outside engaged: %.2f deg"
              % (2 * np.sqrt(2) * ab[osc_mask].std(), 2 * np.sqrt(2) * ab[q].std()))

    # ---------------- Q3b: grip threshold ----------------
    print("\n=== Q3b: driver torque vs oscillation (engaged only) ===")
    edges_q = [0, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 8000]
    aq = np.abs(tqg)
    print("%12s %8s %8s %10s" % ("|tq| raw bin", "n_eng", "P(osc)", "env p50"))
    for lo, hi in zip(edges_q[:-1], edges_q[1:]):
        m = eng & (aq >= lo) & (aq < hi)
        if m.sum() < 50:
            continue
        print("%5d-%-6d %8d %8.3f %10.0f" % (lo, hi, m.sum(), osc_mask[m].mean(), np.median(env_s[m])))
    # at each episode end: torque around the end
    print("episode-end driver torque: |tq| raw median in last 1 s of episode vs 1 s after")
    for k, (s, e) in enumerate(eps):
        a = np.median(np.abs(tqg[max(s, e - 100):e]))
        b = np.median(np.abs(tqg[e:min(len(tqg), e + 100)]))
        still_eng = eng[e:min(len(tqg), e + 100)].mean()
        print("  ep %2d end %.1f s: last1s %5.0f  next1s %5.0f  engaged-after %.2f" % (k, tg[e - 1], a, b, still_eng))

    # ---------------- Q2: selector on 427 ----------------
    print("\n=== Q2: CAN 427 (0x1AB) 10-bit field = ((b0&3)<<8)|b1 ===")
    v, c = np.unique(D["sel"], return_counts=True)
    for vv, cc in sorted(zip(v, c), key=lambda x: -x[1])[:10]:
        print("  wire %4d : %7d (%.3f%%)   => |gp-0x674e| = wire/5 = %.2f" % (vv, cc, 100 * cc / len(D["sel"]), vv / 5))
    vb, cb0 = np.unique(D["b0"], return_counts=True)
    print("  byte0 values: %s" % ", ".join("0x%02X x%d" % (a, b) for a, b in zip(vb, cb0)))
    print("  427 rate: %.2f Hz" % (len(D["t1ab"]) / (D["t1ab"][-1] - D["t1ab"][0])))


if __name__ == "__main__":
    main()


def causality():
    """Second pass: the mode sits at 4-4.7 Hz, so re-run the episode logic in a 2.5-6 Hz band and ask
    WHO LEADS -- cross-correlation lag and cross-spectral phase of openpilot's 0xE4 command against the
    0x18F rate and the 0x14A angle, per engaged interval."""
    D = dict(np.load(os.path.join(HERE, "_direct_read_v276.npz")))
    t0 = D["t18"][0]; T = D["t18"] - t0
    tg = np.arange(0.0, T[-1], 1 / FS)
    rg = np.interp(tg, T, D["rate"]); tqg = np.interp(tg, T, D["tq"] * 1.024)
    scag = np.interp(tg, T, D["sca"]) > 0.5
    reqg = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    cmdg = np.interp(tg, D["te4"] - t0, D["cmd"])
    angg = np.interp(tg, D["t14"] - t0, D["ang"])
    vg = np.interp(tg, D["tcs"] - t0, D["vego"])
    eng = scag & reqg
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")
    rb, cb, ab = (signal.sosfiltfilt(sos, x) for x in (rg, cmdg, angg))
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    thr = max(2.5 * np.percentile(env[~eng], 95), 150)
    on = (env > thr) & eng
    edges = np.diff(np.r_[0, on.astype(int), 0])
    eps = [(s, e) for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]) if e - s >= 100]
    merged = []
    for s, e in eps:
        if merged and s - merged[-1][1] < 100:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    print("\n=== PASS 2: band 2.5-6 Hz, threshold %.0f, >= 1.0 s -- %d episodes ===" % (thr, len(merged)))
    print("%3s %7s %5s %5s %6s %6s %5s %7s %7s %5s %6s %6s %6s %6s" % (
        "#", "start", "dur", "v", "pk|r|", "p95|r|", "fdom", "cmdAmp", "rateAmp", "coh", "ph_cr", "ph_ca", "lag_ms", "|tq|50"))
    tot = 0
    for k, (s, e) in enumerate(merged):
        n = e - s; nps = min(256, n)
        f, P = signal.welch(rb[s:e], fs=FS, nperseg=nps)
        fdom = f[np.argmax(P)]
        f2, C = signal.coherence(cmdg[s:e], rg[s:e], fs=FS, nperseg=nps)
        _, Pcr = signal.csd(cmdg[s:e], rg[s:e], fs=FS, nperseg=nps)
        _, Pca = signal.csd(cmdg[s:e], angg[s:e], fs=FS, nperseg=nps)
        j = np.argmin(np.abs(f2 - fdom))
        # cross-correlation lag of band-passed cmd vs rate: positive => cmd LEADS rate
        x, y = cb[s:e], rb[s:e]
        xc = np.correlate(y - y.mean(), x - x.mean(), "full") / (np.std(x) * np.std(y) * n)
        lags = np.arange(-n + 1, n); w = np.abs(lags) <= 25
        lag = lags[w][np.argmax(xc[w])] * 10.0
        tot += n
        print("%3d %7.1f %5.1f %5.1f %6.0f %6.0f %5.2f %7.0f %7.0f %5.2f %6.0f %6.0f %6.0f %6.0f" % (
            k, tg[s], n / FS, vg[s:e].mean(), np.abs(rg[s:e]).max(), np.percentile(np.abs(rg[s:e]), 95), fdom,
            np.sqrt(2) * cb[s:e].std(), np.sqrt(2) * rb[s:e].std(), C[j], np.degrees(np.angle(Pcr[j])),
            np.degrees(np.angle(Pca[j])), lag, np.median(np.abs(tqg[s:e]))))
    print("total oscillating %.1f s of %.1f s engaged" % (tot / FS, eng.sum() / FS))
    print("ph_cr / ph_ca: phase of RATE / ANGLE relative to COMMAND at fdom (scipy csd(x,y) = conj(X)Y);"
          " lag_ms > 0 means command LEADS rate in band-passed cross-correlation")
    # overall engaged: cmd->angle transfer phase at 3-5 Hz
    f, C = signal.coherence(cmdg[eng], angg[eng], fs=FS, nperseg=512)
    _, Pxy = signal.csd(cmdg[eng], angg[eng], fs=FS, nperseg=512)
    for fq in (2.0, 3.0, 4.0, 4.5, 5.0):
        j = np.argmin(np.abs(f - fq))
        print("  all-engaged cmd->angle @%.1f Hz: coh %.2f phase %.0f deg" % (fq, C[j], np.degrees(np.angle(Pxy[j]))))
    # grip: envelope vs |driver torque| bins, engaged
    aq = np.abs(tqg)
    print("\nGRIP (pass 2 envelope, engaged): |tq| raw bin -> n, P(env>thr), env p50/p90")
    for lo, hi in zip([0, 500, 1000, 1500, 2000, 2500, 3000, 4000], [500, 1000, 1500, 2000, 2500, 3000, 4000, 9000]):
        m = eng & (aq >= lo) & (aq < hi)
        if m.sum() >= 50:
            print("  %5d-%-5d n=%5d P=%.3f env %4.0f/%4.0f" % (lo, hi, m.sum(), (env[m] > thr).mean(), np.median(env[m]), np.percentile(env[m], 90)))


if __name__ == "__main__":
    causality()


def op_state():
    """openpilot's OWN torque-controller state (controlsState.lateralControlState.torqueState):
    split the 0xE4 swing into P (feedback on measured lateral accel / curvature), I, D, F (feedforward
    from the planner's desired path).  If the swing lives in P and the desired path is flat, openpilot is
    FOLLOWING the angle; if desiredLateralAccel swings, the planner is in the loop."""
    import zstandard
    from cereal import log as clog
    cache = os.path.join(HERE, "_direct_read_v276_op.npz")
    if os.path.exists(cache):
        S = dict(np.load(cache))
    else:
        rows = []
        for p in segments(PREFIX):
            with open(p, "rb") as fh:
                data = zstandard.ZstdDecompressor().stream_reader(fh).read()
            for evt in clog.Event.read_multiple_bytes(data):
                try:
                    if evt.which() != "controlsState":
                        continue
                except Exception:
                    continue
                cs = evt.controlsState
                if cs.lateralControlState.which() != "torqueState":
                    continue
                ts = cs.lateralControlState.torqueState
                rows.append((evt.logMonoTime * 1e-9, ts.active, ts.error, ts.p, ts.i, ts.d, ts.f, ts.output,
                             ts.actualLateralAccel, ts.desiredLateralAccel, cs.curvature, cs.desiredCurvature))
        R = np.array(rows, float)
        S = dict(t=R[:, 0], active=R[:, 1], err=R[:, 2], p=R[:, 3], i=R[:, 4], d=R[:, 5], f=R[:, 6],
                 out=R[:, 7], act=R[:, 8], des=R[:, 9], curv=R[:, 10], dcurv=R[:, 11])
        np.savez(cache, **S)
    D = dict(np.load(os.path.join(HERE, "_direct_read_v276.npz")))
    t0 = D["t18"][0]
    ts = S["t"] - t0
    print("\n=== openpilot torqueState: %d rows, %.1f Hz; lateral state kind = torqueState ===" % (len(ts), len(ts) / (ts[-1] - ts[0])))
    tg = np.arange(0.0, ts[-1], 1 / FS)
    G = {k: np.interp(tg, ts, S[k]) for k in ("p", "i", "d", "f", "out", "act", "des", "err", "curv", "dcurv", "active")}
    act = G["active"] > 0.5
    sos = signal.butter(4, [2.5, 6.0], btype="bandpass", fs=FS, output="sos")
    B = {k: signal.sosfiltfilt(sos, G[k]) for k in G}
    envo = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(B["out"])))
    thr = max(2.5 * np.percentile(envo[~act], 95) if (~act).any() else 0, 0.03)
    on = (envo > thr) & act
    edges = np.diff(np.r_[0, on.astype(int), 0])
    eps = [(s, e) for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]) if e - s >= 100]
    print("output-envelope threshold %.3f (of 1.0 full scale); %d episodes >= 1 s" % (thr, len(eps)))
    print("%3s %7s %5s | 2.5-6 Hz amplitude (x sqrt2 std):  %6s %6s %6s %6s %6s | %8s %8s %8s" % (
        "#", "start", "dur", "out", "p", "i", "d", "f", "actLA", "desLA", "err"))
    for k, (s, e) in enumerate(eps):
        a = lambda key: np.sqrt(2) * B[key][s:e].std()
        print("%3d %7.1f %5.1f |                                    %6.3f %6.3f %6.3f %6.3f %6.3f | %8.3f %8.3f %8.3f" % (
            k, tg[s], (e - s) / FS, a("out"), a("p"), a("i"), a("d"), a("f"), a("act"), a("des"), a("err")))
    m = act
    print("ALL-ACTIVE 2.5-6 Hz amplitude: out %.3f  p %.3f  i %.3f  d %.3f  f %.3f | actLA %.3f desLA %.3f  dcurv %.5f curv %.5f" % tuple(
        np.sqrt(2) * B[k][m].std() for k in ("out", "p", "i", "d", "f", "act", "des", "dcurv", "curv")))
    print("active time %.1f s; output full-scale = 1.0 -> 0xE4 4096" % (act.sum() / FS))


if __name__ == "__main__":
    op_state()
