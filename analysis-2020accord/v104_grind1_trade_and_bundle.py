"""THE GRIND-#1 TRADE AT k = 1.85, THE LEVER-B BUNDLE, AND THREE LOOSE ENDS.

Answers, in order:
  1. Does |H(21.73)| crossing unity change the CLOSED-LOOP character at grind #1?
  2. Is there a k with |H(21.73)| <= 1.0 AND dG >= 0.03 at 6-9 Hz?
  3. Lever B + c4 as one build: confounding, per-lever readout, net grind-#1 prediction.
  4. Does the two-regime limiter model destroy a_filt as a single number?
  5. gp-0x6bd0's live duty on route 0x9e -- the highway-exposure check the 98.8 % figure needs.
  6. red-team R0d: what the engagement-boundary step in u actually measures, and its precision.
"""
import sys
import numpy as np
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
DEG = np.pi / 180
c1, c2, c3, c4 = L.honda_exact()
A_FILT = 0.0457
RATE69 = 0.1173                       # |r24+r26| / T_s at 6-9 Hz, GATE2 2.2 (solved)
BANDS = [(2, 4), (4, 6), (6, 9), (9, 13), (15, 22), (18, 22), (21, 22.5), (22, 26), (26, 31)]


def Hh(fc):
    return complex(L.H_biquad(c1, c2, c3, c4, np.array([fc]))[0])


def load_sp(tag, ykey):
    d = L.load(tag)
    eps = L.episodes(d['cc_lat'] > 0.5)
    return (L.episode_specs(d['tq'].astype(float), d[ykey].astype(float), eps, NPER),
            L.episode_specs(d['rate_f'].astype(float) * L.DEG2RAD, d['tq'].astype(float), eps, NPER))


G4s, Z4s = load_sp('r85', 'x6b94')
G8s, Z8s = load_sp('r95', 'x6b94')


def ident(lo, hi, nboot=2000, seed=41):
    def one(i4, i8):
        G4 = L.band_H([G4s[j] for j in i4], f, lo, hi)[0]
        Z4 = L.band_H([Z4s[j] for j in i4], f, lo, hi)[0]
        G8 = L.band_H([G8s[j] for j in i8], f, lo, hi)[0]
        Z8 = L.band_H([Z8s[j] for j in i8], f, lo, hi)[0]
        r = Z4 / Z8
        c = (r - 1) / (G8 - r * G4)
        return c, G4, 1 + c * G4, Z4
    pt = one(range(len(G4s)), range(len(G8s)))
    rng = np.random.default_rng(seed)
    n4, n8 = len(G4s), len(G8s)
    bs = np.array([one(rng.integers(0, n4, n4), rng.integers(0, n8, n8)) for _ in range(nboot)])
    return pt, bs


ID = {b: ident(*b) for b in BANDS}
AF = np.load('_v103_natexp.npz')['a69'].real
AF = AF[(AF > 0.005) & (AF < 0.25)]


def dG_c4(fc, k):
    return (k - 1) * (-A_FILT * Hh(fc))


def dG_rate(fc, m):
    """r24/r26 scaled by m. pol*jw => angle -90 deg; magnitude anchored at 7.5 Hz, ~ f."""
    return (m - 1) * RATE69 * (fc / 7.5) * np.exp(-1j * np.pi / 2)


# ==================================================================================================
print("=" * 104)
print("1. THE GRIND-#1 TRADE -- does |H(21.73)| crossing unity change the CLOSED-LOOP character?")
print("=" * 104)
print("%8s %10s %12s %12s %11s %11s %11s" %
      ('k', '|H|@21.73', 'lane change', '|G|/|G0|', '|A|', 'amp ratio', 'Re Z'))
b = (21, 22.5)
c, G0, A0, Z4 = ID[b][0]
for k in (1.00, 1.168, 1.35, 1.50, 1.70, 1.85, 2.00, 2.50):
    H21 = k * abs(Hh(21.73))
    dG = dG_c4(21.75, k)
    Ak = A0 + c * dG
    print("%8.2f %10.3f %11.0f %% %12.3f %11.3f %11.3f %+11.0f" %
          (k, H21, 100 * (H21 - abs(Hh(21.73))) / abs(Hh(21.73)),
           abs(G0 + dG) / abs(G0), abs(Ak), abs(A0) / abs(Ak), (Z4 * A0 / Ak).real))
aci = np.percentile(np.abs(ID[b][1][:, 2]), [2.5, 97.5])
print("  |A| at 21.0-22.5 Hz = %.3f, 95 %% CI [%.3f, %.3f] -- the loop is NEUTRAL there, so the"
      % (abs(A0), aci[0], aci[1]))
