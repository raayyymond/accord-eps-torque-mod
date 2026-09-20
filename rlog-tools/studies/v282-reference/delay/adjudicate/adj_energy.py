"""ADJUDICATION, part B -- weight the rate-loop phase budget by the WHEEL-RATE SPECTRUM THE CAR ACTUALLY HAS.

The phase table (adj_phase.py) says a rate-feedback term damps below ~3-3.9 Hz and pumps above it at the measured
D_loop.  Whether MORE gain is net-good therefore depends on where the wheel's energy is.  Per unit of
AccordRateLoopGain the mechanical power it removes from the wheel is

    E = integral over f of  m(f; D_loop, RC) * S_rate(f) df ,     m = cos(w D + atan(w RC)) / |1 + jw RC|

(E > 0 removes energy, E < 0 injects it).  Reported per band and as a single net number, on hands-off laterally
engaged data below 8 m/s and 8-15 m/s, per route, with the 1 deg/s quantisation floor shown so the reader can see
where S_rate stops being wheel motion.

Also measured, for the reference-shaping candidate:
  - the demand-coherent fraction gamma^2(f) of the wheel rate against the LOGGED (already 0.06-shaped) setpoint
    controlsState...desiredLateralAccel, in 1.8-3.5 Hz;
  - the band-rms reduction a larger AccordRefFilter would deliver, = sqrt(1 - g2*(1-|Hnew/Hold|^2)) integrated
    over the band with the measured S_rate as the weight.  Delay-independent by construction: every demand path
    (hold FF, MOVE FF, rate-loop desired side, P/I error) is downstream of the filter, so the coherent part of
    the wheel rate scales by |Hnew/Hold| exactly.
"""
import json
import sys
import numpy as np
from scipy import signal

CACHE = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
FS = 100.0
RC = 0.01
NPER = 512                      # 5.12 s, df = 0.195 Hz
BINS = [("<8", 0.0, 8.0), ("8-15", 8.0, 15.0)]
BANDS = [("1.8-3.5", 1.8, 3.5), ("3.5-6", 3.5, 6.0), ("6-10", 6.0, 10.0), ("1.0-12", 1.0, 12.0)]
DLOOPS = [55.0, 65.0, 72.0, 75.0]
QFLOOR = (1.0 ** 2 / 12.0) / (FS / 2.0)   # (deg/s)^2/Hz, 1 deg/s LSB white over 0-50 Hz


def mult(f, D_ms, rc=RC):
    w = 2 * np.pi * np.asarray(f, float)
    return np.cos(w * D_ms / 1000.0 + np.arctan(w * rc)) / np.sqrt(1 + (w * rc) ** 2)


def ref_ratio(f, rc_new, rc_old=0.06):
    """|H_new/H_old| for TWO cascaded first-order lags."""
    w = 2 * np.pi * np.asarray(f, float)
    return (1 + (w * rc_old) ** 2) / (1 + (w * rc_new) ** 2)


def runs(mask, minlen):
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    br = np.where(np.diff(idx) > 1)[0]
    return [c for c in np.split(idx, br + 1) if len(c) >= minlen]


