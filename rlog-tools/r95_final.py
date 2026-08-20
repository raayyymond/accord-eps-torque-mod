#!/usr/bin/env python3
r"""ROUTE 95 / V101 -- THE DECIDING MEASUREMENTS.

  F-4  THE PLANT-GAIN TEST.  The one test that separates "openpilot DRIVES the oscillation" from
       "openpilot ECHOES it", using no assumption about lag.
  F-5  THE FIRMWARE-INTERNAL TEST.  b5 = sign(gp-0x6b4c) at 100 Hz IS the post-intake LKAS command.
  E-4  EVENT-TRIGGERED DECAY / RE-GROWTH around driver-torque onsets and releases.
  E-5  TORQUE SUPPRESSION AT MATCHED WHEEL RATE -- the damping-vs-operating-point split.
  C-4  RING-DOWN Q, with the kit's mandatory control (the estimator returns 79.00 on white noise).
  B-2  THE ONLY ENGAGEMENT CONTROL ON THIS ROUTE -- creep speed, engaged vs manual.

🛑 The np.correlate lag sign is VERIFIED against a synthetic delay before it is used.
"""
import json
import sys

import numpy as np

import r95_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.fs()
lat = L.engaged()
t = L.col("t")
tq, ang, rate_f = L.col("tq"), L.col("ang"), L.col("rate_f")
x6b94, sc_tq = L.col("x6b94"), L.col("sc_tq")
vms = np.abs(L.col("cs_v"))
vk = vms * 3.6
b5 = L.col("v101_b5")            # sign(gp-0x6b4c) -- the POST-INTAKE LKAS command, in-firmware
tq_sus = L.lowpass(tq, FS, 3.0, mask=lat)
out = {}
B8, B23 = (7.3, 9.3), (21.5, 25.5)


def runs(mask, min_n=1):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


RUNS = runs(lat, 512)

# ======================================================================================
print("=" * 104)
print("LAG-SIGN CALIBRATION -- np.correlate(a, v): which sign means `a` leads?")
print("=" * 104)
rng = np.random.default_rng(3)
w = rng.normal(size=4000)
DELAY = 25
a_follows = np.roll(w, DELAY)                    # a[n] = w[n-25]  => a FOLLOWS w by 25 samples
c = np.correlate(a_follows, w, mode="full")
lag_pk = int(np.argmax(c)) - (len(w) - 1)
print(f"    synthetic: a[n] = w[n-25]  (a FOLLOWS w).  peak lag index = {lag_pk:+d}")
SIGN = "POSITIVE lag => the FIRST argument FOLLOWS" if lag_pk > 0 else \
       "POSITIVE lag => the FIRST argument LEADS"
print(f"    ⇒ {SIGN}")
out["lag_sign_calibration"] = dict(synthetic_delay=DELAY, peak_lag=lag_pk, rule=SIGN)

# ======================================================================================
#  F-4.  THE PLANT-GAIN TEST
# ======================================================================================
print("\n" + "=" * 104)
print("F-4. THE PLANT-GAIN TEST  --  |cmd| / |ang| vs FREQUENCY, engaged")
print("  HYPOTHESIS A  openpilot DRIVES:  ang = P(f)*cmd, and P MUST contain the firmware's LKAS")
print("     intake low-pass (~1-5 Hz, Ghidra-established).  Then |cmd|/|ang| = 1/|P| RISES steeply")
print("     above 5 Hz -- at least (f/3.5)^2 for a 2-pole roll-off.")
print("  HYPOTHESIS B  openpilot ECHOES:  cmd = C(f)*ang with C = openpilot's own lateral")
print("     controller gain on the measured angle => |cmd|/|ang| roughly FLAT across 5-45 Hz.")
print("=" * 104)
f, coh, ph, K = L.coherence(sc_tq, ang, lat, FS, nfft=512)
_fa, Pa, _ = L.welch(ang, lat, FS, nfft=512)
_fc, Pc, _ = L.welch(sc_tq, lat, FS, nfft=512)
print(f"    K = {K} non-overlapping windows, chance coh² = {1/K:.4f}")
print(f"    {'f Hz':>8s} {'coh²':>7s} {'|cmd|/|ang| ct/deg':>20s} {'vs 3.5 Hz':>11s}  "
       f"{'A predicts':>11s}")
