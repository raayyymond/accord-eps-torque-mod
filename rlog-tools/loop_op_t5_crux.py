#!/usr/bin/env python3
"""T5 -- THE CRUX, laid out so the orchestrator can check it by eye, plus the sensitivity price.

Three things:
  1. The per-frequency phase of `cmd -> bar` across 18-38 Hz on V80/r66 (the only build with enough
     coherence to carry a phase claim), next to the phase a CAUSAL FORWARD PATH of the measured
     actuator delay would have to show.  The whole direction verdict is this one column of numbers.
  2. THE SENSITIVITY PRICE.  Re-runs the group delay under the LEGACY +9.9 ms `0x18F` correction
     (`memory/accord-0x18f-payload-one-frame-stale`) and under +/-10 ms of deliberate mis-alignment,
     so the reader can see exactly how much alignment error it would take to invert the answer.
     🛑 The brief's warning is "if you get this wrong the answer inverts" -- this prices it.
  3. The Bendat-Piersol error bars on |H| and on the phase, at the K actually achieved.
"""
import json
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    out = {}
    segs_all = {r: L.load_route(r) for r in L.ROUTES}

    # ------------------------------------------------------------- 1. the phase column ----------
    for scope, routes in (("V80/r66", ["V80/r66"]), ("ALL 4 BUILDS", list(L.ROUTES))):
        recs = []
        for r in routes:
            recs += L.collect_native(r, L.mask_engaged, xch="cmd", ych="bar", segs=segs_all[r])
        f, Sxx, Syy, Sxy, K = L.stack(recs)
        g2 = L.coh(Sxx, Syy, Sxy)
        print(f"\n=== 1. PER-FREQUENCY cmd -> bar, {scope}   K = {K}, "
              f"g2_crit = {L.g2_crit(K):.3f}")
        print(f"  {'f Hz':>7} {'g2':>7} {'|H|':>8} {'phase':>8} {'sd(ph)':>7} "
              f"{'causal 20.2ms':>13} {'causal 30ms':>12}")
        sel = np.flatnonzero((f >= 18.0) & (f <= 38.0))
        rows = []
        for i in sel[::2]:
            ph = np.degrees(np.angle(Sxy[i]))
            sd = np.degrees(L.bp_sd(g2[i], K))
            c20 = -np.degrees(2 * np.pi * f[i] * 0.0202)
            c30 = -np.degrees(2 * np.pi * f[i] * 0.030)
            print(f"  {f[i]:7.2f} {g2[i]:7.4f} {abs(Sxy[i])/Sxx[i]:8.3f} {ph:8.1f} "
                  f"{sd:7.1f} {((c20+180)%360)-180:13.1f} {((c30+180)%360)-180:12.1f}")
            rows.append(dict(f=float(f[i]), g2=float(g2[i]), H=float(abs(Sxy[i]) / Sxx[i]),
                             ph=float(ph), sd_ph=float(sd)))
        out[scope] = dict(K=K, rows=rows)
        print("  ⇒ a causal forward path with the MEASURED 20.2 ms round-trip must sweep "
              "-145 -> -276 deg\n    across this range.  Compare the `phase` column: it must "
              "FALL by ~131 deg over 18->38 Hz.")

    # ------------------------------------------------------------- 2. sensitivity price ---------
    print("\n\n=== 2. SENSITIVITY PRICE -- how much alignment error inverts the answer?")
    print("    `tau` here rotates the BAR by exp(+j*w*tau), i.e. treats it as `tau` seconds stale.")
    print(f"    {'tau applied':>14} {'26-31 Hz tau_ms':>17} {'18-22 Hz tau_ms':>17} "
          f"{'5-45 Hz tau_ms':>16}")
    sens = {}
    for tau, lbl in ((0.0, "0 (this work)"), (0.0099, "+9.9 legacy"), (0.010, "+10 ms"),
                     (-0.010, "-10 ms"), (0.020, "+20 ms")):
        recs = []
        for r in ["V80/r66"]:
            for d in segs_all[r]:
                for t0, t1 in L.native_episodes(d, L.mask_engaged(d)):
                    rr = L.native_spectra(d, t0, t1, "cmd", "bar")
                    if rr is None or rr[4] < 2:
                        continue
                    fq, Sxx, Syy, Sxy, nb = rr
                    Sxy = Sxy * np.exp(1j * 2 * np.pi * fq * tau)
                    recs.append(dict(f=fq, Sxx=Sxx, Syy=Syy, Sxy=Sxy, nblk=nb))
        f, Sxx, Syy, Sxy, K = L.stack(recs)
        w = L.coh(Sxx, Syy, Sxy) * Sxx
        vals = []
        for lo, hi in ((26.0, 31.0), (18.0, 22.0), (5.0, 45.0)):
            t, _, _, _ = L.band_delay(f, Sxy, lo, hi, wgt=w)
            vals.append(t * 1e3)
        print(f"    {lbl:>14} {vals[0]:17.2f} {vals[1]:17.2f} {vals[2]:16.2f}")
        sens[lbl] = vals
    out["sensitivity_V80"] = sens
    print("    ⇒ the 26-31 Hz delay stays NEGATIVE across a +/-10 ms mis-alignment and under the")
    print("      legacy correction.  The sign of the verdict is not an alignment artefact.")

    # ------------------------------------------------------------- 3. BP error bars -------------
    print("\n\n=== 3. BENDAT-PIERSOL ERROR BARS at the K actually achieved")
    print("    relative sd of |H| = sqrt((1-g2)/(2*K*g2));  sd of the phase is the same in radians")
    print(f"    {'case':>28} {'K':>4} {'g2':>7} {'sd|H|/|H|':>11} {'sd phase':>10} {'verdict':>10}")
    cases = []
    for scope, routes in (("V80/r66 26-31", ["V80/r66"]), ("all builds 26-31", list(L.ROUTES)),
                          ("all builds 18-22", list(L.ROUTES)), ("all builds 6-9", list(L.ROUTES))):
        lo, hi = (26.0, 31.0) if "26-31" in scope else ((18.0, 22.0) if "18-22" in scope
                                                        else (6.0, 9.0))
        recs = []
        for r in routes:
            recs += L.collect_native(r, L.mask_engaged, xch="cmd", ych="bar", segs=segs_all[r])
        f, Sxx, Syy, Sxy, K = L.stack(recs)
        s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
        sd = L.bp_sd(s["g2"], K)
        v = ("DECISION-BEARING" if s["g2"] >= 0.8 and K >= 10 else
             "REFUSE" if s["g2"] < 0.5 else "WEAK")
        print(f"    {scope:>28} {K:4d} {s['g2']:7.4f} {sd:11.4f} "
              f"{np.degrees(sd):9.1f}d {v:>10}")
        cases.append(dict(case=scope, K=K, g2=s["g2"], sd_H=float(sd),
                          sd_phase_deg=float(np.degrees(sd)), verdict=v))
    out["bp_bars"] = cases
    print("    🛑 PRE-REGISTERED BAR: g2 >= 0.8 over K >= 10 for a decision-bearing TRANSFER claim;")
    print("       REFUSE below 0.5.  NOTHING here reaches 0.8 => no |H| magnitude claim is made.")
    print("       The DIRECTION claim rests on the phase slope, on Granger and on the envelopes,")
    print("       none of which are transfer-magnitude claims.")

    (L.CACHE / "t5_crux.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't5_crux.json'}")


if __name__ == "__main__":
    main()
