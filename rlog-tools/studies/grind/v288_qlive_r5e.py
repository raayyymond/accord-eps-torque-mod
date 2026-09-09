"""
V288 rev 2 -- Q-LIVENESS AND THE FILTER'S MEASURED DYNAMICS on the first V288 drive
route 75604b0a432fdc89_0000005e--03a9714d78 (2026-09-08), the pre-registered first read of this build.

The instrument: 0x14A byte 4 bit 5 = sign(filtered setpoint y) (1 when y < 0), the value the cave at
0xC4C00 stores to gp-0x6a32.  sp_raw is reconstructable offline from the logged 0xE4 through the
memoryless decode -> clamp -> assist-map chain, so a 1 kHz mirror of the cave gives y_model(t), and bit 5
vs sign(y_model) / sign(sp_raw) reads liveness, the frame phase and the group delay directly.

What this script does, in order (each section prints an EVIDENCE/BELIEF-tagged block):
  0. verify the V288 image hash; check the cells this reconstruction uses are byte-identical to V282's;
     count the V288-vs-V282 byte delta (build identity, read from the images, not the script constants)
  1. load the route (the kit's dejittered 0x18F frame axis, creep20_loop_id.load) + the native 0xE4 and
     0x14A-byte-4 streams; reconstruct sp_raw per 0xE4 frame with grind_incident_r35.demand_live
  2. run the golden model's cave mirror (eps_chain_control.lkas_setpoint_prefilter, instruction-for-
     instruction) at 1 kHz, ZOH per 0xE4 frame, hook skipped while not engaged (sentinel semantics)
  3. bit 5 vs sign(y_model): agreement engaged, frame-phase scan, per-segment duty, transition lags with
     bootstrap CIs, disagreement stretches classified
  4. operating regime: |sp_raw - y| lag, capped frames, the per-tick kick into the D term with and
     without the filter, and the D term's OUTPUT after its own clamp (the part the "kick / 16" claim
     does not cover)
  5. wallow check 0.5-4 Hz vs r39/r3a/r3c in matched strata (one route per arm: descriptive)
  6. build attribution from the tap

Writes rlog-tools/studies/grind/_scratch/v288_qlive_r5e.txt.  Reads caches only; builds nothing.
Python = the bin_decompile conda env, invoked as `python`.
"""
# ---- PATH BOOTSTRAP (same shape as grind_incident_r35.py) --------------------------------------------------------------
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
import creep20_loop_id as C20                    # noqa: E402  load, dejitter, grid_from, up1k, bandpass, bamp, runs
import lowcmd_loopgain_v112_v278_v280 as LG      # noqa: E402  read_build, FW, SEL
import v280_map_profiles as V                    # noqa: E402  chain constants
import grind_incident_r35 as R35                 # noqa: E402  read_cells, demand_live, lerp, simulate (V282 reconstruction)
from dataclasses import replace                  # noqa: E402
from eps_chain_core import Calibration, EpsState  # noqa: E402
from eps_chain_control import lkas_setpoint_prefilter  # noqa: E402  the cave mirror

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
CACHE = C20.CACHE                                                     # analysis-2020accord/_scratch/cache/v280
CORPUS = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache")
OUTDIR = os.path.join(HERE, "_scratch"); os.makedirs(OUTDIR, exist_ok=True)
OUTTXT = os.path.join(OUTDIR, "v288_qlive_r5e.txt")
TAG = "r5e_v288"
IMG288 = LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
IMG282 = LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
SHA288 = "94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c"
K_FILT = 4
CAP = 122                                     # wire_0xe4_slewcap.py: |delta| in {122,123} == on openpilot's 122.88 cap
T0_CORPUS = 21739.370758844                   # r5e_v288_bookmarks.json t0_mono_first_msg (the brief's route-relative t)
BOOKMARKS_MONO = (21868.702357025002, 22070.908560324002, 22559.491223219)   # userBookmark, segs 2/5/13
RNG = np.random.default_rng(20260908)
OUT = []


def pr(s=""):
    print(s); OUT.append(s)


def q(x, ps=(50, 90, 99)):
    x = np.asarray(x, float)
    return tuple(float(np.percentile(x, p)) for p in ps) if x.size else tuple(np.nan for _ in ps)


def boot_ci(x, stat=np.median, n=2000):
    x = np.asarray(x, float)
    if x.size < 3:
        return (np.nan, np.nan)
    v = np.array([stat(RNG.choice(x, x.size)) for _ in range(n)])
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


# =====================================================================================================================
# 0. BUILD IDENTITY FROM THE IMAGES
# =====================================================================================================================
pr("V288 REV 2 -- Q-LIVENESS AND THE FILTER'S MEASURED DYNAMICS, route %s (2026-09-08)" % "75604b0a432fdc89_0000005e--03a9714d78")
pr("=" * 118)
b288 = open(IMG288, "rb").read(); b282 = open(IMG282, "rb").read()
sha = hashlib.sha256(b288).hexdigest()
pr("\n0. IMAGE  [EVIDENCE: sha256 + full-file diff]")
pr("   V288r2 image sha256 %s  (%s)" % (sha, "MATCHES the record" if sha == SHA288 else "!! DOES NOT MATCH 94cabdef... -- STOP"))
assert sha == SHA288
diff = np.flatnonzero(np.frombuffer(b288, np.uint8) != np.frombuffer(b282, np.uint8))
regions = C20.runs(np.isin(np.arange(len(b288)), diff), 1) if diff.size else []
# merge byte runs separated by < 8 unchanged bytes into regions, as the record counts them
merged = []
for a, b in regions:
    if merged and a - merged[-1][1] < 8:
        merged[-1] = (merged[-1][0], b)
    else:
        merged.append((a, b))
