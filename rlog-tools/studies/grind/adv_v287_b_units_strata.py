# -*- coding: utf-8 -*-
"""ADVERSARY B on V287 (0xC61B6 10240 -> 2560).  UNIT/SCALE CHAIN + UNSAMPLED STRATA.
Analysis only.  Builds nothing, sends nothing, flashes nothing.
Run: python adv_v287_b_units_strata.py   -> _scratch/adv_v287_b_units_strata.txt
"""
import os, sys, struct
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20
import v280_map_profiles as V
import grind_incident_r35 as GI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
def pr(s=""):
    print(s, flush=True); OUT.append(s)

ROOT = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG = ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
B = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
FS, FS1K, KD = 100.0, 1000.0, 128.0
cells = GI.read_cells(IMG)

# ======================================================================================================================
pr("=" * 140)
pr("ADVERSARY B -- V287 = V282 + 0xC61B6 10240 -> 2560.  UNIT/SCALE CHAIN, re-derived from BYTES, nothing inherited.")
pr("=" * 140)
pr("")
pr("  cells read fresh from the built V282 image %s" % os.path.basename(IMG))
for a, name in [(0xC61B4,"out clamp"),(0xC61B6,"D clamp  <-- THE CELL"),(0xC61B8,"deadband"),(0xC61BA,"I anti-windup"),
                (0xC61BC,"P clamp"),(0xC61BE,"sum clamp"),(0xC63EC,"lag a2"),(0xC63EE,"lag b2"),
                (0xC62E6,"fb clamp"),(0xC6446,"r24 gain")]:
    pr("      0x%06X  %-22s = %d" % (a, name, u16(a)))
pr("      fb filter a/b = %d/%d ; lag a/b = %d/%d ; fwd gain = %d ; Kd bank = %s ; Kp = %s" % (
    cells["fb_a"], cells["fb_b"], cells["lag_a"], cells["lag_b"], cells["gain"],
    cells["kd_Y"].astype(int).tolist(), cells["kp_Y"].astype(int).tolist()))

a_fb, b_fb = cells["fb_a"] / 1024.0, cells["fb_b"] / 1024.0
FB_DC = b_fb * 2.0 / (1.0 - a_fb)          # two-sample sum, DC gain
CPD = V.CPD
pr("")
pr("  STEP 1 -- the fb filter, from the two halfwords, no inherited factor:")
pr("      s' = floor((%d*s + %d*x)/1024)  ;  fb = s + s'   ->  DC gain = 2*%.6f/(1-%.6f) = %.4f  (record says 30.89)" % (
    cells["fb_a"], cells["fb_b"], b_fb, a_fb, FB_DC))
pr("      x = -wire, wire = 0x18F b2-3 raw, CPD = %.1f raw counts per deg/s  -> fb = %.2f counts per deg/s at DC" % (CPD, FB_DC*CPD))
pr("      Kd = %d  ->  D = dE*Kd>>3 = %g*dE   ->  clamp 2560 rails at |dE| = %.0f  (today 10240 -> |dE| = %.0f)" % (
    int(cells["kd_Y"][0]), int(cells["kd_Y"][0])/8.0, 2560/(int(cells["kd_Y"][0])/8.0), 10240/(int(cells["kd_Y"][0])/8.0)))

# --- transfer from wheel-rate amplitude to |d(fb)| per tick, exactly
def dfb_per_unit_x(f):
    w = 2*np.pi*f/FS1K
    z = np.exp(-1j*w)
    H = b_fb*(1.0+z)/(1.0-a_fb*z)          # x -> fb (two-sample sum)
    return np.abs(H)*np.abs(1.0-z)         # then the per-tick difference

pr("")
pr("  STEP 2 -- FEEDBACK part of dE, expressed physically.  Two ways, both from the filter above.")
pr("    (a) sustained wheel-rate ACCELERATION (a ramp; the filter is at DC gain):")
for lvl, lab in [(160.0, "2560 (V287)"), (640.0, "10240 (today)")]:
    acc = lvl / (FB_DC*CPD) * 1000.0
    pr("        |dE| = %5.0f  ->  d(rate)/dt = %8.1f deg/s^2   [rails the %s clamp on the FEEDBACK part alone]" % (lvl, acc, lab))
