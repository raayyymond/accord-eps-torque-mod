# -*- coding: utf-8 -*-
r"""m1_attrib_interlocks.py -- M1 (a) attribution, (d) interlocks on the wire, (e) engage/disengage/override events,
route 79 (V298 first flight).  ANALYSIS ONLY: reads the kit caches, writes one JSON + text under _scratch/out/r79/m1/.
No rlog is read; nothing is sent; nothing is flashed.

CACHES (all on the logMonoTime clock, EVIDENCE from the extractor's README):
  wire  analysis-2020accord/_scratch/cache/v280/r79_a1f5d2_al.npz      (0x18F/0x14A/0x1AB/0xE4 bus-129 echo/carState)
  b4    analysis-2020accord/_scratch/cache/v280/r79_a1f5d2_al_b4.npz   (0x14A byte 4)
  fork  analysis-2020accord/_scratch/cache/v280/r79_fork.npz           (fork-side: 0xE4 by source, panda, events)
  extra _scratch/angle_loop/drive-read/routes/<route>_extras.npz       (0x18F STEER_STATUS st18, carFw, initData params)
Units: wire tq = raw counts (the kit's bar = raw*1.024); wire rate = raw counts, 8 per deg/s; tap field LSB = T/8,
  fld = ((b0&3)<<8)|b1, signed by bit 9 (creep20_loop_id.load).
"""
import json
import time
from pathlib import Path

import numpy as np

T0 = time.time()
KIT = Path(__file__).resolve().parents[4]
C = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
OUT = KIT / "_scratch" / "out" / "r79" / "m1"
OUT.mkdir(parents=True, exist_ok=True)
W = dict(np.load(C / "r79_a1f5d2_al.npz"))
B4 = dict(np.load(C / "r79_a1f5d2_al_b4.npz"))
F = np.load(C / "r79_fork.npz")
X = np.load(KIT / "_scratch" / "angle_loop" / "drive-read" / "routes" /
            "75604b0a432fdc89_00000079--a1f5d2a272_extras.npz")
R = {}
L = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    L.append(s)
    print(s)


def at(tsrc, x, t):
    """ZOH sample of x(tsrc) at t (the last value at or before t)."""
    j = np.clip(np.searchsorted(tsrc, t, side="right") - 1, 0, len(x) - 1)
    return np.asarray(x)[j]


def cnt(a):
    u, c = np.unique(np.asarray(a), return_counts=True)
    return {int(x): int(y) for x, y in zip(u, c)}


# ------------------------------------------------------------------------------------------------ (a) ATTRIBUTION
meta = json.loads(str(X["meta"]))
cp = json.loads(str(F["carparams_json"]))
ip = json.loads(str(F["initdata_params_json"]))["params"]
eps_fw = [f["fw"].strip("\x00 ") for f in meta["carfw"] if f["ecu"] == "eps"]
keys = ["AccordEpsAngleLoop", "GitCommit", "GitBranch", "Version", "SteerRatio", "AccordVariableSteerRatio",
        "AlwaysOnLateral", "AlwaysOnLateralLKAS", "ForceTorqueController", "UseAutoSteerDelay", "SteerDelay",
        "LaneCentering", "LaneChangeSmoothing", "SteerKP", "SteerLatAccel", "SteerFriction", "HondaBoschARadar"]
R["a"] = dict(eps_fw_carFw=eps_fw, carparams_eps=cp.get("carFw_eps"), steerControlType=cp["steerControlType"],
              op_long=cp.get("openpilotLongitudinalControl"), safety=cp["safetyConfigs"],
              maxLateralAccel=cp["maxLateralAccel"], steerRatio_CP=cp["steerRatio"],
              steerActuatorDelay=cp["steerActuatorDelay"], lateralTuning=cp.get("lateralTuning_which"),
              params={k: ip.get(k, meta["params"].get(k)) for k in keys}, git=meta.get("git"),
              fork_commit_meta=json.loads(str(F["meta_json"])).get("fork_commit"),
              lp_sr=(float(F["lp_sr"].min()), float(F["lp_sr"].max())),
              ctl_lat_is_angle=float(np.mean(F["ctl_lat_is_angle"])),
              gitdiff_head=str(meta["params"].get("GitDiff", ""))[:160])