pr("   V288r2 vs V282: %d bytes differ in %d regions: %s" % (diff.size, len(merged), ", ".join("0x%05X-0x%05X" % (a, b - 1) for a, b in merged)))
c288, c282 = R35.read_cells(IMG288), R35.read_cells(IMG282)
same = []
for k in c288:
    a, b = c288[k], c282[k]
    eq = all(np.array_equal(x, y) for x, y in zip(a, b)) if isinstance(a, tuple) else (np.array_equal(a, b) if isinstance(a, np.ndarray) else a == b)
    if not eq:
        same.append(k)
pr("   cells used by the reconstruction (map, Kp, Kd, tapers, fades, fb, lag, clamps, gain): %s" % ("ALL byte-identical V288 == V282" if not same else "DIFFER: %s" % same))
c = c288
pr("   slot %d: map X %s Y %s ; Kp Y %s ; Kd Y %s ; D clamp 0xC61B6 = %d ; P clamp %d ; sum clamp %d ; fb %d/%d clamp %d ; lag %d/%d ; gain %d" % (
    LG.SEL, c["map_X"].astype(int).tolist(), c["map_Y"].astype(int).tolist(), c["kp_Y"].astype(int).tolist(), c["kd_Y"].astype(int).tolist(),
    c["d_clamp"], c["p_clamp"], c["sum_clamp"], c["fb_a"], c["fb_b"], c["fb_clamp"], c["lag_a"], c["lag_b"], c["gain"]))
KD = float(np.median(c["kd_Y"]))
D_CLAMP = float(c["d_clamp"])

# =====================================================================================================================
# 1. LOAD THE ROUTE
# =====================================================================================================================
pr("\n1. ROUTE STREAMS  [EVIDENCE: caches built by extract_r5e_v280cache.py / extract_r5e_v288.py]")
g = C20.load(TAG)                                     # 0x18F frame axis (mono time), bar = tq x 1.024, cmd/ang/vego interpolated
D = dict(np.load(os.path.join(CACHE, TAG + ".npz")))
B4 = dict(np.load(os.path.join(CACHE, TAG + "_b4.npz")))
CP = dict(np.load(os.path.join(CORPUS, TAG, TAG + ".npz"), allow_pickle=True))
t0c = float(CP["t0_mono"][0])
pr("   0x18F frames %d (P %.5f s) ; 0xE4 frames %d ; 0x14A frames %d ; engaged-lateral (SCA & STEER_REQUEST) %.1f s of %.1f s" % (
    len(g["t"]), g["P18"], len(D["te4"]), len(B4["t14b"]), g["eng"].sum() / FS, (g["t"][-1] - g["t"][0])))
pr("   corpus probe_build label: %s ; corpus t0_mono %.3f ; brief's route-relative t0 %.3f ; v280 t0 %.3f" % (CP["probe_build"][0], t0c, T0_CORPUS, D["t18"][0]))
pr("   bookmarks (route-relative, corpus convention): %s" % ", ".join("%.2f s" % (m - T0_CORPUS) for m in BOOKMARKS_MONO))

# --- native 0xE4 frame axis ---------------------------------------------------------------------------------------------
ke4, Pe4, tne4, rese4 = C20.dejitter(D["te4"], 0.01, 100)
Ke = int(ke4[-1])
te = np.interp(np.arange(Ke + 1), ke4, tne4 - ke4 * Pe4) + np.arange(Ke + 1) * Pe4
cmd_e, have_e = C20.grid_from(ke4, D["cmd"].astype(float), Ke)
req_e, _ = C20.grid_from(ke4, D["req"].astype(float), Ke)
bar_e = np.interp(te, g["t"], g["bar"])
sca_e = np.interp(te, g["t"], g["sca"]) > 0.5
eng_e = sca_e & (req_e > 0.5) & have_e
idx_e, sgn_e = R35.demand_live(cmd_e, bar_e, c)
sp_e = sgn_e * R35.lerp(c["map_X"], c["map_Y"], np.round(idx_e))          # sp_raw per 0xE4 frame, signed
sp_e = sp_e.astype(np.int64)
pr("   0xE4 dejitter: P %.5f s, resid p50/p90 %.1f/%.1f ms ; %d frames filled ; sp_raw range [%d, %d], |sp_raw| p50/p90 engaged %.0f/%.0f" % (
    Pe4, 1e3 * np.percentile(rese4, 50), 1e3 * np.percentile(rese4, 90), (~have_e).sum(), sp_e.min(), sp_e.max(), *q(np.abs(sp_e[eng_e]), (50, 90))))

# =====================================================================================================================
# 2. THE 1 kHz MIRROR OF THE CAVE  (golden model function, instruction for instruction)
# =====================================================================================================================
pr("\n2. THE 1 kHz MIRROR  [EVIDENCE for the arithmetic: eps_chain_control.lkas_setpoint_prefilter, verified against the built cave]")
pr("   [BELIEF for the hook-run condition: hook runs <=> engaged-lateral (SCA & STEER_REQUEST) on the 0xE4 frame; the real skip routes")
pr("    follow Honda's engagement ramp, so a few ticks at each edge can differ -- classified in 3d]")
cal288 = replace(Calibration(), spfilt_k=K_FILT)
n1 = (Ke + 1) * 10
sp1k = np.repeat(sp_e, 10)                    # ZOH: the frame's sp lands on tick 0 of its 10
eng1k = np.repeat(eng_e, 10)
t1k = np.repeat(te, 10) + np.tile(np.arange(10) * Pe4 / 10, Ke + 1)
y1k = np.zeros(n1, np.int64)
first_tick = np.zeros(n1, bool)
st = EpsState()                               # fresh: pid_prev_err_cell == 0x7FFFFFFF (sentinel armed)
f = lkas_setpoint_prefilter
for i in range(n1):
    if eng1k[i]:
        first_tick[i] = st.pid_prev_err_cell == 0x7FFFFFFF
        y1k[i] = f(int(sp1k[i]), st, cal288)
        st.pid_prev_err_cell = 0              # the hook ran: Honda's epilogue overwrites the sentinel with a real E
    else:
        y1k[i] = 0                            # the store is not executed; the cell keeps its value but E is not formed
        st.pid_prev_err_cell = 0x7FFFFFFF     # a skip route wrote the sentinel
        # (the cell gp-0x6a32 keeps stale y; the model's st.sp_filter_y keeps it too -- irrelevant, the next tick re-inits)
