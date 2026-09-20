"""THE BUDGET.  For every regime cell: the MEASURED gap, and how much of it each of the four mechanisms
can reach.  Each mechanism's reach is ARITHMETIC ON ITS OWN TRANSFER or a MEASURED contrast -- never a
closed-loop simulation.  The boundary is stated in each column's note.

  (a) LOOP DELAY 55-75 ms.  |exp(-j w D)| = 1 identically -> reach on |H| is EXACTLY 0.000, at every
      frequency, speed and amplitude.  D is also COMMON to both builds (D_ctl 11.0 ms measured the same
      on V282; D_act is the 0xE4 -> carState leg, the same hardware) and flat in speed, so its reach on
      the GAP is 0.000 in magnitude and 0.000 in lag.  The only magnitude in the measured actuation law
      is its 5 Hz pole, printed, and that pole is the firmware output-lag cell (992/1024 = 5.05 Hz),
      unchanged by V293 -> also common.  Reach on the gap: 0.
  (b) SATURATION.  Reach bounded by the railed duty in the cell: |H| is an input-power-weighted ratio,
      so altering the response on a fraction d of frames moves it by at most O(d).  d measured here.
  (c) HOLD-FF DEFICIT +0.0231 torque.  Reach expressed as its share of the cell's own median |command|,
      and as whether the cell is measurable at all.
  (d) OBSERVER.  Reach MEASURED as the ON/OFF contrast at the same cut: (H_TON - H_TOFF) as a share of
      (H_TON - H_V282).  r75 is the only observer-OFF drive that exists; its confounds are listed.
"""
import sys, json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import OUT

GR = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
      "TON": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d"],
      "TOFF": ["00000075--6c8687d5bd"]}
# measured railed duty, |output| >= 0.995 on laterally-engaged hands-off frames (crux.py section 1)
DUTY = {("V282", "0-8"): 0.022638, ("V282", "8-15"): 0.0, ("V282", "15-22"): 0.0, ("V282", "22-40"): 0.0,
        ("TON", "0-8"): (0.35 + 0.14 + 0.0) / (213.0 + 182.1 + 87.6), ("TON", "8-15"): 0.0,
        ("TON", "15-22"): 0.0, ("TON", "22-40"): 0.0,
        ("TOFF", "0-8"): 0.03 / 218.4, ("TOFF", "8-15"): 0.0, ("TOFF", "15-22"): 0.0, ("TOFF", "22-40"): 0.0}
# measured median |command| per group at 0-8 m/s (attrib.py section 5); the deficit is 0.0231 torque
CMD08 = {"V282": 0.0346, "TON": 0.0968, "TOFF": 0.0440}
DEF = 0.0231


