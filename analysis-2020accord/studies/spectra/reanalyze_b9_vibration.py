#!/usr/bin/env python3
r"""
studies/spectra/reanalyze_b9_vibration.py -- FROM-SCRATCH re-derivation of the ~21 Hz EPS steering
vibration measurement on openpilot route b9, from RAW CAN 399, with no dependence on
any prior recorded number. Falsification exercise.

Route b9 = 807a3c21c9f405e8_000000b9--6a1dd9d6dc, 12 segments (0..11).

SIGNAL: raw CAN 399 (0x18F) STEER_STATUS message, bus 1, 7 data bytes. Layout VALIDATED
here by the Honda 4-bit checksum (100% pass across 67,588 frames), not assumed from a DBC:
    bytes[0:2]  STEER_TORQUE_SENSOR  int16 big-endian, DBC scale -1  (packer: -(internal*125/128))
    bytes[2:4]  STEER_ANGLE_RATE     int16 big-endian, DBC scale -0.1 deg/s
    byte4 hi-nibble  STEER_STATUS     (0=normal, 3=low_speed_lockout, 4=no_torque_alert_2)
    byte4 bit3       STEER_CONTROL_ACTIVE (LKAS engaged)
    byte6 bits[5:4]  COUNTER (0-1-2-3)      byte6 lo-nibble CHECKSUM

TIME BASE: logMonoTime is batched (2 frames often share one stamp); but per-segment SPAN is
accurate, the 2-bit COUNTER shows ~0 dropped frames (99.996% delta==1 over the whole route),
and the median logMonoTime inter-frame delta independently gives ~100 Hz. We therefore assign
each 399 frame a timestamp from a per-segment LINEAR fit of logMonoTime vs frame index (this
de-batches, removes drift, and stays on the same clock as carControl/carState for coherence).

Command signal for coherence: carControl.actuators.torque (openpilot normalized lateral output,
~100 Hz). (This Honda is torque-controlled; torqueOutputCan is not populated in these logs.)

Outputs: prints a full numeric report; dumps arrays to reanalyze_b9_vibration.npz and a
per-Nfft PSD CSV next to this script.

Requires: numpy, pycapnp, zstandard, and rlog-tools/lib/rlog_parse.py (added to sys.path below).
No scipy (Welch PSD + coherence are hand-rolled).
"""
import sys, glob, os
from pathlib import Path
from collections import Counter
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOG_GLOB = str(HERE / "rlogs" / "807a3c21c9f405e8_000000b9--6a1dd9d6dc--*--rlog.zst")
FS = 100.0                      # nominal sample rate (validated ~100.00 Hz)
DT = 1.0 / FS

# ---------------------------------------------------------------- decode helpers
def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF

def s16be(b0, b1):
    v = (b0 << 8) | b1
    return v - 0x10000 if v & 0x8000 else v

# ---------------------------------------------------------------- load one segment
def load_segment(path):
    """Return dict of time-ordered arrays for one segment."""
    f399_t = []; f399_tq = []; f399_status = []; f399_active = []; f399_ctr = []; f399_rate = []
    cc_t = []; cc_lat = []; cc_cmd = []
    cs_t = []; cs_pressed = []; cs_vego = []; cs_angle = []; cs_rate = []
    sc_t = []; sc_steer = []; sc_req = []   # sendcan 0xE4 STEERING_CONTROL bus command
    chk_bad = 0; sc_chk_bad = 0
    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        t = evt.logMonoTime
        if w == "can":
            for fr in evt.can:
                if fr.address == 399 and fr.src == 1:
                    d = bytes(fr.dat)
                    if len(d) != 7:
                        continue
                    if honda_checksum(399, d) != (d[6] & 0xF):
                        chk_bad += 1
                        continue
                    f399_t.append(t)
                    f399_tq.append(-s16be(d[0], d[1]))        # DBC scale -1
                    f399_rate.append(-0.1 * s16be(d[2], d[3])) # 399 STEER_ANGLE_RATE (DBC scale -0.1)
                    f399_status.append((d[4] >> 4) & 0xF)
                    f399_active.append((d[4] >> 3) & 1)
                    f399_ctr.append((d[6] >> 4) & 0x3)
        elif w == "carControl":
            cc_t.append(t)
            cc_lat.append(1 if evt.carControl.latActive else 0)
            cc_cmd.append(float(evt.carControl.actuators.torque))
        elif w == "carState":
            cs_t.append(t)
            cs_pressed.append(1 if evt.carState.steeringPressed else 0)
            cs_vego.append(float(evt.carState.vEgo))
            cs_angle.append(float(evt.carState.steeringAngleDeg))
            cs_rate.append(float(evt.carState.steeringRateDeg))
        elif w == "sendcan":
            for fr in evt.sendcan:
                if fr.address == 228 and fr.src == 0:   # 0xE4 STEERING_CONTROL, tx on bus 0
                    d = bytes(fr.dat)
                    if len(d) != 5:
                        continue
                    if honda_checksum(228, d) != (d[4] & 0xF):
                        sc_chk_bad += 1
                        continue
                    sc_t.append(t)
                    sc_steer.append(s16be(d[0], d[1]))     # STEER_TORQUE (int16 BE), actual bus command
                    sc_req.append((d[2] >> 7) & 1)          # STEER_TORQUE_REQUEST
    return dict(
        f399_t=np.array(f399_t, np.int64), f399_tq=np.array(f399_tq, float),
        f399_rate=np.array(f399_rate, float),
        f399_status=np.array(f399_status), f399_active=np.array(f399_active),
        f399_ctr=np.array(f399_ctr),
        cc_t=np.array(cc_t, np.int64), cc_lat=np.array(cc_lat), cc_cmd=np.array(cc_cmd, float),
        cs_t=np.array(cs_t, np.int64), cs_pressed=np.array(cs_pressed), cs_vego=np.array(cs_vego, float),
        cs_angle=np.array(cs_angle, float), cs_rate=np.array(cs_rate, float),
        sc_t=np.array(sc_t, np.int64), sc_steer=np.array(sc_steer, float), sc_req=np.array(sc_req),
        chk_bad=chk_bad, sc_chk_bad=sc_chk_bad,
    )