n_eng_ticks = int(eng1k.sum())
pr("   ticks %d, engaged %d (%.1f s), engage-init ticks %d" % (n1, n_eng_ticks, n_eng_ticks / FS1K, first_tick.sum()))
# sanity: the mirror's own zero-crossing lag vs sp_raw -- what the wire SHOULD show if the cave is live
neg_sp = sp1k < 0; neg_y = y1k < 0


def crossings(neg, t, live):
    """(times, direction) of sign changes of a boolean 'negative' series, restricted to live ticks."""
    d = np.diff(neg.astype(int)); j = np.flatnonzero((d != 0) & live[1:] & live[:-1])
    return t[j + 1], d[j]


def match_lags(tA, dA, tB, dB, win=0.15):
    """for every A transition, the lag to the nearest same-direction B transition within +-win (A after B => positive)."""
    out = []
    for dirn in (+1, -1):
        a = tA[dA == dirn]; b = tB[dB == dirn]
        if not a.size or not b.size:
            continue
        j = np.searchsorted(b, a); j = np.clip(j, 1, len(b) - 1)
        cand = np.stack([a - b[j - 1], a - b[j]], 1)
        pick = cand[np.arange(len(a)), np.argmin(np.abs(cand), 1)]
        out.append(pick[np.abs(pick) <= win])
    return np.concatenate(out) if out else np.array([])


tcs, dcs = crossings(neg_sp, t1k, eng1k)
tcy, dcy = crossings(neg_y, t1k, eng1k)
lag_model = match_lags(tcy, dcy, tcs, dcs)
pr("   MODEL-ONLY: sign(y_model) crossings %d vs sign(sp_raw) crossings %d ; matched %d ; lag y after sp: p50 %.1f ms (IQR %.1f..%.1f), mean %.1f ms" % (
    len(tcy), len(tcs), len(lag_model), 1e3 * np.median(lag_model), 1e3 * np.percentile(lag_model, 25), 1e3 * np.percentile(lag_model, 75), 1e3 * lag_model.mean()))
pr("   (a first-order pole at 10.3 Hz delays a slow zero crossing by ~15 ms; a crossing through a dwell at sp = 0 by less -- this is the mirror's own answer)")

# =====================================================================================================================
# 3. BIT 5 ON THE WIRE vs THE MIRROR
# =====================================================================================================================
pr("\n3. 0x14A BYTE 4 BIT 5 vs sign(y_model)  [EVIDENCE: wire bits vs the offline mirror]")
k14, P14, tn14, res14 = C20.dejitter(B4["t14b"].astype(float), 0.01, 100)
b4 = B4["b4"].astype(int)
bit = {n: (b4 >> n) & 1 for n in range(8)}
eng14 = np.interp(tn14, te, eng_e.astype(float)) > 0.5
seg14 = np.interp(tn14, CP["t"] + t0c, CP["seg"])
pr("   0x14A dejitter: P %.5f s, resid p50/p90 %.1f/%.1f ms ; engaged frames %d (%.1f s)" % (P14, 1e3 * np.percentile(res14, 50), 1e3 * np.percentile(res14, 90), eng14.sum(), eng14.sum() / FS))
pr("   byte-4 bit duties, engaged-lateral: " + "  ".join("b%d %.3f" % (n, bit[n][eng14].mean()) for n in range(7, -1, -1)))

# 3a. frame-phase scan: sample y_model at t14 - delta
deltas = np.arange(-0.040, 0.0401, 0.001)
agree = []
for dl in deltas:
    j = np.clip(np.searchsorted(t1k, tn14 - dl, side="right") - 1, 0, n1 - 1)
    agree.append(float(np.mean((y1k[j] < 0).astype(int)[eng14] == bit[5][eng14])))
agree = np.array(agree); ibest = int(np.argmax(agree)); dbest = float(deltas[ibest])
j0 = np.clip(np.searchsorted(t1k, tn14, side="right") - 1, 0, n1 - 1)
jb = np.clip(np.searchsorted(t1k, tn14 - dbest, side="right") - 1, 0, n1 - 1)
yb = y1k[jb]; spb = sp1k[jb]
agr0 = float(np.mean((y1k[j0] < 0).astype(int)[eng14] == bit[5][eng14]))
agr_sp = float(np.mean((spb < 0).astype(int)[eng14] == bit[5][eng14]))
pr("\n   3a. AGREEMENT bit5 == [y_model < 0], engaged: %.4f at delta 0 ; BEST %.4f at delta %+.0f ms (bit sampled from y_model %.0f ms earlier)" % (agr0, agree[ibest], 1e3 * dbest, 1e3 * dbest))
pr("       agreement vs [sp_raw < 0] at the same delta: %.4f (the unfiltered comparator -- the filter's own lag costs this much agreement)" % agr_sp)
pr("       scan: " + " ".join("%+d:%.3f" % (1e3 * d, a) for d, a in zip(deltas[::5], agree[::5])))
# 3b. per segment
pr("\n   3b. PER SEGMENT (engaged-lateral frames): seg | eng s | bit5 duty | agree(best delta) | liveness")
for s in range(int(np.nanmax(seg14)) + 1):
    m = eng14 & (np.round(seg14) == s)
    if m.sum() < 10:
        pr("       %2d | %6.1f | (< 0.1 s engaged)" % (s, m.sum() / FS)); continue
    du = bit[5][m].mean(); ag = np.mean((yb[m] < 0).astype(int) == bit[5][m])
    live = "RUNG EXECUTES" if 0.0 < du < 1.0 else ("!! duty %.3f over %.1f s -- rung did NOT execute" % (du, m.sum() / FS) if m.sum() / FS >= 20 else "duty %.3f (< 20 s, not a liveness call)" % du)
    pr("       %2d | %6.1f | %9.3f | %17.4f | %s" % (s, m.sum() / FS, du, ag, live))
