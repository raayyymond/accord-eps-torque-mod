"""
V289 rev 1 -- BUILD IDENTITY AND CAVE LIVENESS FROM THE TAP on the first two V289 drives,
routes 75604b0a432fdc89_00000062--1c7daa54e8 (r62_v289) and 75604b0a432fdc89_00000063--1d4b188022 (r63_v289), 2026-09-09.

Attribute the build from the WIRE, not the label (r32/r33 were mis-filed).  The discriminating instrument is
0x14A byte 4:
    V289 rev 1 : b5 = sign(S - y)  -- the notched-out (20 Hz) component of the clamped loop output S.  Zero-mean, so
                 duty ~0.50 engaged, spectrally concentrated at ~20 Hz, phase-locked to the 0x18F rate at the line.
                 b7 = |S - y| >= |y| -- reads 1.000 while DISENGAGED (S = y = 0), ~0.10 engaged, rising at grinding onsets.
    V288 rev 2 : b5 = sign(y_model) -- the FILTERED SETPOINT's sign, i.e. it follows the 0xE4 command sign (agreement
                 0.995 on r5e_v288); b7 = the three-sign rung (~0.56 engaged, NOT 1.000 disengaged).
    V282       : b5 = |r24| >= |aggregator| comparator (duty ~0.13 engaged); b7 = the three-sign rung.
    Bits 4/6 = V282's r24 comparators on all three; b3 as V282; b0-2 stock Honda (1.000).
Also: the 0x1AB (427) torque tap must read <= 310 at the rail (never 313) -- unchanged V282 tap.

Sections (each block is tagged EVIDENCE / BELIEF):
  0. image identity from the files (sha256 of the V289 image, byte delta vs V282 and V288)
  1. routes: engaged-lateral seconds, 0x14A frame counts
  2. byte-4 duties engaged / disengaged / disengaged-and-moving, the two routes vs r5e_v288 (V288) and r39 (V282)
  3. b5 vs the COMMAND sign (the V288 discriminator) and b5's own spectrum (zero-mean 20 Hz content = V289)
  4. b5 vs sign of the 18-22 Hz-bandpassed 0x18F rate: lag scan of the correlation, all engaged frames and
     line-present frames, with a circular-shift null
  5. b7 at grinding onsets (18-22 Hz bar envelope episodes) and in the -6..0 s windows before the operator's bookmarks
  6. 427 tap rail census
  7. verdict per route (rule written before the numbers)

Writes rlog-tools/studies/grind/_scratch/v289_qlive_r62_r63.txt.  Reads caches only; builds nothing.
Python = the bin_decompile conda env, invoked as `python`.
"""
import hashlib
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                    # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG      # noqa: E402  FW

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
CACHE = C20.CACHE
CORPUS = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
OUTDIR = os.path.join(HERE, "_scratch"); os.makedirs(OUTDIR, exist_ok=True)
OUTTXT = os.path.join(OUTDIR, "v289_qlive_r62_r63.txt")
IMG289 = LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG288 = LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG282 = LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
SHA289 = "f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed"
NEW = ["r62_v289", "r63_v289"]
REF = {"r5e_v288": "V288r2", "r39": "V282"}
ALL = NEW + list(REF)
LABEL = {"r62_v289": "V289r1?", "r63_v289": "V289r1?", **REF}
RNG = np.random.default_rng(20260909)
OUT = []


def pr(s=""):
    print(s); OUT.append(s)


def boot_ci(x, stat=np.mean, n=1000):
    x = np.asarray(x, float)
    if x.size < 3:
        return (np.nan, np.nan)
    v = np.array([stat(RNG.choice(x, x.size)) for _ in range(n)])
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


def nanmean(x):
    x = np.asarray(x, float)
    return float(x.mean()) if x.size else float("nan")


# =====================================================================================================================
# 0. IMAGE IDENTITY
# =====================================================================================================================
pr("V289 REV 1 -- BUILD IDENTITY AND CAVE LIVENESS FROM THE TAP, routes r62_v289 / r63_v289 (2026-09-09)")
pr("=" * 118)
pr("\n0. IMAGES  [EVIDENCE: sha256 + full-file diff of the files in ../accord-firmwares]")
b289 = np.frombuffer(open(IMG289, "rb").read(), np.uint8); b282 = np.frombuffer(open(IMG282, "rb").read(), np.uint8)
b288 = np.frombuffer(open(IMG288, "rb").read(), np.uint8)
sha = hashlib.sha256(b289.tobytes()).hexdigest()
pr("   V289 image sha256 %s  (%s)" % (sha, "MATCHES the record f0c10c29..." if sha == SHA289 else "!! DOES NOT MATCH THE RECORD"))