ref = None
gain_rows = []
for lo in np.arange(3.0, 44.0, 2.0):
    hi = lo + 2.0
    m = (f >= lo) & (f < hi)
    if not m.any():
        continue
    ra = float(np.sqrt(np.trapezoid(Pa[m], f[m])))
    rc = float(np.sqrt(np.trapezoid(Pc[m], f[m])))
    g = rc / ra
    fc_ = float(np.mean(f[m]))
    if ref is None:
        ref, fref = g, fc_
    pred_A = (fc_ / fref) ** 2
    print(f"    {fc_:8.2f} {float(coh[m].mean()):7.4f} {g:20.1f} {g/ref:11.2f}  {pred_A:11.1f}")
    gain_rows.append(dict(f=fc_, coh=float(coh[m].mean()), gain=g, rel=g / ref, predA=pred_A))
out["F4_plant_gain"] = gain_rows
hi_coh = [r for r in gain_rows if r["coh"] > 0.25]
if len(hi_coh) >= 3:
    lf = np.log10([r["f"] for r in hi_coh])
    lg = np.log10([r["gain"] for r in hi_coh])
    sl = np.polyfit(lf, lg, 1)[0]
    print(f"\n    Over the {len(hi_coh)} bins with coh² > 0.25:  d log|cmd/ang| / d log f = "
          f"{sl:+.2f}")
    print(f"      HYPOTHESIS A (openpilot drives through a >=2-pole LKAS low-pass) needs >= +2.00")
    print(f"      HYPOTHESIS B (openpilot echoes a flat controller gain) needs ~ 0.00")
    out["F4_loglog_slope"] = float(sl)

# ======================================================================================
#  F-5.  THE FIRMWARE-INTERNAL TEST -- b5 = sign(gp-0x6b4c), the POST-INTAKE LKAS command
# ======================================================================================
print("\n" + "=" * 104)
print("F-5. THE POST-INTAKE LKAS COMMAND, MEASURED IN THE FIRMWARE.")
print("  b5 = (gp-0x6b4c < 0) at 100 Hz.  If the 8x LKAS lane carried the 23 Hz oscillation, b5")
print("  would toggle AT 23 Hz whenever the slow part of the command is small.  Compare with the")
print("  sign of openpilot's RAW command, which demonstrably does carry it.")
print("=" * 104)
sgn_raw = (sc_tq < 0).astype(float)
for nm, s in (("b5  = sign(gp-0x6b4c)  POST-INTAKE, in-firmware", b5),
              ("sign(sc_tq)            openpilot's RAW command", sgn_raw)):
    fq, P, Kk = L.welch(s, lat, FS, nfft=512)
    med = float(np.median(P[(fq >= 2) & (fq <= 45)]))
    tr = float(np.sum(np.abs(np.diff(s[lat]))) / (lat.sum() / FS))
    l8 = float(P[(fq >= B8[0]) & (fq <= B8[1])].max() / med)
    l23 = float(P[(fq >= B23[0]) & (fq <= B23[1])].max() / med)
    print(f"    {nm:48s} toggles {tr:6.2f}/s   peak/median  B8 {l8:6.2f}   B23 {l23:6.2f}")
    out.setdefault("F5_sign_spectra", []).append(dict(name=nm, toggles_per_s=tr, B8=l8, B23=l23))
f2, coh2, _p, K2 = L.coherence(b5, rate_f, lat, FS, nfft=256)
f3, coh3, _p, _K = L.coherence(sgn_raw, rate_f, lat, FS, nfft=256)
for bn, (lo, hi) in (("B8", B8), ("B23", B23)):
    m = (f2 >= lo) & (f2 <= hi)
    print(f"    coh²(b5 POST-INTAKE, rate_f) {bn} = {float(coh2[m].mean()):.4f}    "
          f"coh²(sign(raw cmd), rate_f) {bn} = {float(coh3[m].mean()):.4f}   "
          f"chance {1/K2:.4f}")
    out.setdefault("F5_coh", []).append(dict(band=bn, b5=float(coh2[m].mean()),
                                             raw=float(coh3[m].mean()), chance=float(1 / K2)))

