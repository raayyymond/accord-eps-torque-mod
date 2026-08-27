#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
studies/models/eps_v49_a382_stagec_flip_model.py

GATE-2 (closed-loop) assessment of the V49B candidate: flip the SIGN of FUN_0003a382's
StageC derivative (subr->sub @0x3a836), turning a reinforcing derivative feedback into an
opposing (damping) one, WITHOUT changing its magnitude.

Datapath is disassembly-exact (carrier-topo trace, 2026-07-22; all 4 gains byte-verified):
  residual  = clamp(gp-0x4f60 - ref, +/-10240)                 [ref is DC/slow -> AC passes]
  StageA    = ((residual * L1)>>10)<<5 , EMA pole 0xC6450=1024 (UNITY) -> T_A, instantaneous
              L1 = 0xC6B26 = 256   => StageA(z) = residual * (256/1024) * 32 = 8.0*residual   (flat, 0 deg)
  StageC    = clamp((residual - z^-1 residual)*L3 >>10, +/-10240)<<5 , EMA pole 0xC644A=1024 (UNITY)
              L3 = 0xC6AE6 = 2048  => StageC(z) = 64*(1 - z^-1)*residual                       (derivative, +90 deg)
  S3        = ((residual * L2)>>10) + S3_old   (pure integrator, NO pole; dynamic clamp ignored in linear model)
              L2 = 0xC6B12 = 98    => S3(z) = (98/1024)/(1 - z^-1) * residual                  (integrator, -90 deg)
  out       = ((StageC + S3 + StageA)>>5) * uVar27 >>10 * polarity ,  uVar27=0xC67B8=1024 (UNITY)
           => H_a382(z) = [8 + 64(1-z^-1) + 0.09570/(1-z^-1)] / 32 * polarity

NOTE the S3 domain: StageA/StageC carry a <<5 (x32); S3 does NOT -> S3 is 32x down in the sum, so it is
a MINOR term at 21.5 Hz. L1/L2/L3 are motor-rate LERPs; the values above are the cal Y's used as the
nominal operating point -- results are shown with a sensitivity sweep on L3 (the StageC gain).

CONVENTION (matches studies/models/eps_v48c_gate2_closed_loop.py): positive-feedback loop, critical point +1.
A carrier's loop factor  F = H_a382(jw) * P(jw) * e^{-jw*td}.
  Re[F] > 0  => ANTI-DAMPING (destabilizing);  Re[F] < 0 => DAMPING (stabilizing).
The absolute loop weight kappa is unknown, so the DECISIVE, kappa-independent outputs are:
  (1) angle(F): does the flip move it across the +/-90 deg damping boundary?
  (2) |dF(flip)| / |dF(V48A 75% cut)|: is the flip a bigger, sign-correct lever than the cut that was null?