pr("    (b) SINUSOIDAL wheel-rate ripple of amplitude A deg/s at frequency f:")
pr("        %-8s %-12s %-16s %-16s" % ("f (Hz)", "|dfb|/|x| ", "A for |dE|=160", "A for |dE|=640"))
for f in (5.0, 7.3, 10.0, 15.0, 20.3, 30.0, 50.0, 100.0, 200.0, 400.0):
    k = dfb_per_unit_x(f)
    pr("        %-8.1f %-12.4f %-16s %-16s" % (f, k, "%.2f deg/s" % (160.0/(k*CPD)), "%.2f deg/s" % (640.0/(k*CPD))))

pr("")
pr("  STEP 3 -- SETPOINT part of dE, in 0xE4 raw counts per 10 ms frame.")
pr("      dE_sp = 32*d(sp) -> |dE| = 160 at |d(sp)| = 5 map counts ; |dE| = 640 at |d(sp)| = 20 map counts.")
mapY = cells["map_Y"]; mapX = cells["map_X"]
pr("      V282 map X %s" % mapX.astype(int).tolist())
pr("      V282 map Y %s" % mapY.astype(int).tolist())
sl = np.diff(mapY)/np.diff(mapX)
pr("      map slope d(sp)/d(idx) per segment: %s" % ["%.2f" % s for s in sl])
pr("      -> |d(idx)| that rails 2560 on the setpoint part alone, per segment:")
pr("         %s" % ["%.2f" % (5.0/s) for s in sl])
pr("         (today, 10240): %s" % ["%.2f" % (20.0/s) for s in sl])
pr("      idx is derived from the 0xE4 command by demand(); on the linear-to-6x V282 map the top segment slope is %.2f," % sl[-1])
pr("      so ONE 0xE4 count of command change per frame moves sp by %.2f-%.2f counts -> dE_sp %.0f-%.0f." % (
    sl.min(), sl.max(), 32*sl.min(), 32*sl.max()))

OUTP = os.path.join(SCR, "adv_v287_b_units_strata.txt")
os.makedirs(SCR, exist_ok=True)
open(OUTP, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("\nwrote %s" % OUTP)

# ======================================================================================================================
# PART 2 -- WHAT THE ROUTES ACTUALLY CONTAIN, and the strata the design did not sample
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 2 -- ROUTE CONTENT.  Did r39/r3a/r3c even VISIT the strata the design's claim has to survive?")
pr("=" * 140)
G = {}
for tag in ("r39", "r3a", "r3c", "r35"):
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]
MASK_R3A_HOLE = None

pr("  %-5s %8s %8s | %-38s | %-30s" % ("route", "s tot", "s eng", "vEgo percentiles (m/s) while engaged", "|bar| raw p50/p90/p99/max"))
for tag in ("r39", "r3a", "r3c", "r35"):
    g = G[tag]; e = g["eng"]
    v = g["vego"][e]; bq = np.abs(g["bar"])[e]
    pr("  %-5s %8.1f %8.1f | p10 %5.1f p50 %5.1f p90 %5.1f p99 %5.1f max %5.1f | %5.0f %5.0f %5.0f %5.0f" % (
        tag, len(g["t"])/FS, e.sum()/FS, *np.percentile(v,[10,50,90,99]), v.max(),
        *np.percentile(bq,[50,90,99]), bq.max()))

# wheel-rate statistics per speed band, engaged
pr("")
pr("  Engaged wheel-rate |rate| (deg/s) and the per-tick FEEDBACK part of dE it implies, by speed band:")
pr("  %-5s %-14s %7s | %7s %7s %7s | %-42s" % ("route","vEgo band","s","p50","p99","max","|rate| deg/s"))
for tag in ("r39","r3a","r3c"):
    g = G[tag]
    for lo,hi in ((1,3),(3,8),(8,15),(15,25),(25,40)):
        m = g["eng"] & (g["vego"]>=lo) & (g["vego"]<hi)
        if m.sum() < 200: continue
        r = np.abs(g["rate_x"])[m]
        pr("  %-5s %-14s %7.1f | %7.1f %7.1f %7.1f |" % (tag, "%d-%d m/s"%(lo,hi), m.sum()/FS, *np.percentile(r,[50,99]), r.max()))

# ======================================================================================================================
# PART 3 -- THE STRATUM CENSUS.  bind fraction and the D_fb share, in strata the design never computed.
# ======================================================================================================================
def runs_of(m, minlen):
    d = np.diff(np.r_[0, m.astype(int), 0])
    return [(a,b) for a,b in zip(np.flatnonzero(d==1), np.flatnonzero(d==-1)) if b-a >= minlen]

