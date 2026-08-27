#!/usr/bin/env python3
r"""
studies/spectra/analyze_manual_vibration.py -- characterize the ~21 Hz vibration on the MANUAL drive
(aa5b3e0c01, operator says V49P; telemetry shows it drives as V38 = 4x gain, cave inert).

Fresh dataset, independent of route b9. Reuses the b9 method (Honda-checksum-validated 399 decode,
per-segment logMono linear time base, hand-rolled Welch). Reports:
  1. hands-off + LKAS-engaged 399-torque PSD (peak, -3 dB width, Q, shelf)
  2. per-window peak stationarity (real mode vs artifact)
  3. speed independence (fixed-frequency mode vs road/tire forcing)
  4. does the 0xE4 bus command carry 21.5 Hz? (comma passenger check, fresh data)
"""
import sys, glob, os
from pathlib import Path
from collections import Counter
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

GLOB = str(HERE / "rlogs" / "manual" / "*" / "*" / "rlog.zst")
FS = 100.0; DT = 1.0 / FS


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


def load_segment(path):
    o = dict(t=[], tq=[], status=[], active=[], ctr=[],
             cc_t=[], cc_lat=[], cc_cmd=[], cs_t=[], cs_pressed=[], cs_vego=[],
             sc_t=[], sc_steer=[], sc_req=[], chk_bad=0, sc_chk_bad=0)
    for evt in read_messages(path):
        try:
            w = evt.which()
        except Exception:
            continue
        t = evt.logMonoTime
        if w == "can":
            for fr in evt.can:
                if fr.address == 399 and fr.src == 1 and len(fr.dat) == 7:
                    d = bytes(fr.dat)
                    if honda_checksum(399, d) != (d[6] & 0xF):
                        o["chk_bad"] += 1; continue
                    o["t"].append(t); o["tq"].append(-s16be(d[0], d[1]))
                    o["status"].append((d[4] >> 4) & 0xF); o["active"].append((d[4] >> 3) & 1)
                    o["ctr"].append((d[6] >> 4) & 0x3)
                elif fr.address == 228 and fr.src == 0 and len(fr.dat) == 5:
                    d = bytes(fr.dat)
                    if honda_checksum(228, d) != (d[4] & 0xF):
                        o["sc_chk_bad"] += 1; continue
                    o["sc_t"].append(t); o["sc_steer"].append(s16be(d[0], d[1]))
                    o["sc_req"].append((d[2] >> 7) & 1)
        elif w == "carControl":
            o["cc_t"].append(t); o["cc_lat"].append(1 if evt.carControl.latActive else 0)
            o["cc_cmd"].append(float(evt.carControl.actuators.torque))
        elif w == "carState":
            o["cs_t"].append(t); o["cs_pressed"].append(1 if evt.carState.steeringPressed else 0)
            o["cs_vego"].append(float(evt.carState.vEgo))
    for k in o:
        if isinstance(o[k], list):
            o[k] = np.array(o[k], float if k not in ("t", "cc_t", "cs_t", "sc_t") else np.int64)
    return o


def frame_ts(lm):
    idx = np.arange(len(lm)); lm_s = lm.astype(float) / 1e9
    b, a = np.polyfit(idx, lm_s, 1)
    return a + b * idx, b


def hann(n):
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / n)