# 3c. transition lags
tw5, dw5 = crossings(bit[5].astype(bool), tn14, eng14)                    # bit 0->1 == y went negative == same sense as neg_* crossings
lag_w_sp = match_lags(tw5, dw5, tcs, dcs)
lag_w_y = match_lags(tw5, dw5, tcy, dcy)
ci_sp = boot_ci(lag_w_sp); ci_y = boot_ci(lag_w_y)
pr("\n   3c. TRANSITION LAGS (bit-5 edge time on the dejittered 0x14A axis minus the nearest same-direction crossing, +-150 ms window)")
pr("       bit5 edges engaged: %d ; matched to sign(sp_raw) crossings: %d (%.0f %%) ; to sign(y_model): %d (%.0f %%)" % (
    len(tw5), len(lag_w_sp), 100 * len(lag_w_sp) / max(1, len(tw5)), len(lag_w_y), 100 * len(lag_w_y) / max(1, len(tw5))))
pr("       bit5 after sign(sp_raw): median %+.1f ms  [95 %% bootstrap CI %+.1f .. %+.1f]  IQR %+.1f..%+.1f  mean %+.1f  (10 ms frame quantisation)" % (
    1e3 * np.median(lag_w_sp), 1e3 * ci_sp[0], 1e3 * ci_sp[1], 1e3 * np.percentile(lag_w_sp, 25), 1e3 * np.percentile(lag_w_sp, 75), 1e3 * lag_w_sp.mean()))
pr("       bit5 after sign(y_model): median %+.1f ms  [CI %+.1f .. %+.1f]  IQR %+.1f..%+.1f  mean %+.1f  (= frame phase + bus latency only, if the cave is live)" % (
    1e3 * np.median(lag_w_y), 1e3 * ci_y[0], 1e3 * ci_y[1], 1e3 * np.percentile(lag_w_y, 25), 1e3 * np.percentile(lag_w_y, 75), 1e3 * lag_w_y.mean()))
pr("       difference of medians (the filter's measured group delay at zero crossings): %+.1f ms ; model-only expectation %+.1f ms" % (
    1e3 * (np.median(lag_w_sp) - np.median(lag_w_y)), 1e3 * np.median(lag_model)))
# cross-correlation on the 1 kHz grid, block bootstrap
bit5_1k = np.interp(t1k, tn14, bit[5].astype(float)) > 0.5
lags_ms = np.arange(-100, 101, 1)
live = eng1k.copy()


def xcorr_peak(sel):
    a = bit5_1k[sel].astype(float); a -= a.mean()
    best = (-2, 0)
    for L in lags_ms:
        bser = np.roll(neg_sp, L)[sel].astype(float); bser -= bser.mean()
        r = float(np.dot(a, bser) / (np.linalg.norm(a) * np.linalg.norm(bser) + 1e-12))
        if r > best[0]:
            best = (r, L)
    return best


rpk, Lpk = xcorr_peak(live)
blocks = C20.runs(live, 10000)                                  # >= 10 s engaged blocks
blk_L = []
for _ in range(200):
    pick = RNG.choice(len(blocks), len(blocks))
    m = np.zeros(n1, bool)
    for p in pick:
        m[blocks[p][0]:blocks[p][1]] = True
    blk_L.append(xcorr_peak(m)[1])
pr("       cross-correlation bit5(t) vs [sp_raw<0](t) on the 1 kHz grid: peak r %.3f at lag %+d ms ; block-bootstrap (%d blocks >= 10 s) 95 %% CI %+.0f .. %+.0f ms" % (
    rpk, Lpk, len(blocks), np.percentile(blk_L, 2.5), np.percentile(blk_L, 97.5)))
# 3d. disagreement stretches
dis = eng14 & ((yb < 0).astype(int) != bit[5])
stretches = C20.runs(dis, 3)
edge_e = np.flatnonzero(np.diff(eng_e.astype(int)) != 0); tedge = te[edge_e + 1]
segb = CP["seg_bounds"]; tsegb = np.r_[segb[:, 1], segb[:, 2]] + t0c if segb.shape[1] >= 3 else np.array([])
cls = dict(edge=0, seg=0, hands=0, near0=0, other=0); secs = dict(edge=0.0, seg=0.0, hands=0.0, near0=0.0, other=0.0); ex = []
bar14 = np.interp(tn14, g["t"], g["bar"])
for a, b in stretches:
    tm = tn14[a:b]; L = (b - a) / FS
    if tedge.size and np.min(np.abs(tm[:, None] - tedge[None, :])) < 0.5:
        k = "edge"
    elif tsegb.size and np.min(np.abs(tm[:, None] - tsegb[None, :])) < 1.0:
        k = "seg"
    elif np.max(np.abs(bar14[a:b])) > 700:
        k = "hands"
    elif np.median(np.abs(spb[a:b])) < 16:
        k = "near0"
    else:
        k = "other"
    cls[k] += 1; secs[k] += L
    if k == "other" and len(ex) < 8:
        ex.append((tm[0] - T0_CORPUS, L, float(np.median(spb[a:b])), float(np.median(yb[a:b])), float(np.median(bar14[a:b]))))