out = {}
for rk in ROUTES:
    d = np.load(f"{CACHE}/{rk}.npz")
    t = d["t_cst"]
    g = np.arange(t[0], t[-1], 1.0 / FS)                       # uniform 100 Hz host-time grid
    rate = np.interp(g, t, d["sr_deg"])
    v = np.interp(g, t, d["vego"])
    press = np.interp(g, t, d["spress"]) > 0.5
    act = np.interp(g, d["t_cs"], d["cs_active"]) > 0.5
    lat = np.interp(g, d["t_cc"], d["lat_active"]) > 0.5
    ldes = np.interp(g, d["t_cs"], d["cs_la_des"])             # the SHAPED setpoint (0.06 as flown)
    # a grid point is valid only if a real carState sample sits within 25 ms of it
    near = np.abs(g - t[np.clip(np.searchsorted(t, g), 0, len(t) - 1)]) < 0.025
    base = act & lat & ~press & near
    res = {}
    for tag, lo, hi in BINS:
        ch = runs(base & (v >= lo) & (v < hi), NPER * 2)
        if not ch:
            continue
        Srr = Sdd = Srd = None
        secs = 0.0
        for c in ch:
            r = signal.detrend(rate[c])
            q = signal.detrend(ldes[c])
            f, srr = signal.welch(r, FS, nperseg=NPER, detrend="linear")
            _, sdd = signal.welch(q, FS, nperseg=NPER, detrend="linear")
            _, srd = signal.csd(q, r, FS, nperseg=NPER, detrend="linear")
            nseg = max(1, (len(c) - NPER) // (NPER // 2) + 1)
            Srr = srr * nseg if Srr is None else Srr + srr * nseg
            Sdd = sdd * nseg if Sdd is None else Sdd + sdd * nseg
            Srd = srd * nseg if Srd is None else Srd + srd * nseg
            secs += len(c) / FS
        n = len(ch)
        g2 = np.abs(Srd) ** 2 / np.maximum(Srr * Sdd, 1e-30)
        cell = {"n_runs": n, "secs": round(secs, 1),
                "rms_1.8_3.5": float(np.sqrt(np.trapezoid(Srr[(f >= 1.8) & (f <= 3.5)], f[(f >= 1.8) & (f <= 3.5)])
                                             / max(1, 1) ) ),
                "bands": {}, "energy": {}, "refshape": {}}
        # PSD levels vs the quantisation floor
        cell["psd_vs_qfloor"] = {f"{fq:.1f}": round(float(np.interp(fq, f, Srr)) / (QFLOOR * np.sum(
            [1])), 2) for fq in (2.0, 2.5, 3.5, 5.0, 8.0, 12.0)}
        for bt, blo, bhi in BANDS:
            m = (f >= blo) & (f <= bhi)
            cell["bands"][bt] = {"rms_degps": round(float(np.sqrt(np.trapezoid(Srr[m], f[m]) / max(np.sum(m), 1) * np.sum(m))), 3),
                                 "g2_mean": round(float(np.average(g2[m], weights=Srr[m])), 3)}
        # net damping energy per unit gain, measured spectrum as the weight
        for D in DLOOPS:
            mm = mult(f, D)
            e = {}
            for bt, blo, bhi in BANDS:
                b = (f >= blo) & (f <= bhi)
                e[bt] = round(float(np.trapezoid(mm[b] * Srr[b], f[b])), 4)
            b18 = (f >= 1.8) & (f <= 3.5)
            b36 = (f >= 3.5) & (f <= 6.0)
            e["harm_over_help_1.8-3.5_vs_3.5-6"] = round(-e["3.5-6"] / max(e["1.8-3.5"], 1e-9), 3)
            # same, with the flat quantisation floor removed from S_rate
            Sc = np.maximum(Srr - QFLOOR, 0.0)
            e["net_1-12_qcorr"] = round(float(np.trapezoid(mm[(f >= 1) & (f <= 12)] * Sc[(f >= 1) & (f <= 12)],
                                                           f[(f >= 1) & (f <= 12)])), 4)
            e["net_1-12"] = e["1.0-12"]
            cell["energy"][f"D{D:.0f}"] = e
        # reference shaping: predicted band-rms change in 1.8-3.5 Hz
        b = (f >= 1.8) & (f <= 3.5)
        for rc_new in (0.09, 0.12, 0.16, 0.20):
            rr = ref_ratio(f[b], rc_new)
            Snew = Srr[b] * (1 - g2[b] * (1 - rr ** 2))
            cell["refshape"][f"rc{rc_new:.2f}"] = round(float(np.sqrt(np.trapezoid(Snew, f[b]) /
                                                                     np.trapezoid(Srr[b], f[b]))), 3)
        res[tag] = cell
    out[rk] = res
    del d, g, rate, v, press, act, lat, ldes

print(f"quantisation floor for a 1 deg/s LSB at 100 Hz: {QFLOOR:.2e} (deg/s)^2/Hz")
print()
print(f"{'route':22s} {'bin':5s} {'runs':>4s} {'secs':>6s} | {'rms 1.8-3.5':>11s} {'rms 3.5-6':>9s} "
      f"{'g2 1.8-3.5':>10s} {'g2 3.5-6':>8s} | PSD/qfloor at 2.5 / 5 / 8 / 12 Hz")
for rk, res in out.items():
    for tag, c in res.items():
        p = c["psd_vs_qfloor"]
        print(f"{rk:22s} {tag:5s} {c['n_runs']:4d} {c['secs']:6.0f} | {c['bands']['1.8-3.5']['rms_degps']:11.3f} "
              f"{c['bands']['3.5-6']['rms_degps']:9.3f} {c['bands']['1.8-3.5']['g2_mean']:10.3f} "
              f"{c['bands']['3.5-6']['g2_mean']:8.3f} | {p['2.5']:6.1f} {p['5.0']:6.1f} {p['8.0']:6.1f} {p['12.0']:6.1f}")

print()
print("NET DAMPING ENERGY PER UNIT AccordRateLoopGain, measured spectrum as the weight")
print("  (positive removes energy from the wheel, negative injects it)")
print(f"{'route':22s} {'bin':5s} {'D_loop':>6s} | {'E 1.8-3.5':>10s} {'E 3.5-6':>9s} {'E 6-10':>9s} "
      f"{'harm/help':>9s} {'E net 1-12':>11s} {'E net qcorr':>12s}")
for rk, res in out.items():
    for tag, c in res.items():
        for D in DLOOPS:
            e = c["energy"][f"D{D:.0f}"]
            print(f"{rk:22s} {tag:5s} {D:6.0f} | {e['1.8-3.5']:10.4f} {e['3.5-6']:9.4f} {e['6-10']:9.4f} "
                  f"{e['harm_over_help_1.8-3.5_vs_3.5-6']:9.2f} {e['net_1-12']:11.4f} {e['net_1-12_qcorr']:12.4f}")

print()
print("REFERENCE SHAPING -- predicted 1.8-3.5 Hz wheel-rate rms, as a fraction of today's (AccordRefFilter 0.06)")
print(f"{'route':22s} {'bin':5s} {'g2':>6s} | {'rc 0.09':>8s} {'rc 0.12':>8s} {'rc 0.16':>8s} {'rc 0.20':>8s}")
for rk, res in out.items():
    for tag, c in res.items():
        r = c["refshape"]
        print(f"{rk:22s} {tag:5s} {c['bands']['1.8-3.5']['g2_mean']:6.3f} | {r['rc0.09']:8.3f} {r['rc0.12']:8.3f} "
              f"{r['rc0.16']:8.3f} {r['rc0.20']:8.3f}")

json.dump(out, open("out/adj_energy.json", "w"), indent=1)