Run: python studies/models/eps_v49_a382_stagec_flip_model.py
"""
import cmath, math

FS   = 1000.0
F0   = 21.5
W0   = 2*math.pi*F0
TD   = 1.5/FS                      # ~1.5-sample loop delay (v48c)

L1, L2, L3, UV = 256, 98, 2048, 1024     # byte-verified cal Y's (nominal operating point)

def H_a382(w, flip=False, pol=+1, l3=L3, stagec_pole=1024):
    z_1 = cmath.exp(-1j*w/FS)             # z^-1
    stageA = (L1/1024.0)*32.0                       # 8.0, flat
    raw_c  = (l3/1024.0)*32.0*(1 - z_1)             # 64*(1-z^-1) at l3=2048  (pure derivative)
    aC     = stagec_pole/1024.0                     # StageC EMA pole cal 0xC644A (1024 = unity/no filter)
    ema_C  = aC/(1 - (1-aC)*z_1) if aC < 1 else 1.0 # 1st-order low-pass on the derivative
    stageC = raw_c * ema_C
    if flip:
        stageC = -stageC
    S3     = (L2/1024.0)/(1 - z_1)                  # integrator
    summ   = stageA + stageC + S3
    return summ/32.0 * (UV/1024.0) * pol

def plant(w, zeta):
    s = 1j*w
    return (W0*W0)/(s*s + 2*zeta*W0*s + W0*W0)

def loop_factor(w, zeta, **kw):
    return H_a382(w, **kw) * plant(w, zeta) * cmath.exp(-1j*w*TD)

def ang(x): return math.degrees(cmath.phase(x))

def band(label, zeta):
    print("="*90)
    print(f"{label}   (plant zeta={zeta:.3f}, Q={1/(2*zeta):.1f})")
    print("="*90)
    w = W0
    # lane transfer alone (kappa-independent phase is what matters)
    for pol in (+1, -1):
        Hc = H_a382(w, flip=False, pol=pol)
        Hf = H_a382(w, flip=True,  pol=pol)
        Fc = loop_factor(w, zeta, flip=False, pol=pol)
        Ff = loop_factor(w, zeta, flip=True,  pol=pol)
        def tag(F): return "ANTI-DAMPING" if F.real > 0 else "DAMPING     "
        print(f"\n  polarity gp-0x6752 = {pol:+d}")
        print(f"    a382 lane  H(21.5): current |{abs(Hc):.3f}| ∠{ang(Hc):+6.1f}   flipped |{abs(Hf):.3f}| ∠{ang(Hf):+6.1f}")
        print(f"    loop factor F=H*P*delay:")
        print(f"       current : |{abs(Fc):.3f}| ∠{ang(Fc):+6.1f}   Re={Fc.real:+.3f}  -> {tag(Fc)}")
        print(f"       FLIPPED : |{abs(Ff):.3f}| ∠{ang(Ff):+6.1f}   Re={Ff.real:+.3f}  -> {tag(Ff)}")
        # compare the flip's move vs the V48A 75% magnitude cut's move (both as delta-F)
        Fcut = 0.25*Fc                             # V48A cut a382 to 25% (uVar27 x0.25)
        dF_flip = Ff - Fc
        dF_cut  = Fcut - Fc
        print(f"    LEVER SIZE (change in loop factor, the damping-relevant delta):")
        print(f"       V48A 75%% cut : dRe={dF_cut.real:+.3f}   |dF|={abs(dF_cut):.3f}   (this was NULL on-car)")
        print(f"       StageC flip  : dRe={dF_flip.real:+.3f}   |dF|={abs(dF_flip):.3f}")
        if abs(dF_cut.real) > 1e-9:
            print(f"       => flip moves Re {dF_flip.real/dF_cut.real:+.2f}x as far as the null cut, "
                  f"in the {'SAME' if (dF_flip.real*dF_cut.real)>0 else 'OPPOSITE'} direction")

def sweep_l3(zeta, pol=+1):
    print("="*90)
    print(f"SENSITIVITY: StageC gain L3 (motor-rate LERP; nominal 2048) vs the flip's damping delta")
    print(f"   (polarity {pol:+d}, plant zeta={zeta:.3f})")
    print("="*90)
    w = W0
    Fc0 = loop_factor(w, zeta, flip=False, pol=pol, l3=L3)
    print(f"   {'L3':>6} {'|StageC/StageA|@21.5':>22} {'Re[F] current':>14} {'Re[F] flipped':>14} {'verdict':>14}")
    for l3 in (512, 1024, 2048, 3072, 4096):
        # ratio of StageC to StageA magnitude at 21.5
        z_1 = cmath.exp(-1j*w/FS)
        sc = abs((l3/1024.0)*32.0*(1-z_1)); sa = (L1/1024.0)*32.0
        Fc = loop_factor(w, zeta, flip=False, pol=pol, l3=l3)
        Ff = loop_factor(w, zeta, flip=True,  pol=pol, l3=l3)
        v = "DAMPING" if Ff.real < 0 else "still anti-d"
        print(f"   {l3:>6} {sc/sa:>22.3f} {Fc.real:>+14.3f} {Ff.real:>+14.3f} {v:>14}")

def gate2_frequency_sweep(zeta, pol=+1):
    """GATE-2: does the flip create anti-damping (Re[F]>0) at ANY frequency, not just 21.5 Hz?
    For a single-lane sign flip the concern is a NEW anti-damping region appearing where there
    was none. Sweep the a382 lane's loop-factor real part across the band."""
    print("="*90)
    print(f"GATE-2 FREQUENCY SWEEP  (polarity {pol:+d}, plant Q={1/(2*zeta):.1f})")
    print("="*90)
    print("  a382 loop-factor Re[H_a382*P*delay]:  >0 = ANTI-DAMPING (bad), <0 = damping (good)")
    print(f"   {'f(Hz)':>7} {'Re current':>12} {'Re flipped':>12}   note")
    new_anti, worse = [], []
    for fhz in (1,3,5,8,12,16,21.5,26,32,40,55,78.6,100,140):
        w = 2*math.pi*fhz
        Fc = loop_factor(w, zeta, flip=False, pol=pol).real
        Ff = loop_factor(w, zeta, flip=True,  pol=pol).real
        note = ""
        if Ff > 0 and Fc <= 0:
            new_anti.append(fhz); note = "<-- NEW anti-damping (GATE-2 fail)"
        elif Ff > Fc + 1e-9:
            worse.append(fhz); note = "flip less damping here (still ok if <0)"
        print(f"   {fhz:>7.1f} {Fc:>+12.3f} {Ff:>+12.3f}   {note}")
    if new_anti:
        print(f"  *** GATE-2 CONCERN: flip creates anti-damping at {new_anti} Hz ***")
    else:
        print(f"  => GATE-2 CLEAN (pol {pol:+d}): flip adds damping or is neutral at EVERY swept frequency;")
        print(f"     NO new anti-damping region anywhere -> introduces no new instability. "
              f"{'(worse-but-still-damping at '+str(worse)+')' if worse else ''}")