def welch(runs, key, nperseg=512):
    win = hann(nperseg); U = np.sum(win ** 2); nb = nperseg // 2 + 1
    acc = np.zeros(nb); K = 0; tt = np.arange(nperseg)
    for r in runs:
        x = r[key].astype(float)
        for s0 in range(0, len(x) - nperseg + 1, nperseg // 2):
            seg = x[s0:s0 + nperseg].copy(); seg -= np.polyval(np.polyfit(tt, seg, 1), tt); seg *= win
            P = np.abs(np.fft.rfft(seg)) ** 2 / (FS * U); P[1:-1] *= 2; acc += P; K += 1
    return np.fft.rfftfreq(nperseg, DT), acc / max(K, 1), K


def hp_width(f, P, ip):
    half = P[ip] / 2.0
    il = ip
    while il > 0 and P[il] > half:
        il -= 1
    flo = f[il] if P[il] >= half else np.interp(half, [P[il], P[il + 1]], [f[il], f[il + 1]])
    ir = ip
    while ir < len(P) - 1 and P[ir] > half:
        ir += 1
    fhi = f[ir] if P[ir] >= half else np.interp(half, [P[ir], P[ir - 1]], [f[ir], f[ir - 1]])
    return fhi - flo


def main():
    paths = sorted(glob.glob(GLOB))
    print(f"[load] {len(paths)} manual segments")
    segs = [load_segment(p) for p in paths]
    tot_bad = sum(int(s["chk_bad"]) for s in segs)
    n399 = sum(len(s["t"]) for s in segs)
    print(f"[399] {n399} checksum-valid frames, {tot_bad} bad")

    runs = []
    for si, S in enumerate(segs):
        if len(S["t"]) < 200 or len(S["cc_t"]) < 2 or len(S["cs_t"]) < 2:
            continue
        t399, per = frame_ts(S["t"])
        cc_ts = S["cc_t"].astype(float) / 1e9; cs_ts = S["cs_t"].astype(float) / 1e9
        cmd = np.interp(t399, cc_ts, S["cc_cmd"])
        lat = np.interp(t399, cc_ts, S["cc_lat"]) > 0.5
        pressed = np.interp(t399, cs_ts, S["cs_pressed"]) > 0.5
        vego = np.interp(t399, cs_ts, S["cs_vego"])
        if len(S["sc_t"]) >= 2:
            bus = np.interp(t399, S["sc_t"].astype(float) / 1e9, S["sc_steer"])
        else:
            bus = np.full_like(t399, np.nan)
        ho = lat & (~pressed)
        m = ho.astype(int); edges = np.diff(np.concatenate([[0], m, [0]]))
        for s0, e0 in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            if e0 - s0 < 128:
                continue
            runs.append(dict(seg=si, tq=S["tq"][s0:e0].copy(), cmd=cmd[s0:e0].copy(),
                             bus=bus[s0:e0].copy(), vego=vego[s0:e0].copy(), period=per))
    tot = sum(len(r["tq"]) for r in runs)
    print(f"[seg] hands-off + LKAS-engaged runs: {len(runs)}, {tot} samp = {tot/FS:.1f}s")
    print(f"  per-seg sample period(ms): " +
          ", ".join(f"{frame_ts(s['t'])[1]*1000:.2f}" for s in segs if len(s['t']) > 200))
    if not runs:
        print("  NO hands-off engaged runs -> cannot characterize. Check drive.")
        return

    # ---- TASK 1: PSD
    print("\n" + "=" * 74 + "\nTASK 1 -- hands-off-engaged 399-torque PSD\n" + "=" * 74)
    for nperseg in (256, 512):
        f, P, K = welch(runs, "tq", nperseg)
        band = (f >= 10) & (f <= 35)
        ip = np.where(band)[0][np.argmax(P[band])]
        w = hp_width(f, P, ip); Q = f[ip] / w if w > 0 else np.inf
        # shelf: dB of peak above the 10 Hz level
        i10 = np.argmin(np.abs(f - 10)); shelf_db = 10 * np.log10(P[ip] / P[i10])
        print(f"  Nfft={nperseg} bin={FS/nperseg:.3f}Hz K={K}: PEAK {f[ip]:.2f} Hz, "
              f"-3dB width {w:.2f} Hz, Q={Q:.1f}, {shelf_db:+.1f} dB above 10 Hz level")
        if nperseg == 512:
            print("    10-30 Hz bins (Hz:dB rel peak):", ", ".join(
                f"{f[i]:.1f}:{10*np.log10(P[i]/P[ip]):+.1f}" for i in np.where((f >= 10) & (f <= 30))[0]))
            fpk = f[ip]

    # ---- TASK 2: per-window stationarity
    print("\n" + "=" * 74 + "\nTASK 2 -- per-window peak stationarity (real mode vs artifact)\n" + "=" * 74)
    nperseg = 512; win = hann(nperseg); tt = np.arange(nperseg)
    f = np.fft.rfftfreq(nperseg, DT); band = (f >= 15) & (f <= 30)
    pk = []
    for r in runs:
        x = r["tq"]
        for s0 in range(0, len(x) - nperseg + 1, nperseg):
            seg = x[s0:s0 + nperseg].astype(float).copy(); seg -= np.polyval(np.polyfit(tt, seg, 1), tt); seg *= win
            P = np.abs(np.fft.rfft(seg)) ** 2
            pk.append(f[np.where(band)[0][np.argmax(P[band])]])
    pk = np.array(pk)
    if len(pk):
        print(f"  {len(pk)} independent 512-pt windows: peak in 15-30 Hz "
              f"mean={pk.mean():.2f} median={np.median(pk):.2f} std={pk.std():.2f} Hz")
        print(f"  within +/-1 Hz of median: {100*np.mean(np.abs(pk-np.median(pk))<=1):.0f}%  "
              f"(high => a real narrowish mode; low/scattered => broadband)")

    # ---- TASK 3: speed independence
    print("\n" + "=" * 74 + "\nTASK 3 -- speed independence\n" + "=" * 74)
    rows = []
    for r in runs:
        if len(r["tq"]) < 512:
            continue
        f, P, K = welch([r], "tq", 512)
        bb = (f >= 15) & (f <= 30)
        rows.append((r["vego"].mean(), f[np.where(bb)[0][np.argmax(P[bb])]]))
    rows = np.array(rows)
    if len(rows) >= 4:
        cc = np.corrcoef(rows[:, 0], rows[:, 1])[0, 1]
        print(f"  corr(mean vEgo, per-run 15-30Hz peak freq) = {cc:+.3f} over {len(rows)} runs")
        print(f"  vEgo range {rows[:,0].min():.1f}-{rows[:,0].max():.1f} m/s; "
              f"peak freq range {rows[:,1].min():.1f}-{rows[:,1].max():.1f} Hz")
        print("  (~0 corr + speed range present => FIXED-frequency mode, not speed-proportional road/tire forcing)")

    # ---- TASK 4: does the 0xE4 bus carry 21.5 Hz? (comma passenger)
    print("\n" + "=" * 74 + "\nTASK 4 -- 0xE4 bus command 21.5 Hz content (comma passenger check)\n" + "=" * 74)
    bus_runs = [r for r in runs if np.isfinite(r["bus"]).all() and len(r["bus"]) >= 256]
    print(f"  runs with clean bus signal: {len(bus_runs)}")
    if bus_runs:
        fB, PB, KB = welch(bus_runs, "bus", 512)
        fI, PI, KI = welch(bus_runs, "cmd", 512)
        low = (fB >= 0.5) & (fB <= 5)
        i215 = np.argmin(np.abs(fB - fpk))
        ratio_i = PI[i215] / PI[low].sum(); ratio_b = PB[i215] / PB[low].sum()
        atten = 10 * np.log10(ratio_b / ratio_i)
        floor = np.median(PB[(fB >= 25) & (fB <= 30)])
        print(f"  bus 0xE4 PSD @ {fB[i215]:.1f} Hz sits {10*np.log10(PB[i215]/floor):+.1f} dB above 25-30Hz floor")
        print(f"  internal->bus 21.5Hz attenuation = {atten:+.1f} dB "
              f"({'strips it (comma passenger)' if atten < -3 else 'passes (comma in loop)'})")
        # rate-limiter saturation
        dabs = []
        for S in segs:
            st = S.get("sc_steer")
            if st is None or len(st) < 2:
                continue
            rq = S["sc_req"]; d = np.abs(np.diff(st)); dabs.append(d[rq[1:] == 1])
        dabs = np.concatenate([x for x in dabs if len(x)]) if dabs else np.array([0.0])
        cap = int(np.percentile(dabs, 99)) if len(dabs) else 0
        frac = np.mean(dabs >= cap - 1) if len(dabs) else 0
        print(f"  bus per-step |delta| cap ~{cap}; {100*frac:.0f}% of active steps AT cap "
              f"({'SLEW-SATURATED (Kp/LPF upstream cannot change bus)' if frac > 0.3 else 'not saturated'})")


if __name__ == "__main__":
    main()