pr("(a)", json.dumps(R["a"], default=str))

# ------------------------------------------------------------------------------------------------ wire basics
te4, cmd, req = W["te4"], W["cmd"], W["req"].astype(bool)
t18, sca, rate, tq = W["t18"], W["sca"].astype(bool), -W["rate"] / 8.0, W["tq"] * 1.024   # rate: d(theta)/dt sign
t14, ang = W["t14"], W["ang"]
t1ab = W["t1ab"]
fld = ((W["b0"].astype(int) & 3) << 8) | W["b1"].astype(int)
tap = np.where(fld >= 512, -1.0, 1.0) * (fld & 511)          # field LSB = T/8, sign = +sign(T)
sca_e4 = at(t18, sca.astype(float), te4) > 0.5
eng_e4 = req & sca_e4                                         # lateral engaged at each 0xE4 frame
vego_e4 = at(W["tcs"], W["vego"], te4)

# ------------------------------------------------------------------------------------------------ (d) INTERLOCKS
d = {}
st18 = X["st18"]
tst = X["t18"]
eng18 = (at(te4, req.astype(float), tst) > 0.5) & (at(t18, sca.astype(float), tst) > 0.5)
ss = st18.astype(int) >> 4                                    # STEER_STATUS = 0x18F byte 4 bits 7:4 (st18 = whole byte)
d["steer_status_engaged"] = cnt(ss[eng18])
d["steer_status_all"] = cnt(ss)
d["steer_status_nonzero_t"] = [(round(float(x), 2), int(y)) for x, y in zip(tst[ss != 0], ss[ss != 0])][:20]
d["sca_bit3_equals_wire_sca"] = bool(len(st18) == len(sca) and np.all(((st18.astype(int) >> 3) & 1) == sca))
d["byte4_low3_engaged"] = cnt(st18[eng18].astype(int) & 7)
b4 = B4["b4"]
tb4 = B4["t14b"]
engb4 = (at(te4, req.astype(float), tb4) > 0.5) & (at(t18, sca.astype(float), tb4) > 0.5)
d["b14a_b4_bits02_engaged"] = cnt(b4[engb4] & 7)
d["b14a_b4_bits02_all"] = cnt(b4 & 7)
d["b14a_b4_bits37_engaged"] = cnt(b4[engb4] >> 3)
d["b4_extras_equal_wire"] = bool(len(X["b414"]) == len(b4) and np.all(X["b414"] == b4))
tcs = F["t_cs"]
d["cs_steerFaultTemporary_t"] = [round(float(x), 2) for x in tcs[F["cs_ftemp"].astype(bool)]]
d["cs_steerFaultPermanent_rows"] = int(F["cs_fperm"].sum())
tb = F["ps_txblocked"]
tps = F["t_ps"]
inc = np.flatnonzero(np.diff(tb) != 0)
d["txblocked_steps"] = [(round(float(tps[j + 1]), 2), int(tb[j]), int(tb[j + 1])) for j in inc]
d["e4_rejected_bus1"] = dict(n=int(len(F["t_e4rej1"])), t_first_last=[round(float(F["t_e4rej1"][0]), 2),
                             round(float(F["t_e4rej1"][-1]), 2)], req=int(F["e4rej1_req"].sum()),
                             t=[round(float(x), 2) for x in F["t_e4rej1"]])
ev_t, ev_n = F["t_ev"], F["ev_name"]
for nm in ("commIssue", "selfdrivedLagging", "steerSaturated", "buttonEnable", "wrongCarMode"):
    d[nm + "_t"] = [round(float(x), 2) for x in np.unique(ev_t[ev_n == nm])][:12]