def flip_plus_pole_screen(zeta, pol=+1):
    """V49B-REFINED: the bare flip creates high-freq anti-damping (GATE-2 fail). Band-limiting StageC
    with its EMA pole (cal 0xC644A) rolls off the derivative above the corner, confining the flipped
    damping to ~21.5 Hz. Find a pole that gives Re[F]<0 at 21.5 (damping) AND Re[F]<0 across 45-140 Hz
    (no new high-freq anti-damping). Bonus: confining the effect to ~21.5 Hz means that IF the true mode
    is the 78.6 Hz alias, the edit is a NULL (safe), not a brick."""
    print("="*90)
    print(f"V49B-REFINED -- flip StageC AND band-limit it (pole 0xC644A) to kill the HF anti-damping")
    print(f"   (polarity {pol:+d}, plant Q={1/(2*zeta):.1f})")
    print("="*90)
    print(f"   {'0xC644A':>8} {'corner~Hz':>10} {'Re@21.5(want<0)':>16} {'maxRe 45-140(want<0)':>21}   verdict")
    for pole in (1024, 512, 256, 128, 96, 64):
        aC = pole/1024.0
        corner = (-math.log(1-aC)/(2*math.pi)*FS) if aC < 1 else float('inf')
        re215 = loop_factor(W0, zeta, flip=True, pol=pol, stagec_pole=pole).real
        hi = max(loop_factor(2*math.pi*f, zeta, flip=True, pol=pol, stagec_pole=pole).real
                 for f in (45,55,65,78.6,90,100,120,140))
        if re215 < 0 and hi <= 1e-6:
            v = "GATE-2 CLEAN + damps 21.5"
        elif re215 >= 0:
            v = "no 21.5 damping (pole too low)"
        else:
            v = "HF anti-damping remains"
        cs = f"{corner:.1f}" if corner != float('inf') else "inf(unity)"
        print(f"   {pole:>8} {cs:>10} {re215:>+16.3f} {hi:>+21.3f}   {v}")


def main():
    print("\nV49B GATE-2 PRE-SCREEN -- does flipping FUN_0003a382 StageC add DAMPING at 21.5 Hz?\n")
    print("Datapath disasm-exact; loop weight kappa unknown so read ANGLES and RELATIVE deltas, not |F|.\n")
    # corrected measurement: broad shelf, Q ~ 2-8 (not 13.6). Show a marginal and a broad case.
    for zeta in (0.06, 0.15):     # Q ~ 8.3 and ~3.3
        band(f"PLANT Q={1/(2*zeta):.1f}", zeta)
        print()
    sweep_l3(0.15, pol=+1)
    print()
    for pol in (+1, -1):
        gate2_frequency_sweep(0.15, pol=pol)
        print()
    flip_plus_pole_screen(0.15, pol=+1)
    print()
    print("READ-OUT:")
    print(" * The flip's DIRECTION (damping vs anti-damping) is set by the polarity sign gp-0x6752,")
    print("   which is EEPROM-resident and NOT readable from code.bin (default +1). If it is -1 on the")
    print("   as-shipped car, every 'DAMPING' verdict here becomes 'ANTI-DAMPING' -> the flip BRICKS.")
    print(" * a382 is a MINORITY carrier (V48A's 75%% cut was null), so even a sign-correct flip may be")
    print("   insufficient against the distributed anti-damping from the other 1 kHz collocated lanes.")
    print(" * S3 is 32x down (no <<5) -> negligible at 21.5 Hz; StageA (flat) ~ StageC (deriv) in size,")
    print("   so the flip SWINGS PHASE ~90 deg rather than cleanly negating the lane.")

if __name__ == "__main__":
    main()
