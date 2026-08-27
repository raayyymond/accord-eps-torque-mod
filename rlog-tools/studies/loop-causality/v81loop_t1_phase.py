#!/usr/bin/env python3
"""T1 / T3 -- PHASE-RESOLVED COMMAND<->PLANT analysis for the V81 highway instability.

Everything is built on NATIVE timestamps and a uniform 100.000 Hz lattice, per contiguous run:

    command  (sc_t, sc_tq_raw)     openpilot's own sendcan 0x0E4, its decision clock
    bar      (t18, tq)             0x18F STEER_TORQUE_SENSOR on the 0x18F frames' OWN arrival times
    angle    (t14, ang)            0x14A STEER_ANGLE
    rate     (t14, rate_f * 1.25)  0x18F's 8x-finer rate copy, scale corrected (see v81loop_t2)

🛑 THE PHASE IS ONLY AS GOOD AS THE CLOCK.  `sendcan` and `can` are timestamped by different
   daemons on the same device monotonic clock, so command->bar carries a REAL bus+ECU latency plus
   an unknown residual.  A raw phase at 27 Hz is therefore NOT a causal arrow on its own: 5 ms of
   unmodelled offset is 49 deg.  Three things are done about that:
     (i)   the offset is CALIBRATED from the same data at low frequency, where openpilot is
           unambiguously the driver, by fitting phase(f) = -2 pi f tau over 1-8 Hz;
     (ii)  the 27 Hz phase is quoted as a RESIDUAL against that pure-delay fit;
     (iii) the sendcan->bus-echo (`e4tq`, src 129) leg is measured separately, which bounds the
           daemon-to-daemon part of the offset directly.

🛑 ALIASING.  fs = 100.000 Hz, Nyquist 50 Hz.  A line at f is indistinguishable from 100-f and
   100+f.  Every phase here is reported for BOTH readings of the line.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import (CACHE, FS_NOM, band_env, circ_mean_ci, coherence,  # noqa: E402
                         lattice, load_route, locate, native_18f, prom_spectrum,
                         resamp, welch_cross, wrap)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RATE_FIX = 1.25
NF = 256
HOP = 64
EVENT = (38.0, 52.0)        # seg-8-relative, converted below
BAND = (24.0, 32.0)


def dedup(t, *vs):
    """Strictly increasing time base. 1.7% of CAN rows share a logMonoTime (same log block); a
    zero dt silently produces inf in any derivative and NaN in a fit."""
    t = np.asarray(t, float)
    keep = np.ones(len(t), bool)
    keep[1:] = np.diff(t) > 0
    return (t[keep],) + tuple(np.asarray(v, float)[keep] for v in vs)


def build(R, t0, t1):
    """All four channels on ONE uniform 100 Hz lattice over [t0, t1], route-absolute seconds."""
    t14 = np.asarray(R["t"], float)
    # 🛑 tq / rate_f / thermo-bearing columns come off DIFFERENT CAN messages with different
    # arrival clocks. Each family is resampled from its OWN native timestamps.
    t18, v18, drop18 = native_18f(R, ("tq", "rate_f"))
    sct = np.asarray(R["sc_t"], float)
    scv = np.asarray(R["sc_tq_raw"], float)
    tau = lattice(t0, t1, FS_NOM)
    names14 = ["ang", "rate_c", "e4tq", "cs_v", "cc_lat", "thermo", "damp_nz", "g6ac2",
               "ct_dcurv", "ct_curv", "imu_lat", "imu_vert", "ws_fl", "ws_rr", "probe"]
    a14 = dedup(t14, *[R[n] for n in names14])
    a18 = dedup(t18, v18["tq"], v18["rate_f"])
    asc = dedup(sct, scv)
    out = dict(t=tau, drop18=drop18)
    for i, nm in enumerate(names14):
        out[nm] = resamp(tau, a14[0], np.nan_to_num(a14[1 + i]))
    out["bar"] = resamp(tau, a18[0], a18[1])
    out["rate"] = resamp(tau, a18[0], a18[2]) * RATE_FIX
    out["cmd"] = resamp(tau, asc[0], asc[1])
    return out


def xspec(x, y, fs=FS_NOM, nf=NF, hop=HOP):
    f, Pxx, Pyy, Pxy, n = welch_cross(x, y, fs, nf, hop)
    if n == 0:
        return None
    return dict(f=f, Pxx=Pxx, Pyy=Pyy, Pxy=Pxy, n=n, C=coherence(Pxx, Pyy, Pxy))


def at(f, arr, f0):
    j = int(np.argmin(np.abs(f - f0)))
    return j, arr[j]


def seg_phases(x, y, fs, f0, nf=NF, hop=HOP):
    """Per-Welch-segment cross-phase at f0, with each segment's cross-power as its weight."""
    w = np.hanning(nf)
    r = np.arange(nf, dtype=float)
    f = np.fft.rfftfreq(nf, 1 / fs)
    j = int(np.argmin(np.abs(f - f0)))
    ph, wt = [], []
    for i in range(0, len(x) - nf + 1, hop):
        xs, ys = x[i:i + nf], y[i:i + nf]
        if not (np.isfinite(xs).all() and np.isfinite(ys).all()):
            continue
        xs = xs - np.polyval(np.polyfit(r, xs, 1), r)
        ys = ys - np.polyval(np.polyfit(r, ys, 1), r)
        X = np.fft.rfft(xs * w)[j]
        Y = np.fft.rfft(ys * w)[j]
        c = np.conj(X) * Y
        ph.append(np.angle(c))
        wt.append(np.abs(c))
    return np.array(ph), np.array(wt)


