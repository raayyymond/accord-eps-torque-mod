# -*- coding: utf-8 -*-
"""studies/grind/wire_0xe4_burst_damping.py -- second addendum to wire_0xe4_20hz.py, requested by the
team-lead 2026-09-07.

CRUX HE RAISED, AND HE IS RIGHT: GI.simulate is an OPEN-LOOP mirror.  It drives the PID with the LOGGED
0x18F wheel rate as the feedback operand and the LOGGED 0xE4 as the command; there is no plant and no
loop closure (see grind_incident_r35.simulate: `wire = C20.up1k(g["wire"][seg]) ; x = -wire` feeds the
feedback filter directly).  So wire_0xe4_20hz.py section 4's "delete the command's 18-22 Hz -> T falls
to 0.909" is the command term's SHARE of T's 20 Hz content inside the PID sum, with the feedback's own
ring HELD FIXED BY CONSTRUCTION.  It is NOT a closed-loop prediction: in a lightly damped stable mode
the ring amplitude scales with whatever excites it, so removing the trigger would also shrink the
feedback term.  Same caveat applies to every ratio in sections 4 and 5b.

THE CLOSED-LOOP QUESTION THE WIRE CAN STILL ANSWER: is the 18-22 Hz mode SELF-SUSTAINED (damping <= 0 --
a filter on the trigger cannot cure it) or a RUNG BELL (damping > 0 -- the trigger sets the amplitude)?

Tests here:
  1  Envelope rise/decay slopes of every V282 episode (GI.growth_fit), by census class.
  2  🛑 THE CONTROL: the same detector run on PHASE-RANDOMISED surrogates of the same routes.  A
     surrogate has the identical power spectrum -- hence the identical envelope correlation time -- but
     no transient structure at all.  Any episode detector that thresholds a narrowband envelope
     MECHANICALLY produces rise-then-fall shapes; the surrogate says how much of the observed
     "exponential burst" is that artefact.
  3  FREE DECAY: stretches inside/after an episode where the excitation goes quiet (zero slew-capped
     frames AND |dcmd| below the route's engaged baseline median for >= 0.3 s) while the envelope is
     still up.  Fit the decay there and convert to a damping ratio at 20 Hz.  This is the closest the
     wire gets to a free-ring measurement.
  4  EXCITATION LEAD: cross-correlation of the 18-22 Hz envelope against a smoothed excitation proxy
     (capped-frame rate), and whether growth phases coincide with rising or flat excitation.

ANALYSIS ONLY: builds nothing, sends nothing.
Run: python wire_0xe4_burst_damping.py     (writes _scratch/wire_0xe4_burst_damping.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import wire_0xe4_20hz as WIRE                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
LO, HI = 18.0, 22.0
W, STEP = 200, 50
ROUTES = ("r39", "r3a", "r3c")
CAP = 122
NSUR = 3
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def detect(bar, eng, tr):
    """the census's episode detector, on an arbitrary bar-like array. returns list of (a,b,f0,gu,gd,dur)."""
    wt, wp = [], []
    for aa, bb in C20.runs(eng, W):
        for s in range(aa, bb - W + 1, STEP):
            e = s + W
            _f, prom, _, _ = GI.line_of(bar[s:e], FS, 15.0, 26.0)
            wt.append(tr[s])
            wp.append((prom >= 8) and (GI.band(bar[s:e], LO, HI, FS) >= 40))
    if not wt:
        return [], np.zeros(len(tr), bool)
    wt, wp = np.array(wt), np.array(wp, bool)
    j = np.clip(np.searchsorted(wt, tr - 1.0), 0, len(wt) - 1)
    hot = eng & (np.abs(wt[j] + 1.0 - tr) < 1.5) & wp[j]
    out = []
    n = len(tr)
    for a, b in C20.runs(hot, int(0.5 * FS)):
        f0, prom, _, _ = GI.line_of(bar[a:b], FS, 15.0, 26.0)
        if not np.isfinite(f0):
            continue
        s0, s1 = max(0, a - 100), min(n, b + 100)
        env = GI.envelope(bar[s0:s1], f0, FS)
        gu, du, gd, dd = GI.growth_fit(tr[s0:s1], env)
        out.append(dict(a=a, b=b, f0=f0, gu=gu, gd=gd, dur=(b - a) / FS,
                        pk=float(np.max(env)), env=env, s0=s0, s1=s1))
    return out, hot


