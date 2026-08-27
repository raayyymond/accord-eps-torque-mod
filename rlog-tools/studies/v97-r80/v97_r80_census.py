#!/usr/bin/env python3
r"""Route 80 (V97 flight) -- regime census + probe liveness.  Reads `_scratch/cache/r80/r80.npz` only.

🛑 raw14 OFF-BY-ONE: `t` == `raw14_t[1:]` and `probe` == `raw14_b4[1:]`.  This file uses the
`row2raw14` index map written by `extract_r7d.extract_route`, which is ASSERTED elementwise, so
byte 7 is paired with the row grid correctly.  Never pair `t` with `raw14_b4` directly.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
CACHE = ROOT / "analysis-2020accord" / "_scratch/cache/r80"

KMH = 3.6


def pct(x, q):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.percentile(x, q)) if len(x) else float("nan")


def main():
    z = np.load(CACHE / "r80.npz", allow_pickle=True)
    out = {}
    t = np.asarray(z["t"], float)
    n = len(t)
    idx = np.asarray(z["row2raw14"], int)
    b4 = (np.asarray(z["raw14_b4"], int) & 0xFF)[idx]
    b7 = (np.asarray(z["raw14_b7"], int) & 0xFF)[idx]
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF)), "row2raw14 map broken"

    # ---- cave decode, V96/V97 map (builds/v80_v107/build_v96_tva.py THE PAYLOAD)
    sign_6b70 = (b4 >> 7) & 1          # gp-0x6b70 < 0
    sign_374c = (b4 >> 6) & 1          # (gp-0x374c>>4) < 0
    Mhi = ((b4 >> 4) & 0x03)           # min(|v|>>12, 3), SATURATING
    mode_rung = (b4 >> 3) & 1          # gp-0x674e < 28
    Mlo = (b7 >> 7) & 1                # bit 11 of |v|
    ident = (b7 >> 6) & 1              # constant 1
    M = 2 * Mhi + Mlo                  # == |v|>>11 exactly when Mhi < 3

    eng = np.asarray(z["cc_lat"], float) > 0.5
    v = np.asarray(z["cs_v"], float)
    rate = np.asarray(z["cs_rate"], float)
    ang = np.asarray(z["cs_ang"], float)
    tq = np.asarray(z["tq"], float)          # 0x18F STEER_TORQUE_SENSOR (scaled -1.0)
    press = np.asarray(z["cs_press"], float) > 0.5

    print(f"route 80: {n:,} rows  {t[-1]:.1f} s   engaged(latActive) {eng.mean()*100:.1f} % "
          f"= {eng.sum()*0.01:.1f} s   manual {(~eng).sum()*0.01:.1f} s")

    out["frames"] = int(n)
    out["duration_s"] = float(t[-1])
    out["engaged_frames"] = int(eng.sum())
    out["manual_frames"] = int((~eng).sum())

    # ---- REGIME CENSUS
    print("\n=== REGIME CENSUS ===")
    for nm, sel in (("ALL", np.ones(n, bool)), ("ENGAGED", eng), ("MANUAL", ~eng)):
        if sel.sum() < 10:
            continue
        vk = v[sel] * KMH
        r = np.abs(rate[sel])
        a = ang[sel]
        print(f"  {nm:8s} n={sel.sum():6,}  speed km/h p05/p50/p95/max "
              f"{pct(vk,5):5.2f}/{pct(vk,50):5.2f}/{pct(vk,95):5.2f}/{vk.max():5.2f}  "
              f"|rate| deg/s p50/p95/max {pct(r,50):6.2f}/{pct(r,95):6.2f}/{r.max():7.2f}  "
              f"angle {a.min():7.1f}..{a.max():7.1f} deg")
        out[f"census_{nm}"] = dict(
            n=int(sel.sum()), speed_kph=dict(p05=pct(vk, 5), p50=pct(vk, 50), p95=pct(vk, 95),
                                             max=float(vk.max())),
            abs_rate_dps=dict(p50=pct(r, 50), p95=pct(r, 95), max=float(r.max())),
            angle_deg=dict(min=float(a.min()), max=float(a.max())),
            steering_pressed_duty=float(press[sel].mean()))

    # ---- DEAD ZONES the brief named
    print("\n=== DEAD ZONES ===")
    lock = v * KMH < 5.0                      # 0xC62EA low-speed steer lockout ~5 km/h (320 ct)
    dampC = v * KMH >= 35.0                   # base-assist damper FactorC dead zone
    dampE = np.abs(rate) >= 12.7              # FactorE dead zone
    for nm, sel in (("ALL", np.ones(n, bool)), ("ENGAGED", eng)):
        print(f"  {nm:8s} below 5 km/h (0xC62EA lockout window): "
              f"{lock[sel].mean()*100:6.2f} %   "
              f"FactorC open (>=35 km/h): {dampC[sel].mean()*100:5.2f} %   "
              f"FactorE open (>=12.7 deg/s): {dampE[sel].mean()*100:5.2f} %   "
              f"BOTH open: {(dampC & dampE)[sel].mean()*100:5.2f} %")
        out[f"deadzone_{nm}"] = dict(below_5kph=float(lock[sel].mean()),
                                     factorC_open=float(dampC[sel].mean()),
                                     factorE_open=float(dampE[sel].mean()),
                                     both_open=float((dampC & dampE)[sel].mean()))
    su, sc = np.unique(np.asarray(z["sstat"], int), return_counts=True)
    out["steer_status_hist"] = {int(a): int(b) for a, b in zip(su, sc)}
    print("  0x18F STEER_STATUS histogram: " + "  ".join(f"{int(a)}:{int(b):,}"
                                                         for a, b in zip(su, sc)))

    # ---- PROBE LIVENESS
    print("\n=== PROBE LIVENESS (the cave) ===")
    for nm, sel in (("ALL", np.ones(n, bool)), ("ENGAGED", eng), ("MANUAL", ~eng)):
        if sel.sum() < 10:
            continue
        print(f"  {nm:8s} b7 sign(gp-0x6b70)<0 duty {sign_6b70[sel].mean():.4f} | "
              f"b6 sign(374c)<0 duty {sign_374c[sel].mean():.4f} | "
              f"Mhi duty>0 {np.mean(Mhi[sel] > 0):.4f} | Mhi==3 (SAT) {np.mean(Mhi[sel] == 3):.4f} | "
              f"Mlo duty {Mlo[sel].mean():.4f} | M>0 {np.mean(M[sel] > 0):.4f} | "
              f"mode b3 {mode_rung[sel].mean():.4f} | ident b6 {ident[sel].mean():.4f}")
        out[f"probe_{nm}"] = dict(
            sign_6b70_duty=float(sign_6b70[sel].mean()),
            sign_374c_duty=float(sign_374c[sel].mean()),
            Mhi_nonzero=float(np.mean(Mhi[sel] > 0)), Mhi_sat=float(np.mean(Mhi[sel] == 3)),
            Mlo_duty=float(Mlo[sel].mean()), M_nonzero=float(np.mean(M[sel] > 0)),
            mode_rung=float(mode_rung[sel].mean()), identity=float(ident[sel].mean()))
    mu, mc = np.unique(M, return_counts=True)
    out["M_hist"] = {int(a): int(b) for a, b in zip(mu, mc)}
    print("  M = |gp-0x374c>>4|>>11 histogram: " + "  ".join(f"{int(a)}:{int(b):,}"
                                                             for a, b in zip(mu, mc)))
    print("  => |gp-0x374c>>4| lies in [%d, %d) counts for %.2f %% of frames"
          % (0, 2048, 100 * np.mean(M == 0)))

    # ---- 427 LANE = gp-0x6b70, de-rectified with the sign bit
    print("\n=== 427 LANE  gp-0x6b70 (PID reference) ===")
    abt = np.asarray(z["ab_t1ab"], float)
    mt = np.asarray(z["ab_mt"], int)
    counts = mt * (64.0 / 5.0)
    # de-rectify: nearest-neighbour the 100 Hz sign bit onto the 50 Hz 427 grid
    j = np.clip(np.searchsorted(t, abt), 0, n - 1)
    sgn = np.where(sign_6b70[j] == 1, -1.0, 1.0)
    signed = counts * sgn
    eng_ab = eng[j]
    out["lane427"] = dict(
        frames=int(len(mt)), rate_hz=float(1.0 / np.median(np.diff(abt))),
        nonzero=float(np.mean(mt != 0)), distinct=int(len(np.unique(mt))),
        wire_max=int(mt.max()), wire_sat_frac=float(np.mean(mt >= 1023)),
        counts_p50=pct(counts, 50), counts_p95=pct(counts, 95), counts_p99=pct(counts, 99),
        counts_max=float(counts.max()), clamp=8192,
        frac_of_clamp_p99=float(pct(counts, 99) / 8192.0),
        lsb_counts=12.8)
    print(f"  {len(mt):,} frames @ {out['lane427']['rate_hz']:.2f} Hz  nonzero "
          f"{100*out['lane427']['nonzero']:.2f} %  distinct {out['lane427']['distinct']}  "
          f"sat {100*out['lane427']['wire_sat_frac']:.3f} %")
    print(f"  |gp-0x6b70| counts  p50 {out['lane427']['counts_p50']:.0f}  p95 "
          f"{out['lane427']['counts_p95']:.0f}  p99 {out['lane427']['counts_p99']:.0f}  max "
          f"{out['lane427']['counts_max']:.0f}   clamp +-8192  (p99 = "
          f"{100*out['lane427']['frac_of_clamp_p99']:.1f} % of clamp)  LSB 12.8 ct")
    for nm, sel in (("ENGAGED", eng_ab), ("MANUAL", ~eng_ab)):
        if sel.sum() < 10:
            continue
        print(f"    {nm:8s} n={sel.sum():5,}  |b70| p50 {pct(counts[sel],50):6.0f} p95 "
              f"{pct(counts[sel],95):6.0f}   signed p50 {pct(signed[sel],50):7.0f}  "
              f"neg-duty {np.mean(sgn[sel] < 0):.4f}")
        out[f"lane427_{nm}"] = dict(n=int(sel.sum()), abs_p50=pct(counts[sel], 50),
                                    abs_p95=pct(counts[sel], 95),
                                    signed_p50=pct(signed[sel], 50),
                                    neg_duty=float(np.mean(sgn[sel] < 0)))

    np.savez_compressed(CACHE / "r80_decoded.npz", t=t, b4=b4, b7=b7, sign_6b70=sign_6b70,
                        sign_374c=sign_374c, Mhi=Mhi, Mlo=Mlo, M=M, mode_rung=mode_rung,
                        eng=eng.astype(np.int8), ab_t=abt, ab_counts=counts, ab_signed=signed,
                        ab_eng=eng_ab.astype(np.int8))
    (CACHE / "r80_census.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {CACHE/'r80_census.json'} and r80_decoded.npz")


if __name__ == "__main__":
    main()