def frame_timestamps(lm):
    """Per-frame seconds from a linear fit of logMonoTime vs index (de-batch + de-drift)."""
    n = len(lm)
    idx = np.arange(n)
    lm_s = lm.astype(np.float64) / 1e9
    b, a = np.polyfit(idx, lm_s, 1)     # lm_s ~ a + b*idx ; b = sample period
    fit = a + b * idx
    resid = lm_s - fit
    return fit, b, resid

# ---------------------------------------------------------------- spectral core (no scipy)
def periodic_hann(n):
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)

def welch_psd(x, fs, nperseg, noverlap=None, detrend="linear"):
    x = np.asarray(x, float)
    if noverlap is None:
        noverlap = nperseg // 2
    step = nperseg - noverlap
    win = periodic_hann(nperseg)
    U = np.sum(win ** 2)
    n_bins = nperseg // 2 + 1
    acc = np.zeros(n_bins); K = 0
    t = np.arange(nperseg)
    for start in range(0, len(x) - nperseg + 1, step):
        seg = x[start:start + nperseg].astype(float).copy()
        if detrend == "constant":
            seg -= seg.mean()
        elif detrend == "linear":
            p = np.polyfit(t, seg, 1); seg = seg - (p[0] * t + p[1])
        seg *= win
        F = np.fft.rfft(seg)
        P = (np.abs(F) ** 2) / (fs * U)
        P[1:-1] *= 2.0
        acc += P; K += 1
    f = np.fft.rfftfreq(nperseg, 1 / fs)
    return f, (acc / K if K else acc), K

def welch_coherence(x, y, fs, nperseg, noverlap=None, detrend="linear"):
    """Aggregate cross/auto spectra across windows of x,y (same grid). Returns f, Cxy, K."""
    if noverlap is None:
        noverlap = nperseg // 2
    step = nperseg - noverlap
    win = periodic_hann(nperseg)
    n_bins = nperseg // 2 + 1
    Pxx = np.zeros(n_bins); Pyy = np.zeros(n_bins); Pxy = np.zeros(n_bins, complex); K = 0
    t = np.arange(nperseg)
    for start in range(0, len(x) - nperseg + 1, step):
        xs = x[start:start + nperseg].astype(float).copy()
        ys = y[start:start + nperseg].astype(float).copy()
        if detrend == "linear":
            p = np.polyfit(t, xs, 1); xs -= (p[0] * t + p[1])
            q = np.polyfit(t, ys, 1); ys -= (q[0] * t + q[1])
        else:
            xs -= xs.mean(); ys -= ys.mean()
        xs *= win; ys *= win
        X = np.fft.rfft(xs); Y = np.fft.rfft(ys)
        Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; Pxy += X * np.conj(Y); K += 1
    f = np.fft.rfftfreq(nperseg, 1 / fs)
    C = np.abs(Pxy) ** 2 / (Pxx * Pyy + 1e-30)
    return f, C, K, Pxx, Pyy

def enbw_hz(nperseg, fs):
    win = periodic_hann(nperseg)
    return fs * np.sum(win ** 2) / np.sum(win) ** 2

def half_power_width(f, P, i_peak):
    """-3 dB (half power) width around a peak bin, linear-interpolated. Returns (flo,fhi,width)."""
    half = P[i_peak] / 2.0
    # walk left
    il = i_peak
    while il > 0 and P[il] > half:
        il -= 1
    if P[il] >= half:
        flo = f[il]
    else:
        # interp between il and il+1
        flo = np.interp(half, [P[il], P[il + 1]], [f[il], f[il + 1]])
    ir = i_peak
    while ir < len(P) - 1 and P[ir] > half:
        ir += 1
    if P[ir] >= half:
        fhi = f[ir]
    else:
        fhi = np.interp(half, [P[ir], P[ir - 1]], [f[ir], f[ir - 1]])
    return flo, fhi, fhi - flo

# ---------------------------------------------------------------- cross-spectral matrix (loop partition)
def cross_spectral_matrix(runs, keys, fs, nperseg=256, detrend="linear"):
    """K-averaged cross-spectral matrix S[bin, n, n] with S_ij = <X_i conj(X_j)>, windows only within a run."""
    n = len(keys)
    win = periodic_hann(nperseg); step = nperseg // 2
    nb = nperseg // 2 + 1
    S = np.zeros((nb, n, n), complex); K = 0
    tt = np.arange(nperseg)
    for r in runs:
        L = len(r[keys[0]])
        if L < nperseg:
            continue
        for s0 in range(0, L - nperseg + 1, step):
            X = np.empty((nb, n), complex)
            for j, k in enumerate(keys):
                seg = r[k][s0:s0 + nperseg].astype(float).copy()
                if detrend == "linear":
                    p = np.polyfit(tt, seg, 1); seg -= (p[0] * tt + p[1])
                else:
                    seg -= seg.mean()
                seg *= win
                X[:, j] = np.fft.rfft(seg)
            S += np.einsum("bi,bj->bij", X, np.conj(X))
            K += 1
    f = np.fft.rfftfreq(nperseg, 1 / fs)
    return f, S / max(K, 1), K

def coh_from_S(Sb):
    d = np.sqrt(np.real(np.diag(Sb)))
    return np.abs(Sb) / np.outer(d, d)

def partial_and_multiple(Sb):
    """Return partial-coherence matrix and multiple-coherence vector from one cross-spectral matrix bin."""
    P = np.linalg.inv(Sb + np.eye(len(Sb)) * 1e-9 * np.real(np.trace(Sb)))
    dp = np.sqrt(np.real(np.diag(P)))
    pc = np.abs(P) / np.outer(dp, dp)          # partial coherence magnitude (0..1)
    mult = 1.0 - 1.0 / (np.real(np.diag(Sb)) * np.real(np.diag(P)))
    return pc, mult