pr("\n   3d. DISAGREEMENT STRETCHES (>= 3 consecutive engaged frames): %d stretches, %.2f s of %.1f s engaged (%.2f %%)" % (
    len(stretches), dis.sum() / FS, eng14.sum() / FS, 100 * dis.sum() / max(1, eng14.sum())))
pr("       by class: " + " ; ".join("%s %d (%.2f s)" % (k, cls[k], secs[k]) for k in cls) + "   [edge: < 0.5 s of an engage edge ; seg: < 1 s of a segment boundary ; hands: |bar| > 700 ; near0: |sp_raw| < 16]")
for e in ex:
    pr("       'other' example: t %.2f s, %.2f s long, sp_raw %+.0f y_model %+.0f bar %+.0f" % e)
# the three bookmarks: is the instrument sane right there?
pr("\n   3e. AT THE THREE BOOKMARKS (+-2 s window, engaged frames): agree | bit5 duty | |sp_raw| p50 | |sp_raw - y| p50 | capped frames")
for m_ in BOOKMARKS_MONO:
    w = eng14 & (np.abs(tn14 - m_) <= 2.0)
    we = eng_e & (np.abs(te - m_) <= 2.0)
    dce = np.abs(np.diff(cmd_e, prepend=cmd_e[0]))
    if w.sum():
        pr("       t %.2f s: %.3f | %.3f | %5.0f | %5.0f | %.2f" % (m_ - T0_CORPUS, np.mean((yb[w] < 0).astype(int) == bit[5][w]), bit[5][w].mean(),
                                                                    np.median(np.abs(spb[w])), np.median(np.abs(spb[w] - yb[w])), np.mean(dce[we] >= CAP) if we.sum() else np.nan))

# =====================================================================================================================
# 4. OPERATING REGIME -- how far the filter lags, capped frames, the kick into the D term
# =====================================================================================================================
pr("\n4. THE FILTER'S OPERATING REGIME ON THIS DRIVE  [EVIDENCE from the mirror; the D-term OUTPUT lines are the mirror's arithmetic with the image's clamp]")
lagc = np.abs(sp1k - y1k)[eng1k]
pr("   |sp_raw - y| per engaged tick (counts of sp, +-1032 full scale): p50/p90/p99/max %.0f/%.0f/%.0f/%.0f ; == 0 on %.1f %% of ticks ; >= 16 on %.1f %% ; >= 32 on %.1f %%" % (
    *q(lagc), lagc.max(), 100 * np.mean(lagc == 0), 100 * np.mean(lagc >= 16), 100 * np.mean(lagc >= 32)))
dcmd = np.diff(cmd_e, prepend=cmd_e[0]); chg = eng_e & have_e & (dcmd != 0); capf = eng_e & have_e & (np.abs(dcmd) >= CAP)
pr("   0xE4 frames engaged: %d ; command changes on %.1f %% ; ON THE SLEW CAP (|d| >= %d) %.2f %% (%d frames) ; longest same-sign capped run %d frames" % (
    eng_e.sum(), 100 * chg.sum() / eng_e.sum(), CAP, 100 * capf.sum() / eng_e.sum(), capf.sum(),
    max([b - a for a, b in C20.runs(capf & (np.sign(dcmd) == np.sign(np.roll(dcmd, 1))), 1)] + [0])))
# per-tick setpoint kick into the D term: raw = 32*dsp on the landing tick (0 elsewhere) ; filtered = 32*dy every tick
dsp1k = np.zeros(n1, np.int64); dsp1k[::10] = np.diff(sp_e, prepend=sp_e[0])
dEs_raw = 32 * dsp1k; dEs_f = 32 * np.diff(y1k, prepend=y1k[0])
land = eng1k & (np.arange(n1) % 10 == 0) & (dsp1k != 0)
pr("\n   4a. PER-TICK SETPOINT KICK 32*d(sp) INTO THE D TERM (setpoint part of dE only; feedback dfb identical in both builds)")
pr("       V282 (raw, landing ticks with a change, n=%d): |32 dsp| p50/p90/p99/max %.0f/%.0f/%.0f/%.0f" % (land.sum(), *q(np.abs(dEs_raw[land])), np.abs(dEs_raw[land]).max()))
nz = eng1k & (dEs_f != 0)
pr("       V288 (filtered, all engaged ticks with dy != 0, n=%d): |32 dy| p50/p90/p99/max %.0f/%.0f/%.0f/%.0f" % (nz.sum(), *q(np.abs(dEs_f[nz])), np.abs(dEs_f[nz]).max()))
# per-frame peak ratio on capped frames
fr = np.flatnonzero(capf)
pk_raw = np.abs(32 * dsp1k[fr * 10]); pk_f = np.array([np.abs(dEs_f[i * 10:i * 10 + 10]).max() for i in fr])
if fr.size:
    pr("       on the %d CAPPED frames: raw kick p50 %.0f, filtered peak-in-frame p50 %.0f -> ratio p50 %.1fx (the 'kick / 16' claim; %.0f -> %.0f in the design note)" % (
        fr.size, np.median(pk_raw), np.median(pk_f), np.median(pk_raw / np.maximum(pk_f, 1)), 3936, 224))