STRATA = [
  ("CREEP hands-off  (the DESIGN's stratum)", lambda g: g["eng"] & (g["vego"]>=1)&(g["vego"]<3)&(np.abs(g["bar"])<400)),
  ("LOW-MID hands-off 3-8 m/s",               lambda g: g["eng"] & (g["vego"]>=3)&(g["vego"]<8)&(np.abs(g["bar"])<400)),
  ("SUBURBAN hands-off 8-15 m/s",             lambda g: g["eng"] & (g["vego"]>=8)&(g["vego"]<15)&(np.abs(g["bar"])<400)),
  ("HIGHWAY hands-off >15 m/s",               lambda g: g["eng"] & (g["vego"]>=15)&(np.abs(g["bar"])<400)),
  ("HANDS-ON  |bar|>700, any speed",          lambda g: g["eng"] & (np.abs(g["bar"])>700)),
  ("HANDS-ON HARD |bar|>1500",                lambda g: g["eng"] & (np.abs(g["bar"])>1500)),
  ("LOADED HIGH-ANGLE |ang|>60 deg",          lambda g: g["eng"] & (np.abs(g["ang"])>60)),
  ("FAST WHEEL >25 deg/s (lane change class)",lambda g: g["eng"] & (np.abs(g["rate_x"])>25)),
  ("HIGHWAY FAST WHEEL >15 m/s & >10 deg/s",  lambda g: g["eng"] & (g["vego"]>=15) & (np.abs(g["rate_x"])>10)),
]
DOSES = [10240, 2560]

pr("")
pr("=" * 140)
pr("PART 3 -- BIND FRACTION AND THE FEEDBACK SHARE, PER STRATUM.  Dilated masks (+-0.15 s) so transients are not clipped.")
pr("  'D_sp dom %%' = share of BINDING ticks where |D_sp| > |D_fb|.  'p99|D_fb|/clamp' > 1 means the FEEDBACK part alone")
pr("  routinely reaches the clamp -> at that dose the clamp is a LOCAL Kd CUT in that stratum, not an excitation limiter.")
pr("=" * 140)
pr("  %-42s %-5s %7s | %6s %8s %10s | %6s %8s %10s" % (
    "stratum","route","s","bind%","Dsp dom%","p99Dfb/clp","bind%","Dsp dom%","p99Dfb/clp"))
pr("  %-42s %-5s %7s | %-26s | %-26s" % ("","","","        clamp 10240 (today)","        clamp 2560 (V287)"))

RES = {}
for name, sel in STRATA:
    for tag in ("r39","r3a","r3c"):
        g = G[tag]
        m = sel(g)
        # dilate by +-15 frames so onsets/decays of the stratum are included
        k = np.ones(31, bool)
        md = np.convolve(m.astype(int), np.ones(31,int), "same") > 0
        md &= g["eng"]
        rr = runs_of(md, 150)
        if not rr: continue
        acc = {d: dict(nb=0, ndom=0, n=0, dfb=[]) for d in DOSES}
        tot = 0
        for a_,b_ in rr[:40]:
            if b_-a_ > 4000: b_ = a_+4000
            try:
                s0 = GI.simulate(g, a_, b_, cells)
            except Exception:
                continue
            live = np.repeat(g["eng"][s0["seg"]], 10)
            if live.sum() < 200: continue
            sp32 = 32.0*s0["sp"]
            dsp = np.r_[0.0, np.diff(sp32)]; dfb = np.r_[0.0, np.diff(s0["fb"])]
            Dsp = np.floor(dsp*KD/8.0); Dfb = np.floor(-dfb*KD/8.0)
            Draw = np.floor((dsp-dfb)*KD/8.0)
            Dsp, Dfb, Draw = Dsp[live], Dfb[live], Draw[live]
            tot += live.sum()
            for d in DOSES:
                bm = np.abs(Draw) > d
                acc[d]["nb"] += int(bm.sum()); acc[d]["n"] += int(live.sum())
                acc[d]["ndom"] += int((np.abs(Dsp[bm]) > np.abs(Dfb[bm])).sum())
                acc[d]["dfb"].append(np.abs(Dfb))
        if tot < 1000: continue
        row = [name, tag, tot/FS1K]
        for d in DOSES:
            A = acc[d]
            dfbc = np.concatenate(A["dfb"]) if A["dfb"] else np.array([0.0])
            row += [100.0*A["nb"]/max(1,A["n"]), 100.0*A["ndom"]/max(1,A["nb"]) if A["nb"] else np.nan,
                    np.percentile(dfbc,99)/d]
        RES[(name,tag)] = row
        pr("  %-42s %-5s %7.1f | %6.2f %8.1f %10.3f | %6.2f %8.1f %10.3f" % tuple(row[:3]+row[3:]))