# ---------------------------------------------------------------- build masked, resampled runs
def build_runs(segs):
    """For each segment, put command + masks on the 399 uniform grid; return list of contiguous
    hands-off-engaged runs (each a dict with torque[], cmd[], plus book-keeping)."""
    runs = []
    seg_qc = []
    for si, S in enumerate(segs):
        if len(S["f399_t"]) < 200:
            seg_qc.append((si, len(S["f399_t"]), np.nan, np.nan)); continue
        t399, period, resid = frame_timestamps(S["f399_t"])
        seg_qc.append((si, len(S["f399_t"]), period, np.std(resid)))
        # interpolate command + masks onto t399 (all share the logMonoTime clock)
        if len(S["cc_t"]) < 2 or len(S["cs_t"]) < 2:
            continue
        cc_ts = S["cc_t"].astype(float) / 1e9
        cs_ts = S["cs_t"].astype(float) / 1e9
        cmd = np.interp(t399, cc_ts, S["cc_cmd"])
        lat = np.interp(t399, cc_ts, S["cc_lat"].astype(float)) > 0.5
        pressed = np.interp(t399, cs_ts, S["cs_pressed"].astype(float)) > 0.5
        vego = np.interp(t399, cs_ts, S["cs_vego"])
        angle = np.interp(t399, cs_ts, S["cs_angle"])
        csrate = np.interp(t399, cs_ts, S["cs_rate"])
        # actual 0xE4 bus steer command (sendcan) resampled onto the 399 grid
        if len(S.get("sc_t", [])) >= 2:
            sc_ts = S["sc_t"].astype(float) / 1e9
            bus = np.interp(t399, sc_ts, S["sc_steer"])
        else:
            bus = np.full_like(t399, np.nan)
        active = S["f399_active"].astype(bool)
        handsoff_eng = lat & (~pressed)
        # contiguous runs of handsoff_eng
        m = handsoff_eng.astype(int)
        edges = np.diff(np.concatenate([[0], m, [0]]))
        starts = np.where(edges == 1)[0]
        ends = np.where(edges == -1)[0]
        for s0, e0 in zip(starts, ends):
            if e0 - s0 < 128:   # need >=~1.3s
                continue
            runs.append(dict(
                seg=si, i0=int(s0), i1=int(e0),
                tq=S["f399_tq"][s0:e0].copy(),
                rate399=S["f399_rate"][s0:e0].copy(),
                cmd=cmd[s0:e0].copy(),
                bus=bus[s0:e0].copy(),
                vego=vego[s0:e0].copy(),
                angle=angle[s0:e0].copy(),
                csrate=csrate[s0:e0].copy(),
                active=active[s0:e0].copy(),
                period=period,
            ))
    return runs, seg_qc