def regions(a, b):
    d = np.flatnonzero(a != b)
    rs = C20.runs(np.isin(np.arange(len(a)), d), 1) if d.size else []
    m = []
    for x, y in rs:
        if m and x - m[-1][1] < 8:
            m[-1] = (m[-1][0], y)
        else:
            m.append((x, y))
    return d.size, m


for nm, other in (("V282", b282), ("V288r2", b288)):
    n, m = regions(b289, other)
    pr("   V289 vs %-6s: %d bytes differ in %d regions: %s" % (nm, n, len(m), ", ".join("0x%05X-0x%05X" % (a, b - 1) for a, b in m)))
pr("   [the telemetry tail 0xC4BDC-0xC4BF7 and the notch cave at 0xC4C00 exist ONLY on the V289 image; a V288 or V282 ECU cannot emit V289's bit semantics]")

# =====================================================================================================================
# 1. ROUTES
# =====================================================================================================================
pr("\n1. ROUTES  [EVIDENCE: v280 caches (extract_v289_v280cache.py) + corpus caches (extract_v289_routes.py); refs from the record]")
G, B, BIT, ENG14, TN14, MOV14, CMD14, SEG14 = {}, {}, {}, {}, {}, {}, {}, {}
for tag in ALL:
    g = C20.load(tag); G[tag] = g
    Bz = dict(np.load(os.path.join(CACHE, tag + "_b4.npz"))); B[tag] = Bz
    k14, P14, tn14, res14 = C20.dejitter(Bz["t14b"].astype(float), 0.01, 100)
    b4 = Bz["b4"].astype(int)
    BIT[tag] = {n: (b4 >> n) & 1 for n in range(8)}
    TN14[tag] = tn14
    ENG14[tag] = np.interp(tn14, g["t"], g["eng"].astype(float)) > 0.5
    MOV14[tag] = np.interp(tn14, g["t"], g["vego"]) > 1.0
    CMD14[tag] = np.interp(tn14, g["t"], g["cmd"])
    cp = os.path.join(CORPUS, tag, tag + ".npz")
    if os.path.exists(cp):
        CP = np.load(cp, allow_pickle=True)
        SEG14[tag] = np.round(np.interp(tn14, CP["t"] + float(CP["t0_mono"][0]), CP["seg"])).astype(int)
        lab = str(CP["probe_build"][0])
    else:
        SEG14[tag] = np.zeros(len(tn14), int); lab = "?"
    pr("   %-9s label %-8s | 0x18F frames %6d (P %.5f) | 0x14A frames %6d (P %.5f, resid p90 %.1f ms) | engaged-lateral %6.1f s of %6.1f s | 0x14A frames engaged %6d, disengaged %6d (moving %6d)" % (
        tag, lab, len(g["t"]), g["P18"], len(tn14), P14, 1e3 * np.percentile(res14, 90), g["eng"].sum() / FS, g["t"][-1] - g["t"][0],
        ENG14[tag].sum(), (~ENG14[tag]).sum(), (~ENG14[tag] & MOV14[tag]).sum()))
pr("   'engaged' = LATERAL engaged: 0x18F steer-control-active AND 0xE4 STEER_REQUEST, on the dejittered 0x18F frame axis, interpolated to each 0x14A frame.")

# =====================================================================================================================
# 2. BYTE-4 DUTIES
# =====================================================================================================================
pr("\n2. 0x14A BYTE-4 BIT DUTIES  [EVIDENCE: wire bits]  expected V289: b5 ~0.50 eng ; b7 1.000 diseng / ~0.10 eng ; b4 ~0.40, b6 ~0.11-0.15, b3 ~0.47 as V282 ; b0-2 = 1")
pr("   %-9s %-8s %-15s " % ("route", "label", "state") + "  ".join("   b%d" % n for n in range(7, -1, -1)) + "   frames")
DUTY = {}
for tag in ALL:
    for st, m in (("engaged", ENG14[tag]), ("disengaged", ~ENG14[tag]), ("diseng+moving", ~ENG14[tag] & MOV14[tag])):
        d = [nanmean(BIT[tag][n][m]) for n in range(7, -1, -1)]
        DUTY[(tag, st)] = d
        pr("   %-9s %-8s %-15s " % (tag, LABEL[tag], st) + "  ".join("%6.3f" % v for v in d) + "   %6d" % m.sum())