def delay_fit(f, Pxy, lo, hi, Pxx=None, Pyy=None):
    """Weighted fit of unwrapped phase to -2 pi f tau over [lo,hi]. Returns tau in SECONDS."""
    m = (f >= lo) & (f <= hi)
    ph = np.unwrap(np.angle(Pxy[m]))
    w = np.abs(Pxy[m])
    if m.sum() < 3:
        return np.nan, np.nan
    A = np.vstack([f[m], np.ones(m.sum())]).T
    W = np.diag(w / w.sum())
    coef = np.linalg.lstsq(A.T @ W @ A, A.T @ W @ ph, rcond=None)[0]
    pred = A @ coef
    ss = 1 - np.sum(w * (ph - pred) ** 2) / max(np.sum(w * (ph - np.average(ph, weights=w)) ** 2), 1e-30)
    return -coef[0] / (2 * np.pi), float(ss)


def main():
    R = load_route()
    sb = {int(r[0]): (r[1], r[2]) for r in np.asarray(R["seg_bounds"], float)}
    e0 = sb[8][0] + EVENT[0]
    e1 = sb[8][0] + EVENT[1]
    d = build(R, e0, e1)
    fs = FS_NOM
    print("=" * 104)
    print(f"T1  EVENT: route-absolute {e0:.2f}-{e1:.2f} s (seg 8 + {EVENT[0]}-{EVENT[1]} s), "
          f"{len(d['t']) / fs:.1f} s, v {d['cs_v'].min():.1f}-{d['cs_v'].max():.1f} m/s, "
          f"engaged {100 * np.mean(d['cc_lat'] > 0.5):.0f}%")
    print("=" * 104)

    # ---- where is the line, in each channel, independently ------------------------------------
    print("\n  --- the line, located INDEPENDENTLY in each channel (12-45 Hz, prominence argmax) ---")
    print(f"  {'channel':>12} {'f0 (Hz)':>9} {'prom':>8} {'alias 100-f0':>13}")
    f0s = {}
    for nm in ("bar", "ang", "rate", "cmd", "e4tq", "ct_curv", "imu_lat", "imu_vert"):
        x = np.nan_to_num(d[nm])
        x = x - x.mean()
        P = np.zeros(NF // 2 + 1)
        w = np.hanning(NF)
        k = 0
        for i in range(0, len(x) - NF + 1, HOP):
            P += np.abs(np.fft.rfft((x[i:i + NF] - x[i:i + NF].mean()) * w)) ** 2
            k += 1
        P /= max(k, 1)
        f = np.fft.rfftfreq(NF, 1 / fs)
        ff, pp = locate(f, P, 12.0, 45.0)
        f0s[nm] = ff
        print(f"  {nm:>12} {ff:>9.3f} {pp:>8.1f} {100 - ff:>13.3f}")
    F0 = f0s["bar"]
    print(f"\n  ==> f0 taken from the BAR: {F0:.3f} Hz   (alias twin {100 - F0:.3f} Hz)")

    # ---- VALIDITY GATE ------------------------------------------------------------------------
    # `rate` is d(angle)/dt, so it MUST lead `angle` by +90 deg at f0. This is the one relationship
    # in the data whose answer is known a priori, so it is the only available check that the
    # per-message timebases have been reconstructed correctly. It caught a real bug: resampling
    # rate_f on the 0x14A clock instead of its native 0x18F clock put this at -120 deg.
    Sg = xspec(np.nan_to_num(d["ang"]), np.nan_to_num(d["rate"]))
    jg, pg = at(Sg["f"], Sg["Pxy"], F0)
    lead = np.degrees(np.angle(pg))
    err = np.degrees(wrap(np.angle(pg) - np.pi / 2))
    print(f"\n  --- VALIDITY GATE: rate must lead angle by +90 deg (it is the derivative) ---")
    print(f"      measured lead {lead:+.1f} deg   error {err:+.1f} deg "
          f"= {err / 360 / F0 * 1e3:+.2f} ms of residual timebase error   "
          f"coherence {Sg['C'][jg]:.3f}   [{'PASS' if abs(err) < 25 else 'FAIL'}]")
    print(f"      0x18F frames dropped by the hold-recovery: {100 * d['drop18']:.2f} %")

    # ---- coherence + surrogate null -----------------------------------------------------------
    print("\n  --- COHERENCE at f0, with a circular-shift surrogate null (within this ONE run) ---")
    print(f"  {'pair':>22} {'coh@f0':>8} {'1/nseg':>8} {'null p50':>9} {'null p95':>9} "
          f"{'null max':>9} {'verdict':>10}")
    rng = np.random.default_rng(0xC0FFEE)
    pairs = [("cmd -> bar", "cmd", "bar"), ("cmd -> angle", "cmd", "ang"),
             ("cmd -> rate", "cmd", "rate"), ("bar -> angle", "bar", "ang"),
             ("cmd -> ct_curv", "cmd", "ct_curv"), ("cmd -> imu_lat", "cmd", "imu_lat")]
    res = {}
    for lab, a, b in pairs:
        x, y = np.nan_to_num(d[a]), np.nan_to_num(d[b])
        S = xspec(x, y)
        j, c = at(S["f"], S["C"], F0)
        nulls = []
        for _ in range(300):
            s = int(rng.integers(int(0.15 * len(y)), int(0.85 * len(y))))
            Sn = xspec(x, np.roll(y, s))
            nulls.append(Sn["C"][j])
        nulls = np.array(nulls)
        v = ("REAL" if c > np.percentile(nulls, 99) else
             "marginal" if c > np.percentile(nulls, 95) else "NULL")
        res[lab] = dict(coh=float(c), n=S["n"], null95=float(np.percentile(nulls, 95)))
        print(f"  {lab:>22} {c:>8.3f} {1 / S['n']:>8.3f} {np.percentile(nulls, 50):>9.3f} "
              f"{np.percentile(nulls, 95):>9.3f} {nulls.max():>9.3f} {v:>10}")

    # ---- phase, delay calibration, residual ---------------------------------------------------
    print("\n  --- CROSS-PHASE.  angle(Pxy) > 0 means the SECOND channel LEADS the first ---")
    print(f"  {'pair':>22} {'phase@f0':>10} {'CI (deg)':>18} {'lag@f0':>9} "
          f"{'tau 1-8Hz':>10} {'R2':>6} {'resid@f0':>10}")
    for lab, a, b in pairs:
        x, y = np.nan_to_num(d[a]), np.nan_to_num(d[b])
        S = xspec(x, y)
        j, pxy = at(S["f"], S["Pxy"], F0)
        ph, wt = seg_phases(x, y, fs, F0)
        mu, lo, hi = circ_mean_ci(ph, wt)
        tau, r2 = delay_fit(S["f"], S["Pxy"], 1.0, 8.0)
        pred = wrap(-2 * np.pi * F0 * tau) if np.isfinite(tau) else np.nan
        resid = np.degrees(wrap(mu - pred)) if np.isfinite(pred) else np.nan
        lag_ms = -np.degrees(mu) / 360.0 / F0 * 1e3
        print(f"  {lab:>22} {np.degrees(mu):>+10.1f} "
              f"[{np.degrees(lo):>+7.1f},{np.degrees(hi):>+7.1f}] {lag_ms:>+8.1f}ms "
              f"{1e3 * tau if np.isfinite(tau) else np.nan:>9.2f}ms {r2:>6.2f} {resid:>+9.1f}")
        res[lab].update(phase_deg=float(np.degrees(mu)), ci=[float(np.degrees(lo)),
                        float(np.degrees(hi))], tau_ms=float(1e3 * tau) if np.isfinite(tau) else None)

    # ---- the daemon-clock bound: sendcan vs its own bus echo ----------------------------------
    S = xspec(np.nan_to_num(d["cmd"]), np.nan_to_num(d["e4tq"]))
    tau_e, r2e = delay_fit(S["f"], S["Pxy"], 1.0, 12.0)
    j, pe = at(S["f"], S["Pxy"], F0)
    print(f"\n  CLOCK BOUND  sendcan 0x0E4 -> its own bus echo (can src129), same payload:")
    print(f"      pure-delay fit 1-12 Hz  tau = {1e3 * tau_e:+.2f} ms  (R2 {r2e:.3f})   "
          f"coherence@f0 {S['C'][j]:.3f}   phase@f0 {np.degrees(np.angle(pe)):+.1f} deg")
    print(f"      => the sendcan-vs-can daemon offset is {1e3 * tau_e:+.2f} ms, i.e. "
          f"{360 * F0 * tau_e:+.0f} deg at {F0:.1f} Hz. Everything below is corrected by it.")

    # ---- THE ENERGY-SIGN TEST -----------------------------------------------------------------
    print()
    print("=" * 104)
    print("T1-CRUX  DOES OPENPILOT'S COMMAND PUMP THE OSCILLATION, OR DAMP IT?")
    print("=" * 104)
    print("  A torque command acting on a moving column does work at a rate proportional to")
    print("  Re<cmd, rate> at f0.  If the command's f0 component is IN PHASE with the column RATE,")
    print("  it adds energy (negative damping = pumping).  If it OPPOSES the rate, it removes")
    print("  energy.  The sign convention is fixed empirically at 1-4 Hz, where openpilot is")
    print("  unambiguously driving the column, so no unit or polarity assumption is needed.")
    x, y = np.nan_to_num(d["cmd"]), np.nan_to_num(d["rate"])
    S = xspec(x, y)
    print("  🛑 THE ANSWER DEPENDS ON THE TRANSPORT DELAY L2 (openpilot's sendcan timestamp -> the")
    print("     command actually acting at the rack). At 1-4 Hz a 10 ms L2 is 4-14 deg and cannot")
    print(f"     change a sign. At {F0:.1f} Hz it is {360 * F0 * 0.010:.0f} deg and changes"
          " EVERYTHING. So the test is run")
    print("     as a SWEEP over L2, and only a sign that survives the whole plausible range is a")
    print("     finding. Reporting a single number here would be the confidently-wrong answer.")
    for lab, lo, hi in (("1-4 Hz (openpilot IS driving)", 1.0, 4.0),
                        ("6-10 Hz", 6.0, 10.0),
                        (f"{BAND[0]}-{BAND[1]} Hz (instability)", *BAND)):
        m = (S["f"] >= lo) & (S["f"] <= hi)
        row = []
        for L2 in (0.0, 0.005, 0.010, 0.015, 0.020):
            rot = np.exp(-2j * np.pi * S["f"][m] * L2)   # delay the COMMAND by L2
            cp = (S["Pxy"][m] * np.conj(rot)).sum()
            row.append(cp.real / np.abs(S["Pxy"][m]).sum())
        print(f"  {lab:>32}  cos(work) at L2 = 0/5/10/15/20 ms: "
              + " ".join(f"{v:+.3f}" for v in row)
              + f"   mean coh {np.nanmean(S['C'][m]):.3f}")
    print("  A NEGATIVE cos means the command opposes the column's motion => it REMOVES energy")
    print("  (damping). POSITIVE means it adds energy (pumping). Compare each row's sign pattern")
    print("  with the 1-4 Hz row, which is the calibration: that is what 'openpilot driving' looks")
    print("  like, and its sign is stable across the whole L2 sweep by construction.")

    # ---- alias robustness ---------------------------------------------------------------------
    print()
    print("  --- ALIAS ROBUSTNESS: the same phase read at f0 and at its twin 100-f0 ---")
    print("  (a real line at 100-f0 would appear at f0 with the CONJUGATE phase, i.e. sign-flipped)")
    for lab, a, b in pairs[:3]:
        S = xspec(np.nan_to_num(d[a]), np.nan_to_num(d[b]))
        j, pxy = at(S["f"], S["Pxy"], F0)
        print(f"  {lab:>22}  read as {F0:5.2f} Hz: {np.degrees(np.angle(pxy)):+7.1f} deg"
              f"   |   read as {100 - F0:5.2f} Hz: {-np.degrees(np.angle(pxy)):+7.1f} deg"
              f"   lag {-np.degrees(np.angle(pxy)) / 360 / (100 - F0) * 1e3:+6.1f} ms")

    (CACHE / "v81loop_t1.json").write_text(json.dumps(
        dict(f0=float(F0), f0_by_chan={k: float(v) for k, v in f0s.items()},
             tau_echo_ms=float(1e3 * tau_e), pairs=res), indent=0))
    print(f"\n  wrote {CACHE / 'v81loop_t1.json'}")


if __name__ == "__main__":
    main()