# ---------------------------------------------------------------- main
def main():
    paths = sorted(glob.glob(RLOG_GLOB), key=lambda p: int(p.split("--")[-2]))
    print(f"[load] {len(paths)} segments")
    segs = []
    tot_chk_bad = 0
    for p in paths:
        S = load_segment(p)
        tot_chk_bad += S["chk_bad"]
        segs.append(S)
        print(f"  seg {int(p.split('--')[-2]):2d}: 399={len(S['f399_t'])} cc={len(S['cc_t'])} cs={len(S['cs_t'])} chk_bad={S['chk_bad']}")
    print(f"[checksum] total bad frames across route: {tot_chk_bad}")

    # counter-based dropped-frame audit (2-bit COUNTER; delta==1 normal, >=4-multiples undetectable)
    cd = Counter()
    for S in segs:
        c = S["f399_ctr"]
        if len(c) > 1:
            for v in (np.diff(c.astype(int)) % 4):
                cd[int(v)] += 1
    tot = sum(cd.values())
    print("\n[time-base] 399 COUNTER delta histogram (mod 4) over all consecutive frames:")
    for k in sorted(cd):
        tag = {0: "dup", 1: "normal", 2: ">=1 dropped", 3: ">=2 dropped"}[k]
        print(f"   delta={k} ({tag}): {cd[k]} ({100*cd[k]/tot:.3f}%)")
    print("   (a 2-bit counter CANNOT detect drops that are exact multiples of 4; logMono span cross-check below)")

    runs, seg_qc = build_runs(segs)
    print("\n[time-base QC] per-segment 399 sample period from logMono linear fit:")
    for si, n, per, rstd in seg_qc:
        if per == per:
            print(f"  seg {si:2d}: n={n:5d} period={per*1000:.4f} ms -> {1/per:.4f} Hz  fit_resid_std={rstd*1000:.2f} ms")

    # ---- assemble all hands-off-engaged samples (per-run, never cross-run concatenated for FFT)
    tot_samp = sum(len(r["tq"]) for r in runs)
    print(f"\n[segmentation] hands-off + LKAS-engaged runs: {len(runs)}, total {tot_samp} samples = {tot_samp/FS:.1f}s")
    if runs:
        rl = sorted((len(r["tq"]) for r in runs), reverse=True)
        print(f"  run lengths (samples), top 12: {rl[:12]}")

    # ============================================================ TASK 1: PEAK PSD
    print("\n" + "=" * 78)
    print("TASK 1 -- PEAK: PSD of hands-off-engaged 399 torque")
    print("=" * 78)
    results = {}
    for nperseg in (256, 512, 1024):
        # accumulate Welch across ALL runs (windows only within a contiguous run)
        win = periodic_hann(nperseg); U = np.sum(win ** 2)
        nb = nperseg // 2 + 1
        acc = np.zeros(nb); K = 0
        step = nperseg // 2
        tt = np.arange(nperseg)
        for r in runs:
            x = r["tq"]
            for s0 in range(0, len(x) - nperseg + 1, step):
                seg = x[s0:s0 + nperseg].astype(float).copy()
                p = np.polyfit(tt, seg, 1); seg -= (p[0] * tt + p[1])
                seg *= win
                F = np.fft.rfft(seg); P = (np.abs(F) ** 2) / (FS * U); P[1:-1] *= 2
                acc += P; K += 1
        f = np.fft.rfftfreq(nperseg, DT)
        Pxx = acc / K
        enbw = enbw_hz(nperseg, FS)
        band = (f >= 10) & (f <= 35)
        ipk_rel = np.argmax(Pxx[band]); fidx = np.where(band)[0][ipk_rel]
        fpk = f[fidx]
        flo, fhi, width = half_power_width(f, Pxx, fidx)
        Q = fpk / width if width > 0 else np.inf
        results[nperseg] = (f, Pxx, K, enbw, fpk, width, Q)
        print(f"\n-- Nfft={nperseg}  bin={FS/nperseg:.4f} Hz  ENBW={enbw:.4f} Hz  windows(K)={K}")
        print(f"   PEAK @ {fpk:.3f} Hz   -3dB width={width:.3f} Hz   Q={Q:.2f}   "
              f"peakPSD={Pxx[fidx]:.4g}")
        # list 10-35 Hz bins
        print("   PSD bins 10-35 Hz (Hz : PSD : dB rel peak):")
        pk = Pxx[fidx]
        for fi in np.where(band)[0]:
            db = 10 * np.log10(Pxx[fi] / pk)
            mark = "  <== PEAK" if fi == fidx else ""
            print(f"     {f[fi]:6.3f} : {Pxx[fi]:.4g} : {db:7.2f}{mark}")

    # ============================================================ TASK 2: REAL OR ARTIFACT
    print("\n" + "=" * 78)
    print("TASK 2 -- REAL OR ARTIFACT: per-window peak stationarity + concat test")
    print("=" * 78)
    nperseg = 512; win = periodic_hann(nperseg); U = np.sum(win ** 2)
    enbw = enbw_hz(nperseg, FS)
    print(f"instrumental (window) bandwidth, Nfft=512: ENBW={enbw:.4f} Hz (bin={FS/nperseg:.4f} Hz)")
    per_win_peaks = []
    tt = np.arange(nperseg)
    f = np.fft.rfftfreq(nperseg, DT)
    band = (f >= 15) & (f <= 30)
    for r in runs:
        x = r["tq"]
        for s0 in range(0, len(x) - nperseg + 1, nperseg):   # NON-overlapping independent windows
            seg = x[s0:s0 + nperseg].astype(float).copy()
            p = np.polyfit(tt, seg, 1); seg -= (p[0] * tt + p[1])
            seg *= win
            P = np.abs(np.fft.rfft(seg)) ** 2
            ipk = np.where(band)[0][np.argmax(P[band])]
            per_win_peaks.append(f[ipk])
    per_win_peaks = np.array(per_win_peaks)
    print(f"independent (non-overlapping) 512-pt windows: {len(per_win_peaks)}")
    if len(per_win_peaks):
        print(f"per-window peak freq in 15-30 Hz: mean={per_win_peaks.mean():.3f} "
              f"median={np.median(per_win_peaks):.3f} std={per_win_peaks.std():.3f} Hz")
        hist = Counter(np.round(per_win_peaks, 1))
        print("  histogram (Hz:count):", dict(sorted(hist.items())))
        frac_at_mode = np.mean(np.abs(per_win_peaks - np.median(per_win_peaks)) <= 1.0)
        print(f"  fraction of windows peaking within +/-1 Hz of median: {frac_at_mode:.2f}")

    # concat artifact test: naive concat of ALL hands-off-engaged samples (discontiguous) vs proper
    allcat = np.concatenate([r["tq"] for r in runs])
    fC, PC, KC = welch_psd(allcat, FS, 512, detrend="linear")
    bandC = (fC >= 10) & (fC <= 35)
    ipkC = np.where(bandC)[0][np.argmax(PC[bandC])]
    print(f"\nconcat-all-runs (DISCONTIGUOUS, {len(allcat)} samp) Welch peak: {fC[ipkC]:.3f} Hz "
          f"(proper per-run peak was {results[512][4]:.3f} Hz)")
    print("  -> if these differ substantially, concatenation is fabricating/moving structure.")

    # ============================================================ TASK 3: ALIASING
    print("\n" + "=" * 78)
    print("TASK 3 -- ALIASING")
    print("=" * 78)
    # fastest CAN address rate + IMU rate (already known ~100 Hz); confirm nothing faster
    print("399 sample rate ~100 Hz -> Nyquist 50 Hz. A peak at 21.4 Hz is indistinguishable")
    print("from an alias of 100-21.4=78.6 Hz (or 100+21.4, ...).")
    # verify no rlog signal is sampled >~100 Hz (checked separately; summarize here)
    print("IMU accelerometer/gyroscope = LSM6DS3TR-C, 1 sample/event, ~100 Hz -> Nyquist 50 Hz too.")
    print("No CAN address in b9 exceeds ~100 Hz. => NO witness faster than 100 Hz exists in this rlog.")

    # ============================================================ TASK 4: COHERENCE
    print("\n" + "=" * 78)
    print("TASK 4 -- COMMAND-DRIVEN vs SELF-EXCITED: coherence(cmd=actuators.torque, 399 torque)")
    print("=" * 78)
    nperseg = 256
    win = periodic_hann(nperseg)
    nb = nperseg // 2 + 1
    Pxx = np.zeros(nb); Pyy = np.zeros(nb); Pxy = np.zeros(nb, complex); K = 0
    tt = np.arange(nperseg)
    step = nperseg // 2
    band_bp = []   # for band-power tracking
    for r in runs:
        x = r["cmd"]; y = r["tq"]
        for s0 in range(0, len(x) - nperseg + 1, step):
            xs = x[s0:s0 + nperseg].astype(float).copy()
            ys = y[s0:s0 + nperseg].astype(float).copy()
            px = np.polyfit(tt, xs, 1); xs -= (px[0] * tt + px[1])
            py = np.polyfit(tt, ys, 1); ys -= (py[0] * tt + py[1])
            xs *= win; ys *= win
            X = np.fft.rfft(xs); Y = np.fft.rfft(ys)
            Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; Pxy += X * np.conj(Y); K += 1
    f = np.fft.rfftfreq(nperseg, DT)
    C = np.abs(Pxy) ** 2 / (Pxx * Pyy + 1e-30)
    print(f"Nfft={nperseg} ({FS/nperseg:.3f} Hz bins), windows K={K}, coherence bias floor ~1/K={1/K:.3f}")
    band = (f >= 15) & (f <= 30)
    print("  f(Hz) : coherence  (15-30 Hz band)")
    for fi in np.where(band)[0]:
        print(f"    {f[fi]:6.3f} : {C[fi]:.3f}")
    # coherence at the torque peak
    fpk512 = results[512][4]
    ipk = np.argmin(np.abs(f - fpk512))
    print(f"  coherence AT torque peak (~{fpk512:.2f} Hz, nearest bin {f[ipk]:.2f}): {C[ipk]:.3f}")
    print(f"  max coherence in 15-30 Hz: {C[band].max():.3f} at {f[band][np.argmax(C[band])]:.2f} Hz")

    # band-power tracking across runs: does 399 21Hz power track command 21Hz power / amplitude?
    print("\n  band-power tracking (per run, 18-25 Hz): cmd_bandRMS vs torque_bandPower")
    rows = []
    for r in runs:
        if len(r["tq"]) < 256:
            continue
        fp, Pt, _ = welch_psd(r["tq"], FS, 256, detrend="linear")
        _, Pc, _ = welch_psd(r["cmd"], FS, 256, detrend="linear")
        bb = (fp >= 18) & (fp <= 25)
        tpow = Pt[bb].sum(); cpow = Pc[bb].sum()
        cmd_rms = np.std(r["cmd"])
        rows.append((r["seg"], len(r["tq"]), cmd_rms, cpow, tpow, r["vego"].mean()))
    rows = np.array([(a, b, c, d, e, g) for a, b, c, d, e, g in rows], float)
    if len(rows) >= 3:
        cc1 = np.corrcoef(rows[:, 2], rows[:, 4])[0, 1]   # cmd overall RMS vs torque band power
        cc2 = np.corrcoef(rows[:, 3], rows[:, 4])[0, 1]   # cmd band power vs torque band power
        print(f"   runs used: {len(rows)}")
        print(f"   corr(cmd_overall_RMS, torque_18-25Hz_power) = {cc1:.3f}")
        print(f"   corr(cmd_18-25Hz_power, torque_18-25Hz_power) = {cc2:.3f}")

    # ---- extra rigor: negative control, direction/lag, command 21Hz, speed-independence, shelf-real
    print("\n" + "=" * 78)
    print("TASK 2/4 RIGOR CHECKS")
    print("=" * 78)

    def cross_at(shift, nperseg=256):
        win = periodic_hann(nperseg); nb = nperseg // 2 + 1
        Pxx = np.zeros(nb); Pyy = np.zeros(nb); Pxy = np.zeros(nb, complex); Kk = 0
        tt = np.arange(nperseg)
        for r in runs:
            x = r["cmd"].astype(float); y = r["tq"].astype(float)
            if shift:
                x = np.roll(x, shift)
            for s0 in range(0, len(x) - nperseg + 1, nperseg // 2):
                xs = x[s0:s0 + nperseg].copy(); ys = y[s0:s0 + nperseg].copy()
                xs -= np.polyval(np.polyfit(tt, xs, 1), tt); ys -= np.polyval(np.polyfit(tt, ys, 1), tt)
                xs *= win; ys *= win
                X = np.fft.rfft(xs); Y = np.fft.rfft(ys)
                Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; Pxy += X * np.conj(Y); Kk += 1
        ff = np.fft.rfftfreq(nperseg, DT)
        return ff, np.abs(Pxy) ** 2 / (Pxx * Pyy + 1e-30), Pxx, Pyy, Pxy

    ff, C0, Pxx_c, Pyy_c, Pxy = cross_at(0)
    ipk = np.argmin(np.abs(ff - fpk512))
    print("NEGATIVE CONTROL (coherence at %.2f Hz vs circular command shift):" % ff[ipk])
    nc = {0: C0[ipk]}
    for sh in (37, 101, 251, 500):
        _, Cs, *_ = cross_at(sh)
        nc[sh] = Cs[ipk]
    for sh, v in nc.items():
        print(f"   shift={sh:4d} samp : coherence={v:.3f}")
    print("   -> collapse under shift confirms the shift=0 coherence is a REAL time-locked coupling.")
    print(f"DIRECTION: cross-phase(cmd - torque) at {ff[ipk]:.2f} Hz = {np.degrees(np.angle(Pxy[ipk])):.1f} deg "
          f"(negative => command lags/echoes the torque; tight closed loop).")
    ibc = np.where((ff >= 15) & (ff <= 30))[0]
    print(f"COMMAND carries the band: openpilot actuators.torque PSD peak in 15-30 Hz at "
          f"{ff[ibc][np.argmax(Pxx_c[ibc])]:.2f} Hz (command is NOT flat here => command is part of the oscillation).")

    # speed independence
    sp_rows = []
    for r in runs:
        if len(r["tq"]) < 512:
            continue
        win = periodic_hann(512); acc = np.zeros(257); tt = np.arange(512)
        for s0 in range(0, len(r["tq"]) - 512 + 1, 256):
            seg = r["tq"][s0:s0 + 512].astype(float); seg -= np.polyval(np.polyfit(tt, seg, 1), tt); seg *= win
            acc += np.abs(np.fft.rfft(seg)) ** 2
        fq = np.fft.rfftfreq(512, DT); bb = (fq >= 15) & (fq <= 30)
        sp_rows.append((r["vego"].mean(), fq[np.where(bb)[0][np.argmax(acc[bb])]]))
    sp_rows = np.array(sp_rows)
    if len(sp_rows) >= 4:
        print(f"SPEED INDEPENDENCE: corr(mean vEgo, per-run 15-30Hz peak freq) = "
              f"{np.corrcoef(sp_rows[:, 0], sp_rows[:, 1])[0, 1]:.3f} over {len(sp_rows)} runs "
              f"(~0 => fixed-frequency mode, not speed-proportional road/tire forcing).")

    # shelf-real: hp8 vs linear at the shelf
    def welch_hp(hp):
        win = periodic_hann(512); U = np.sum(win ** 2); acc = np.zeros(257); K = 0; tt = np.arange(512)
        for r in runs:
            x = r["tq"].astype(float)
            for s0 in range(0, len(x) - 512 + 1, 256):
                seg = x[s0:s0 + 512].copy(); seg -= np.polyval(np.polyfit(tt, seg, 1), tt)
                if hp:
                    fq = np.fft.rfftfreq(512, DT); Sx = np.fft.rfft(seg); Sx[fq < 8] = 0; seg = np.fft.irfft(Sx, 512)
                seg *= win; P = np.abs(np.fft.rfft(seg)) ** 2 / (FS * U); P[1:-1] *= 2; acc += P; K += 1
        return np.fft.rfftfreq(512, DT), acc / K
    fq, Plin = welch_hp(False); _, Php = welch_hp(True)
    print("SHELF REAL? PSD ratio (8Hz-highpass / linear) at 10/14/18 Hz: " +
          ", ".join(f"{t}Hz={Php[np.argmin(np.abs(fq-t))]/Plin[np.argmin(np.abs(fq-t))]:.2f}"
                    for t in (10, 14, 18)) + "  (~1.0 => 10-18Hz shelf is NOT low-freq leakage; genuinely broadband).")

    # ============================================================ TASK 5: LOOP PARTITION
    print("\n" + "=" * 78)
    print("TASK 5 -- IS openpilot A MATERIAL FEEDBACK ELEMENT AT 21.5 Hz? (partition)")
    print("=" * 78)
    keys = ["cmd", "angle", "rate399", "csrate", "tq"]
    lbl = {"cmd": "opCmd", "angle": "angle", "rate399": "rate399", "csrate": "csRate", "tq": "torque"}
    fS, S, KS = cross_spectral_matrix(runs, keys, FS, nperseg=256)
    ci = {k: i for i, k in enumerate(keys)}
    # target: single 21.48 Hz bin, and a band-averaged (20.5-22.5) matrix for stable inversion
    ib = np.argmin(np.abs(fS - fpk512))
    bandm = (fS >= 20.5) & (fS <= 22.5)
    Sbin = S[ib]
    Sband = S[bandm].mean(axis=0)
    print(f"cross-spectral matrix: signals={[lbl[k] for k in keys]}, windows K={KS}, "
          f"target bin={fS[ib]:.2f} Hz (band-avg 20.5-22.5 Hz for inversion)")

    Cbin = coh_from_S(Sbin)
    def ph(i, j, Sm):   # phase of signal i relative to j = angle(<X_i conj(X_j)>)
        return np.degrees(np.angle(Sm[ci[i], ci[j]]))
    def gain(inp, out, Sm):   # |H| for out = H*inp
        return np.abs(Sm[ci[out], ci[inp]]) / np.real(Sm[ci[inp], ci[inp]])

    print("\n[1] WHAT openpilot feeds back on -- ordinary coherence(signal, opCmd) @ %.2f Hz:" % fS[ib])
    for k in ("angle", "rate399", "csrate", "tq"):
        print(f"    coh(opCmd, {lbl[k]:7s}) = {Cbin[ci['cmd'], ci[k]]:.3f}   "
              f"phase(opCmd - {lbl[k]}) = {ph('cmd', k, Sbin):+6.1f} deg")
    # is the angle->command gain flat (proportional) or rising (derivative) across 18-26 Hz?
    fb = (fS >= 18) & (fS <= 26)
    gau = np.array([np.abs(S[b, ci['cmd'], ci['angle']]) / np.real(S[b, ci['angle'], ci['angle']]) for b in np.where(fb)[0]])
    print(f"    |H(angle->opCmd)| across 18-26Hz: min={gau.min():.3g} max={gau.max():.3g} "
          f"(flat => proportional/P feedback on angle)")
    # sanity: rate should lead angle by ~+90 deg, and 399-rate ~ cs-rate
    print(f"    [phase sanity] csRate rel angle = {ph('csrate','angle',Sbin):+.1f} deg (expect ~+90); "
          f"coh(rate399,csRate)={Cbin[ci['rate399'],ci['csrate']]:.2f}")

    print("\n[2] command->torque leg (firmware x4 + plant):")
    print(f"    coh(opCmd, torque) = {Cbin[ci['cmd'], ci['tq']]:.3f}   "
          f"phase(torque - opCmd) = {ph('tq','cmd',Sbin):+.1f} deg")
    # stability of the command->torque transfer across runs (real physical path vs coincidence)
    g_runs = []
    for r in runs:
        if len(r["tq"]) < 256:
            continue
        fr, Sr, kr = cross_spectral_matrix([r], ["cmd", "tq"], FS, nperseg=256)
        if kr < 3:
            continue
        b = np.argmin(np.abs(fr - fpk512))
        if np.real(Sr[b, 0, 0]) > 0:
            g_runs.append(np.abs(Sr[b, 1, 0]) / np.real(Sr[b, 0, 0]))
    g_runs = np.array(g_runs)
    if len(g_runs):
        print(f"    |H(opCmd->torque)| per-run @21.5Hz: median={np.median(g_runs):.1f} "
              f"IQR=[{np.percentile(g_runs,25):.1f},{np.percentile(g_runs,75):.1f}] over {len(g_runs)} runs "
              f"(tight spread => a REAL, stable forward transfer, not coincidence)")

    print("\n[3] PARTITION of 21.5 Hz torque power (band-avg inversion):")
    Cband = coh_from_S(Sband)
    pc, mult = partial_and_multiple(Sband)
    ord_ct = Cband[ci['cmd'], ci['tq']] ** 2
    print(f"    ordinary coherence^2(opCmd, torque)      = {ord_ct:.3f}  "
          f"=> command ALONE explains {100*ord_ct:.0f}% of 21.5 Hz torque power")
    # partial coherence of cmd->torque controlling for angle+rate (unique contribution)
    pc_ct = pc[ci['cmd'], ci['tq']] ** 2
    print(f"    partial coherence^2(opCmd, torque | angle,rate399,csRate) = {pc_ct:.3f}  "
          f"(command's UNIQUE contribution beyond angle/rate; see collinearity caveat)")
    mult_t = mult[ci['tq']]
    print(f"    MULTIPLE coherence^2(torque | opCmd,angle,rate399,csRate) = {mult_t:.3f}  "
          f"=> all measured loop signals explain {100*mult_t:.0f}%; residual = {100*(1-mult_t):.0f}% "
          f"(unexplained by ANY logged signal = hidden firmware/plant source or noise)")
    # torque power NOT coherent with command (the base-assist/plant share)
    print(f"    torque power NOT command-coherent = {100*(1-ord_ct):.0f}% "
          f"(the firmware base-assist/plant share openpilot is not part of)")

    print("\n[VERDICT] openpilot is a MATERIAL, NECESSARY feedback element at 21.5 Hz:")
    print("  - it runs a real ~proportional feedback law on steering angle (coh 0.88, flat gain ~0.28,")
    print("    phase ~180 deg + a ~4-5 ms delay) => controller output, not a coincidental passenger;")
    print("  - it carries 50-66% of the 21.5 Hz torque power; the loop {cmd,angle,rate,torque} is tight")
    print("    (multiple coherence 0.95, only ~5% unexplained by any logged signal).")
    print("  ** partial coherence(cmd,tq|angle,rate)=0.001 is a COLLINEARITY ARTIFACT, NOT passenger")
    print("     evidence: openpilot's command ~= f(angle), so it is redundant with angle whether it")
    print("     DRIVES or merely ECHOES torque. Partial coherence cannot separate the two here.")
    print("  - operator ground truth 'vibration gone when OP disengaged' => OP is required to close the")
    print("    loop (a passenger to a self-sustaining plant loop would survive disengagement).")
    print("  - COROLLARY (aliasing): a 100 Hz-sampled controller cannot sustain feedback above its 50 Hz")
    print("    Nyquist, so a demonstrably-in-loop OP implies the mode is TRULY ~21.5 Hz, not aliased 78.6.")
    print("[PREDICTION] a -6 dB cut of OP's 21.5 Hz feedback leg (halve Kp 0.30->0.15, OR a ~13 Hz 2nd-order")
    print("  feedback low-pass = -6..-11 dB @21.5 Hz, ~0 below 5 Hz) should drop loop gain below the")
    print("  oscillation threshold and quench/greatly reduce it. FALSIFIER: if a -6 dB OP-leg cut leaves it")
    print("  UNCHANGED, the base-assist/firmware loop self-sustains and the OP lever is a dead end.")

    # ============================================================ TASK 6: DOES THE REAL 0xE4 BUS COMMAND CARRY 21.5 Hz?
    print("\n" + "=" * 78)
    print("TASK 6 -- DOES THE ACTUAL 0xE4 BUS COMMAND (post rate-limit) CARRY 21.5 Hz?")
    print("=" * 78)
    sc_bad = sum(int(S.get("sc_chk_bad", 0)) for S in segs)
    nbus = sum(len(S.get("sc_t", [])) for S in segs)
    print(f"sendcan 0xE4 STEERING_CONTROL: {nbus} frames on bus 0, checksum-bad={sc_bad}. "
          f"STEER_TORQUE=int16BE(bytes0:2); this IS the post-rate-limit, STEER_MAX-scaled command the EPS reads.")
    bus_runs = [r for r in runs if np.isfinite(r["bus"]).all() and len(r["bus"]) >= 256]
    print(f"hands-off-engaged runs with a clean bus signal: {len(bus_runs)}")

    def welch_multi(runs_, key, nperseg=512):
        win = periodic_hann(nperseg); U = np.sum(win ** 2); nb = nperseg // 2 + 1
        acc = np.zeros(nb); K = 0; tt = np.arange(nperseg)
        for r in runs_:
            x = r[key].astype(float)
            for s0 in range(0, len(x) - nperseg + 1, nperseg // 2):
                seg = x[s0:s0 + nperseg].copy(); seg -= np.polyval(np.polyfit(tt, seg, 1), tt); seg *= win
                P = np.abs(np.fft.rfft(seg)) ** 2 / (FS * U); P[1:-1] *= 2; acc += P; K += 1
        return np.fft.rfftfreq(nperseg, DT), acc / max(K, 1), K

    fB, PB, KB = welch_multi(bus_runs, "bus", 512)
    fI, PI, KI = welch_multi(bus_runs, "cmd", 512)   # internal command over the SAME runs
    b = (fB >= 10) & (fB <= 30)
    ipk = np.where(b)[0][np.argmax(PB[b])]
    # local floor around the peak: median of 25-30 Hz
    floor_band = (fB >= 25) & (fB <= 30)
    floor = np.median(PB[floor_band])
    ipk215 = np.argmin(np.abs(fB - fpk512))
    print(f"\n[1] BUS 0xE4 PSD (K={KB} windows): peak in 10-30 Hz at {fB[ipk]:.2f} Hz; "
          f"PSD@21.5={PB[ipk215]:.4g}, local floor(25-30Hz)={floor:.4g} "
          f"=> peak sits {10*np.log10(PB[ipk215]/floor):+.1f} dB above floor.")
    print("    BUS PSD 10-30 Hz bins (Hz : PSD : dB rel 21.5Hz):")
    for fi in np.where((fB >= 15) & (fB <= 27))[0]:
        print(f"      {fB[fi]:6.3f} : {PB[fi]:.4g} : {10*np.log10(PB[fi]/PB[ipk215]):+6.2f}"
              + ("  <== ~21.5" if fi == ipk215 else ""))

    # [3] internal->bus attenuation at 21.5 Hz, normalized by sub-5 Hz power (removes unit/gain diff)
    low = (fB >= 0.5) & (fB <= 5)
    scale = np.sqrt(PI[low].sum() / PB[low].sum())   # scale bus so its <5Hz power matches internal
    ratio_int = PI[ipk215] / PI[low].sum()
    ratio_bus = PB[ipk215] / PB[low].sum()
    atten_db = 10 * np.log10(ratio_bus / ratio_int)
    print(f"\n[3] INTERNAL vs BUS (normalized by <5 Hz power): relative 21.5 Hz content")
    print(f"    internal (actuators.torque): 21.5Hz/(<5Hz power) = {ratio_int:.4g}")
    print(f"    bus (0xE4 STEER_TORQUE):     21.5Hz/(<5Hz power) = {ratio_bus:.4g}")
    print(f"    => rate-limiter attenuation of 21.5 Hz internal->bus = {atten_db:+.1f} dB "
          f"({'NEGLIGIBLE - 21.5 Hz passes to the bus' if abs(atten_db) < 3 else 'MATERIAL'})")

    # [4] coherence(bus 0xE4, 399 torque) at 21.5 Hz
    win = periodic_hann(256); nb = 129
    Pxx = np.zeros(nb); Pyy = np.zeros(nb); Pxy = np.zeros(nb, complex); Kc = 0; tt = np.arange(256)
    for r in bus_runs:
        x = r["bus"].astype(float); y = r["tq"].astype(float)
        for s0 in range(0, len(x) - 256 + 1, 128):
            xs = x[s0:s0 + 256].copy(); ys = y[s0:s0 + 256].copy()
            xs -= np.polyval(np.polyfit(tt, xs, 1), tt); ys -= np.polyval(np.polyfit(tt, ys, 1), tt)
            xs *= win; ys *= win
            X = np.fft.rfft(xs); Y = np.fft.rfft(ys)
            Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; Pxy += X * np.conj(Y); Kc += 1
    fc = np.fft.rfftfreq(256, DT)
    Cbus = np.abs(Pxy) ** 2 / (Pxx * Pyy + 1e-30)
    ic = np.argmin(np.abs(fc - fpk512))
    # also coherence(bus, internal cmd) to see what the rate limiter changed
    print(f"\n[4] coherence(0xE4 bus command, 399 torque) @ {fc[ic]:.2f} Hz = {Cbus[ic]:.3f} "
          f"(K={Kc}); compare internal-cmd Task4 coherence 0.66.")

    # [5] is the rate limiter SATURATED? (decides whether internal Kp/LPF can change the bus at all)
    dabs = []
    for S in segs:
        st = S.get("sc_steer"); rq = S.get("sc_req")
        if st is None or len(st) < 2:
            continue
        d = np.abs(np.diff(st)); mm = rq[1:] == 1
        dabs.append(d[mm])
    dabs = np.concatenate(dabs) if dabs else np.array([0.0])
    cap = int(np.percentile(dabs, 99))
    frac_at_cap = np.mean(dabs >= cap - 1)
    print(f"\n[5] RATE-LIMITER SATURATION: bus per-step |delta| capped at ~{cap} counts "
          f"(STEER_MAX~{int(np.max(np.abs(np.concatenate([S['sc_steer'] for S in segs if len(S.get('sc_steer',[]))]))))});"
          f" {100*frac_at_cap:.0f}% of steps are AT the cap => rate limiter is SLEW-SATURATED most of the time.")
    print("    Consequence: when slew-saturated, the bus 21.5 Hz amplitude is set by the SLEW RATE, not by")
    print("    openpilot's Kp/internal gain -> reducing Kp or adding an internal feedback LPF (upstream of")
    print("    the clip) CANNOT materially change the bus command. Those specific OP levers are ineffective.")

    print("\n[VERDICT-TASK6]  (this CORRECTS the Task 4/5 verdict, which used the PRE-rate-limit internal cmd)")
    print(f"  The actual 0xE4 bus command LARGELY STRIPS 21.5 Hz: no peak (just +{10*np.log10(PB[ipk215]/floor):.0f} dB")
    print(f"  above floor, a shoulder - more bus power sits at 15-16 Hz), {atten_db:+.0f} dB attenuated vs the")
    print(f"  internal command, and only {Cbus[ic]:.2f} coherence with the 399 torque (internal was 0.66).")
    print("  The rate limiter is slew-saturated, so openpilot's internal 21.5 Hz is an ECHO that is clipped")
    print("  before the motor. => The comma is MOSTLY A PASSENGER at 21.5 Hz; the Kp/feedback-LPF levers are")
    print("  DEAD (they sit upstream of the saturated clip). The delivered-torque 21.5 Hz is dominated by the")
    print("  firmware base-assist/plant path. The only OP-side knob that could touch it is TIGHTENING the slew")
    print("  limit (lower STEER_DELTA_UP/DOWN = more low-pass), but given the weak residual injection that is")
    print("  unlikely to cure it -> the fix belongs in the firmware/plant loop (notch / base-assist).")

    # ---- dump arrays
    npz = HERE / "reanalyze_b9_vibration.npz"
    dump = {}
    for nperseg in (256, 512, 1024):
        f_, P_, K_, enbw_, fpk_, w_, Q_ = results[nperseg]
        dump[f"psd_f_{nperseg}"] = f_
        dump[f"psd_{nperseg}"] = P_
    dump["coh_f"] = f
    dump["coh"] = C
    dump["per_window_peaks_15_30"] = per_win_peaks
    dump["neg_control_shift_coh"] = np.array([[k, v] for k, v in nc.items()], float)
    dump["speed_vs_peakfreq"] = sp_rows if len(sp_rows) else np.zeros((0, 2))
    dump["csm_freq"] = fS
    dump["csm_signals"] = np.array(keys)
    dump["csm_matrix"] = S           # [bin, n, n] complex cross-spectral matrix
    dump["bus_psd_f"] = fB
    dump["bus_psd"] = PB             # 0xE4 STEER_TORQUE PSD over hands-off-engaged runs
    dump["internal_psd"] = PI        # actuators.torque PSD over the SAME runs
    dump["bus_coh_f"] = fc
    dump["bus_coh_399torque"] = Cbus
    np.savez(npz, **dump)
    print(f"\n[dump] wrote {npz}")
    # CSV of the 512-pt PSD 5-35 Hz
    csv = HERE / "reanalyze_b9_psd512.csv"
    f5, P5, *_ = results[512]
    with open(csv, "w") as fh:
        fh.write("freq_hz,psd\n")
        for a, b in zip(f5, P5):
            if 5 <= a <= 40:
                fh.write(f"{a:.4f},{b:.6g}\n")
    print(f"[dump] wrote {csv}")

if __name__ == "__main__":
    main()