# STEER_REQUEST episodes / drops (bus-129 echo = what the EPS bus carried)
dr = np.diff(req.astype(int))
rise = np.flatnonzero(dr == 1) + 1
fall = np.flatnonzero(dr == -1) + 1
if req[0]:
    rise = np.r_[0, rise]
if req[-1]:
    fall = np.r_[fall, len(req) - 1]
d["req_episodes"] = [(round(float(te4[a]), 2), round(float(te4[b] - te4[a]), 2)) for a, b in zip(rise, fall)]
d["req_gaps_s"] = [(round(float(te4[f]), 2), round(float(te4[r] - te4[f]), 3)) for f, r in zip(fall[:-1], rise[1:])]
d["req_on_s"] = float(np.sum(np.diff(te4)[req[:-1]]))
d["eng_s"] = float(np.sum(np.diff(te4)[eng_e4[:-1]]))
# req==1 but SCA==0 (EPS not accepting) census
m = req & ~sca_e4
d["req1_sca0_s"] = float(np.sum(np.diff(te4)[m[:-1]]))
# 0xE4 inter-frame gaps
g = np.diff(te4)
big = np.flatnonzero(g > 0.020)
d["e4_gap_gt20ms"] = dict(n=int(len(big)), n_inside_req=int(np.sum(req[big] & req[np.minimum(big + 1, len(req) - 1)])),
                          max_ms=float(g.max() * 1e3), p999_ms=float(np.percentile(g, 99.9) * 1e3),
                          median_ms=float(np.median(g) * 1e3),
                          worst=[(round(float(te4[i]), 2), round(float(g[i]) * 1e3, 1), bool(req[i]))
                                 for i in big[np.argsort(-g[big])][:8]])
# true bus drops: the Honda 2-bit COUNTER (byte 4 bits 5:4) of the bus-129 echo must advance by 1 per frame
ctr = (F["e4tx1_raw"][:, 4].astype(int) >> 4) & 3
dc = (np.diff(ctr) % 4)
skip = np.flatnonzero(dc != 1)
d["e4_counter_skips_bus129"] = dict(n=int(len(skip)), inside_req=int(np.sum(req[skip] & req[np.minimum(skip + 1, len(req) - 1)])),
                                    t=[(round(float(te4[i]), 2), int(dc[i]), bool(req[i])) for i in skip][:12])
d["e4_sent_minus_echoed_minus_rejected"] = int(len(F["t_e4send"]) - len(te4) - len(F["t_e4rej1"]))
d["e4_gap_gt20ms_note"] = "echo logMonoTime is the USB-batch receipt time; the counter test above is the bus truth"
i14 = int(np.argmax(np.diff(t14)))
d["a14a_longest_gap"] = dict(t=round(float(t14[i14]), 2), ms=round(float(np.diff(t14)[i14] * 1e3), 1),
                             req=bool(at(te4, req.astype(float), np.array([t14[i14]]))[0] > 0.5))
gs = np.diff(F["t_e4send"])
d["e4send_gap_gt20ms"] = dict(n=int(np.sum(gs > 0.020)), max_ms=float(gs.max() * 1e3))
gb = np.diff(t1ab)
d["tap_gap_gt40ms"] = dict(n=int(np.sum(gb > 0.040)), max_ms=float(gb.max() * 1e3))
g14 = np.diff(t14)
d["a14a_gap_gt20ms"] = dict(n=int(np.sum(g14 > 0.020)), max_ms=float(g14.max() * 1e3))
# the fork's byte-2 bits 3:2
d["fork_arm_bus129"] = cnt(F["e4tx1_arm"])
d["fork_arm_sendcan"] = cnt(F["e4send_arm"])
d["fork_b2_low_bits_and_bits4to6"] = cnt(F["e4tx1_b2"] & 0x73)
d["fork_req_vs_wire_req_identical"] = bool(len(F["e4tx1_req"]) == len(req) and np.all(F["e4tx1_req"].astype(bool) == req))
# the camera on bus 2 and the bus-0 forward
cam_arm = F["e4cam_arm"]
cam_req = F["e4cam_req"].astype(bool)
d["cam"] = dict(n=int(len(cam_arm)), arm=cnt(cam_arm), req1=int(cam_req.sum()),
                max_abs_field=int(np.abs(F["e4cam_i16"]).max()),
                max_abs_field_req1=int(np.abs(F["e4cam_i16"][cam_req]).max()) if cam_req.any() else 0,
                arm_when_req1=cnt(cam_arm[cam_req]))