def main():
    D = json.load(open(OUT / "decomp.json"))
    bands = []
    for r in D:
        if r["band"] not in bands:
            bands.append(r["band"])
    print("=" * 152)
    print("THE BUDGET.  H_dwn = setpoint -> achieved (the EPS+plant leg; the fork's demand shaping is divided out).")
    print("  'gap' = H_dwn(group) - H_dwn(V282) at the same band x speed.  Coherence floor 0.5 on every route used.")
    print("=" * 152)
    hdr = (f"{'band':11s} {'v':7s} {'n rt':>5s} {'H_dwn V282':>11s} {'H_dwn TON':>10s} {'gap':>7s} "
           f"{'H_dwn TOFF':>11s} {'gap':>7s} || {'(a) max|dH|':>11s} {'(b) max|dH|':>11s} {'(c) holdFF':>11s} "
           f"{'(d) obs share':>14s} {'residual':>9s}")
    print(hdr)
    rows = []
    for bn in bands:
        fc = float(bn.split("-")[0]) * 0.5 + float(bn.split("-")[1]) * 0.5
        for v in ["0-8", "8-15", "15-22", "22-40"]:
            g = {}
            for gname, rks in GR.items():
                sel = [r for r in D if r["band"] == bn and r["v"] == v and r["rk"] in rks and r["cd"] > 0.5]
                if not sel:
                    continue
                g[gname] = dict(H=float(np.median([r["Hd"] for r in sel])),
                                lag=float(np.median([r["ld"] for r in sel])),
                                n=len(set(r["rk"] for r in sel)),
                                sec=sum(r["secs"] for r in sel))
            if "V282" not in g or "TON" not in g:
                continue
            g0, g1 = g["V282"], g["TON"]
            gap = g1["H"] - g0["H"]
            g2 = g.get("TOFF")
            gap2 = (g2["H"] - g0["H"]) if g2 else float("nan")
            # (a)
            a_reach = 0.0
            pole = 1.0 / math.hypot(1.0, fc / 5.0)
            # (b)
            b_reach = DUTY.get(("TON", v), 0.0)
            # (c)
            c_share = DEF / CMD08["TON"] if v == "0-8" else 0.0
            # (d): the ON/OFF contrast, as a share of the gap
            d_share = ((g1["H"] - g2["H"]) / gap) if (g2 and abs(gap) > 1e-6) else float("nan")
            resid = gap - a_reach - math.copysign(min(b_reach, abs(gap)), gap)
            print(f"{bn:11s} {v:7s} {g0['n']}/{g1['n']}  {g0['H']:11.3f} {g1['H']:10.3f} {gap:+7.3f} "
                  f"{(f'{g2[chr(72)]:.3f}' if g2 else '--'):>11s} {gap2:+7.3f} || "
                  f"{a_reach:10.3f} {b_reach:9.5f} "
                  f"{(f'{c_share:.2f} of cmd' if v=='0-8' else 'n/a (v>=8)'):>11s} "
                  f"{(f'{d_share:+.2f}' if d_share == d_share else '--'):>14s} {resid:+9.3f}")
            rows.append(dict(band=bn, v=v, H0=g0["H"], H1=g1["H"], gap=gap, H2=(g2["H"] if g2 else None),
                             gap2=(gap2 if gap2 == gap2 else None), pole=pole, b=b_reach,
                             d_share=(d_share if d_share == d_share else None), resid=resid,
                             lag0=g0["lag"], lag1=g1["lag"], lag2=(g2["lag"] if g2 else None)))
    json.dump(rows, open(OUT / "budget.json", "w"), indent=1)

    print("\n" + "=" * 152)
    print("(a) DELAY -- the full algebra, so the zero is checkable.  |H| of a pure delay, and of the measured")
    print("    actuation pole, at each band centre.  A delay's magnitude is 1 by construction; the pole is common")
    print("    to both builds.  The phase column is what the delay DOES own, and it owns it EQUALLY on both builds.")
    print("=" * 152)
    print(f"{'band':11s} {'fc Hz':>6s} {'|e^-jwD|':>9s} {'|1/(1+jf/5)|':>13s} "
          f"{'phase @55ms':>12s} {'@65':>7s} {'@75':>7s} {'phase delay s':>14s}")
    for bn in bands:
        f1, f2 = [float(x) for x in bn.split("-")]
        fc = 0.5 * (f1 + f2)
        print(f"{bn:11s} {fc:6.3f} {1.0:9.3f} {1.0/math.hypot(1.0, fc/5.0):13.4f} "
              f"{-360*fc*0.055:12.1f} {-360*fc*0.065:7.1f} {-360*fc*0.075:7.1f} {0.065:14.3f}")

    print("\n" + "=" * 152)
    print("(b) SATURATION -- the bound, spelled out.  duty = railed seconds / laterally-engaged hands-off seconds.")
    print("=" * 152)
    for k in sorted(DUTY):
        print(f"   {k[0]:5s} {k[1]:7s} duty {100*DUTY[k]:8.4f} %   -> reach on a |H| of ~1 is at most "
              f"{DUTY[k]:.5f} ({100*DUTY[k]:.3f} %)")
    print("   THE REFERENCE RAILS 14-165x MORE THAN TORQUE MODE BELOW 8 m/s (2.26 % vs 0.14 %), so saturation")
    print("   cannot be what makes torque mode worse than V282 anywhere -- and above 8 m/s neither build rails at all.")

    print("\n" + "=" * 152)
    print("(d) OBSERVER -- the contrast, and everything it is confounded with (all read from r75's own initData).")
    print("=" * 152)
    print("   r75 (TOFF) differs from the TON routes in SIX ways, not one:  AccordDobHz ABSENT (observer off) ;")
    print("   AccordTorqueKi 0.6 + AccordTorqueKiHigh 2.5 (a Ki SCHEDULE, vs a flat 0.3) ; SteerKP 0.85 (vs 1.0) ;")
    print("   AccordRateLoopGain 0.0006 (vs 0.001) ; AccordRefFilter 0.12 (vs 0.06 on 6c/6d/6e) ;")
    print("   SteerFriction 0.212 (vs 0.0 on 6c/6e/76 -- 6d also ran 0.212).  A single-route contrast across six")
    print("   changes cannot assign a share to one of them; the column above is an UPPER bound on the observer's")
    print("   share and it is the sum of all six.")


def admissibility_cost():
    """How much data the coherence / n / split-half floors cost, band by band."""
    P = json.load(open(OUT / "pooled.json"))
    print("\n" + "=" * 152)
    print("ADMISSIBILITY COST -- seconds of laterally-engaged hands-off data that entered a cell vs the seconds")
    print("  that survived coh >= 0.55 and n >= 8.  Per band, per group.  (The frames are never 'thrown away' from")
    print("  the drive; they are excluded from a |H| READING because the demand does not explain the output there.)")
    print("=" * 152)
    bands = []
    for k in P:
        bn = k.split("|")[0]
        if bn not in bands:
            bands.append(bn)
    print(f"{'band':11s} " + "".join(f"{g:>26s}" for g in ("V282", "TON", "TOFF", "V282old")))
    print(f"{'':11s} " + "".join(f"{'sec in / sec adm / %':>26s}" for _ in range(4)))
    for bn in bands:
        line = f"{bn:11s} "
        for g in ("V282", "TON", "TOFF", "V282old"):
            tin = sum(cr[g]["secs"] for k, cr in P.items() if k.startswith(bn + "|") and g in cr)
            tad = sum(cr[g]["secs"] for k, cr in P.items() if k.startswith(bn + "|") and g in cr and cr[g]["adm"])
            line += f"{tin:9.0f} /{tad:8.0f} /{(100*tad/max(tin,1e-9)):5.0f}%"
        print(line)


if __name__ == "__main__":
    main()
    admissibility_cost()