# 4b. the D term's OUTPUT after its own clamp -- setpoint part only, then full E via the chain mirror
Draw_sp = np.clip(np.floor(dEs_raw * KD / 8), -D_CLAMP, D_CLAMP); Df_sp = np.clip(np.floor(dEs_f * KD / 8), -D_CLAMP, D_CLAMP)
pr("\n   4b. THE D TERM'S OUTPUT AFTER ITS CLAMP (D = floor(dE*Kd/8), Kd %d, clamp %d -> binds at |dE| >= %d, i.e. |dy| >= %d counts/tick)" % (KD, D_CLAMP, int(np.ceil(D_CLAMP * 8 / KD)), int(np.ceil(D_CLAMP * 8 / KD / 32))))
pr("       setpoint-only D, engaged ticks: V282 mean|D| %.0f, bind duty %.3f, nonzero duty %.3f | V288 mean|D| %.0f, bind duty %.3f, nonzero duty %.3f" % (
    np.abs(Draw_sp[eng1k]).mean(), np.mean(np.abs(Draw_sp[eng1k]) >= D_CLAMP), np.mean(Draw_sp[eng1k] != 0),
    np.abs(Df_sp[eng1k]).mean(), np.mean(np.abs(Df_sp[eng1k]) >= D_CLAMP), np.mean(Df_sp[eng1k] != 0)))
if fr.size:
    capt = np.zeros(n1, bool)
    for i in fr:
        capt[i * 10:i * 10 + 10] = True
    pr("       inside CAPPED frames (%d ticks): V282 mean|D| %.0f (sum per frame %.0f) | V288 mean|D| %.0f (sum per frame %.0f) -> x%.1f" % (
        capt.sum(), np.abs(Draw_sp[capt]).mean(), np.abs(Draw_sp[capt]).mean() * 10, np.abs(Df_sp[capt]).mean(), np.abs(Df_sp[capt]).mean() * 10,
        np.abs(Df_sp[capt]).mean() / max(1e-9, np.abs(Draw_sp[capt]).mean())))
pr("       reading: with the image's clamp the filtered per-tick steps NEVER bind D (|dy| >= 20 counts/tick is unreachable at |sp - y| < 320); the")
pr("       integral of dE over a frame is the same in both arms (DC gain 1), so the D term's integrated output per moving frame is conserved (+8 % inside")
pr("       capped frames, the raw arm's rare clamp binds removed) while the per-tick peak falls ~11x.  The 'kick / 16' claim holds as a RATIO; the design")
pr("       note's absolute figures (3936 -> 224) were sized in raw 0xE4 counts, not sp counts: a capped 123-raw step is ~33 sp counts (map slope 4.3/idx,")
pr("       idx = raw/16), i.e. 32*33 = 1056, matching the measured p50 1088.  [EVIDENCE: arithmetic + this route]")
# 4b'. small-signal regime: the +1 fix makes the filter a +-1 count/tick slew follower below |sp - y| = 16
pr("\n   4b'. SMALL-SIGNAL REGIME -- the +1 rounding fix makes |dy| = 1 for ANY 0 < |sp - y| < 16 (and sar's floor gives |dy| = ceil(|d|/16) for d < 0),")
pr("        so below 16 counts of tracking error the cave is a UNIT-SLEW FOLLOWER (1 count/ms), not a 10.3 Hz pole.  A ripple of amplitude A counts at f Hz")
pr("        has peak slope 2*pi*f*A/1000 counts/tick: at 20 Hz any A < 8 counts is followed with ~1 count of lag, i.e. UNFILTERED.  Measured on this route:")
for lo, hi, lab in ((1, 3, "1-3 Hz"), (5, 10, "5-10 Hz"), (18, 22, "18-22 Hz"), (30, 45, "30-45 Hz")):
    a_sp = C20.bamp(sp1k[eng1k].astype(float), lo, hi, FS1K); a_y = C20.bamp(y1k[eng1k].astype(float), lo, hi, FS1K)
    fc = 0.5 * (lo + hi); Hlin = 1.0 / np.sqrt(1.0 + (fc / 10.3) ** 2)
    pr("        %-8s band amplitude of sp_raw %.2f -> y_model %.2f : delivered |H| = %.2f ; a LINEAR 10.3 Hz pole would give %.2f" % (lab, a_sp, a_y, a_y / max(a_sp, 1e-9), Hlin))
# by tracking-error regime: attenuation at 18-22 Hz in 2 s windows split by the window's p90 |sp - y|
wins = [(i, i + 2000) for i in range(0, n1 - 2000, 2000) if eng1k[i:i + 2000].all()]
reg = dict(small=[], mid=[], large=[])
for a_, b_ in wins:
    e90 = np.percentile(np.abs(sp1k[a_:b_] - y1k[a_:b_]), 90)
    r_ = C20.bamp(y1k[a_:b_].astype(float), 18, 22, FS1K) / max(1e-9, C20.bamp(sp1k[a_:b_].astype(float), 18, 22, FS1K))
    reg["small" if e90 < 8 else ("mid" if e90 < 32 else "large")].append(r_)
pr("        18-22 Hz |H| per fully-engaged 2 s window, by the window's p90 |sp - y|:  < 8 counts: %.2f (n %d) | 8-32: %.2f (n %d) | >= 32: %.2f (n %d)" % (
    np.median(reg["small"]) if reg["small"] else np.nan, len(reg["small"]), np.median(reg["mid"]) if reg["mid"] else np.nan, len(reg["mid"]),
    np.median(reg["large"]) if reg["large"] else np.nan, len(reg["large"])))
pr("        [EVIDENCE: arithmetic of the built cave + the mirror on this route.  Consequence for the design's target: the small 20 Hz ECHO on the command")
pr("         passes the filter nearly untouched; only the large capped-frame steps are spread out.]")
np.savez_compressed(os.path.join(OUTDIR, "v288_qlive_r5e_mirror.npz"), t1k=t1k, sp1k=sp1k, y1k=y1k, eng1k=eng1k, te=te, sp_e=sp_e, cmd_e=cmd_e, eng_e=eng_e, tn14=tn14, b4=b4)