tc, rc = F["t_e4cam"], F["e4cam_raw"]
t0b, r0b = F["t_e4tx0"], F["e4tx0_raw"]
j = np.clip(np.searchsorted(tc, t0b, side="right") - 1, 0, len(tc) - 1)
same = np.all(rc[j] == r0b, axis=1) & ((t0b - tc[j]) <= 0.015)
j2 = np.clip(j - 1, 0, len(tc) - 1)
same2 = same | (np.all(rc[j2] == r0b, axis=1) & ((t0b - tc[j2]) <= 0.025))
d["bus0_fwd"] = dict(n_tx0=int(len(t0b)), first_t=round(float(t0b[0]), 2), last_t=round(float(t0b[-1]), 2),
                     byte_identical_to_cam_le25ms=float(same2.mean()),
                     cam_frames_after_first_fwd=int(np.sum(tc >= t0b[0])),
                     n_tx0_req1=int(F["e4tx0_req"].sum()),
                     n_tx0_req1_cam_identical=int(np.sum(same2 & F["e4tx0_req"].astype(bool))),
                     tx0_arm=cnt(F["e4tx0_arm"]))
d["bus1_rx_not_ours"] = dict(n=int(len(F["t_e4rx1"])),
                             t_range=[round(float(F["t_e4rx1"].min()), 2), round(float(F["t_e4rx1"].max()), 2)]
                             if len(F["t_e4rx1"]) else None, n_req1=int(F["e4rx1_req"].sum()),
                             arm=cnt(F["e4rx1_arm"]) if len(F["t_e4rx1"]) else {})
d["bus0_rx"] = dict(n=int(len(F["t_e4rx0"])),
                    t_range=[round(float(F["t_e4rx0"].min()), 2), round(float(F["t_e4rx0"].max()), 2)]
                    if len(F["t_e4rx0"]) else None)
d["first_fork_frame_bus129_t"] = round(float(te4[0]), 2)
cam_req_t = tc[cam_req]
d["cam_req1_while_fork_engaged"] = int(np.sum(at(te4, eng_e4.astype(float), cam_req_t) > 0.5))
cr = cam_req.astype(int)
dd = np.diff(np.r_[0, cr, 0])
a_ = np.flatnonzero(dd == 1)
b_ = np.flatnonzero(dd == -1)
d["cam_req1_n_episodes"] = int(len(a_))
d["cam_req1_episodes_first12"] = [(round(float(tc[a]), 2), round(float(tc[b - 1] - tc[a]), 2)) for a, b in zip(a_, b_)][:12]
R["d"] = d
for k, v in d.items():
    pr("(d)", k, json.dumps(v, default=str)[:700])

# ------------------------------------------------------------------------------------------------ (e) EVENTS
theta_sp = -cmd / 10.0
th_e4 = at(t14, ang, te4)