print("  identification has little leverage and this row is the weakest in the table.")
print()
print("  *** THE RESOLUTION: |H| is a statement about the LANE, not about the car.")
print("      lane content at 21.73 Hz     0.856 -> 1.583  = +85 %% of the STOCK lane")
print("      aggregator SUM |G|/|G0|              %.3f  = a small REDUCTION" %
      (abs(G0 + dG_c4(21.75, 1.85)) / abs(G0)))
print("      closed-loop amplification            %.3f  = a small REDUCTION" %
      (abs(A0) / abs(A0 + c * dG_c4(21.75, 1.85))))
print("      The +85 %% does not propagate: at 21.73 Hz the lane sits %.0f deg from the sum"
      % abs(np.angle(dG_c4(21.75, 1.85) / G0, deg=True)))
print("      (>90 deg => it SUBTRACTS), and |A| ~ 1 means the loop neither amplifies nor damps.")

print()
print("2. IS THERE A k THAT KEEPS |H(21.73)| <= 1.0 AND STILL DELIVERS dG >= 0.03 AT 6-9 Hz?")
kmax = 1.0 / abs(Hh(21.73))
print("   |H(21.73)| = %.4f*k  =>  unity at k = %.3f" % (abs(Hh(21.73)), kmax))
print("   at k = %.3f the 6-9 Hz dose is dG = %.4f" % (kmax, abs(dG_c4(7.5, kmax))))
print("   dG >= 0.030 needs k >= %.3f, at which |H(21.73)| = %.3f" %
      (1 + 0.030 / (A_FILT * abs(Hh(7.5))), abs(Hh(21.73)) * (1 + 0.030 / (A_FILT * abs(Hh(7.5))))))
print("   *** MUTUALLY EXCLUSIVE by %.1fx in dose. The constraints cannot both be met." %
      (0.030 / abs(dG_c4(7.5, kmax))))

# ==================================================================================================
print()
print("=" * 104)
print("3. THE LEVER-B BUNDLE -- c4 k = 1.85 + r24 x2.000 engaged, one build")
print("=" * 104)
print("[3.1] do they confound each other?  angle between the two dG vectors, per band")
print("%10s %12s %12s %12s %12s" % ('band', 'arg dG_c4', 'arg dG_rate', 'separation', '|dG| ratio'))
for bb in BANDS:
    fc = 0.5 * (bb[0] + bb[1])
    a1 = np.angle(dG_c4(fc, 1.85), deg=True)
    a2 = np.angle(dG_rate(fc, 2.0), deg=True)
    sep = abs((a1 - a2 + 180) % 360 - 180)
    print("%5.1f-%-4.1f %+12.1f %+12.1f %12.1f %12.2f" %
          (bb[0], bb[1], a1, a2, sep, abs(dG_c4(fc, 1.85)) / abs(dG_rate(fc, 2.0))))

print()
print("[3.2] each lever alone and both together (exact Mobius, a_filt)")
print("%10s %11s %11s %11s %11s %11s %11s" %
      ('band', 'ReZ base', 'ReZ c4', 'ReZ LevB', 'ReZ BOTH', 'amp c4', 'amp BOTH'))
Z9E = {(6, 9): 6873 * np.exp(1j * -123.2 * DEG), (15, 22): 1379 * np.exp(1j * 108.6 * DEG),
       (22, 26): 1168 * np.exp(1j * 96.8 * DEG)}
for bb in BANDS:
    fc = 0.5 * (bb[0] + bb[1])
    c, G0, A0, Z4 = ID[bb][0]
    Z1 = Z9E.get(bb, Z4)
    A_c4 = A0 + c * dG_c4(fc, 1.85)
    A_lb = A0 + c * dG_rate(fc, 2.0)
    A_bo = A0 + c * (dG_c4(fc, 1.85) + dG_rate(fc, 2.0))
    print("%5.1f-%-4.1f %+11.0f %+11.0f %+11.0f %+11.0f %11.3f %11.3f" %
          (bb[0], bb[1], Z1.real, (Z1 * A0 / A_c4).real, (Z1 * A0 / A_lb).real,
           (Z1 * A0 / A_bo).real, abs(A0) / abs(A_c4), abs(A0) / abs(A_bo)))

print()
print("[3.3] NET GRIND-#1 prediction for the bundle, 18-22 Hz band amplitude")
print("   Lever B, ROAD-MEASURED (V67/V68, build_v84_tva.py): 0.40 [0.27, 0.58]")
bb = (18, 22)
c, G0, A0, Z4 = ID[bb][1][:, 0], ID[bb][1][:, 1], ID[bb][1][:, 2], ID[bb][1][:, 3]
amp_c4 = np.abs(ID[bb][0][2]) / np.abs(ID[bb][0][2] + ID[bb][0][0] * dG_c4(20.0, 1.85))
bsamp = np.abs(ID[bb][1][:, 2]) / np.abs(ID[bb][1][:, 2] + ID[bb][1][:, 0] * dG_c4(20.0, 1.85))
ci = np.percentile(bsamp, [2.5, 97.5])
print("   c4 k=1.85 at 18-22 Hz, MODELLED amplification ratio: %.3f  [%.3f, %.3f]"
      % (amp_c4, ci[0], ci[1]))