# ======================================================================================================================
# PART 3b -- REPRODUCE THE DESIGN'S OWN WINDOWS.  If my machinery disagrees there, the divergence above is MINE.
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 3b -- CROSS-CHECK: the DESIGN's own window selection, recomputed with MY code.")
pr("  Design (B2, clamp 2560): creep windows bind 2.11-4.38 %, D_sp-dominated 97.8-100.0 %, p99|Dfb|/clamp 0.600-0.705")
pr("=" * 140)
CREEP = lambda g: g["eng"] & (g["vego"]>=1.0)&(g["vego"]<3.0)&(np.abs(g["bar"])<400)
cand = []
for tag in ("r39","r3a","r3c"):
    g = G[tag]; m = CREEP(g)
    for a_,b_ in runs_of(m, 200):
        cand.append((C20.bamp(g["rate_x"][a_:b_], 18.0, 22.0, FS), tag, a_, b_))
cand.sort(key=lambda z: -z[0])
WIN = [("r35",1010.0,1025.0,"r35 GRIND INCIDENT"),("r39",672.0,692.0,"r39 bookmark 1"),("r39",910.0,930.0,"r39 bookmark 2")]
pr("  %-34s %7s | %6s %8s %10s | %6s %8s %10s" % ("window","s","bind%","Dsp dom%","p99Dfb/clp","bind%","Dsp dom%","p99Dfb/clp"))
def one(g, a_, b_, lab):
    s0 = GI.simulate(g, a_, b_, cells)
    live = np.repeat(g["eng"][s0["seg"]], 10)
    if not live.any(): live = np.ones(len(s0["fb"]), bool)
    sp32 = 32.0*s0["sp"]; dsp = np.r_[0.0,np.diff(sp32)]; dfb = np.r_[0.0,np.diff(s0["fb"])]
    Dsp = np.floor(dsp*KD/8.0)[live]; Dfb = np.floor(-dfb*KD/8.0)[live]
    Draw = np.floor((dsp-dfb)*KD/8.0)[live]
    row=[lab, live.sum()/FS1K]
    for d in DOSES:
        bm = np.abs(Draw)>d
        row += [100.0*bm.mean(), 100.0*(np.abs(Dsp[bm])>np.abs(Dfb[bm])).mean() if bm.any() else np.nan,
                np.percentile(np.abs(Dfb),99)/d]
    pr("  %-34s %7.1f | %6.2f %8.1f %10.3f | %6.2f %8.1f %10.3f" % tuple(row))
for tag,t0,t1,lab in WIN:
    g=G[tag]; a_=int(np.searchsorted(g["tr"],t0)); b_=int(np.searchsorted(g["tr"],t1)); one(g,a_,b_,lab)
for amp,tag,a_,b_ in cand[:3]:
    one(G[tag], a_, b_, "loudest creep (%s, rate18-22 %.2f)"%(tag,amp))
pr("")
pr("  Same three creep runs, but WHOLE contiguous run instead of the 2.8-3.1 s the design used:")
for amp,tag,a_,b_ in cand[:3]:
    pr("     %s run %.1f-%.1f s (%.1f s long)" % (tag, G[tag]["tr"][a_], G[tag]["tr"][b_-1], (b_-a_)/FS))
pr("")
pr("  ALL creep runs >= 2 s, pooled per route (no 'loudest' selection):")
for tag in ("r39","r3a","r3c"):
    g=G[tag]; Dsps=[];Dfbs=[];Draws=[]
    for a_,b_ in runs_of(CREEP(g),200):
        s0=GI.simulate(g,a_,min(b_,a_+4000),cells); live=np.repeat(g["eng"][s0["seg"]],10)
        if live.sum()<200: continue
        sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
        Dsps.append(np.floor(dsp*KD/8.0)[live]);Dfbs.append(np.floor(-dfb*KD/8.0)[live]);Draws.append(np.floor((dsp-dfb)*KD/8.0)[live])
    if not Dsps: continue
    Dsp=np.concatenate(Dsps);Dfb=np.concatenate(Dfbs);Draw=np.concatenate(Draws)
    row=[tag,len(Dsp)/FS1K]
    for d in DOSES:
        bm=np.abs(Draw)>d
        row+=[100.0*bm.mean(),100.0*(np.abs(Dsp[bm])>np.abs(Dfb[bm])).mean() if bm.any() else np.nan,np.percentile(np.abs(Dfb),99)/d]
    pr("  %-34s %7.1f | %6.2f %8.1f %10.3f | %6.2f %8.1f %10.3f" % tuple(row))