def window(t0, dur=2.0):
    m1 = (t1ab >= t0) & (t1ab < t0 + dur)
    m2 = (te4 >= t0) & (te4 < t0 + dur)
    m3 = (t14 >= t0) & (t14 < t0 + dur)
    a0 = float(at(t14, ang, np.array([t0]))[0])
    tp = tap[m1]
    return dict(tap_max=float(np.max(np.abs(tp))) if tp.size else np.nan,
                tap_at150ms=float(at(t1ab, tap, np.array([t0 + 0.15]))[0]),
                tap_at500ms=float(at(t1ab, tap, np.array([t0 + 0.5]))[0]),
                dang=float(ang[m3][-1] - a0) if m3.any() else np.nan,
                maxerr=float(np.max(np.abs(theta_sp[m2] - th_e4[m2]))) if m2.any() else np.nan,
                max_rate=float(np.max(np.abs(at(t18, rate, t14[m3])))) if m3.any() else np.nan,
                max_bar=float(np.max(np.abs(at(t18, tq, t14[m3])))) if m3.any() else np.nan)


ev = []
for i in rise:
    t0 = float(te4[i])
    ev.append(dict(kind="REQ rise", t=t0, v=float(vego_e4[i]), sca=bool(sca_e4[min(i + 20, len(te4) - 1)]),
                   err0=float(theta_sp[i] - th_e4[i]), ang0=float(th_e4[i]), **window(t0)))
for i in fall:
    t0 = float(te4[i])
    ev.append(dict(kind="REQ fall", t=t0, v=float(vego_e4[i]), sca=bool(sca_e4[max(i - 1, 0)]),
                   err0=float(theta_sp[i - 1] - th_e4[i - 1]), ang0=float(th_e4[i]),
                   tap_before=float(at(t1ab, tap, np.array([t0 - 0.02]))[0]), **window(t0)))
# what ended each request episode: the nearest onroad/fork event within 0.5 s
names_near = []
for e in ev:
    if e["kind"] != "REQ fall":
        continue
    mm = (np.abs(ev_t - e["t"]) < 0.6)
    e["events_near"] = sorted(set(str(x) for x in ev_n[mm]))[:6]
    mm2 = (np.abs(F["t_spev"] - e["t"]) < 0.6)
    e["events_near"] += sorted(set(str(x) for x in F["spev_name"][mm2]))
    mm3 = np.abs(F["t_sd"] - e["t"]) < 0.3
    e["sd_state"] = sorted(set(int(x) for x in F["sd_state"][mm3]))
    e["cs_vcruise_en"] = bool(at(tcs, F["cs_cr_en"].astype(float), np.array([e["t"]]))[0] > 0.5)
    e["cc_latActive_after"] = bool(at(F["t_cc"], F["cc_latActive"].astype(float), np.array([e["t"] + 0.05]))[0] > 0.5)
# fork O1 override: |cs_tq| > 600 rising edges with 500 hysteresis, while the request is on
cst = F["cs_tq"]
hi = np.abs(cst) > 600
lo = np.abs(cst) < 500
lastset = np.maximum.accumulate(np.where(hi | lo, np.arange(len(cst)), -1))
o = np.where(lastset >= 0, hi[np.maximum(lastset, 0)], False)
dd = np.diff(np.r_[0, o.astype(int), 0])
oa_, ob_ = np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)
req_cs = at(te4, req.astype(float), tcs) > 0.5
ov = []
for a, b in zip(oa_, ob_):
    if not req_cs[a]:
        continue
    t0 = float(tcs[a])
    t1 = float(tcs[min(b, len(tcs) - 1)])
    w0 = window(t0, 0.5)
    w1 = window(t1, 2.0)          # after RELEASE: what the tap and angle did
    ov.append(dict(t=t0, v=float(F["cs_vego"][a]), dur=t1 - t0, bar0=float(cst[a] * 1.024),
                   tap_max_first500ms=w0["tap_max"], rel_tap_max=w1["tap_max"], rel_tap_at150=w1["tap_at150ms"],
                   rel_dang=w1["dang"], rel_maxerr=w1["maxerr"], rel_max_rate=w1["max_rate"]))