lo = 0.40 * ci[0]
hi = 0.40 * ci[1]
print("   NET (independent multiplication of the two, point estimates): %.3f" % (0.40 * amp_c4))
print("   NET range using Lever B's own road CI x c4's model CI: [%.3f, %.3f]"
      % (0.27 * ci[0], 0.58 * ci[1]))
print("   => c4's grind-#1 cost is a MODELLED %+.0f %%, against Lever B's MEASURED -60 %%."
      % (100 * (amp_c4 - 1)))
print("   *** the two are not commensurable: one is road-measured, one is model-predicted from an")
print("       identification whose |A| CI at 18-22 Hz is [%.3f, %.3f]. Do not add them as if equal."
      % tuple(np.percentile(np.abs(ID[bb][1][:, 2]), [2.5, 97.5])))


# ==================================================================================================
print()
print("=" * 104)
print("4. DOES THE TWO-REGIME LIMITER MODEL DESTROY a_filt AS A SINGLE NUMBER?")
print("=" * 104)
print("  Regimes (biquad-structure / red-team): limiter OFF => lane at angle 180 deg, a_filt/a = 1;")
print("  limiter hard-ON => pedestal carries the AC and the lane rotates to angle -76.9 deg.")
print("  A mixture with ON-duty d would rotate the SOLVED complex `a` away from pure-real.")
print("  My inversion solved a COMPLEX a and the imaginary part is a FREE consistency check:")
aj = np.load('_v103_natexp.npz')['a69']
ph = np.angle(aj[np.abs(aj.real) > 1e-6], deg=True)
ph = (ph + 180) % 360 - 180
print("     solved a = 0.0457 with Im/Re = -0.031  =>  phase %+0.2f deg from pure real"
      % np.degrees(np.arctan(-0.031)))
print("     bootstrap phase of a: p50 %+.1f deg, 95 %% CI [%+.1f, %+.1f]"
      % (np.median(ph), *np.percentile(ph, [2.5, 97.5])))
rot = (-76.9) - 180.0
rot = (rot + 180) % 360 - 180
print("     an ON-regime frame rotates the lane by %+.1f deg." % rot)
print("%14s %14s" % ('ON duty d', 'phase shift it would induce (rho = 1)'))
for d in (0.0, 0.05, 0.10, 0.20, 0.30, 0.50):
    v = (1 - d) + d * np.exp(1j * rot * DEG)
    print("%14.2f %14.1f deg" % (d, np.angle(v, deg=True)))
print("  *** the measured phase is %+0.2f deg and the rotation an ON frame would cause is %+.1f deg"
      % (np.degrees(np.arctan(-0.031)), rot))
print("      -- OPPOSITE in sign. The data does not support ANY appreciable ON duty at 6-9 Hz.")
print("      This does NOT prove d = 0 (rho is unknown and the CI is wide), but it does mean the")
print("      mixture is not visible in the one place it would have to show up.")
print("  *** THE CLAIM THAT SURVIVES, stated narrowly:")
print("      a_filt = 0.0457 is the AS-FLOWN, DUTY-WEIGHTED sensitivity of the aggregator sum to a")
print("      change in H.  A c4 edit acts through H and ONLY through H, under the same duty mix.")
print("      So a_filt is the correct coefficient for pricing c4 BY CONSTRUCTION, whatever the")
print("      regime mixture is.  It is NOT a measurement of the ROM map slope, and it should never")
print("      be quoted as 'we measured a'.")

# ==================================================================================================
print()
print("=" * 104)
print("5. gp-0x6bd0's LIVE DUTY -- the highway-exposure check the 98.8 %% figure needs")
print("=" * 104)
import os
root = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares') + '/analysis-2020accord'
v103 = open(os.path.join(root, "_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN."
                               "3680.6B4C.6ADA-ID.B3VARIES_plain_image.bin"), 'rb').read()


def u16(bb_, a):
    return bb_[a] | (bb_[a + 1] << 8)


print("  FactorC m26 record read from the FLOWN V103 image (count at 0xD77D0):")
CX = [u16(v103, 0xD77D2 + 2 * i) for i in range(4)]
CY = [u16(v103, 0xD77DA + 2 * i) for i in range(4)]
print("     count = %d   X = %s counts = %s km/h   Y = %s"
      % (u16(v103, 0xD77D0), CX, [round(x / 64.0, 1) for x in CX], CY))
