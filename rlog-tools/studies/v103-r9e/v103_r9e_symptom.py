#!/usr/bin/env python3
r"""studies/v103-r9e/v103_r9e_symptom.py -- ROUTE 9e (V103): LOCATE THE OPERATOR'S TWO SYMPTOMS IN TIME AND FREQUENCY.

Operator's own report on this drive: **grinding #1 (low speed) PRESENT** and **ratcheting at high
steer-angle rate PRESENT**.  He did NOT report vibration.  This file:

  A  per-window band-RMS on every channel, per REGIME, with a MATCHED-SPEED census attached
     (an unmatched average manufactures an "only on route X" line -- `accord-averaged-spectrum...`)
  B  WHERE the worst windows are: segment, timestamp, speed, wheel rate, hands, engaged
  C  is there a ~23 Hz LINE at all on this route?  (peak-prominence search, with a shuffled control)
  D  THE RATCHET, channel by channel: driver torque vs angle rate vs LKAS command vs the EPS's own
     427 lane.  Engaged vs manual.  Amplitude vs wheel rate.

🛑 `band_envelope` in `_r31_common`/`_r2b_common` is RECTIFIED, not analytic.  Envelopes here come
   from `scipy.signal.hilbert`.  Ratios from the broken version survive; duty/CV/p50 do not.
🛑 Bands per `docs/specs/SPEC-2026-08-20-band-definition.md`: 20-28 primary, 21.5-25.5 legacy, 2.5-4.5 the
   shape denominator, 31-35 the negative control.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import hilbert

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(9103)
NW, HOP = 256, 128                 # 2.56 s windows, 50 % hop.  STATED WITH EVERY NUMBER (spec §5).
BANDS = [("2.5-4.5", 2.5, 4.5), ("6-9", 6.0, 9.0), ("10-15", 10.0, 15.0),
         ("15-22", 15.0, 22.0), ("18-22", 18.0, 22.0), ("20-28", 20.0, 28.0),
         ("21.5-25.5", 21.5, 25.5), ("22-26", 22.0, 26.0), ("31-35", 31.0, 35.0)]
CTRL = "2.5-4.5"
CH = [("tq", "driver torque 0x18F"), ("rate_c", "steer rate 0x14A"),
      ("rate_f", "filtered rate 0x18F"), ("cs_ang", "steering angle"),
      ("e4tq", "LKAS command 0x0E4"), ("x6b4c", "EPS 427 lane (gp-0x6b4c)"),
      ("imu_lat", "IMU lateral"), ("imu_vert", "IMU vertical")]
OUT = {}
DT = 0.01


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def windows(z, mask, fs):
    """Index windows over contiguous runs of `mask`, 2.56 s / 50 % hop."""
    t = np.asarray(z["t"], float)
    out = []
    for a, b in V.episodes(mask, t, NW):
        for i in range(0, (b - a) - NW + 1, HOP):
            out.append(slice(a + i, a + i + NW))
    return out


def brms(x, fs):
    """Band RMS of ONE window for every band in BANDS."""
    w = np.hanning(len(x))
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    X = np.fft.rfft((x - x.mean()) * w)
    psd = (np.abs(X) ** 2) / (np.sum(w ** 2) * fs)
    psd[1:-1] *= 2.0
    df = f[1] - f[0]
    return {nm: float(np.sqrt(np.sum(psd[(f >= lo) & (f <= hi)]) * df)) for nm, lo, hi in BANDS}


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    seg = np.asarray(z["seg"], int)
    fs = 1.0 / float(np.median(np.diff(t)))
    eng, press = M["eng"], M["press"]
    v = M["v"]                                     # m/s
    rate = M["rate"]                               # deg/s
    print("  fs = %.2f Hz   window %d samples = %.2f s   hop %d = %.2f s   (STATED PER SPEC §5)"
          % (fs, NW, NW / fs, HOP, HOP / fs))

    chan = {}
    for k, _lab in CH:
        if k in z.files if hasattr(z, "files") else k in z:
            chan[k] = np.asarray(z[k], float)
    for k in list(chan):
        if not np.isfinite(chan[k]).any():
            print("  channel %s is ALL-NaN -- dropped" % k)
            chan.pop(k)

    # ------------------------------------------------------------------ A  REGIMES
    hdr("A -- BAND-RMS BY REGIME.  2.56 s windows, median over windows (the pre-registered\n"
        "     summary statistic).  A per-regime SPEED CENSUS is printed so an unmatched average\n"
        "     cannot masquerade as a firmware effect.")
    REG = [
        ("ENG lowspeed  <30 km/h", eng & (v < 8.33)),
        ("ENG mid    30-60 km/h", eng & (v >= 8.33) & (v < 16.67)),
        ("ENG high   60-85 km/h", eng & (v >= 16.67) & (v < 23.6)),
        ("ENG motorway >85 km/h", eng & (v >= 23.6)),
        ("ENG hands-OFF 29-86", eng & (~press) & (v >= 8.0) & (v < 24.0)),
        ("ENG hands-ON  any v", eng & press),
        ("ENG micro rate 1-13", eng & (rate >= 1) & (rate < 13)),
        ("ENG ratchet rate 13-50", eng & (rate >= 13) & (rate < 50)),
        ("ENG macro rate >50", eng & (rate >= 50)),
        ("MANUAL moving >18km/h", (~eng) & (v > 5.0)),
        ("MANUAL lowspeed <30", (~eng) & (v > 0.5) & (v < 8.33)),
    ]
    OUT["regimes"] = {}
    for nm, m in REG:
        W = windows(z, m, fs)
        if len(W) < 4:
            print("\n  %-24s only %d windows -- skipped" % (nm, len(W)))
            continue
        vs = np.array([np.median(v[w]) * 3.6 for w in W])
        rs = np.array([np.median(rate[w]) for w in W])
        print("\n  %-24s n=%3d windows (%.0f s)   speed p10/p50/p90 %.0f/%.0f/%.0f km/h   "
              "rate p50 %.1f deg/s"
              % (nm, len(W), len(W) * HOP / fs, np.percentile(vs, 10), np.percentile(vs, 50),
                 np.percentile(vs, 90), np.median(rs)))
        print("      %-22s " % "channel" + " ".join("%9s" % b[0] for b in BANDS))
        rec = {}
        for k, lab in CH:
            if k not in chan:
                continue
            vals = [brms(chan[k][w], fs) for w in W]
            med = {b[0]: float(np.median([x[b[0]] for x in vals])) for b in BANDS}
            rec[k] = med
            print("      %-22s " % lab + " ".join("%9.2f" % med[b[0]] for b in BANDS))
        # shape ratios vs the control band, on the primary symptom channel
        if "tq" in rec:
            r = rec["tq"]
            print("      %-22s " % "tq SHAPE (/2.5-4.5)" +
                  " ".join("%9.3f" % (r[b[0]] / max(r[CTRL], 1e-9)) for b in BANDS))
        OUT["regimes"][nm] = dict(n_win=len(W), sec=float(len(W) * HOP / fs),
                                  v_p50_kmh=float(np.median(vs)), rate_p50=float(np.median(rs)),
                                  bands=rec)

    # ------------------------------------------------------------------ B  LOCALISATION
    hdr("B -- WHERE THE SYMPTOMS ARE.  Top windows by band-RMS on DRIVER TORQUE `tq`.\n"
        "     6-9 Hz = the ratchet band (record: 7.79 Hz, speed-invariant, axis is WHEEL RATE).\n"
        "     20-28 Hz = the primary vibration/grind band (SPEC-2026-08-20).")
    Wall = windows(z, np.ones(len(t), bool), fs)
    rowsv = []
    for w in Wall:
        b = brms(chan["tq"][w], fs)
        rowsv.append(dict(i0=w.start, t0=float(t[w.start]), t1=float(t[w.stop - 1]),
                          seg=int(np.median(seg[w])),
                          v=float(np.median(v[w]) * 3.6), rate=float(np.median(rate[w])),
                          rate_p90=float(np.percentile(rate[w], 90)),
                          eng=float(eng[w].mean()), press=float(press[w].mean()),
                          cmd=float(np.median(np.abs(chan["e4tq"][w]))), **b))
    OUT["all_windows_n"] = len(rowsv)
    for band, title in (("6-9", "RATCHET BAND 6-9 Hz"), ("20-28", "VIBRATION/GRIND 20-28 Hz"),
                        ("15-22", "GRIND 15-22 Hz")):
        s = sorted(rowsv, key=lambda r: -r[band])[:14]
        print("\n  --- TOP 14 WINDOWS, %s, on driver torque ---" % title)
        print("      %8s %4s %8s %8s %8s %7s %7s %8s %10s %10s"
              % ("t0 s", "seg", "RMS", "ctrl2.5-4.5", "ratio", "v kmh", "rate", "ratep90",
                 "eng duty", "hands"))
        for r in s:
            print("      %8.1f %4d %8.2f %8.2f %8.2f %7.1f %7.1f %8.1f %10.2f %10.2f"
                  % (r["t0"], r["seg"], r[band], r[CTRL], r[band] / max(r[CTRL], 1e-9),
                     r["v"], r["rate"], r["rate_p90"], r["eng"], r["press"]))
        OUT.setdefault("top_windows", {})[band] = s
        # what fraction of the top decile is engaged / low-speed / high-rate?
        q9 = np.percentile([r[band] for r in rowsv], 90)
        hi = [r for r in rowsv if r[band] >= q9]
        print("      TOP DECILE (n=%d): engaged %.2f · hands-on %.2f · v p50 %.0f km/h · "
              "rate p50 %.1f deg/s   || ALL (n=%d): engaged %.2f · v p50 %.0f · rate p50 %.1f"
              % (len(hi), np.mean([r["eng"] for r in hi]), np.mean([r["press"] for r in hi]),
                 np.median([r["v"] for r in hi]), np.median([r["rate"] for r in hi]),
                 len(rowsv), np.mean([r["eng"] for r in rowsv]),
                 np.median([r["v"] for r in rowsv]), np.median([r["rate"] for r in rowsv])))
        OUT.setdefault("top_decile", {})[band] = dict(
            n=len(hi), eng=float(np.mean([r["eng"] for r in hi])),
            press=float(np.mean([r["press"] for r in hi])),
            v_p50=float(np.median([r["v"] for r in hi])),
            rate_p50=float(np.median([r["rate"] for r in hi])),
            all_eng=float(np.mean([r["eng"] for r in rowsv])),
            all_v_p50=float(np.median([r["v"] for r in rowsv])),
            all_rate_p50=float(np.median([r["rate"] for r in rowsv])))

    # ------------------------------------------------------------------ C  THE ~23 Hz LINE
    hdr("C -- IS THERE A ~23 Hz LINE ON THIS ROUTE AT ALL?  The operator did NOT report vibration\n"
        "     this drive.  Averaged spectrum over SPEED-MATCHED engaged hands-off windows, with a\n"
        "     per-window speed census, plus a phase-shuffled control.  Peak PROMINENCE is the test.")
    for nm, m in (("ENG hands-off 29-86 km/h", eng & (~press) & (v >= 8.0) & (v < 24.0)),
                  ("ENG hands-off 60-85 km/h", eng & (~press) & (v >= 16.67) & (v < 23.6)),
                  ("MANUAL moving 29-86 km/h", (~eng) & (v >= 8.0) & (v < 24.0))):
        W = windows(z, m, fs)
        if len(W) < 6:
            print("\n  %-26s only %d windows -- skipped" % (nm, len(W)))
            continue
        wn = np.hanning(NW)
        f = np.fft.rfftfreq(NW, 1.0 / fs)
        acc = np.zeros(len(f))
        for w in W:
            x = chan["tq"][w]
            acc += np.abs(np.fft.rfft((x - x.mean()) * wn)) ** 2
        acc /= len(W)
        sel = (f >= 15.0) & (f <= 32.0)
        base = np.median(acc[sel])
        j = np.argmax(acc[sel])
        fpk = f[sel][j]
        prom = acc[sel][j] / base
        vs = np.array([np.median(v[w]) * 3.6 for w in W])
        print("\n  %-26s n=%3d win   speed p10/p50/p90 %.0f/%.0f/%.0f km/h"
              % (nm, len(W), np.percentile(vs, 10), np.percentile(vs, 50), np.percentile(vs, 90)))
        print("      peak in 15-32 Hz at %.2f Hz, prominence %.2f x the band median" % (fpk, prom))
        # top 5 local maxima
        loc = [(f[sel][i], acc[sel][i] / base) for i in range(1, len(acc[sel]) - 1)
               if acc[sel][i] > acc[sel][i - 1] and acc[sel][i] > acc[sel][i + 1]]
        loc.sort(key=lambda x: -x[1])
        print("      top local maxima: " + "  ".join("%.2f Hz (x%.2f)" % x for x in loc[:6]))
        # shuffled control: same windows, phase-randomised -> what prominence does noise give?
        pr = []
        for _ in range(60):
            a2 = np.zeros(len(f))
            for w in W:
                x = chan["tq"][w]
                X = np.fft.rfft((x - x.mean()) * wn)
                ph = RNG.uniform(0, 2 * np.pi, len(X))
                a2 += np.abs(np.abs(X) * np.exp(1j * ph)) ** 2
            a2 /= len(W)
            pr.append(a2[sel].max() / np.median(a2[sel]))
        print("      phase-shuffled control prominence: p50 %.2f  p95 %.2f   => %s"
              % (np.median(pr), np.percentile(pr, 95),
                 "A REAL LINE" if prom > np.percentile(pr, 95) else "NOT distinguishable from noise"))
        OUT.setdefault("line23", {})[nm] = dict(
            n_win=len(W), f_peak=float(fpk), prominence=float(prom),
            shuffled_p50=float(np.median(pr)), shuffled_p95=float(np.percentile(pr, 95)),
            top_maxima=[[float(a), float(b)] for a, b in loc[:6]],
            v_p50_kmh=float(np.median(vs)))

    # ------------------------------------------------------------------ D  THE RATCHET
    hdr("D -- THE RATCHET, CHANNEL BY CHANNEL.  Operator: driven by driver-side wheel INERTIA at\n"
        "     high steer-angle rate.  Q1 which channel carries it?  Q2 does it need ENGAGEMENT?\n"
        "     Q3 does its amplitude scale with WHEEL RATE?  (record: axis is rate, not speed)")
    RB = "6-9"
    # ---- Q3 first: amplitude vs wheel rate, per channel, engaged AND manual, speed-partialled
    RBINS = [(0.35, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0), (13.0, 25.0), (25.0, 50.0),
             (50.0, 1e9)]
    OUT["ratchet_vs_rate"] = {}
    for armnm, am in (("ENGAGED", eng), ("MANUAL", ~eng)):
        print("\n  --- %s: 6-9 Hz band-RMS by |wheel rate| bin (median over 2.56 s windows) ---"
              % armnm)
        print("      %-12s %6s %8s " % ("rate bin", "n", "v p50") +
              " ".join("%13s" % c[0] for c in CH if c[0] in chan))
        for lo_, hi_ in RBINS:
            m = am & (rate >= lo_) & (rate < hi_) & (v > 0.5)
            W = windows(z, m, fs)
            if len(W) < 4:
                continue
            vs = float(np.median([np.median(v[w]) * 3.6 for w in W]))
            vals = {}
            for k, _l in CH:
                if k not in chan:
                    continue
                vals[k] = float(np.median([brms(chan[k][w], fs)[RB] for w in W]))
            print("      %-12s %6d %8.0f " % ("%.2g-%.2g" % (lo_, min(hi_, 999)), len(W), vs) +
                  " ".join("%13.2f" % vals[k] for k, _l in CH if k in chan))
            OUT["ratchet_vs_rate"].setdefault(armnm, {})["%.2g-%.2g" % (lo_, min(hi_, 999))] = \
                dict(n=len(W), v_p50=vs, **vals)

    # ---- Q2: does it need engagement?  SPEED- AND RATE-MATCHED engaged/manual contrast
    hdr("D2 -- ENGAGED vs MANUAL, MATCHED on speed AND wheel rate (the record's own failure mode:\n"
        "      an unmatched contrast is a rate effect wearing an engagement label).")
    cells = []
    for vlo, vhi in ((0.5, 8.33), (8.33, 16.67), (16.67, 23.6)):
        for rlo, rhi in ((1.0, 13.0), (13.0, 50.0), (50.0, 1e9)):
            me = eng & (v >= vlo) & (v < vhi) & (rate >= rlo) & (rate < rhi)
            mm = (~eng) & (v >= vlo) & (v < vhi) & (rate >= rlo) & (rate < rhi)
            We, Wm = windows(z, me, fs), windows(z, mm, fs)
            if len(We) < 4 or len(Wm) < 4:
                continue
            row = dict(v="%.0f-%.0f km/h" % (vlo * 3.6, vhi * 3.6),
                       r="%.0f-%.0f deg/s" % (rlo, min(rhi, 999)),
                       ne=len(We), nm=len(Wm))
            for k, _l in CH:
                if k not in chan:
                    continue
                a = np.median([brms(chan[k][w], fs)[RB] for w in We])
                b = np.median([brms(chan[k][w], fs)[RB] for w in Wm])
                row[k + "_eng"] = float(a)
                row[k + "_man"] = float(b)
                row[k + "_ratio"] = float(a / max(b, 1e-9))
            cells.append(row)
    print("      %-12s %-12s %5s %5s " % ("speed", "rate", "n_eng", "n_man") +
          " ".join("%12s" % (c[0] + " E/M") for c in CH if c[0] in chan and c[0] != "e4tq"))
    for r in cells:
        print("      %-12s %-12s %5d %5d " % (r["v"], r["r"], r["ne"], r["nm"]) +
              " ".join("%12.2f" % r[k + "_ratio"] for k, _l in CH
                       if k in chan and k != "e4tq"))
    OUT["engaged_vs_manual_matched"] = cells

    # ---- Q1: which channel LEADS?  coherence + phase between tq and the others at 6-9 Hz
    hdr("D3 -- IS THE RATCHET IN THE COMMAND?  Coherence of driver torque against every other\n"
        "      channel at 6-9 Hz, engaged, with a shuffled-pair control.")
    import decode_v90_probe as P
    m = eng & (v > 0.5)
    Wz = []
    tt = np.asarray(z["t"], float)
    for a, b in V.episodes(m, tt, V.NW_Z):
        for i in range(0, (b - a) - V.NW_Z + 1, V.HOP_Z):
            Wz.append(slice(a + i, a + i + V.NW_Z))
    print("      %d windows of %.2f s, engaged" % (len(Wz), V.NW_Z / fs))
    print("      %-24s %10s %10s %10s %10s" % ("pair (x -> tq)", "coh2 6-9", "shuffled",
                                               "phase deg", "gain"))
    OUT["ratchet_coherence"] = {}
    for k, lab in CH:
        if k not in chan or k == "tq":
            continue
        pr = [(chan[k][w], chan["tq"][w]) for w in Wz]
        pr = [(x, y) for x, y in pr if np.isfinite(x).all() and np.isfinite(y).all()]
        if len(pr) < 6:
            continue
        r = P._band_transfer(pr, fs, V.NW_Z, [("b", 6.0, 9.0)])["b"]
        idx = RNG.permutation(len(pr))
        sh = P._band_transfer([(pr[i][0], pr[(idx[i] + 1) % len(pr)][1]) for i in range(len(pr))],
                              fs, V.NW_Z, [("b", 6.0, 9.0)])["b"]
        print("      %-24s %10.3f %10.4f %10.1f %10.3f"
              % (lab, r["coh2"], sh["coh2"], r["phase_deg"], r["gain"]))
        OUT["ratchet_coherence"][k] = dict(label=lab, coh2=float(r["coh2"]),
                                           shuffled=float(sh["coh2"]),
                                           phase_deg=float(r["phase_deg"]),
                                           gain=float(r["gain"]))

    # ---- envelope, via scipy.signal.hilbert (the BROKEN band_envelope is NOT used)
    hdr("D4 -- RATCHET ENVELOPE (scipy.signal.hilbert -- the kit's own `band_envelope` is\n"
        "      RECTIFIED, not analytic, so its duty/CV/p50 numbers do NOT travel).")
    from scipy.signal import butter, filtfilt
    b_, a_ = butter(4, [6.0 / (fs / 2), 9.0 / (fs / 2)], btype="band")
    envs = {}
    for k in ("tq", "rate_c", "e4tq"):
        if k not in chan:
            continue
        x = np.nan_to_num(chan[k])
        envs[k] = np.abs(hilbert(filtfilt(b_, a_, x)))
    for k, e in envs.items():
        for armnm, am in (("engaged", eng & (v > 0.5)), ("manual", (~eng) & (v > 0.5))):
            print("      %-8s %-8s  env p50 %8.2f  p90 %8.2f  p99 %8.2f   "
                  "burstiness p90/p50 %6.2f"
                  % (k, armnm, np.percentile(e[am], 50), np.percentile(e[am], 90),
                     np.percentile(e[am], 99),
                     np.percentile(e[am], 90) / max(np.percentile(e[am], 50), 1e-9)))
            OUT.setdefault("envelope", {}).setdefault(k, {})[armnm] = dict(
                p50=float(np.percentile(e[am], 50)), p90=float(np.percentile(e[am], 90)),
                p99=float(np.percentile(e[am], 99)))
        # correlation of the envelope with wheel rate -- the record's "axis is wheel rate"
        mm = eng & (v > 0.5)
        c = float(np.corrcoef(np.log(e[mm] + 1e-3), np.log(rate[mm] + 0.05))[0, 1])
        print("      %-8s corr(log env, log |wheel rate|) engaged = %+.3f" % (k, c))
        OUT.setdefault("envelope", {}).setdefault(k, {})["corr_log_rate"] = c

    Path(HERE / "_scratch/out/_v103_r9e_symptom.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_symptom.json")


if __name__ == "__main__":
    main()