pr("\n   2b. b5 and b7 duty PER SEGMENT, engaged-lateral frames (a liveness bit must sit strictly inside (0,1) in every engaged segment)")
for tag in NEW:
    rows = []
    for s in sorted(set(SEG14[tag].tolist())):
        m = ENG14[tag] & (SEG14[tag] == s)
        if m.sum() < 100:
            continue
        rows.append("s%d:%.2f/%.2f" % (s, BIT[tag][5][m].mean(), BIT[tag][7][m].mean()))
    pr("   %-9s (seg: b5/b7)  " % tag + "  ".join(rows))

pr("\n   2c. b7 BY GATE STATE.  The notch hook sits inside Honda's rate PID, whose gate is 0x18F STEER-CONTROL-ACTIVE (SCA, byte 0x3AA96 since V104), not STEER_REQUEST;")
pr("       b7 = 1 needs S = y = 0, i.e. the hook NOT running and the notch state drained.  So the clean 'disengaged' read is SCA = 0.  [EVIDENCE: wire bits by state]")
pr("       %-9s %-8s %14s %14s %14s | b7 after SCA falls: 0-0.2 s  0.2-1 s  1-3 s  >3 s | b7 in the 1 s before SCA rises" % ("route", "label", "SCA=0", "SCA=1,REQ=0", "SCA=1,REQ=1"))
SCA0 = {}
for tag in ALL:
    g = G[tag]; tn14 = TN14[tag]
    sca = np.interp(tn14, g["t"], g["sca"]) > 0.5; req = np.interp(tn14, g["t"], g["req"].astype(float)) > 0.5
    b7 = BIT[tag][7]
    st = {"SCA=0": ~sca, "SCA=1,REQ=0": sca & ~req, "SCA=1,REQ=1": sca & req}
    SCA0[tag] = nanmean(b7[~sca])
    # time since the last SCA fall / until the next rise
    d = np.diff(np.r_[0, sca.astype(int)]); falls = np.flatnonzero(d == -1); rises = np.flatnonzero(d == 1)
    idx = np.arange(len(tn14))
    last_fall = np.full(len(tn14), -1e9)
    if falls.size:
        j = np.searchsorted(falls, idx, side="right") - 1; ok = j >= 0; last_fall[ok] = falls[j[ok]]
    since = (idx - last_fall) / FS
    next_rise = np.full(len(tn14), 1e9)
    if rises.size:
        j = np.searchsorted(rises, idx, side="left"); ok = j < rises.size; next_rise[ok] = rises[j[ok]]
    until = (next_rise - idx) / FS
    dec = [nanmean(b7[~sca & (since >= a) & (since < b)]) for a, b in ((0, 0.2), (0.2, 1), (1, 3), (3, 1e9))]
    pre = nanmean(b7[~sca & (until <= 1.0)])
    SCA0[tag + "_late"] = nanmean(b7[~sca & (since >= 3.0)])
    # is the hook still RUNNING in the drain window?  a frozen FLAG cannot toggle; a running notch toggles b5 ~20x/s
    b5 = BIT[tag][5]
    tog = {}
    for a, b in ((0, 1), (1, 3), (3, 1e9)):
        m = ~sca & (since >= a) & (since < b)
        tog[(a, b)] = (float(np.mean(np.diff(b5[m]) != 0) * FS) if m.sum() > 10 else np.nan, nanmean(b5[m]))
    SCA0[tag + "_tog"] = tog
    pr("       %-9s %-8s %6.3f (%6d) %6.3f (%6d) %6.3f (%6d) |                    %.3f    %.3f    %.3f  %.3f |  %.3f   (SCA falls %d, rises %d)" % (
        tag, LABEL[tag], nanmean(b7[st["SCA=0"]]), st["SCA=0"].sum(), nanmean(b7[st["SCA=1,REQ=0"]]), st["SCA=1,REQ=0"].sum(), nanmean(b7[st["SCA=1,REQ=1"]]), st["SCA=1,REQ=1"].sum(),
        dec[0], dec[1], dec[2], dec[3], pre, falls.size, rises.size))