R["e"] = dict(events=ev, n_override=len(ov), overrides=ov,
              n_override_v_gt5=int(sum(1 for z in ov if z["v"] > 5)),
              n_override_v_gt5_dur_gt0p5=int(sum(1 for z in ov if z["v"] > 5 and z["dur"] > 0.5)))
so_t = np.unique(ev_t[ev_n == "steerOverride"])
R["e"]["steerOverride_frames"] = int(len(so_t))
R["e"]["steerOverride_episodes"] = int(np.sum(np.diff(so_t) > 0.05) + (1 if len(so_t) else 0))
R["e"]["lkas_events"] = [(str(n_), round(float(t_), 2)) for n_, t_ in zip(F["spev_name"], F["t_spev"]) if "lkas" in str(n_)]
pr("(e) request edges (2 s after each):")
for e in sorted(ev, key=lambda z: z["t"]):
    pr("  %-8s t %7.2f v %5.1f sca %d err0 %+6.2f ang0 %+7.1f | tap max %4.0f @150ms %+5.0f @500ms %+5.0f dang %+6.2f "
       "maxerr %5.2f maxrate %5.1f maxbar %5.0f %s %s" % (
           e["kind"], e["t"], e["v"], e["sca"], e["err0"], e["ang0"], e["tap_max"], e["tap_at150ms"], e["tap_at500ms"],
           e["dang"], e["maxerr"], e["max_rate"], e["max_bar"],
           ("tap_before %+.0f" % e["tap_before"]) if "tap_before" in e else "",
           ("%s sd%s cr_en %d latAct_after %d" % (e["events_near"], e["sd_state"], e["cs_vcruise_en"],
                                                  e["cc_latActive_after"])) if "events_near" in e else ""))
ova = np.array([[z["dur"], z["tap_max_first500ms"], z["rel_tap_max"], abs(z["rel_dang"]), z["rel_maxerr"], z["v"]]
                for z in ov]) if ov else np.zeros((0, 6))
if len(ova):
    pr("(e) O1 overrides while requested: n %d ; dur p50 %.2f p90 %.2f s ; |tap| max in first 0.5 s p50 %.0f p90 %.0f ; "
       "after release: tap max p50 %.0f p90 %.0f, |dang| 2 s p50 %.2f p90 %.2f max %.2f deg, maxerr p50 %.2f p90 %.2f"
       % (len(ova), *np.percentile(ova[:, 0], [50, 90]), *np.percentile(ova[:, 1], [50, 90]),
          *np.percentile(ova[:, 2], [50, 90]), *np.percentile(ova[:, 3], [50, 90]), ova[:, 3].max(),
          *np.percentile(ova[:, 4], [50, 90])))
    R["e"]["override_summary"] = dict(n=len(ova), dur_p50=float(np.median(ova[:, 0])),
                                      rel_dang_p90=float(np.percentile(ova[:, 3], 90)), rel_dang_max=float(ova[:, 3].max()))
    for z in sorted(ov, key=lambda q: -abs(q["rel_dang"]))[:6]:
        pr("   largest release moves: t %7.2f v %5.1f dur %5.2f bar0 %+5.0f rel tap max %4.0f dang %+6.2f maxerr %5.2f"
           % (z["t"], z["v"], z["dur"], z["bar0"], z["rel_tap_max"], z["rel_dang"], z["rel_maxerr"]))
pr("(e) misc", json.dumps({k: R["e"][k] for k in ("steerOverride_frames", "steerOverride_episodes", "lkas_events",
                                                  "n_override_v_gt5", "n_override_v_gt5_dur_gt0p5")}))
R["wall_s"] = time.time() - T0
pr("wall %.2f s" % R["wall_s"])
(OUT / "m1_attrib_interlocks.json").write_text(json.dumps(R, default=lambda z: z.item() if hasattr(z, "item") else str(z),
                                                          indent=1))
(OUT / "m1_attrib_interlocks.txt").write_text("\n".join(L), encoding="utf-8")