# ======================================================================================
#  E-4.  EVENT-TRIGGERED DECAY AND RE-GROWTH
# ======================================================================================
print("\n" + "=" * 104)
print("E-4. EVENT-TRIGGERED: what happens to the oscillation when the driver GRIPS and RELEASES?")
print("  GRIP   = |lowpass(tq,3Hz)| crosses 150 -> 600 counts and stays > 600 for >= 0.5 s")
print("  RELEASE= |lowpass(tq,3Hz)| crosses 600 -> 150 counts and stays < 150 for >= 0.5 s")
print("=" * 104)
ts = np.abs(tq_sus)
lo_m, hi_m = ts < 150, ts > 600
HOLD = int(0.5 * FS)


def crossings(from_m, to_m):
    ev = []
    idx = np.where(np.diff(to_m.astype(int)) == 1)[0] + 1
    for i in idx:
        if i < 2 * FS or i > len(ts) - 3 * FS:
            continue
        if not lat[i - int(FS)] or not lat[i + int(2 * FS)]:
            continue
        if not from_m[max(0, i - int(0.5 * FS)):i].all():
            continue
        if not to_m[i:i + HOLD].all():
            continue
        ev.append(i)
    return ev


GRIP = crossings(lo_m, hi_m)
REL = crossings(hi_m, lo_m)
print(f"    {len(GRIP)} GRIP events,  {len(REL)} RELEASE events")
PRE, POST = int(1.5 * FS), int(3.0 * FS)
for bn, (lo, hi) in (("B8", B8), ("B23", B23), ("CTRL 2.5-4.5", (2.5, 4.5))):
    env = L.band_envelope(tq, FS, lo, hi, mask=lat)
    for tag, EV in (("GRIP", GRIP), ("RELEASE", REL)):
        if len(EV) < 3:
            print(f"    {bn:14s} {tag:8s}: only {len(EV)} events -- CANNOT ANSWER")
            continue
        M = np.array([env[i - PRE:i + POST] for i in EV
                      if np.all(np.isfinite(env[i - PRE:i + POST]))])
        if len(M) < 3:
            print(f"    {bn:14s} {tag:8s}: {len(M)} usable -- CANNOT ANSWER")
            continue
        prof = np.median(M, axis=0)
        base = float(np.median(prof[:PRE]))
        after = float(np.median(prof[PRE + int(0.5 * FS):]))
        # time constant of the transition, fitted on the median profile
        seg = prof[PRE:PRE + int(1.5 * FS)]
        target = after
        y = np.abs(seg - target) + 1e-6
        xx = np.arange(len(seg)) / FS
        sl = np.polyfit(xx, np.log(y), 1)[0]
        tau = -1.0 / sl if sl < 0 else float("nan")
        print(f"    {bn:14s} {tag:8s}: n={len(M):2d}  pre {base:8.1f} -> post {after:8.1f}  "
              f"ratio {after/max(base,1e-9):5.2f}   tau {tau:5.2f} s")
        out.setdefault("E4_events", []).append(
            dict(band=bn, event=tag, n=int(len(M)), pre=base, post=after,
                 ratio=float(after / max(base, 1e-9)), tau_s=float(tau)))

# ======================================================================================
#  E-5.  TORQUE SUPPRESSION AT MATCHED WHEEL RATE
# ======================================================================================
print("\n" + "=" * 104)
print("E-5. IS IT |TORQUE| OR THE OPERATING POINT?  Stratify by |driver torque| INSIDE narrow")
print("     |wheel rate| bands, at v >= 5 m/s.  If the suppression survives at matched rate it is")
print("     a DAMPING (describing-function) effect, not an operating-point effect.")
print("=" * 104)
WL = int(round(2.0 * FS))
rowsE = []
bp8 = L.bandpass(tq, FS, *B8, mask=lat)
bp23 = L.bandpass(tq, FS, *B23, mask=lat)
bpr8 = L.bandpass(rate_f, FS, *B8, mask=lat)
for a, b in runs(lat, WL):
    for i in range(a, b - WL + 1, WL):
        sl = slice(i, i + WL)
        rowsE.append(dict(
            v=float(np.median(vms[sl])), rate=float(np.median(np.abs(rate_f[sl]))),
            tqs=float(np.median(ts[sl])), angoff=float(np.median(np.abs(ang[sl] + 4.25))),
            r8=float(np.sqrt(np.nanmean(bp8[sl] ** 2))),
            r23=float(np.sqrt(np.nanmean(bp23[sl] ** 2))),
            rr8=float(np.sqrt(np.nanmean(bpr8[sl] ** 2)))))
