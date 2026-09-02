#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/highangle_stutter.py -- the instrument for the operator's report on V278 rev 3:
"stuttering and oscillations at high angles far from center (angle = 0)".

For one route, over ENGAGED frames (0x18F b4.3 STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST), bin by
|steering angle| (0x14A) and report per bin: time, speed, band energy (2-4 / 4-8 / 8-15 Hz) of the 0x18F
rate, of openpilot's 0xE4 command and of the CAN-427 delivered-torque tap T, T saturation duty, T sign
flips/s, demand-index distribution, driver torque vs the override cliff (raw 2240-2560), and the
fraction of frames where the lane opposes the wheel (sign(T) != sign(rate)).  Then an EPISODE finder:
engaged stretches with a 2-8 Hz rate envelope above a disengaged-derived threshold, each listed with
angle, speed, dominant frequency (rate and T), amplitudes, and the command-vs-angle coherence at the
dominant frequency plus openpilot's desired-path flatness (controlsState.torqueState) -- the V276
diagnosis's own test for "is the outer loop in it".

Wire conventions (kit convention, see probe/decode_v278r3_torque_tap.py, studies/osc-2to4/direct_read_v276.py):
  0x18F src1  b0-1 i16be driver torque WIRE (raw = wire*1.024)  b2-3 i16be rate = -gp-0x6a56 (8 counts/deg/s)
              b4 bit3 STEER_CONTROL_ACTIVE
  0x14A src1  b0-1 i16be angle * -0.1 deg
  0x1AB src1  10-bit field ((b0&3)<<8)|b1 (the kit convention, direct_read_v276.py; VERIFIED on r31 seg 6: byte 0 is
              only ever 0x80/0x82, so probe/decode_v278r3_torque_tap.py's DBC layout ((b0&0x7F)<<3)|(b1>>5) reads 0-22
              and is WRONG for this wire -- reported 2026-09-02).  V278r3/V279r2: T = (-1 if bit9 else 1)*((field&0x1ff)<<3)
              🛑 on any other build this field is a DIFFERENT tap; T columns are printed only with --build v278r3
  0x0E4 src>=128 (openpilot TX) b0-1 i16be STEER_TORQUE command  b2 bit7 STEER_REQUEST
Demand index / override taper mirror studies/osc-2to4/dose_e_sign_by_k.py (from the FUN_00028ea6 decompile):
  S = clamp(-4*cmd, +-15360); taper = LERP(X 70,72,78,80 / Y 254,234,12,0 ; |tq_raw|>>5); v = (taper*255 & 0xFFFF)*S >> 16;
  idx = |clamp(v>>6, +-240)|.  Map X = (0,12,20,24,32,64,96,128,160,240); the ceiling index is 240 (idx>=160 = last segment).