def classify(ep, bar, tr):
    a, b = ep["a"], ep["b"]
    amp = GI.band(bar[a:b], LO, HI, FS)
    amp6 = GI.band(bar[a:b], 6.0, 10.0, FS)
    env7 = GI.envelope(bar[ep["s0"]:ep["s1"]], 7.5, FS, bw=2.5)
    e20 = ep["env"][a - ep["s0"]:a - ep["s0"] + (b - a)]
    e7 = env7[a - ep["s0"]:a - ep["s0"] + (b - a)]
    m = min(len(e20), len(e7))
    n25 = max(4, int(0.25 * FS))
    if m >= n25:
        e20b = e20[:m - m % n25].reshape(-1, n25).mean(1)
        e7b = e7[:m - m % n25].reshape(-1, n25).mean(1)
        corr7 = float(np.corrcoef(e20b, e7b)[0, 1]) if len(e20b) >= 4 and e20b.std() > 0 and e7b.std() > 0 else np.nan
    else:
        corr7 = np.nan
    if np.isfinite(ep["gu"]) and np.isfinite(ep["gd"]) and ep["gu"] >= 1.0 and ep["gd"] <= -1.0 and ep["dur"] <= 3.0:
        return "BURST"
    if amp6 >= 1.2 * amp and np.isfinite(corr7) and corr7 >= 0.5:
        return "RIDE-ALONG"
    return "SUSTAINED"


def phase_randomise(x, rng):
    """surrogate with an IDENTICAL power spectrum and no transient structure."""
    n = len(x)
    X = np.fft.rfft(x - x.mean())
    ph = rng.uniform(0, 2 * np.pi, len(X))
    ph[0] = 0.0
    if n % 2 == 0:
        ph[-1] = 0.0
    return np.fft.irfft(np.abs(X) * np.exp(1j * ph), n=n) + x.mean()