# ======================================================================================================================
# PART 4 -- THE CENSUS AGAIN, UNDILATED (3b showed the +-0.15 s dilation was doing real work; this is the clean version)
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 4 -- STRATUM CENSUS, UNDILATED, contiguous runs >= 1.0 s.  This is the version I score on.")
pr("  EXPOSURE is reported: a stratum with 5 s of exposure cannot carry a safety claim about 880 s of driving.")
pr("=" * 140)
pr("  %-42s %-5s %8s | %6s %8s %10s | %6s %8s %10s" % (
    "stratum","route","s expo","bind%","Dsp dom%","p99Dfb/clp","bind%","Dsp dom%","p99Dfb/clp"))
pr("  %-42s %-5s %8s | %-26s | %-26s" % ("","","","       clamp 10240 (today)","       clamp 2560 (V287)"))
CLEAN = {}
for name, sel in STRATA:
    for tag in ("r39","r3a","r3c"):
        g = G[tag]; m = sel(g) & g["eng"]
        Dsps=[];Dfbs=[];Draws=[]
        for a_,b_ in runs_of(m, 100)[:60]:
            b_ = min(b_, a_+4000)
            try: s0 = GI.simulate(g, a_, b_, cells)
            except Exception: continue
            # restrict to the ticks that are actually IN the stratum (simulate pads +-50 frames)
            inmask = np.zeros(len(g["t"]), bool); inmask[a_:b_] = True
            live = np.repeat((g["eng"] & inmask)[s0["seg"]], 10)
            if live.sum() < 100: continue
            sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
            Dsps.append(np.floor(dsp*KD/8.0)[live]);Dfbs.append(np.floor(-dfb*KD/8.0)[live])
            Draws.append(np.floor((dsp-dfb)*KD/8.0)[live])
        if not Dsps: continue
        Dsp=np.concatenate(Dsps);Dfb=np.concatenate(Dfbs);Draw=np.concatenate(Draws)
        if len(Dsp) < 1000: continue
        row=[name,tag,len(Dsp)/FS1K]
        for d in DOSES:
            bm=np.abs(Draw)>d
            row+=[100.0*bm.mean(),100.0*(np.abs(Dsp[bm])>np.abs(Dfb[bm])).mean() if bm.any() else np.nan,
                  np.percentile(np.abs(Dfb),99)/d]
        CLEAN[(name,tag)]=row
        pr("  %-42s %-5s %8.1f | %6.2f %8.1f %10.3f | %6.2f %8.1f %10.3f" % tuple(row))

# ======================================================================================================================
# PART 5 -- EFFECTIVE Kd.  The clamp's describing-function gain on the D signal, measured in-band, per stratum.
#   ratio = band-amplitude of clip(D_raw,+-L) / band-amplitude of D_raw, at 6-9 Hz (the ring) and 18-22 Hz (the grind).
#   A ratio < 1 IS a local Kd cut at that frequency, in that stratum.  A4 (the design's own appendix) says a Kd cut
#   RAISES |S|@20 and drags the sensitivity peak from 26.3 Hz down to 20.7 Hz -- i.e. INTO the grind band.
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 5 -- EFFECTIVE Kd MULTIPLIER (in-band gain of the clamped D vs the unclamped D), per stratum")
pr("=" * 140)
pr("  %-42s %-5s %8s | %-19s | %-19s" % ("stratum","route","s expo","clamp 10240 (today)","clamp 2560 (V287)"))
pr("  %-42s %-5s %8s | %9s %9s | %9s %9s" % ("","","","Kd@6-9Hz","Kd@18-22","Kd@6-9Hz","Kd@18-22"))
for name, sel in STRATA:
    if "HIGHWAY FAST" in name: continue
    for tag in ("r39","r3a","r3c"):
        g = G[tag]; m = sel(g) & g["eng"]
        segs=[]
        for a_,b_ in runs_of(m, 300)[:40]:
            b_ = min(b_, a_+4000)
            try: s0 = GI.simulate(g, a_, b_, cells)
            except Exception: continue
            inm = np.zeros(len(g["t"]), bool); inm[a_:b_]=True
            live = np.repeat((g["eng"]&inm)[s0["seg"]],10)
            if live.sum() < 600: continue
            sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
            segs.append(np.floor((dsp-dfb)*KD/8.0)[live])
        if not segs: continue
        tot = sum(len(s) for s in segs)
        if tot < 3000: continue
        row=[name,tag,tot/FS1K]
        for d in DOSES:
            for lo,hi in ((6.0,9.0),(18.0,22.0)):
                num=den=0.0
                for D in segs:
                    if len(D) < 512: continue
                    num += C20.bamp(np.clip(D,-d,d), lo, hi, FS1K)**2 * len(D)
                    den += C20.bamp(D, lo, hi, FS1K)**2 * len(D)
                row.append(np.sqrt(num/den) if den>0 else np.nan)
        pr("  %-42s %-5s %8.1f | %9.4f %9.4f | %9.4f %9.4f" % tuple(row))

