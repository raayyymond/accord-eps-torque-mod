#!/usr/bin/env python3
r"""v95_override_authority_chatter.py -- THE DECISIVE OVERRIDE TEST.

Two candidate mechanisms, both firing on a threshold being crossed repeatedly during override, both
predicting the same measurable signature: crossings clustering at 6-9 Hz.

  A. THE DRIVER-OVERRIDE AUTHORITY CURVE (tables 0xCBA74 / 0xCBA04, byte-verified)
        gp-0x682f = min(|gp-0x4f60| >> 5, 255)
        X = [70, 72, 78, 80] raw-byte  =>  raw knots 2240 / 2304 / 2496 / 2560
        Y = [254, 234, 12, 0]          =>  FULL authority below 2240, EXACTLY ZERO by 2560
        downstream IIR pole 992/1024   =>  tau ~ 31.5 ms, corner ~ 5.05 Hz
     A driver whose torque oscillates across ~2240 makes LKAS authority collapse and recover --
     assist appearing and disappearing.  Amplitude-triggered, not proportional: a switch, not a dose.
     🛑 The curve reads sign(gp-0x4f60) only to pick a MIRRORED table, so it collapses on ANY strong
        driver torque, with or against the command.  Condition on MAGNITUDE, never on opposition.

  B. THE COMMAND-DIRECTION REVERSAL.  The sign-guard relay is gated by gp-0x6806, decoded from
     openpilot's own CAN request state, not from the torque sensor.  If the request bit holds through
     an override the relay never arms; but if the command DIRECTION reverses, a re-armed ramp state
     machine would fire on every reversal.  ⚠ openpilot's 0x0E4 has no explicit direction field in
     the DBC, so direction is proxied here by sign(sc_tq) and that proxy is stated, not hidden.

🛑 WHY THIS FILE USES NO WELCH WINDOWS.  Override is a FLICKER, not a state: 5013 contiguous runs
   make up the corpus's 994.9 s, median run 0.02 s, and only SEVEN runs corpus-wide reach 5.12 s
   (`v95_override_exposure.py`).  The kit's band estimator cannot be used in this regime.  Everything
   here is a point-process or short-segment statistic: crossing rates, 1.28 s spectra (0.78 Hz bins,
   6-9 Hz still spans four of them), and sample-by-sample correlation.

⚠ UNIT CAVEAT, swept rather than assumed: the knots are `gp-0x4f60` raw counts and it is NOT
   established that `STEER_TORQUE_SENSOR` counts are the same units.  Every headline number is
   recomputed over a scale sweep so a unit error cannot hide the answer.

Usage:  python v95_override_authority_chatter.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v95_override_exposure import channels  # noqa: E402
from v95_rez_lib import BUILD, CACHES, hdr  # noqa: E402

RNG = np.random.default_rng(950823)
CX = np.array([2240.0, 2304.0, 2496.0, 2560.0])      # authority-curve knots, raw counts
CY = np.array([254.0, 234.0, 12.0, 0.0])
TAU = 0.0315                                          # s, from the 992/1024 pole at 1 kHz
NWS = 128                                             # 1.28 s at 100 Hz -> 0.78 Hz bins
ROUTES = ["r77", "r73", "r79", "r6e", "r76", "r6f", "r71", "r66", "r67x", "r68x", "r75"]


def authority(absq, fs, scale=1.0):
    """The 4-point curve applied sample by sample, then the downstream one-pole IIR."""
    a = np.interp(absq / scale, CX, CY, left=CY[0], right=CY[-1])
    al = 1.0 - np.exp(-1.0 / (fs * TAU))
    out = np.empty_like(a)
    acc = a[0]
    for i, x in enumerate(a):                          # explicit loop: this IS the firmware's IIR
        acc += al * (x - acc)
        out[i] = acc
    return a, out


def episodes(mask, t, fs, min_dur=0.6, join=0.30):
    """Override EPISODES, not frames: join gaps < `join` s, keep blocks >= `min_dur` s."""
    m = mask.astype(int)
    e = np.diff(np.concatenate(([0], m, [0])))
    st, en = list(np.flatnonzero(e == 1)), list(np.flatnonzero(e == -1))
    out = []
    for s, x in zip(st, en):
        if out and (t[s] - t[out[-1][1] - 1]) < join:
            out[-1] = (out[-1][0], x)
        else:
            out.append((s, x))
    return [(s, x) for s, x in out if (x - s) / fs >= min_dur]


def crossings(x, thr, dead=40.0):
    """Threshold crossings with a deadband, so sensor noise at the knot is not counted."""
    st = np.where(x > thr + dead, 1, np.where(x < thr - dead, -1, 0))
    st = st[st != 0]
    return int(np.sum(np.diff(st) != 0)) if len(st) > 1 else 0


def bandpow(x, fs, lo, hi, nw=NWS):
    h = np.hanning(nw)
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    sel = (f >= lo) & (f <= hi)
    out = []
    for i in range(0, len(x) - nw + 1, nw // 2):
        X = np.abs(np.fft.rfft((x[i:i + nw] - x[i:i + nw].mean()) * h)) ** 2
        out.append(float(X[sel].sum()))
    return np.asarray(out)


def spectrum(sigs, fs, nw=NWS):
    h = np.hanning(nw)
    acc, n = 0, 0
    for x in sigs:
        for i in range(0, len(x) - nw + 1, nw // 2):
            acc = acc + np.abs(np.fft.rfft((x[i:i + nw] - x[i:i + nw].mean()) * h)) ** 2
            n += 1
    return (np.fft.rfftfreq(nw, 1.0 / fs), acc / max(n, 1), n)


# ======================================================================================
def part_a():
    hdr("A.  CROSSING RATE OF THE 2240 KNOT DURING OVERRIDE -- the decisive number")
    print(f"  {'route':6s} {'build':12s} {'arm':8s} {'eps':>4s} {'secs':>7s} "
          f"{'cross/s':>8s} {'implied Hz':>10s} | {'authority p50':>13s} {'sd':>7s} "
          f"{'frac time A=0':>13s}")
    keep = {}
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        fs, mov = B["fs"], B["v"] > 0.5
        absq = np.abs(B["ctq"])
        for tag, m in (("OVR", B["lat"] & B["press"] & mov),
                       ("MAN/ON", (~B["lat"]) & B["press"] & mov)):
            eps = episodes(m, B["t"], fs)
            if not eps:
                continue
            secs = sum((x - s) for s, x in eps) / fs
            nx = sum(crossings(absq[s:x], CX[0]) for s, x in eps)
            _, A = authority(absq, fs)
            Ae = np.concatenate([A[s:x] for s, x in eps])
            print(f"  {r:6s} {BUILD.get(r,'?'):12s} {tag:8s} {len(eps):4d} {secs:7.1f} "
                  f"{nx/max(secs,1e-9):8.2f} {nx/max(secs,1e-9)/2:10.2f} | "
                  f"{np.median(Ae):13.0f} {np.std(Ae):7.0f} {np.mean(Ae < 1.0):13.3f}")
            if tag == "OVR":
                keep[r] = (B, eps)
    print("\n  'implied Hz' = crossings/s / 2, since one full oscillation cycle crosses twice.")
    print("  ⇒ if that lands in 6-9 Hz the micro-ratchet has a named mechanism.  If it lands at")
    print("    1-2 Hz the chatter is far too slow and mechanism A is refuted as the 6-9 Hz source.")
    return keep


def part_b(keep):
    hdr("B.  SPECTRUM OF THE RECONSTRUCTED AUTHORITY SIGNAL  (1.28 s windows, 0.78 Hz bins)")
    print(f"  {'route':6s} {'nwin':>5s} | {'peak Hz':>8s} {'frac 0-3':>9s} {'frac 3-6':>9s} "
          f"{'frac 6-9':>9s} {'frac 9-15':>10s} {'frac 15-25':>11s}")
    for r, (B, eps) in keep.items():
        _, A = authority(np.abs(B["ctq"]), B["fs"])
        sigs = [A[s:x] for s, x in eps if (x - s) >= NWS]
        if not sigs:
            print(f"  {r:6s}  -- no episode reaches 1.28 s")
            continue
        f, P, n = spectrum(sigs, B["fs"])
        tot = P[(f > 0.5)].sum()
        fr = [P[(f >= a) & (f < b)].sum() / max(tot, 1e-30) for a, b in
              ((0.5, 3), (3, 6), (6, 9), (9, 15), (15, 25))]
        pk = f[(f > 0.5)][np.argmax(P[(f > 0.5)])]
        print(f"  {r:6s} {n:5d} | {pk:8.2f} {fr[0]:9.3f} {fr[1]:9.3f} {fr[2]:9.3f} "
              f"{fr[3]:10.3f} {fr[4]:11.3f}")
    print("  ⇒ the authority signal's OWN spectrum.  A 6-9 Hz fraction that dominates is the")
    print("    confirmation; energy piled at 0-3 Hz means the collapse is slow and cannot be it.")


def part_c(keep):
    hdr("C.  DOES AUTHORITY CHATTER PREDICT 6-9 Hz COLUMN ENERGY?  (shuffled control on every row)")
    print(f"  {'route':6s} {'arm':8s} {'nwin':>5s} | {'r(chatter, 6-9 tq)':>19s} {'shuf':>7s} | "
          f"{'r(chatter, 6-9 rate)':>21s} {'shuf':>7s}")
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        fs, mov = B["fs"], B["v"] > 0.5
        for tag, m in (("OVR", B["lat"] & B["press"] & mov),
                       ("MAN/ON", (~B["lat"]) & B["press"] & mov)):
            eps = [(s, x) for s, x in episodes(m, B["t"], fs) if (x - s) >= NWS]
            if len(eps) < 4:
                continue
            _, A = authority(np.abs(B["ctq"]), fs)
            ch, pt, pw = [], [], []
            for s, x in eps:
                a = A[s:x]
                nwn = (len(a) - NWS) // (NWS // 2) + 1
                for i in range(nwn):
                    j = i * (NWS // 2)
                    ch.append(float(np.std(a[j:j + NWS])))
                pt += list(bandpow(B["tq"][s:x], fs, 6, 9))
                pw += list(bandpow(B["w"][s:x], fs, 6, 9))
            n = min(len(ch), len(pt), len(pw))
            if n < 12:
                continue
            ch, pt, pw = np.log1p(np.array(ch[:n])), np.log1p(np.array(pt[:n])), \
                np.log1p(np.array(pw[:n]))
            c1 = float(np.corrcoef(ch, pt)[0, 1])
            c2 = float(np.corrcoef(ch, pw)[0, 1])
            s1 = float(np.corrcoef(ch, RNG.permutation(pt))[0, 1])
            s2 = float(np.corrcoef(ch, RNG.permutation(pw))[0, 1])
            print(f"  {r:6s} {tag:8s} {n:5d} | {c1:19.3f} {s1:7.3f} | {c2:21.3f} {s2:7.3f}")
    print("  chatter = per-window sd of the reconstructed authority.  MAN/ON is the NEGATIVE")
    print("  CONTROL: manual has no LKAS authority to collapse, so the curve must be irrelevant")
    print("  there.  A correlation that is just as strong in MAN/ON is a confound, not a mechanism.")


def part_d(keep):
    hdr("D.  MECHANISM B -- the LKAS command during override (request bit, magnitude, direction)")
    print(f"  {'route':6s} {'arm':8s} {'secs':>7s} | {'req duty':>9s} {'req drops/s':>12s} | "
          f"{'|cmd| p50':>10s} {'ratio vs non-OVR':>17s} | {'sign flips/s':>13s} {'implied Hz':>10s}")
    for r in ROUTES:
        if r not in CACHES:
            continue
        B = channels(r)
        if B is None:
            continue
        z = __import__("numpy").load(CACHES[r], allow_pickle=True)
        req = np.asarray(z["sc_req"], float) if "sc_req" in z.files else None
        fs, mov = B["fs"], B["v"] > 0.5
        base_m = B["lat"] & (~B["press"]) & mov
        ref = np.median(np.abs(B["sc"][base_m])) if base_m.sum() > 500 else np.nan
        for tag, m in (("OVR", B["lat"] & B["press"] & mov),
                       ("ENG/OFF", base_m)):
            eps = episodes(m, B["t"], fs)
            if not eps:
                continue
            secs = sum((x - s) for s, x in eps) / fs
            sc = np.concatenate([B["sc"][s:x] for s, x in eps])
            rq = np.concatenate([req[s:x] for s, x in eps]) if req is not None else None
            drops = (int(np.sum(np.diff((rq > 0.5).astype(int)) == -1)) / max(secs, 1e-9)
                     if rq is not None else np.nan)
            sg = np.sign(sc)
            sg = sg[sg != 0]
            flips = int(np.sum(np.diff(sg) != 0)) / max(secs, 1e-9)
            print(f"  {r:6s} {tag:8s} {secs:7.1f} | "
                  f"{(np.mean(rq > 0.5) if rq is not None else np.nan):9.4f} {drops:12.3f} | "
                  f"{np.median(np.abs(sc)):10.0f} "
                  f"{np.median(np.abs(sc))/ref if np.isfinite(ref) and ref else np.nan:17.3f} | "
                  f"{flips:13.2f} {flips/2:10.2f}")
    print("  ⚠ 'sign flips' PROXIES the direction bits: openpilot's 0x0E4 has no explicit direction")
    print("    field in the DBC, so sign(commanded torque) is the closest observable.")
    print("  ⇒ req duty ~1.0 with no drops => the sign-guard relay never arms and mechanism B needs")
    print("    the direction route; flips clustering at 6-9 Hz would be the second signature.")


def part_e():
    hdr("E.  UNIT-SCALE SWEEP -- can a counts mismatch hide or manufacture the answer?")
    print("  Recomputing the OVR crossing rate with the knots scaled, route 77 (best exposure).")
    B = channels("r77")
    fs = B["fs"]
    m = B["lat"] & B["press"] & (B["v"] > 0.5)
    eps = episodes(m, B["t"], fs)
    secs = sum((x - s) for s, x in eps) / fs
    absq = np.abs(B["ctq"])
    print(f"    {'scale':>6s} {'knot':>7s} {'cross/s':>8s} {'implied Hz':>11s} "
          f"{'frac time A=0':>14s}")
    for sc in (0.6, 0.8, 1.0, 1.25, 1.6, 2.0):
        nx = sum(crossings(absq[s:x], CX[0] * sc) for s, x in eps)
        _, A = authority(absq, fs, scale=1.0 / sc)
        Ae = np.concatenate([A[s:x] for s, x in eps])
        print(f"    {sc:6.2f} {CX[0]*sc:7.0f} {nx/secs:8.2f} {nx/secs/2:11.2f} "
              f"{np.mean(Ae < 1.0):14.3f}")


if __name__ == "__main__":
    keep = part_a()
    part_b(keep)
    part_c(keep)
    part_d(keep)
    part_e()