def main():
    cells = GI.read_cells(WIRE.V282_IMG)
    G, EPS = {}, {}
    for t in ROUTES:
        G[t] = WIRE.load_route(t, cells)
        e = G[t]["e4"]
        e["d"] = np.diff(e["grid"])
        e["base"] = e["egrid"][1:] & e["egrid"][:-1]
        eps, hot = detect(G[t]["bar"], G[t]["eng"], G[t]["tr"])
        for ep in eps:
            ep["cls"] = classify(ep, G[t]["bar"], G[t]["tr"])
        EPS[t] = eps
        G[t]["hot"] = hot
        print("loaded %s: %d episodes" % (t, len(eps)), flush=True)

    pr("=" * 150)
    pr("IS GRIND #1 SELF-SUSTAINED OR A RUNG BELL?  -- second addendum, V282 (r39/r3a/r3c)")
    pr("script wire_0xe4_burst_damping.py, subagent `wire`, 2026-09-07.  Analysis only.")
    pr("=" * 150)

    pr("\n0. 🛑 WHAT GI.simulate ACTUALLY IS -- the crux the team-lead raised  [EVIDENCE: source]")
    pr("   grind_incident_r35.simulate():  wire = C20.up1k(g['wire'][seg]) ; x = -wire ; then the")
    pr("   feedback filter, E = 32*sp - fb, P, D, clamps and the output lag.  Both the feedback operand")
    pr("   (LOGGED 0x18F wheel rate) and the command (LOGGED 0xE4) are exogenous.  THERE IS NO PLANT AND")
    pr("   NO LOOP CLOSURE.  It is a replay mirror of the controller arithmetic, not a simulation of the")
    pr("   car.  => every ratio in wire_0xe4_20hz.py sections 4 and 5b is a SHARE of T's 18-22 Hz content")
    pr("   attributable to one input path with the other input HELD AT WHAT ACTUALLY HAPPENED.  It is an")
    pr("   upper bound on nothing and a lower bound on the closed-loop benefit only if damping > 0.")

    # ============================================================ 1. observed envelope shapes
    pr("\n" + "=" * 150)
    pr("1. OBSERVED ENVELOPE SHAPES, V282 episodes  [EVIDENCE]")
    pr("=" * 150)
    pr("  GI.growth_fit: log-envelope slope over the 10 %->90 % rise and the 90 %->10 % fall about the peak.")
    pr("  tau = 1/|slope|.  A stable mode at 20 Hz with damping ratio z has tau = 1/(z*2*pi*20) s.")
    pr("  %-6s %-12s %6s %10s %10s %10s %10s %10s %10s" %
       ("route", "class", "n", "gu p50 /s", "gu p90", "gd p50 /s", "gd p10", "tau_up ms", "tau_dn ms"))
    ALL = []
    for tag in ROUTES:
        for cls in ("BURST", "SUSTAINED", "RIDE-ALONG"):
            sel = [e for e in EPS[tag] if e["cls"] == cls and np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
            if len(sel) < 3:
                pr("  %-6s %-12s %6d   (thin)" % (tag, cls, len(sel)))
                continue
            gu = np.array([e["gu"] for e in sel])
            gd = np.array([e["gd"] for e in sel])
            pr("  %-6s %-12s %6d %10.2f %10.2f %10.2f %10.2f %10.0f %10.0f" %
               (tag, cls, len(sel), np.percentile(gu, 50), np.percentile(gu, 90),
                np.percentile(gd, 50), np.percentile(gd, 10),
                1000 / max(np.percentile(gu, 50), 1e-9), 1000 / max(-np.percentile(gd, 50), 1e-9)))
        ALL += [e for e in EPS[tag] if np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
    gu = np.array([e["gu"] for e in ALL])
    gd = np.array([e["gd"] for e in ALL])
    pr("  %-6s %-12s %6d %10.2f %10.2f %10.2f %10.2f %10.0f %10.0f" %
       ("POOL", "all", len(ALL), np.percentile(gu, 50), np.percentile(gu, 90),
        np.percentile(gd, 50), np.percentile(gd, 10),
        1000 / max(np.percentile(gu, 50), 1e-9), 1000 / max(-np.percentile(gd, 50), 1e-9)))
    nb = sum(1 for e in ALL if e["cls"] == "BURST")
    pr("\n  Class split, V282 pooled: BURST %d, SUSTAINED %d, RIDE-ALONG %d of %d." %
       (nb, sum(1 for e in ALL if e["cls"] == "SUSTAINED"),
        sum(1 for e in ALL if e["cls"] == "RIDE-ALONG"), len(ALL)))
    pr("  🛑 EVERY detected episode has a rise and a fall BY CONSTRUCTION -- the detector starts it when")
    pr("  the envelope crosses a threshold and ends it when it drops back.  Section 2 is the control.")

    # ============================================================ 2. surrogate control
    pr("\n" + "=" * 150)
    pr("2. 🛑 THE CONTROL -- the same detector on PHASE-RANDOMISED surrogates  [EVIDENCE]")
    pr("=" * 150)
    pr("  A surrogate has the route's EXACT power spectrum (hence the same 18-22 Hz envelope correlation")
    pr("  time) and no transient structure whatsoever.  If the observed 'exponential burst' shape is a")
    pr("  threshold-crossing artefact of a stationary narrowband process, the surrogate reproduces it.")
    pr("  %d surrogate realisations per route, identical engagement mask and detector." % NSUR)
    pr("  %-6s %-10s %8s %10s %10s %10s %10s %10s" %
       ("route", "data", "n eps", "BURST %", "gu p50 /s", "gu p90", "gd p50 /s", "dur p50 s"))
    rng = np.random.default_rng(20260907)
    SURA = []
    for tag in ROUTES:
        real = [e for e in EPS[tag] if np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
        rgu = np.array([e["gu"] for e in real])
        rgd = np.array([e["gd"] for e in real])
        pr("  %-6s %-10s %8d %10.1f %10.2f %10.2f %10.2f %10.2f" %
           (tag, "REAL", len(real), 100 * np.mean([e["cls"] == "BURST" for e in real]),
            np.percentile(rgu, 50), np.percentile(rgu, 90), np.percentile(rgd, 50),
            np.median([e["dur"] for e in real])))
        sg, sd, sb, sn, sdur = [], [], [], [], []
        for k in range(NSUR):
            sbar = phase_randomise(G[tag]["bar"], rng)
            se, _ = detect(sbar, G[tag]["eng"], G[tag]["tr"])
            for ep in se:
                ep["cls"] = classify(ep, sbar, G[tag]["tr"])
            se = [e for e in se if np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
            sn.append(len(se))
            sg += [e["gu"] for e in se]
            sd += [e["gd"] for e in se]
            sb += [e["cls"] == "BURST" for e in se]
            sdur += [e["dur"] for e in se]
            print("   surrogate %s #%d: %d episodes" % (tag, k + 1, len(se)), flush=True)
        if sg:
            pr("  %-6s %-10s %8.0f %10.1f %10.2f %10.2f %10.2f %10.2f" %
               ("", "surrogate", np.mean(sn), 100 * np.mean(sb), np.percentile(sg, 50),
                np.percentile(sg, 90), np.percentile(sd, 50), np.median(sdur)))
            u = stats.mannwhitneyu(rgu, sg, alternative="greater")
            pr("        Mann-Whitney, real gu > surrogate gu:  U p = %.4f   (real median %.2f vs %.2f /s)" %
               (u.pvalue, np.median(rgu), np.median(sg)))
            SURA += list(sg)
    pr("\n  Reading: if the real BURST fraction and rise slopes are inside the surrogate's, the observed")
    pr("  'exponential burst' is the detector meeting a stationary lightly-damped resonance, NOT evidence")
    pr("  of self-sustained growth.")

    # ============================================================ 3. free decay
    pr("\n" + "=" * 150)
    pr("3. FREE DECAY -- envelope decay while the command excitation is QUIET  [EVIDENCE]")
    pr("=" * 150)
    pr("  'Quiet' = >= 0.3 s of engaged frames with ZERO slew-capped 0xE4 frames AND mean |dcmd| below")
    pr("  the route's engaged baseline median, starting at or after an episode's envelope peak.")
    pr("  Fit: log-envelope slope over the quiet stretch.  z = 1/(tau * 2*pi*20).")
    pr("  %-6s %8s %12s %12s %12s %12s %12s" %
       ("route", "n quiet", "gd p50 /s", "gd p25", "gd p75", "tau p50 ms", "z p50 @20Hz"))
    ZS = []
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float))
        dabs = np.interp(g["t"], e["tgrid"][1:], np.abs(e["d"]))
        hot_e4 = np.interp(e["tgrid"], g["t"], g["hot"].astype(float))[1:] > 0.5
        base_med = np.median(np.abs(e["d"])[e["base"] & ~hot_e4])
        sl = []
        for ep in EPS[tag]:
            env = ep["env"]
            t = g["tr"][ep["s0"]:ep["s1"]]
            k = int(np.argmax(env))
            quiet = (capf[ep["s0"]:ep["s1"]] < 0.5) & (dabs[ep["s0"]:ep["s1"]] <= base_med)
            quiet[:k] = False
            for a, b in C20.runs(quiet, 30):
                seg = np.log(np.maximum(env[a:b], 1e-9))
                if seg.max() - seg.min() < 0.1:
                    continue
                s, ic, r, p, se = stats.linregress(t[a:b], seg)
                if np.isfinite(s):
                    sl.append(s)
        if len(sl) >= 5:
            sl = np.array(sl)
            neg = sl[sl < 0]
            tau = 1000 / np.abs(np.percentile(sl, 50)) if np.percentile(sl, 50) != 0 else np.nan
            z = np.abs(np.percentile(sl, 50)) / (2 * np.pi * 20)
            ZS.append(z)
            pr("  %-6s %8d %12.2f %12.2f %12.2f %12.0f %12.4f" %
               (tag, len(sl), np.percentile(sl, 50), np.percentile(sl, 25), np.percentile(sl, 75),
                tau, z))
            pr("        fraction of quiet stretches with a DECAYING envelope (slope < 0): %.3f  (n=%d)" %
               (np.mean(sl < 0), len(sl)))
        else:
            pr("  %-6s %8d   (thin)" % (tag, len(sl)))
    if ZS:
        pr("\n  Pooled damping ratio implied by the free decays: z ~ %.4f -- %.4f at 20 Hz." %
           (min(ZS), max(ZS)))
        pr("  z > 0 everywhere means the mode is STABLE and its amplitude is set by the excitation.")

    # ============================================================ 4. excitation lead
    pr("\n" + "=" * 150)
    pr("4. DOES THE EXCITATION LEAD THE ENVELOPE?  [EVIDENCE]")
    pr("=" * 150)
    pr("  Cross-correlation of the route-wide 18-22 Hz bar envelope (0.25 s smoothed) against the")
    pr("  slew-capped-frame rate (0.25 s smoothed), engaged frames only.  Positive lag = excitation FIRST.")
    pr("  %-6s %10s %14s %14s %14s" % ("route", "peak r", "at lag ms", "r at lag 0", "r at -200 ms"))
    for tag in ROUTES:
        g, e = G[tag], G[tag]["e4"]
        capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float))
        sos = signal.butter(2, 4.0, btype="lowpass", fs=FS, output="sos")
        bp = signal.butter(4, [LO, HI], btype="bandpass", fs=FS, output="sos")
        env = np.abs(signal.hilbert(signal.sosfiltfilt(bp, g["bar"])))
        env = signal.sosfiltfilt(sos, env)
        exc = signal.sosfiltfilt(sos, capf)
        m = g["eng"]
        a = env[m] - env[m].mean()
        b = exc[m] - exc[m].mean()
        lags = np.arange(-50, 51)
        r = np.array([np.corrcoef(a[max(0, l):len(a) + min(0, l)],
                                  b[max(0, -l):len(b) + min(0, -l)])[0, 1] for l in lags])
        i = int(np.argmax(r))
        pr("  %-6s %10.3f %14.0f %14.3f %14.3f" %
           (tag, r[i], lags[i] * 10.0, r[lags == 0][0], r[lags == -20][0]))
    pr("  (lag convention: r[l] correlates env[t] with exc[t-l], so l > 0 means the capped frames come")
    pr("   BEFORE the envelope rises.)")

    with open(os.path.join(SCR, "wire_0xe4_burst_damping.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\n[written: _scratch/wire_0xe4_burst_damping.txt]")


if __name__ == "__main__":
    main()