# ======================================================================================================================
# PART 6 -- THE "MAX-RATE UNCHANGED" CLAIM.  B4 pooled MEDIANS across clamps (n=24 each) and got a non-monotone +-3 %.
#   That is an UNDERPOWERED test: the medians are dominated by P, and pooling different steps per clamp adds variance
#   the design never had to take.  The powered test is PAIRED: same step, both clamps, difference per step.
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 6 -- PAIRED AUTHORITY TEST.  Same steps, both clamps.  (B4 compared POOLED medians of different steps.)")
pr("=" * 140)
def steps_of(g, barmax=300.0):
    idx = g["idx"]; d = np.r_[0.0, np.diff(idx)]
    thr = np.percentile(np.abs(d[g["eng"]]), 97.0)
    hit = g["eng"] & (np.abs(d) >= thr) & (np.abs(g["bar"]) < barmax)
    ks = np.flatnonzero(hit)
    out=[]; last=-999
    for k in ks:
        if k-last < 40 or k < 60 or k > len(idx)-40: continue
        out.append(k); last=k
    return out, thr

pr("  %-5s %6s | %-34s | %-34s" % ("route","n", "PAIRED median dT/T (2560 vs 10240)", "POOLED medians |T| (B4's method)"))
pr("  %-5s %6s | %9s %9s %9s %5s | %9s %9s" % ("","","0-50ms","0-100ms","0-200ms","peak","10240","2560"))
PLANT = {}
for tag in ("r39","r3a","r3c"):
    g = G[tag]; ks, thr = steps_of(g)
    rats = {w:[] for w in (50,100,200)}; pk=[]; pool={d:[] for d in DOSES}
    for k in ks[:200]:
        a_ = k-5; b_ = k+40
        try:
            V.D_CLAMP = 10240; s10 = GI.simulate(g, a_, b_, cells)
            V.D_CLAMP = 2560;  s25 = GI.simulate(g, a_, b_, cells)
        finally:
            V.D_CLAMP = 10240
        # t index of the step inside the 1 kHz frame
        j0 = (k - s10["seg"].start)*10
        for w in (50,100,200):
            A = np.abs(s10["T"][j0:j0+w]); Bq = np.abs(s25["T"][j0:j0+w])
            if len(A) < w or np.median(A) < 20: continue
            rats[w].append(np.median(Bq)/np.median(A))
        A = np.abs(s10["T"][j0:j0+200]); Bq = np.abs(s25["T"][j0:j0+200])
        if len(A)==200 and A.max()>20: pk.append(Bq.max()/A.max())
        pool[10240].append(np.median(np.abs(s10["T"][j0:j0+100])))
        pool[2560].append(np.median(np.abs(s25["T"][j0:j0+100])))
    if not rats[100]: continue
    pr("  %-5s %6d | %9.4f %9.4f %9.4f %5.3f | %9.1f %9.1f" % (
        tag, len(rats[100]), np.median(rats[50]), np.median(rats[100]), np.median(rats[200]),
        np.median(pk), np.median(pool[10240]), np.median(pool[2560])))
    # bootstrap CI on the paired 0-100 ms ratio
    r = np.array(rats[100]); bs = np.array([np.median(np.random.choice(r, len(r))) for _ in range(2000)])
    pr("        paired 0-100 ms ratio  median %.4f  95%% CI [%.4f, %.4f]  ;  share of steps with ratio < 1: %.1f %%" % (
        np.median(r), np.percentile(bs,2.5), np.percentile(bs,97.5), 100.0*np.mean(r<1.0)))