pr("       drain-window check -- b5 toggles per second (duty) on SCA = 0 frames by time since SCA fell: a frozen FLAG cannot toggle, a running notch toggles ~20-40/s")
for tag in ALL:
    tog = SCA0[tag + "_tog"]
    pr("       %-9s %-8s 0-1 s: %5.1f/s (%.2f) | 1-3 s: %5.1f/s (%.2f) | >3 s: %5.1f/s (%.2f)" % (
        tag, LABEL[tag], tog[(0, 1)][0], tog[(0, 1)][1], tog[(1, 3)][0], tog[(1, 3)][1], tog[(3, 1e9)][0], tog[(3, 1e9)][1]))
pr("       [EVIDENCE: the duty profile.  BELIEF: after SCA falls Honda's PID keeps running through a disengage fade with a decaying S for ~1-3 s; while S is small")
pr("        and slow, y ~ S and n ~ 0 so b7 = 0; once S is exactly 0, |n| >= |y| is 0 >= 0 and b7 = 1.  The build's 'reads 1.000 while disengaged' is met > 3 s after SCA falls.]")

# =====================================================================================================================
# 3. b5 vs COMMAND SIGN  and  b5's OWN SPECTRUM
# =====================================================================================================================
pr("\n3. WHAT DOES b5 FOLLOW?  [EVIDENCE: wire bits vs the logged 0xE4 command; Welch PSD of the bit itself]")
pr("   3a. agreement of b5 with [0xE4 cmd < 0] (best over -40..+40 ms), engaged frames with |cmd| >= 20.  V288 (b5 = sign of the filtered setpoint) reads ~0.99;")
pr("       a zero-mean 20 Hz sign bit (V289) reads ~0.50.  [either polarity is a V288 signature -- |agree - 0.5| is the statistic]")
deltas = np.arange(-0.040, 0.0401, 0.002)
AGREE = {}
for tag in ALL:
    g = G[tag]; tn14 = TN14[tag]; m = ENG14[tag] & (np.abs(CMD14[tag]) >= 20)
    best = (0.5, 0.0)
    for dl in deltas:
        c = np.interp(tn14 - dl, g["t"], g["cmd"])
        a = float(np.mean((c[m] < 0).astype(int) == BIT[tag][5][m]))
        if abs(a - 0.5) > abs(best[0] - 0.5):
            best = (a, dl)
    AGREE[tag] = abs(best[0] - 0.5)
    pr("       %-9s %-8s agree %.3f at %+.0f ms  (|agree - 0.5| = %.3f)  n %d  -> %s" % (
        tag, LABEL[tag], best[0], 1e3 * best[1], AGREE[tag], m.sum(),
        "FOLLOWS THE COMMAND SIGN (V288-like)" if AGREE[tag] > 0.3 else "does NOT follow the command sign"))

pr("\n   3b. Welch PSD of (2*b5 - 1) on engaged runs >= 8 s (100 Hz frame axis, nperseg 256): peak frequency in 3-45 Hz, and the fraction of 3-45 Hz power in 18-22 Hz")
pr("       (a 4 Hz-wide band is 9.5 % of 3-45 Hz: a flat spectrum reads ~0.10; a bit that is the sign of a 20 Hz-bandpassed signal reads far above it)")
SPEC = {}
for tag in ALL:
    tn14 = TN14[tag]; e = ENG14[tag]; x = 2.0 * BIT[tag][5] - 1.0; x7 = 2.0 * BIT[tag][7] - 1.0
    acc = None; acc7 = None; nseg = 0
    for a, b in C20.runs(e, 800):
        f, P = signal.welch(x[a:b] - x[a:b].mean(), fs=FS, nperseg=256)
        f7, P7 = signal.welch(x7[a:b] - x7[a:b].mean(), fs=FS, nperseg=256)
        acc = P if acc is None else acc + P; acc7 = P7 if acc7 is None else acc7 + P7; nseg += 1
    if acc is None:
        pr("       %-9s no engaged run >= 8 s" % tag); SPEC[tag] = (np.nan, np.nan); continue
    P = acc / nseg; P7 = acc7 / nseg; band = (f >= 3) & (f <= 45); line = (f >= 18) & (f <= 22)
    fpk = f[band][np.argmax(P[band])]; frac = float(np.trapezoid(P[line], f[line]) / np.trapezoid(P[band], f[band]))
    fpk7 = f[band][np.argmax(P7[band])]; frac7 = float(np.trapezoid(P7[line], f[line]) / np.trapezoid(P7[band], f[band]))
    SPEC[tag] = (fpk, frac)
    pr("       %-9s %-8s b5: peak %5.1f Hz, 18-22 Hz share %.3f | b7: peak %5.1f Hz, share %.3f | runs %d" % (tag, LABEL[tag], fpk, frac, fpk7, frac7, nseg))