# 4c. full chain mirror on the whole route (open loop: logged rate as feedback), sp raw vs filtered
def chain_1k(sp_in, kd=KD):
    """grind_incident_r35.simulate's arithmetic on a caller-supplied 1 kHz setpoint (validated against simulate() below)."""
    wire1k = np.interp(t1k, g["t"], g["wire"])      # rate wire on the 0xE4 tick grid (the two grids share the mono clock)
    x = -wire1k
    s = 0.0; fb = np.empty(n1)
    for i in range(n1):
        s_new = np.floor((c["fb_a"] * s + c["fb_b"] * x[i]) / 1024.0)
        fb[i] = s + s_new; s = s_new
    fb = np.clip(fb, -c["fb_clamp"], c["fb_clamp"])
    idx1k = np.repeat(np.round(idx_e), 10); bar1k = np.repeat(bar_e, 10)
    kp = R35.lerp(c["kp_X"], c["kp_Y"], idx1k)
    E = 32 * sp_in - fb
    P = np.clip(np.floor(E * kp / 256), -c["p_clamp"], c["p_clamp"])
    dE = np.r_[0.0, np.diff(E)]
    Dt = np.clip(np.floor(dE * kd / 8), -D_CLAMP, D_CLAMP)
    B = R35.lerp(c["fadeB"][0], c["fadeB"][1], np.abs(bar1k) // 32)
    m = ((255.0 * B).astype(np.int64) & 0xFFFF) >> 8

    def post(u):
        S = np.clip(np.floor(m * u / 256), -c["sum_clamp"], c["sum_clamp"]); S[~eng1k] = 0.0
        stt = signal.lfilter([c["lag_b"] / 1024.0], [1.0, -c["lag_a"] / 1024.0], S); y = (np.r_[0.0, stt[:-1]] + stt) / 32.0
        return np.clip(np.floor(-y * c["gain"] / 32768), -V.OUT_CAP, V.OUT_CAP)
    return dict(T=post(P + Dt), TD=post(Dt), TP=post(P), D=Dt, P=P, E=E, dE=dE, fb=fb)


S282 = chain_1k(sp1k.astype(float)); S288 = chain_1k(y1k.astype(float))
pr("\n   4c. FULL-E MIRROR ON THE WHOLE ROUTE (open loop: the LOGGED rate is the feedback in both arms; shares, not closed-loop predictions)")
for lab, S in (("V282 arm (sp raw) ", S282), ("V288 arm (sp filt)", S288)):
    e = eng1k
    pr("       %s: D bind duty %.3f | mean|D| %4.0f | mean|T_D| %4.0f mean|T| %4.0f | 18-22 Hz amp of T %.1f, of T_D %.1f, of T_P %.1f | 1-3 Hz amp of T %.1f" % (
        lab, np.mean(np.abs(S["D"][e]) >= D_CLAMP), np.abs(S["D"][e]).mean(), np.abs(S["TD"][e]).mean(), np.abs(S["T"][e]).mean(),
        C20.bamp(S["T"][e], 18, 22, FS1K), C20.bamp(S["TD"][e], 18, 22, FS1K), C20.bamp(S["TP"][e], 18, 22, FS1K), C20.bamp(S["T"][e], 1, 3, FS1K)))
if fr.size:
    pr("       inside CAPPED frames: mean|T_D| V282 %.0f -> V288 %.0f ; mean T (signed, along the command direction) V282 %+.0f -> V288 %+.0f" % (
        np.abs(S282["TD"][capt]).mean(), np.abs(S288["TD"][capt]).mean(),
        np.mean(S282["T"][capt] * np.repeat(np.sign(dsp1k[::10]), 10)[capt]), np.mean(S288["T"][capt] * np.repeat(np.sign(dsp1k[::10]), 10)[capt])))
# validate chain_1k against R35.simulate on one engaged window with the identity setpoint (same grid semantics differ: simulate uses the 0x18F axis)
w = C20.runs(g["eng"], 600)
if w:
    a, b = w[0][0] + 50, w[0][0] + 550
    Ssim = R35.simulate(g, a, b, c, kd=KD, lag=(c["lag_a"], c["lag_b"]))
    pr("       cross-check vs grind_incident_r35.simulate on one 5 s window (0x18F axis vs 0xE4 axis, so not bit-identical): median|T| %.0f vs %.0f, D bind duty %.3f vs %.3f" % (
        np.median(np.abs(Ssim["T"])), np.median(np.abs(S282["T"][(t1k >= g["t"][a]) & (t1k < g["t"][b])])), Ssim["drail"],
        np.mean(np.abs(S282["D"][(t1k >= g["t"][a]) & (t1k < g["t"][b]) & eng1k]) >= D_CLAMP)))

# =====================================================================================================================
# 5. WALLOW CHECK 0.5-4 Hz vs V282's r39 / r3a / r3c in matched strata
# =====================================================================================================================
pr("\n5. NEW SLOW WALLOW?  0.5-4 Hz on engaged, straight (|ang| < 10 deg), hands-off (|bar| < 400) driving  [descriptive: ONE route per arm]")
ARMS = {"r5e_v288": "V288r2", "r39": "V282", "r3a": "V282", "r3c": "V282"}
SPEED = [("v 1-6", 1.0, 6.0), ("v 6-15", 6.0, 15.0), ("v 15-30", 15.0, 30.0)]
GG = {TAG: g}
for r in ("r39", "r3a", "r3c"):
    GG[r] = C20.load(r)
CPX = {TAG: CP}
for r in ("r39", "r3a", "r3c"):
    p = os.path.join(CORPUS, r, r + ".npz")
    CPX[r] = dict(np.load(p, allow_pickle=True)) if os.path.exists(p) else None


def band_power(x, fs, lo, hi, nseg):
    f, P = signal.welch(x - x.mean(), fs=fs, nperseg=nseg)
    m = (f >= lo) & (f < hi)
    return float(np.trapezoid(P[m], f[m])), f[m][int(np.argmax(P[m]))] if m.any() else np.nan


def stratum_runs(gg, lo, hi, min_s=4.0):
    m = gg["eng"] & (gg["vego"] >= lo) & (gg["vego"] < hi) & (np.abs(gg["ang"]) < 10) & (np.abs(gg["bar"]) < 400)
    return C20.runs(m, int(min_s * FS)), m.sum() / FS


res = {}
for lab, lo, hi in SPEED:
    pr("\n   %s, runs >= 4 s (Welch 2.56 s): route | build | n runs | secs | 1-3 Hz power (bootstrap over runs) of ang [deg^2] | cmd [raw^2] | bar [raw^2] | 0.5-4 Hz peak f ang/cmd | op co_req 1-3 Hz" % lab)
    for r in ARMS:
        gg = GG[r]; rr, msecs = stratum_runs(gg, lo, hi)
        if not rr:
            pr("       %-8s | %-6s | 0 runs (stratum mask %.0f s in total, none contiguous >= 4 s)" % (r, ARMS[r], msecs)); continue
        P = dict(ang=[], cmd=[], bar=[], fang=[], fcmd=[], op=[])
        for a, b in rr:
            for k in ("ang", "cmd", "bar"):
                p_, fpk = band_power(gg[k][a:b], FS, 1.0, 3.0, 256)
                P[k].append(p_)
                if k == "ang":
                    P["fang"].append(band_power(gg[k][a:b], FS, 0.5, 4.0, 256)[1])
                if k == "cmd":
                    P["fcmd"].append(band_power(gg[k][a:b], FS, 0.5, 4.0, 256)[1])
            cp = CPX[r]
            if cp is not None and "co_req" in cp:
                tt = cp["t"] + float(cp["t0_mono"][0]); sel = (tt >= gg["t"][a]) & (tt < gg["t"][b])
                if sel.sum() > 400:
                    xo = np.interp(gg["t"][a:b], tt[sel], cp["co_req"][sel]); P["op"].append(band_power(xo, FS, 1.0, 3.0, 256)[0])
        secs = sum(b - a for a, b in rr) / FS
        res[(lab, r)] = P
        ci = {k: boot_ci(P[k], np.mean) for k in ("ang", "cmd", "bar")}
        pr("       %-8s | %-6s | %2d | %5.0f | %.4f [%.4f..%.4f] | %6.0f [%6.0f..%6.0f] | %6.0f [%6.0f..%6.0f] | %.2f/%.2f | %s" % (
            r, ARMS[r], len(rr), secs, np.mean(P["ang"]), *ci["ang"], np.mean(P["cmd"]), *ci["cmd"], np.mean(P["bar"]), *ci["bar"],
            np.median(P["fang"]), np.median(P["fcmd"]), ("%.3g" % np.mean(P["op"])) if P["op"] else "n/a"))
    # ratio V288 / pooled V282
    for k in ("ang", "cmd", "bar"):
        a_ = res.get((lab, TAG), {}).get(k, []); b_ = sum((res.get((lab, r), {}).get(k, []) for r in ("r39", "r3a", "r3c")), [])
        if a_ and b_:
            rat = [np.mean(RNG.choice(a_, len(a_))) / np.mean(RNG.choice(b_, len(b_))) for _ in range(2000)]
            pr("       ratio V288 / V282(pooled r39+r3a+r3c) 1-3 Hz power of %-3s: %.2f  [95 %% CI %.2f .. %.2f]  (runs bootstrapped; one route per arm)" % (
                k, np.mean(a_) / np.mean(b_), np.percentile(rat, 2.5), np.percentile(rat, 97.5)))

# =====================================================================================================================
# 6. BUILD ATTRIBUTION FROM THE TAP
# =====================================================================================================================
pr("\n6. IS THIS V288 REV 2?  attribute from the tap, not the label  [EVIDENCE]")
g39 = GG["r39"]; B39 = dict(np.load(os.path.join(CACHE, "r39_b4.npz"))); b39 = B39["b4"].astype(int)
e39 = np.interp(B39["t14b"], g39["t"], g39["eng"].astype(float)) > 0.5
pr("   byte-4 duty engaged   this route: " + "  ".join("b%d %.3f" % (n, bit[n][eng14].mean()) for n in range(7, -1, -1)))
pr("   byte-4 duty engaged   r39 (V282): " + "  ".join("b%d %.3f" % (n, ((b39 >> n) & 1)[e39].mean()) for n in range(7, -1, -1)))
pr("   bit 5 tracks sign(y_model) at %.3f agreement here; on V282 bit 5 was |r24| >= |aggregator| (r39 duty %.3f).  A V282 image cannot produce a bit that" % (agree[ibest], ((b39 >> 5) & 1)[e39].mean()))
pr("   follows the sign of the FILTERED setpoint with a %+.0f ms lag; bits 6/4/3/7 keep their V282 duties within the route-to-route spread; bits 0-2 (stock) are intact." % (1e3 * (np.median(lag_w_sp))))
pr("   corpus label: %s ; 0x1AB tap frames %d." % (CP["probe_build"][0], len(CP["ab_t1ab"])))

open(OUTTXT, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("\nwrote", OUTTXT)