# plant DC gain, crude but honest: |rate| per unit |T| in each stratum (engaged, from the log)
pr("")
pr("  Plant scale, measured (median |rate| deg/s per 100 counts of tap |T|), engaged, for converting a torque loss to a rate loss:")
for tag in ("r39","r3a","r3c"):
    g=G[tag]
    for lab, m in (("creep 1-3 m/s", g["eng"]&(g["vego"]>=1)&(g["vego"]<3)&(np.abs(g["bar"])<400)),
                   ("high-angle >60 deg", g["eng"]&(np.abs(g["ang"])>60)),
                   ("fast wheel >25 deg/s", g["eng"]&(np.abs(g["rate_x"])>25))):
        if m.sum()<300: continue
        T=np.abs(g["T100"])[m]; r=np.abs(g["rate_x"])[m]; sel=T>50
        if sel.sum()<100: continue
        pr("      %-5s %-22s  %.3f deg/s per 100 T   (n %d)" % (tag, lab, 100.0*np.median(r[sel]/T[sel]), sel.sum()))

# ======================================================================================================================
# PART 7 -- CAN THE PREREG'S FAIL STATISTICS ACTUALLY BE COMPUTED FROM ONE SHORT DRIVE?
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 7 -- PREREG FAIL-CRITERION AUDIT (B6: Q1 liveness, Q5 ring, Q6 shelf, Q7 detector, Q8 authority)")
pr("=" * 140)
pr("  7a. EXPOSURE.  What fraction of engaged time does each stratum occupy?  (the build is ALWAYS ON; the")
pr("      pre-registration only looks at creep and at episode windows.)")
pr("  %-42s %-8s %-8s %-8s" % ("stratum","r39 %","r3a %","r3c %"))
for name, sel in STRATA:
    row=[name]
    for tag in ("r39","r3a","r3c"):
        g=G[tag]; row.append(100.0*(sel(g)&g["eng"]).sum()/max(1,g["eng"].sum()))
    pr("  %-42s %-8.2f %-8.2f %-8.2f" % tuple(row))
pr("      strict creep runs >= 2 s, TOTAL seconds available per route: %s" % (
    ", ".join("%s %.1f s" % (t, sum(b-a for a,b in runs_of(G[t]["eng"]&(G[t]["vego"]>=1)&(G[t]["vego"]<3)&(np.abs(G[t]["bar"])<400),200))/FS) for t in ("r39","r3a","r3c"))))

pr("")
pr("  7b. Q6 (SHELF, a FAIL criterion): 0x18F rate 33-49.9 / 2-6.  Threshold is 'must not exceed x1.3'.")
pr("      Route-to-route AND window-to-window spread of the statistic ITSELF, in the creep stratum:")
def q6(x):
    return C20.bamp(x, 33.0, 49.9, FS) / max(1e-9, C20.bamp(x, 2.0, 6.0, FS))
allv=[]
for tag in ("r39","r3a","r3c"):
    g=G[tag]; m=g["eng"]&(g["vego"]>=1)&(g["vego"]<3)&(np.abs(g["bar"])<400)
    ws=[q6(g["rate_x"][a_:b_]) for a_,b_ in runs_of(m,200)]
    if not ws: continue
    pooled = q6(np.concatenate([g["rate_x"][a_:b_] for a_,b_ in runs_of(m,200)]))
    allv.append(pooled)
    pr("      %-5s pooled %.4f | per-window n %d  min %.4f  p50 %.4f  max %.4f  -> within-route spread x%.2f" % (
        tag, pooled, len(ws), min(ws), np.median(ws), max(ws), max(ws)/max(1e-9,min(ws))))
pr("      route-to-route spread of the pooled statistic: x%.2f  (FAIL threshold is x1.30)" % (max(allv)/min(allv)))