Run:  python highangle_stutter.py --route 75604b0a432fdc89_00000031--a680e9b2ac --build v278r3 [--edges 0,10,30,60,120]
"""
import argparse
import glob
import json
import os
import sys

# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rlog_parse import read_messages  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
FS = 100.0
COUNTS_PER_DEGS = 8.0
BANDS = {"2-4": (2.0, 4.0), "4-8": (4.0, 8.0), "8-15": (8.0, 15.0)}
T_SAT_FIELD = 309                 # |field| >= 309 -> |T| >= 2472 (rail reads 310)
CLIFF_LO, CLIFF_HI = 2240, 2560   # override taper cliff, raw driver torque

MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
TAPER_X = np.array([70, 72, 78, 80], float)
TAPER_Y = np.array([254, 234, 12, 0], float)


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def segments(prefix):
    return sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))


def read_route(prefix):
    t18, tq, rate, sca = [], [], [], []
    t14, ang = [], []
    t1ab, b0, b1 = [], [], []
    e4 = {}                                   # src -> (t, cmd, req)
    tcs, vego = [], []
    tts, des, err, out = [], [], [], []
    for p in segments(prefix):
        it = read_messages(p)
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as ex:          # truncated tail segment (seen on r31 seg 10): keep what was read
                print("  ⚠ %s: stopped early (%s)" % (os.path.basename(p), str(ex).splitlines()[0][:80]))
                break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    src, addr = int(m.src), int(m.address)
                    if src == 1:
                        if addr == 0x18F and len(d) >= 5:
                            t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2))
                            sca.append((d[4] >> 3) & 1)
                        elif addr == 0x14A and len(d) >= 4:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1)
                        elif addr == 0x1AB and len(d) >= 2:
                            t1ab.append(tm); b0.append(d[0]); b1.append(d[1])
                    elif src >= 128 and addr == 0x0E4 and len(d) >= 3:
                        L = e4.setdefault(src, ([], [], []))
                        L[0].append(tm); L[1].append(i16be(d, 0)); L[2].append((d[2] >> 7) & 1)
            elif w == "carState":
                tcs.append(tm); vego.append(evt.carState.vEgo)
            elif w == "controlsState":
                cs = evt.controlsState
                try:
                    if cs.lateralControlState.which() == "torqueState":
                        ts = cs.lateralControlState.torqueState
                        tts.append(tm); des.append(ts.desiredLateralAccel); err.append(ts.error); out.append(ts.output)
                except Exception:
                    pass
        print("  read %s" % os.path.basename(p), flush=True)
    # openpilot's command appears on more than one src (bus 0 copy carries zeros on r31); take the src
    # that actually carries a request/command, not the busiest one
    src_e4 = max(e4, key=lambda s: (sum(e4[s][2]), sum(abs(c) for c in e4[s][1]))) if e4 else -1
    te4, cmd, req = e4.get(src_e4, ([], [], []))
    A = lambda x: np.asarray(x, float)
    return dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca), t14=A(t14), ang=A(ang),
                t1ab=A(t1ab), b0=A(b0), b1=A(b1), te4=A(te4), cmd=A(cmd), req=A(req), src_e4=np.array([src_e4]),
                tcs=A(tcs), vego=A(vego), tts=A(tts), des=A(des), err=A(err), out=A(out),
                e4_census=np.array([(s, len(e4[s][0])) for s in e4], float).reshape(-1, 2))


def demand_index(cmd, tq_raw):
    S = np.clip(-4.0 * np.round(cmd), -15360, 15360)
    taper = np.interp(np.abs(tq_raw) // 32, TAPER_X, TAPER_Y)
    prod = (taper * 255).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0)
    v = np.clip(np.floor(v / 64.0), -240, 240)
    return np.abs(v), taper


def runs_of(mask, minlen):
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.r_[0, m, 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def band_power(x, mask, nperseg=256):
    """Length-weighted Welch over contiguous runs of `mask`; returns {band: power} (variance units)."""
    runs = runs_of(mask, nperseg)
    if not runs:
        return {b: np.nan for b in BANDS}, 0
    acc, tot = None, 0
    for a, b in runs:
        seg = x[a:b] - x[a:b].mean()
        f, P = signal.welch(seg, fs=FS, nperseg=nperseg)
        acc = P * (b - a) if acc is None else acc + P * (b - a)
        tot += b - a
    P = acc / tot
    df = f[1] - f[0]
    return {k: float(P[(f >= lo) & (f < hi)].sum() * df) for k, (lo, hi) in BANDS.items()}, tot


def grid(D):
    t0 = D["t18"][0]
    T = D["t18"] - t0
    tg = np.arange(0.0, T[-1], 1 / FS)
    G = dict(t=tg)
    G["rate"] = np.interp(tg, T, D["rate"])
    G["tq"] = np.interp(tg, T, D["tq"] * 1.024)
    G["sca"] = np.interp(tg, T, D["sca"]) > 0.5
    G["ang"] = np.interp(tg, D["t14"] - t0, D["ang"])
    if len(D["te4"]):
        G["cmd"] = np.interp(tg, D["te4"] - t0, D["cmd"]); G["req"] = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    else:
        G["cmd"] = np.zeros_like(tg); G["req"] = np.zeros_like(tg, bool)
    G["v"] = np.interp(tg, D["tcs"] - t0, D["vego"]) if len(D["tcs"]) else np.zeros_like(tg)
    # 427 field held on the 100 Hz grid (50 Hz source, most-recent-value)
    idx = np.searchsorted(D["t1ab"] - t0, tg, side="right") - 1
    fld_native = (((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)) if "b0" in D else D["fld"].astype(int)
    fld = np.where(idx >= 0, fld_native[np.maximum(idx, 0)], 0).astype(int)
    G["fld"] = fld
    G["T"] = np.where((fld >> 9) & 1, -1.0, 1.0) * ((fld & 0x1FF) << 3)
    if len(D["tts"]):
        G["des"] = np.interp(tg, D["tts"] - t0, D["des"]); G["err"] = np.interp(tg, D["tts"] - t0, D["err"])
    else:
        G["des"] = G["err"] = None
    G["eng"] = G["sca"] & G["req"]
    G["idx"], G["taper"] = demand_index(G["cmd"], G["tq"])
    return G


def peak_freq(x, mask, lo=1.0, hi=20.0, nperseg=256):
    """Dominant frequency of x over the runs of mask, and its prominence over the median PSD in [lo,hi)."""
    runs = runs_of(mask, nperseg)
    if not runs:
        return np.nan, np.nan
    acc, tot = None, 0
    for a, b in runs:
        f, P = signal.welch(x[a:b] - x[a:b].mean(), fs=FS, nperseg=nperseg)
        acc = P * (b - a) if acc is None else acc + P * (b - a); tot += b - a
    P = acc / tot; sel = (f >= lo) & (f < hi)
    i = int(np.argmax(P[sel]))
    return float(f[sel][i]), float(P[sel][i] / max(np.median(P[sel]), 1e-30))


def per_bin(G, edges, haveT, base_key=None):
    eng, aa = G["eng"], np.abs(G["ang"])
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = eng & (aa >= lo) & (aa < hi)
        n = int(m.sum())
        r = dict(bin="%g-%g" % (lo, hi), secs=n / FS, v=float(np.nanmean(G["v"][m])) if n else np.nan)
        if n < 100:
            rows.append(r); continue
        r["rate"], r["nwelch"] = band_power(G["rate"], m)
        r["cmd"], _ = band_power(G["cmd"], m)
        r["idx_p50"] = float(np.median(G["idx"][m])); r["idx_ge160"] = float((G["idx"][m] >= 160).mean())
        r["idx_ge240"] = float((G["idx"][m] >= 240).mean())
        aq = np.abs(G["tq"][m])
        r["tq_p50"] = float(np.median(aq)); r["tq_p90"] = float(np.percentile(aq, 90))
        r["tq_ge_cliff"] = float((aq >= CLIFF_LO).mean()); r["tq_past_cliff"] = float((aq >= CLIFF_HI).mean())
        r["cmd_p50"] = float(np.median(np.abs(G["cmd"][m])))
        r["rate_p95"] = float(np.percentile(np.abs(G["rate"][m]), 95))
        r["fpk"], r["fpk_prom"] = peak_freq(G["rate"], m)
        if haveT:
            r["T"], _ = band_power(G["T"], m)
            f = G["fld"][m]
            r["T_sat"] = float(((f & 0x1FF) >= T_SAT_FIELD).mean())
            Tm = G["T"][m]
            s = np.sign(Tm); s = s[s != 0]
            r["T_flips_s"] = float((np.diff(s) != 0).sum() / (n / FS))
            ok = (G["rate"][m] != 0) & (Tm != 0)
            r["opposes"] = float((np.sign(Tm[ok]) != np.sign(G["rate"][m][ok])).mean()) if ok.any() else np.nan
            r["T_p50"] = float(np.median(np.abs(Tm))); r["T_p90"] = float(np.percentile(np.abs(Tm), 90))
            okc = (G["cmd"][m] != 0) & (Tm != 0)
            r["T_with_cmd"] = float((np.sign(Tm[okc]) == np.sign(G["cmd"][m][okc])).mean()) if okc.any() else np.nan
        rows.append(r)
    return rows


def episodes(G, haveT, ang_thr, band=(2.0, 8.0), thr_ref="lowang"):
    eng = G["eng"]
    sos = signal.butter(4, band, btype="bandpass", fs=FS, output="sos")
    rb = signal.sosfiltfilt(sos, G["rate"])
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    dis = ~eng
    thr_dis = max(2.5 * (np.percentile(env[dis], 95) if dis.any() else 0), 150.0)
    ref = eng & (np.abs(G["ang"]) < 10.0)
    thr_low = max(2.5 * (np.percentile(env[ref], 95) if ref.any() else 0), 100.0)
    thr = thr_low if thr_ref == "lowang" else thr_dis
    on = (env > thr) & eng
    eps = runs_of(on, int(1.0 * FS))
    merged = []
    for s, e in eps:
        if merged and s - merged[-1][1] < FS:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    cb = signal.sosfiltfilt(sos, G["cmd"]); Tb = signal.sosfiltfilt(sos, G["T"]) if haveT else None
    ab = signal.sosfiltfilt(sos, G["ang"])
    rows = []
    for s, e in merged:
        n = e - s; nps = min(256, n)
        f, P = signal.welch(rb[s:e], fs=FS, nperseg=nps)
        fdom = float(f[np.argmax(P)])
        f2, C = signal.coherence(G["cmd"][s:e], G["ang"][s:e], fs=FS, nperseg=nps)
        _, Pxy = signal.csd(G["cmd"][s:e], G["ang"][s:e], fs=FS, nperseg=nps)
        j = int(np.argmin(np.abs(f2 - fdom)))
        row = dict(t0=float(G["t"][s]), dur=n / FS, ang=float(np.median(G["ang"][s:e])),
                   ang_abs=float(np.median(np.abs(G["ang"][s:e]))), v=float(G["v"][s:e].mean()), fdom=fdom,
                   rate_amp=float(np.sqrt(2) * rb[s:e].std()), rate_pk=float(np.abs(G["rate"][s:e]).max()),
                   ang_swing=float(2 * np.sqrt(2) * ab[s:e].std()),
                   cmd_amp=float(np.sqrt(2) * cb[s:e].std()), cmd_p50=float(np.median(np.abs(G["cmd"][s:e]))),
                   coh=float(C[j]), phase=float(np.degrees(np.angle(Pxy[j]))),
                   tq_p50=float(np.median(np.abs(G["tq"][s:e]))), tq_ge_cliff=float((np.abs(G["tq"][s:e]) >= CLIFF_LO).mean()),
                   idx_p50=float(np.median(G["idx"][s:e])), idx_ge240=float((G["idx"][s:e] >= 240).mean()),
                   high=bool(np.median(np.abs(G["ang"][s:e])) >= ang_thr))
        if haveT:
            fT, PT = signal.welch(Tb[s:e], fs=FS, nperseg=nps)
            row["fdom_T"] = float(fT[np.argmax(PT)]); row["T_amp"] = float(np.sqrt(2) * Tb[s:e].std())
            row["T_sat"] = float(((G["fld"][s:e] & 0x1FF) >= T_SAT_FIELD).mean())
            fc, Ctr = signal.coherence(G["rate"][s:e], G["T"][s:e], fs=FS, nperseg=nps)
            _, Ptr = signal.csd(G["rate"][s:e], G["T"][s:e], fs=FS, nperseg=nps)
            jj = int(np.argmin(np.abs(fc - fdom)))
            row["coh_Tr"] = float(Ctr[jj]); row["ph_Tr"] = float(np.degrees(np.angle(Ptr[jj])))   # phase of T relative to RATE at fdom
            ok = (G["rate"][s:e] != 0) & (G["T"][s:e] != 0)
            row["opposes"] = float((np.sign(G["T"][s:e][ok]) != np.sign(G["rate"][s:e][ok])).mean()) if ok.any() else np.nan
        if G["des"] is not None:
            db = signal.sosfiltfilt(sos, G["des"]); eb = signal.sosfiltfilt(sos, G["err"])
            row["des_amp"] = float(np.sqrt(2) * db[s:e].std()); row["err_amp"] = float(np.sqrt(2) * eb[s:e].std())
        rows.append(row)
    return rows, (thr, thr_dis, thr_low), env


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True)
    ap.add_argument("--build", default="", help="v278r3 / v279r2 enables the T (427 tap) columns")
    ap.add_argument("--edges", default="0,10,30,60,120", help="|angle| bin edges, deg (open-ended last bin)")
    ap.add_argument("--ang-thr", type=float, default=30.0, help="episode 'high angle' threshold, deg")
    ap.add_argument("--thr-ref", default="lowang", choices=("lowang", "dis"),
                    help="episode envelope threshold reference: engaged |angle|<10 (default) or disengaged (V276 convention)")
    ap.add_argument("--band", default="2,8", help="episode band-pass, Hz")
    ap.add_argument("--cache", default=os.path.join(HERE, "_scratch"))
    ap.add_argument("--json", default="")
    a = ap.parse_args(argv)
    os.makedirs(a.cache, exist_ok=True)
    cache = os.path.join(a.cache, "_ha_%s.npz" % a.route)
    if os.path.exists(cache):
        D = dict(np.load(cache))
    else:
        D = read_route(a.route); np.savez(cache, **D)
    haveT = a.build.lower() in ("v278r3", "v279r2", "v279")
    G = grid(D)
    eng = G["eng"]
    print("=== ROUTE %s  (build %s) ===" % (a.route, a.build or "unstated"))
    print("0x18F %d  0x14A %d  0x1AB %d  0xE4 src %d (%d frames; census %s)  torqueState %d" % (
        len(D["t18"]), len(D["t14"]), len(D["t1ab"]), int(D["src_e4"][0]), len(D["te4"]),
        ", ".join("%d:%d" % tuple(x) for x in D["e4_census"]), len(D["tts"])))
    print("engaged %.1f s of %.1f s" % (eng.sum() / FS, len(eng) / FS))
    if not haveT:
        print("🛑 --build is not v278r3/v279r2: the 427 field is a DIFFERENT tap on this build; T columns suppressed.")
    aa = np.abs(G["ang"][eng])
    pct = np.percentile(aa, [50, 75, 90, 95, 99]) if eng.any() else [np.nan] * 5
    print("engaged |angle| deg: p50 %.1f p75 %.1f p90 %.1f p95 %.1f p99 %.1f max %.1f" % (*pct, aa.max() if eng.any() else np.nan))
    edges = [float(x) for x in a.edges.split(",")] + [np.inf]
    rows = per_bin(G, edges, haveT)
    base = next((r for r in rows if "rate" in r), None)
    print("\nPER |ANGLE| BIN (engaged; band energy = Welch power in band, ratio vs the lowest populated bin)")
    hdr = "%-9s %6s %5s | %-22s | %-22s |" % ("bin deg", "secs", "v", "RATE 2-4/4-8/8-15 (x base)", "CMD 2-4/4-8/8-15 (x base)")
    if haveT:
        hdr += " %-22s %5s %6s %5s |" % ("T 2-4/4-8/8-15 (x base)", "Tsat", "flip/s", "oppos")
    hdr += " %5s %5s %5s | %6s %6s %5s %5s | %6s %6s %5s %5s" % ("idx50", ">=160", "=240", "tq50", "tq90", ">=2240", ">2560", "cmd50", "r_p95", "fpk", "prom")
    if haveT:
        hdr += " | %5s %5s %5s" % ("|T|50", "|T|90", "T~cmd")
    print(hdr)
    for r in rows:
        line = "%-9s %6.1f %5.1f | " % (r["bin"], r["secs"], r["v"])
        if "rate" not in r:
            print(line + "(too few frames)"); continue
        fx = lambda k: "/".join("%5.2f" % (r[k][b] / base[k][b]) if base[k][b] else "  nan" for b in BANDS)
        line += "%-22s | %-22s |" % (fx("rate"), fx("cmd"))
        if haveT:
            line += " %-22s %5.3f %6.2f %5.2f |" % (fx("T"), r["T_sat"], r["T_flips_s"], r["opposes"])
        line += " %5.0f %5.2f %5.2f | %6.0f %6.0f %5.2f %5.2f | %6.0f %6.0f %5.1f %5.0f" % (
            r["idx_p50"], r["idx_ge160"], r["idx_ge240"], r["tq_p50"], r["tq_p90"], r["tq_ge_cliff"], r["tq_past_cliff"], r["cmd_p50"], r["rate_p95"], r["fpk"], r["fpk_prom"])
        if haveT:
            line += " | %5.0f %5.0f %5.2f" % (r["T_p50"], r["T_p90"], r["T_with_cmd"])
        print(line)
    if base is None:
        print("no populated bin -- nothing engaged"); return 1
    print("absolute base-bin band power: rate %s  cmd %s%s" % (
        {k: round(v) for k, v in base["rate"].items()}, {k: round(v) for k, v in base["cmd"].items()},
        ("  T %s" % {k: round(v) for k, v in base["T"].items()}) if haveT else ""))

    # hands split inside the high-angle bins: is the excess there when the driver is NOT pushing?
    hiA = eng & (np.abs(G["ang"]) >= a.ang_thr)
    print("\nHANDS SPLIT at |angle| >= %g deg (rate band power x low-angle base; 1.28 s Welch runs): " % a.ang_thr)
    for nm, mm in (("|tq_raw| < 1000", hiA & (np.abs(G["tq"]) < 1000)), ("1000-2240", hiA & (np.abs(G["tq"]) >= 1000) & (np.abs(G["tq"]) < CLIFF_LO)),
                   (">= 2240 (cliff)", hiA & (np.abs(G["tq"]) >= CLIFF_LO))):
        bp, nn = band_power(G["rate"], mm, nperseg=128)          # 1.28 s runs: the hands mask is fragmented
        fp = peak_freq(G["rate"], mm, nperseg=128)
        print("  %-18s %6.1f s  rate %s  fpk %.1f Hz prom %.0f" % (nm, mm.sum() / FS,
              "/".join("%6.1f" % (bp[b] / base["rate"][b]) if base["rate"][b] and np.isfinite(bp[b]) else "   nan" for b in BANDS), *fp))
    band = tuple(float(x) for x in a.band.split(","))
    eps, (thr, thr_dis, thr_low), env = episodes(G, haveT, a.ang_thr, band=band, thr_ref=a.thr_ref)
    print("\nEPISODES: %g-%g Hz rate envelope > %.0f wire (ref %s; disengaged-ref %.0f, low-angle-ref %.0f), engaged, >= 1 s; %d found, %.1f s total"
          % (band[0], band[1], thr, a.thr_ref, thr_dis, thr_low, len(eps), sum(e["dur"] for e in eps)))
    hi = [e for e in eps if e["high"]]
    print("  at |angle| >= %g deg: %d episodes, %.1f s;  engaged time at |angle| >= %g: %.1f s (%.1f%% of engaged) vs %.1f%% of oscillating time"
          % (a.ang_thr, len(hi), sum(e["dur"] for e in hi), a.ang_thr, (eng & (np.abs(G["ang"]) >= a.ang_thr)).sum() / FS,
             100 * (np.abs(G["ang"][eng]) >= a.ang_thr).mean(), 100 * sum(e["dur"] for e in hi) / max(sum(e["dur"] for e in eps), 1e-9)))
    hdr = "%3s %7s %5s %6s %5s %5s | %6s %6s %5s | %6s %5s %5s %5s | %5s %5s %4s %5s" % (
        "#", "t0", "dur", "ang", "v", "fdom", "rAmp", "rPk", "swing", "cAmp", "c50", "coh", "phase", "tq50", "cliff", "idx", "=240")
    if haveT:
        hdr += " | %5s %6s %5s %5s %5s %5s" % ("fdomT", "Tamp", "Tsat", "oppos", "cohTr", "phTr")
    if G["des"] is not None:
        hdr += " | %6s %6s" % ("desAmp", "errAmp")
    print(hdr)
    for k, e in enumerate(eps):
        line = "%3d %7.1f %5.1f %6.1f %5.1f %5.2f | %6.0f %6.0f %5.2f | %6.0f %6.0f %5.2f %5.0f | %5.0f %5.2f %4.0f %5.2f" % (
            k, e["t0"], e["dur"], e["ang"], e["v"], e["fdom"], e["rate_amp"], e["rate_pk"], e["ang_swing"], e["cmd_amp"], e["cmd_p50"],
            e["coh"], e["phase"], e["tq_p50"], e["tq_ge_cliff"], e["idx_p50"], e["idx_ge240"])
        if haveT:
            line += " | %5.2f %6.0f %5.3f %5.2f %5.2f %5.0f" % (e["fdom_T"], e["T_amp"], e["T_sat"], e["opposes"], e["coh_Tr"], e["ph_Tr"])
        if "des_amp" in e:
            line += " | %6.3f %6.3f" % (e["des_amp"], e["err_amp"])
        print(line + ("   <HIGH" if e["high"] else ""))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(dict(route=a.route, build=a.build, edges=edges[:-1], bins=rows, thr=thr, episodes=eps), fh, indent=1, default=float)
        print("wrote", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