E = {k: np.array([r[k] for r in rowsE]) for k in rowsE[0]}
print(f"    {'|rate| band':>16s} {'tq bin':>14s} {'n':>4s} {'v':>5s} {'|ang-c|':>8s} "
      f"{'tq B8 RMS':>10s} {'tq B23 RMS':>11s} {'rate B8':>9s}")
for rlo, rhi in ((0, 8), (8, 20), (20, 40), (40, 200)):
    m0 = (E["v"] >= 5.0) & (E["rate"] >= rlo) & (E["rate"] < rhi)
    if m0.sum() < 6:
        continue
    med = np.median(E["tqs"][m0])
    for tag, m in (("LOW  tq", m0 & (E["tqs"] <= med)), ("HIGH tq", m0 & (E["tqs"] > med))):
        print(f"    {rlo:6d}-{rhi:<8d} {tag:>14s} {int(m.sum()):4d} {np.median(E['v'][m]):5.1f} "
              f"{np.median(E['angoff'][m]):8.2f} {np.median(E['r8'][m]):10.1f} "
              f"{np.median(E['r23'][m]):11.1f} {np.median(E['rr8'][m]):9.2f}")
    r8 = np.median(E["r8"][m0 & (E["tqs"] > med)]) / np.median(E["r8"][m0 & (E["tqs"] <= med)])
    r23 = np.median(E["r23"][m0 & (E["tqs"] > med)]) / np.median(E["r23"][m0 & (E["tqs"] <= med)])
    print(f"    {'':16s} {'HIGH/LOW ratio':>14s}      tq_median {med:6.0f} counts   "
          f"B8 {r8:5.3f}   B23 {r23:5.3f}")
    out.setdefault("E5_matched_rate", []).append(
        dict(rate_lo=rlo, rate_hi=rhi, n=int(m0.sum()), tq_median=float(med),
             ratio_B8=float(r8), ratio_B23=float(r23)))

# ======================================================================================
#  C-4.  RING-DOWN Q, WITH THE CONTROL
# ======================================================================================
print("\n" + "=" * 104)
print("C-4. RING-DOWN Q.  🛑 THE CONTROL RUNS FIRST: the same estimator on WHITE NOISE and on a")
print("     phase-randomised surrogate.  A Q that the controls also produce is NOT a measurement.")
print("=" * 104)


def ringdowns(x, lo, hi, mask, label):
    env = L.band_envelope(x, FS, lo, hi, mask=mask)
    sm = np.convolve(np.nan_to_num(env), np.ones(int(0.15 * FS)) / int(0.15 * FS), mode="same")
    ee = env[mask]
    ee = ee[np.isfinite(ee)]
    hi_thr, lo_thr = np.percentile(ee, 80), np.percentile(ee, 30)
    zs = []
    fc = 0.5 * (lo + hi)
    for a, b in runs(mask, 512):
        e = sm[a:b]
        i = 0
        while i < len(e) - 1:
            if e[i] < hi_thr:
                i += 1
                continue
            j = i
            while j < len(e) and e[j] > lo_thr:
                j += 1
            if j >= len(e):
                break
            if (j - i) >= int(0.3 * FS):
                y = np.log(np.maximum(e[i:j], 1e-9))
                xx = np.arange(j - i) / FS
                A = np.vstack([xx, np.ones_like(xx)]).T
                beta, *_ = np.linalg.lstsq(A, y, rcond=None)
                r2 = 1 - np.var(y - A @ beta) / max(np.var(y), 1e-30)
                if beta[0] < 0 and r2 > 0.90:
                    zeta = -beta[0] / (2 * np.pi * fc)
                    zs.append(zeta)
            i = max(j, i + 1)
    if not zs:
        print(f"    {label:44s} NO qualifying ring-downs")
        return None
    zs = np.array(zs)
    Q = 1.0 / (2 * zs)
    print(f"    {label:44s} n={len(zs):3d}  zeta p50 {np.median(zs):.4f} "
          f"[p25 {np.percentile(zs,25):.4f}, p75 {np.percentile(zs,75):.4f}]   "
          f"Q p50 {np.median(Q):6.1f}")
    return dict(label=label, n=int(len(zs)), zeta=float(np.median(zs)), Q=float(np.median(Q)))