pr("")
pr("  7c. Q1 (LIVENESS, the gate on everything else).  Size of the observable step on the 50 Hz 427 tap.")
lag_a, lag_b, gain = cells["lag_a"], cells["lag_b"], cells["gain"]
imp = signal.lfilter([lag_b/1024.0],[1.0,-lag_a/1024.0], np.r_[1.0, np.zeros(400)])
y = (np.r_[0.0, imp[:-1]] + imp)/32.0
Timp = -y*gain/32768.0
dD = 10240-2560
pr("      one clipped tick removes up to %d counts of D; through fade/sum/lag/gain that is a T impulse of" % dD)
pr("      peak %.1f counts decaying with tau ~%.0f ms.  The 427 tap quantises T in steps of 8 -> %.1f LSB." % (
    dD*np.abs(Timp).max(), -1.0/np.log(lag_a/1024.0), dD*np.abs(Timp).max()/8.0))
pr("      binding ticks per second of engaged driving, at 2560: creep %.0f/s, high-angle %.0f/s, hands-on %.0f/s" % (
    22.3, 173.4, 100.2))
pr("      -> Q1 is computable; it is the ONE prereg statistic with real power.")

pr("")
pr("  7d. Q5 (RING, a FAIL criterion): today 0.980 with CI [0.971, 0.983].  FAIL = 'rises above 0.980'.")
pr("      The threshold IS the current point estimate and sits INSIDE its own confidence interval.")
pr("      -> a null build trips this FAIL roughly half the time.  MIS-SPECIFIED.")

pr("")
pr("  7e. Q2/Q3 (PRIMARY + its negative control) are defined on EPISODE windows -- operator-bookmarked grind")
pr("      events.  r39 (952 s) contained 2; r3a and r3c contained 0 that the design used.  A drive with no")
pr("      episode returns NO primary endpoint at all.  That is a real probability, not a remote one.")

OUTP = os.path.join(SCR, "adv_v287_b_units_strata.txt")
open(OUTP, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
print("\nwrote %s" % OUTP)

# ======================================================================================================================
# PART 8 -- THE REMEDY: what dose keeps the design's own "excitation limiter" test TRUE in the unsampled strata?
# ======================================================================================================================
pr("")
pr("=" * 140)
pr("PART 8 -- DOSE LADDER IN THE UNSAMPLED STRATA.  The design's own admissibility test is")
pr("  'D_sp-dominated on the binding ticks AND p99|D_fb|/clamp < 1'.  Where does each dose still pass it?")
pr("=" * 140)
LAD = [10240, 7680, 5120, 3840, 2560]
pr("  %-32s %-5s | %s" % ("stratum","route", " ".join("%-22s"%("clamp %d"%d) for d in LAD)))
pr("  %-32s %-5s | %s" % ("","", " ".join("%-22s"%"dom%  p99Dfb/clp  bind%" for d in LAD)))
for name, sel in STRATA:
    if not any(k in name for k in ("HANDS-ON  ","LOADED","FAST WHEEL >25","CREEP")): continue
    for tag in ("r39","r3a","r3c"):
        g=G[tag]; m=sel(g)&g["eng"]; Dsps=[];Dfbs=[];Draws=[]
        for a_,b_ in runs_of(m,100)[:60]:
            b_=min(b_,a_+4000)
            try: s0=GI.simulate(g,a_,b_,cells)
            except Exception: continue
            inm=np.zeros(len(g["t"]),bool); inm[a_:b_]=True
            live=np.repeat((g["eng"]&inm)[s0["seg"]],10)
            if live.sum()<100: continue
            sp32=32.0*s0["sp"];dsp=np.r_[0.0,np.diff(sp32)];dfb=np.r_[0.0,np.diff(s0["fb"])]
            Dsps.append(np.floor(dsp*KD/8.0)[live]);Dfbs.append(np.floor(-dfb*KD/8.0)[live]);Draws.append(np.floor((dsp-dfb)*KD/8.0)[live])
        if not Dsps: continue
        Dsp=np.concatenate(Dsps);Dfb=np.concatenate(Dfbs);Draw=np.concatenate(Draws)
        if len(Dsp)<3000: continue
        cellsout=[]
        for d in LAD:
            bm=np.abs(Draw)>d
            dom=100.0*(np.abs(Dsp[bm])>np.abs(Dfb[bm])).mean() if bm.any() else 100.0
            cellsout.append("%5.1f %10.3f %6.2f" % (dom, np.percentile(np.abs(Dfb),99)/d, 100.0*bm.mean()))
        pr("  %-32s %-5s | %s" % (name[:32], tag, " ".join("%-22s"%c for c in cellsout)))
OUTP = os.path.join(SCR, "adv_v287_b_units_strata.txt")
open(OUTP,"w",encoding="utf-8").write("\n".join(OUT)+"\n")
print("\nwrote %s" % OUTP)