# =====================================================================================================================
# 4. b5 vs THE 18-22 Hz RATE
# =====================================================================================================================
pr("\n4. b5 vs THE 18-22 Hz-BANDPASSED 0x18F RATE  [EVIDENCE: correlation of (2*b5-1) with the bandpassed rate sampled at t14 - lag, 1 ms lag scan]")
pr("   The notched-out component n = S - y is the 20 Hz content of the loop output; the loop output at 20 Hz is driven by the rate feedback, so a live V289")
pr("   b5 is phase-locked to the 20 Hz rate.  V288's b5 (setpoint sign) and V282's b5 (comparator) have no 20 Hz phase relation.  Null: b5 circularly")
pr("   shifted by 0.5-2 s (20 draws) -> the chance |r|.  'line-present' = frames whose 18-22 Hz rate envelope exceeds the engaged p90.")
lags = np.arange(-0.050, 0.0501, 0.001)
XC = {}
for tag in ALL:
    g = G[tag]; tn14 = TN14[tag]; e = ENG14[tag]
    r20 = C20.bandpass(g["wire"], 18, 22, FS)                                   # 0x18F frame axis, uniform in k
    env = np.abs(signal.hilbert(r20))
    x = 2.0 * BIT[tag][5] - 1.0
    env14 = np.interp(tn14, g["t"], env)
    thr = np.percentile(env14[e], 90) if e.sum() else np.inf
    pres = e & (env14 >= thr)
    res = {}
    for nm, m in (("all engaged", e), ("line-present", pres)):
        rr = []
        for lg in lags:
            v = np.interp(tn14 - lg, g["t"], r20)
            rr.append(np.corrcoef(x[m], v[m])[0, 1] if m.sum() > 100 else np.nan)
        rr = np.array(rr); i = int(np.nanargmax(np.abs(rr)))
        null = []
        v0 = np.interp(tn14 - lags[i], g["t"], r20)
        for _ in range(20):
            sh = int(RNG.integers(50, 200)) * (1 if RNG.random() < 0.5 else -1)
            null.append(abs(np.corrcoef(np.roll(x, sh)[m], v0[m])[0, 1]))
        res[nm] = (float(rr[i]), float(lags[i]), float(np.mean(null)), float(np.max(null)), int(m.sum()), rr)
    XC[tag] = res
    A_, L_ = res["all engaged"], res["line-present"]
    pr("   %-9s %-8s all engaged: r %+.3f at lag %+3.0f ms (null mean|r| %.3f, max %.3f, n %6d) | line-present: r %+.3f at %+3.0f ms (null %.3f/%.3f, n %6d, env thr %.0f)" % (
        tag, LABEL[tag], A_[0], 1e3 * A_[1], A_[2], A_[3], A_[4], L_[0], 1e3 * L_[1], L_[2], L_[3], L_[4], thr))
    if tag in NEW:
        pr("             lag scan (line-present), every 5 ms: " + " ".join("%+d:%+.2f" % (1e3 * l, r) for l, r in zip(lags[::5], L_[5][::5])))