rngc = np.random.default_rng(5)
white = rngc.normal(size=len(tq))
res = []
for lo, hi, nm in ((B23[0], B23[1], "B23"), (B8[0], B8[1], "B8")):
    r = ringdowns(white, lo, hi, lat, f"CONTROL white noise, {nm}")
    if r:
        res.append(r)
    bp = L.bandpass(tq, FS, lo, hi, mask=lat)
    sur = np.copy(bp)
    for a, b in RUNS:
        X = np.fft.rfft(np.nan_to_num(bp[a:b]))
        phz = rngc.uniform(0, 2 * np.pi, len(X))
        phz[0] = 0
        sur[a:b] = np.fft.irfft(np.abs(X) * np.exp(1j * phz), n=b - a)
    r = ringdowns(sur, lo, hi, lat, f"CONTROL phase-surrogate of tq, {nm}")
    if r:
        res.append(r)
    r = ringdowns(tq, lo, hi, lat, f"MEASURED tq, {nm}")
    if r:
        res.append(r)
    r = ringdowns(rate_f, lo, hi, lat, f"MEASURED rate_f, {nm}")
    if r:
        res.append(r)
out["C4_ringdown"] = res

# ======================================================================================
#  B-2.  THE ONLY ENGAGEMENT CONTROL ON THIS ROUTE
# ======================================================================================
print("\n" + "=" * 104)
print("B-2. ENGAGED vs MANUAL.  🛑 Manual exposure on route 95 is 79.4 s and its p99 speed is")
print("     7.0 km/h -- there is NO LKAS-off control at road speed.  The ONLY matched contrast")
print("     available is at CREEP speed.")
print("=" * 104)
for vlo, vhi in ((0.3, 2.0), (0.3, 1.0), (1.0, 2.0)):
    me = lat & (vms >= vlo) & (vms < vhi)
    mm = (~lat) & (vms >= vlo) & (vms < vhi)
    if me.sum() < 400 or mm.sum() < 400:
        print(f"    {vlo}-{vhi} m/s: engaged {me.sum()/FS:.1f} s  manual {mm.sum()/FS:.1f} s "
              f"-- too little")
        continue
    print(f"    {vlo}-{vhi} m/s   engaged {me.sum()/FS:6.1f} s   manual {mm.sum()/FS:6.1f} s   "
          f"v_med eng {np.median(vms[me]):.2f}  man {np.median(vms[mm]):.2f} m/s")
    for ch, x in (("tq", tq), ("rate_f", rate_f)):
        for bn, (lo, hi) in (("B8", B8), ("B23", B23), ("CTRL", (2.5, 4.5))):
            fe, Pe, Ke = L.welch(x, me, FS, nfft=256)
            fm, Pm, Km = L.welch(x, mm, FS, nfft=256)
            if Ke == 0 or Km == 0:
                continue
            b = (fe >= lo) & (fe <= hi)
            re_ = float(np.sqrt(np.trapezoid(Pe[b], fe[b])))
            rm_ = float(np.sqrt(np.trapezoid(Pm[b], fm[b])))
            print(f"        {ch:7s} {bn:5s}  engaged RMS {re_:9.2f} (K={Ke})   manual RMS "
                  f"{rm_:9.2f} (K={Km})   ratio {re_/max(rm_,1e-9):6.2f}x")
            out.setdefault("B2_engaged_vs_manual", []).append(
                dict(v_lo=vlo, v_hi=vhi, ch=ch, band=bn, eng=re_, man=rm_, Ke=Ke, Km=Km,
                     ratio=float(re_ / max(rm_, 1e-9))))

(L.CACHE / "r95_FINAL.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_FINAL.json'}")
