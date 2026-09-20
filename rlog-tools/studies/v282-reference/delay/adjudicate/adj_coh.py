"""ADJUDICATION, part B2 -- how much of the 1.8-3.5 Hz low-speed shake is DEMAND-COHERENT, pooled and with the
coherence bias floor stated.  The reference-shaping candidate's whole reach is this number, so it is checked
with the averaging count in front of it (gamma^2 is biased UP by 1/nave with few averages).

Pooled over the 5 V293 torque routes, hands-off laterally engaged, 3-8 m/s and <8 m/s, nperseg 256 (2.56 s,
df 0.39 Hz) to buy averages.  Reference signals tried:
  cs_la_des  = controlsState...desiredLateralAccel  (the setpoint AFTER the 0.06 ref filter -- the right one,
               because the candidate multiplies exactly this signal's 1.8-3.5 Hz content by |Hnew/Hold|)
  cs_err     = the P/I error, as a cross-check on whether the band is error-driven or disturbance-driven
"""
import numpy as np
from scipy import signal

CACHE = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
ROUTES = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
FS, NPER = 100.0, 256
BINS = [("<8", 0.0, 8.0), ("3-8", 3.0, 8.0), ("8-12", 8.0, 12.0)]


def ratio2(f, rc_new, rc_old=0.06):
    w = 2 * np.pi * f
    return (1 + (w * rc_old) ** 2) ** 2 / (1 + (w * rc_new) ** 2) ** 2   # |Hnew/Hold|^2, two cascaded lags


acc = {t: {"Srr": None, "Sdd": None, "Srd": None, "See": None, "Sre": None,
           "nave": 0, "secs": 0.0, "routes": set()} for t, _, _ in BINS}
for rk in ROUTES:
    d = np.load(f"{CACHE}/{rk}.npz")
    t = d["t_cst"]
    g = np.arange(t[0], t[-1], 1.0 / FS)
    rate = np.interp(g, t, d["sr_deg"]); v = np.interp(g, t, d["vego"])
    press = np.interp(g, t, d["spress"]) > 0.5
    act = np.interp(g, d["t_cs"], d["cs_active"]) > 0.5
    lat = np.interp(g, d["t_cc"], d["lat_active"]) > 0.5
    ldes = np.interp(g, d["t_cs"], d["cs_la_des"]); err = np.interp(g, d["t_cs"], d["cs_err"])
    near = np.abs(g - t[np.clip(np.searchsorted(t, g), 0, len(t) - 1)]) < 0.025
    base = act & lat & ~press & near
    for tag, lo, hi in BINS:
        m = base & (v >= lo) & (v < hi)
        idx = np.where(m)[0]
        if len(idx) == 0:
            continue
        for c in np.split(idx, np.where(np.diff(idx) > 1)[0] + 1):
            if len(c) < NPER:
                continue
            nave = (len(c) - NPER) // (NPER // 2) + 1
            kw = dict(fs=FS, nperseg=NPER, detrend="linear")
            f, srr = signal.welch(rate[c], **kw)
            _, sdd = signal.welch(ldes[c], **kw)
            _, see = signal.welch(err[c], **kw)
            _, srd = signal.csd(ldes[c], rate[c], **kw)
            _, sre = signal.csd(err[c], rate[c], **kw)
            a = acc[tag]
            for k, s in (("Srr", srr), ("Sdd", sdd), ("See", see), ("Srd", srd), ("Sre", sre)):
                a[k] = s * nave if a[k] is None else a[k] + s * nave
            a["nave"] += nave; a["secs"] += len(c) / FS; a["routes"].add(rk)
    del d, g, rate, v, press, act, lat, ldes, err

print(f"{'bin':5s} {'routes':>6s} {'secs':>6s} {'nave':>5s} {'g2floor':>8s} | "
      f"{'g2(des) 1.8-3.5':>15s} {'g2(err) 1.8-3.5':>15s} {'rms 1.8-3.5':>11s} | "
      f"predicted 1.8-3.5 rms / today at AccordRefFilter 0.09 / 0.12 / 0.16")
for tag, _, _ in BINS:
    a = acc[tag]
    if a["nave"] == 0:
        continue
    Srr, Sdd, See, Srd, Sre = (a[k] / a["nave"] for k in ("Srr", "Sdd", "See", "Srd", "Sre"))
    g2d = np.abs(Srd) ** 2 / np.maximum(Srr * Sdd, 1e-30)
    g2e = np.abs(Sre) ** 2 / np.maximum(Srr * See, 1e-30)
    b = (f >= 1.8) & (f <= 3.5)
    wd = float(np.average(g2d[b], weights=Srr[b])); we = float(np.average(g2e[b], weights=Srr[b]))
    rms = float(np.sqrt(np.trapezoid(Srr[b], f[b])))
    pred = []
    for rc in (0.09, 0.12, 0.16):
        Sn = Srr[b] * (1 - g2d[b] * (1 - ratio2(f[b], rc)))
        pred.append(np.sqrt(np.trapezoid(Sn, f[b]) / np.trapezoid(Srr[b], f[b])))
    print(f"{tag:5s} {len(a['routes']):6d} {a['secs']:6.0f} {a['nave']:5d} {1.0/a['nave']:8.3f} | "
          f"{wd:15.3f} {we:15.3f} {rms:11.2f} | " + "   ".join(f"{p:5.3f}" for p in pred))
    # where in the band is the coherence?
    print(f"{'':5s} g2(des) by 0.39 Hz bin, 1.6-4.0 Hz: " +
          " ".join(f"{f[i]:.2f}:{g2d[i]:.2f}" for i in np.where((f >= 1.6) & (f <= 4.0))[0]))