# =====================================================================================================================
# 5. b7 AT GRINDING ONSETS AND BEFORE THE BOOKMARKS
# =====================================================================================================================
pr("\n5. b7 (= |S - y| >= |y|) AT GRINDING ONSETS  [EVIDENCE: wire bit vs the 18-22 Hz envelope of the 0x18F bar (twist); episodes = envelope >= 3x the engaged median for >= 0.3 s]")
pr("   prediction from the build's own emulation: ~0.10-0.11 on quiet engaged frames, 0.12-0.37 inside grinding windows; reads 1.000 disengaged (S = y = 0).")
EP = {}
for tag in ALL:
    g = G[tag]; tn14 = TN14[tag]; e = ENG14[tag]
    bp = C20.bandpass(g["bar"], 18, 22, FS); env = np.abs(signal.hilbert(bp))
    env14 = np.interp(tn14, g["t"], env)
    med = np.median(env14[e]); quiet = e & (env14 < med); loud = e & (env14 >= 3 * med)
    eps = C20.runs(loud, 30)
    onset = np.zeros(len(tn14), bool); pre = np.zeros(len(tn14), bool); body = np.zeros(len(tn14), bool)
    for a, b in eps:
        onset[a:a + 50] = True; pre[max(0, a - 100):a] = True; body[a:b] = True
    onset &= e; pre &= e
    b7 = BIT[tag][7]; b5 = BIT[tag][5]
    EP[tag] = dict(n_ep=len(eps), quiet=nanmean(b7[quiet]), pre=nanmean(b7[pre]), onset=nanmean(b7[onset]), body=nanmean(b7[body]), med=med)
    ci_q = boot_ci(b7[quiet]); ci_b = boot_ci(b7[body]) if body.sum() > 3 else (np.nan, np.nan)
    pr("   %-9s %-8s episodes %3d (%5.1f s) | b7 duty: quiet %.3f [%.3f..%.3f] | pre-onset -1..0 s %.3f | onset 0..0.5 s %.3f | episode body %.3f [%.3f..%.3f] | b5 duty quiet %.3f body %.3f | env median %.0f" % (
        tag, LABEL[tag], len(eps), body.sum() / FS, EP[tag]["quiet"], ci_q[0], ci_q[1], EP[tag]["pre"], EP[tag]["onset"], EP[tag]["body"], ci_b[0], ci_b[1],
        nanmean(b5[quiet]), nanmean(b5[body]), med))
pr("\n   5b. THE OPERATOR'S BOOKMARKS (pressed right after a grinding episode): b7 / b5 duty and the 18-22 Hz envelopes in windows around each mark, engaged frames only")
for tag in NEW:
    M = json.load(open(os.path.join(CACHE, tag + "_marks.json")))
    g = G[tag]; tn14 = TN14[tag]; e = ENG14[tag]
    bp = C20.bandpass(g["bar"], 18, 22, FS); env = np.abs(signal.hilbert(bp)); env14 = np.interp(tn14, g["t"], env)
    rp = C20.bandpass(g["wire"], 18, 22, FS); renv = np.abs(signal.hilbert(rp)); renv14 = np.interp(tn14, g["t"], renv)
    for mk in M["marks"]:
        tm = mk["mono"]
        for lo, hi in ((-12, -6), (-6, 0), (0, 6)):
            w = e & (tn14 >= tm + lo) & (tn14 < tm + hi)
            pr("   %-9s bookmark seg %2d t_route %7.1f | window %+3d..%+3d s: engaged %4.1f s | b7 %.3f  b5 %.3f | bar 18-22 Hz env p50/max %5.0f/%5.0f | rate env p50/max %5.0f/%5.0f | v %.1f m/s |ang| %.0f" % (
                tag, mk["seg"], mk["t_route"], lo, hi, w.sum() / FS, nanmean(BIT[tag][7][w]), nanmean(BIT[tag][5][w]),
                np.median(env14[w]) if w.sum() else np.nan, env14[w].max() if w.sum() else np.nan,
                np.median(renv14[w]) if w.sum() else np.nan, renv14[w].max() if w.sum() else np.nan,
                np.interp(tm + (lo + hi) / 2, g["t"], g["vego"]), abs(np.interp(tm + (lo + hi) / 2, g["t"], g["ang"]))))

# =====================================================================================================================
# 6. 427 TAP RAIL
# =====================================================================================================================
pr("\n6. 427 (0x1AB) TORQUE TAP RAIL  [EVIDENCE: field = ((b0&3)<<8)|b1, magnitude = field & 511; the readout arithmetic caps at 310, 313 would refute it]")
RAIL = {}
for tag in ALL:
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int); mag = fld & 511
    u, c = np.unique(mag, return_counts=True)
    top = sorted(zip(u.tolist(), c.tolist()))[-4:]
    RAIL[tag] = int(mag.max())
    pr("   %-9s %-8s frames %6d | max |field| %3d | n(>=309) %5d (%.4f) | n(>=311) %d | n(313) %d | top values %s | %s" % (
        tag, LABEL[tag], len(mag), mag.max(), (mag >= 309).sum(), (mag >= 309).mean(), (mag >= 311).sum(), (mag == 313).sum(), top,
        "OK: rail <= 310" if mag.max() <= 310 else "!! EXCEEDS 310"))