print("  FactorE m26 record (0x14 before m27's 0xD7822):")
EX = [u16(v103, 0xD780E + 2 * i) for i in range(4)]
EY = [u16(v103, 0xD7816 + 2 * i) for i in range(4)]
print("     raw halfwords 0xD7804..0xD7820: %s"
      % [u16(v103, a) for a in range(0xD7804, 0xD7822, 2)])
print()
d9 = L.load('r9e')
eng = d9['cc_lat'] > 0.5
vk = d9['v_rear'].astype(float) * 3.6
rate = np.abs(d9['rate_f'].astype(float))
print("  route 0x9e, ENGAGED frames (%d), joint duty of the damper's TWO gates:" % eng.sum())
print("%18s %10s %10s %10s" % ('condition', 'duty', 'n frames', 'note'))
for lbl, m in (('v > 35 km/h (FactorC)', eng & (vk > 35)),
               ('|rate| > 12.7 deg/s (FactorE)', eng & (rate > 12.7)),
               ('BOTH gates open', eng & (vk > 35) & (rate > 12.7)),
               ('BOTH + micro regime 1-13 deg/s', eng & (vk > 35) & (rate > 1) & (rate < 13))):
    print("%30s %10.4f %10d" % (lbl, m.sum() / eng.sum(), m.sum()))
print()
print("  *** the 98.8 %% zero figure came from routes 6e/5e. Route 0x9e has %.1f %% of engaged time"
      % (100 * (eng & (vk > 35)).sum() / eng.sum()))
print("      above 35 km/h -- REAL highway exposure -- so the speed gate is NOT the binding one here.")
print("      The RATE gate is: |rate| > 12.7 deg/s on only %.2f %% of engaged frames."
      % (100 * (eng & (rate > 12.7)).sum() / eng.sum()))
print("      And the 6-9 Hz ratchet lives in the MICRO regime (1-13 deg/s), where FactorE is 0.")

# ==================================================================================================
print()
print("=" * 104)
print("6. red-team R0d -- what the engagement-boundary step in u actually measures")
print("=" * 104)
d85 = L.load('r85')
e85 = d85['cc_lat'] > 0.5
u85 = d85['x6b94'].astype(float)
du = np.abs(np.diff(u85[e85]))
print("  frame-to-frame |du| on the SUM, engaged (route 0x85, 427 = gp-0x6b94, 100 Hz CAN):")
print("     p50 %.0f   p90 %.0f   p95 %.0f   p99 %.0f   MAX %.0f counts"
      % (*np.percentile(du, [50, 90, 95, 99]), du.max()))
print("  a k = 1.85 arm/disarm step is (k.H - 1).gp-0x6b82 ~ 0.85 x |gp-0x6b82| at DC.")
print("     to clear the p95 frame-to-frame noise (%.0f ct) the step needs |gp-0x6b82| >= %.0f ct"
      % (np.percentile(du, 95), np.percentile(du, 95) / 0.85))
for tag in ('r9e',):
    d = L.load(tag)
    m = d['cc_lat'] > 0.5
    trans = int(np.abs(np.diff(m.astype(np.int8))).sum())
    dur = len(m) / L.FS
    print("  transitions available: route %s has %d engagement edges in %.0f s = %.2f per 30 s"
          % (tag, trans, dur, 30 * trans / dur))
print()
print("  *** CORRECTION TO THE ENTHUSIASM: an edge gives |gp-0x6b82| at ONE INSTANT.")
print("      `a` is a TRANSFER FUNCTION over a band; you cannot build one from ~2 point samples.")
print("      R0d is an excellent IN-FORCE WITNESS and a direct check on the lane's MAGNITUDE.")
print("      It is NOT a measurement of `a` on a 15-30 s drive.")
print("  *** THE VERSION THAT DOES WORK, and it needs no edges: with 427 packing the SUM, estimate")
print("      tq -> u SEPARATELY on engaged (H = k.H_stock) and manual (H = 1) frames of the SAME")
print("      drive.  Their difference is (k.H_stock - 1).a_map -- the V102->V103 inversion, WITHIN")
print("      one drive.  Its feasibility rests entirely on the MANUAL arm's coherence:")
for tag in ('r85', 'r95'):
    d = L.load(tag)
    m = d['cc_lat'] > 0.5
    for lbl, mask in (('engaged', m), ('manual', ~m)):
        eps = L.episodes(mask)
        if not eps:
            continue
        sp = L.episode_specs(d['tq'].astype(float), d['x6b94'].astype(float), eps, NPER)
        if not sp:
            continue
        H, co = L.band_H(sp, f, 6, 9)
        print("     %s %-8s tq->u at 6-9 Hz: |H| %.4f at %+.1f deg, coh2 %.3f, %d runs, %.0f s"
              % (tag, lbl, abs(H), np.angle(H, deg=True), co, len(eps),
                 sum(bq - aq for aq, bq in eps) / L.FS))