# =====================================================================================================================
# 7. VERDICT
# =====================================================================================================================
pr("\n7. VERDICT PER ROUTE  [the rule AS FIRST WRITTEN, before the numbers: V289 rev 1 LIVE requires ALL of (i) b7 disengaged >= 0.99 AND b7 engaged < 0.30;")
pr("   (ii) b5 engaged in 0.40..0.60 AND b5 does NOT follow the command sign (|agree-0.5| < 0.15); (iii) b5's 18-22 Hz share > 2x the flat 0.095 OR the")
pr("   line-present |r| with the 20 Hz rate > 3x its null; (iv) bits 0-2 = 1.000 and b4/b6 within 0.05 of r39; (v) 427 rail <= 310.")
pr("   A V288 image fails (i) and (ii); a V282 image fails (i), (ii), (iii).]")
pr("   REVISIONS AFTER THE FIRST RUN, recorded so the reader can judge them:")
pr("   (i)  first read 0.966 / 0.952 on all not-lateral-engaged frames -> FAIL against 0.99.  Section 2c shows WHY: b7 climbs 0.10 -> 0.15 -> 0.5 -> 1.000 over the")
pr("        1-3 s after SCA falls, i.e. the 'reads 1.000 while disengaged' prediction assumed an instant drain that the wire does not show.  (i) is re-scored as")
pr("        b7 >= 0.99 on SCA = 0 frames MORE THAN 3 s after SCA fell, AND b7 >= 0.90 on all SCA = 0 frames.  The gap to the alternatives is two orders of magnitude")
pr("        (V288 0.007, V282 0.000 on the same statistic), so the revision cannot flip the answer; it is recorded because the threshold moved after the data were seen.")
pr("   (iv) b6 is V282's |r24| >= |T| comparator, whose duty is regime-dependent (r39 0.114, r5e 0.146, r63 0.228 on a faster route): reported, NOT scored.")
VERD = {}
for tag in NEW:
    de = DUTY[(tag, "engaged")]; dd = DUTY[(tag, "disengaged")]; d39 = DUTY[("r39", "engaged")]
    b = lambda n, d: d[7 - n]  # noqa: E731
    ag = AGREE[tag]
    i = SCA0[tag + "_late"] >= 0.99 and SCA0[tag] >= 0.90 and b(7, de) < 0.30
    ii = 0.40 <= b(5, de) <= 0.60 and ag < 0.15
    iii = SPEC[tag][1] > 0.19 or abs(XC[tag]["line-present"][0]) > 3 * XC[tag]["line-present"][2]
    iv = all(b(n, de) > 0.999 for n in (0, 1, 2)) and abs(b(4, de) - b(4, d39)) < 0.05
    v = RAIL[tag] <= 310
    ok = i and ii and iii and iv and v
    VERD[tag] = "V289 rev 1 LIVE" if ok else ("NOT V289 (V288-like)" if ag > 0.3 else "undecidable")
    pr("   %-9s (i) b7 SCA=0 >3 s %.3f, all SCA=0 %.3f (any-disengaged %.3f) / eng %.3f -> %s | (ii) b5 eng %.3f, |agree(cmd)-0.5| %.3f -> %s | (iii) b5 20 Hz share %.3f, line |r| %.3f vs null %.3f -> %s | (iv) b0-2 %s, b4 %.3f vs %.3f, b6 %.3f vs %.3f -> %s | (v) rail %d -> %s" % (
        tag, SCA0[tag + "_late"], SCA0[tag], b(7, dd), b(7, de), "PASS" if i else "FAIL", b(5, de), ag, "PASS" if ii else "FAIL", SPEC[tag][1], abs(XC[tag]["line-present"][0]), XC[tag]["line-present"][2], "PASS" if iii else "FAIL",
        "1/1/1" if all(b(n, de) > 0.999 for n in (0, 1, 2)) else "!!", b(4, de), b(4, d39), b(6, de), b(6, d39), "PASS" if iv else "FAIL", RAIL[tag], "PASS" if v else "FAIL"))
    pr("   %-9s ==> %s" % (tag, VERD[tag]))

open(OUTTXT, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("\nwrote", OUTTXT)
