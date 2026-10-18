# ADV-V37A lens 2: unit/scale chain and feedback clamp (2026-10-17, adv37a-units)

VERDICT: PASS_WITH_DEFECTS. None of the four pre-written FAIL conditions fired. Five defects/observations below.
Image checked: _v37a_plain_image.bin sha256 7cb6fd3a...9930 (hash verified). Ghidra program open = STOCK code.bin;
built vs stock code bytes in [0x13000,0xC0000) differ ONLY at 0x13109 and 0x14120 (a '-'->',' text byte) => every
decompile/disasm below is valid for the built image's code (EVIDENCE: Python byte diff).

## (1) Demand-index scale  -- CONFIRMED
- FUN_00052676 decompile: gp-0x69ae = FUN_00049a90(sVar1 * -4, 0xffffc000, 0x4000)  => cmd = clamp(-4*raw, +-0x4000). EVIDENCE.
- 0x29032 ld.h gp-0x69ae; LIM = LERP(bank 0xCB844[7] -> record 0xE51A8, X=speed 3200..8320, Y=15360 flat) => cmd clamped +-15360.
- 0x29CB4 mulu taper*spF -> andi 0xffff = G ; 0x29CBC mul r22,G ; sar 16 ; 0x29CD6 sar 6 ; clamp +-cal(0xC64F0/F1)=240 ; idx=|v|.
- taper (0xE52FC/0xE5284) Y=255 for gp-0x682f<=42/38 ; spF (0xC6974) Y=255 flat => G=65025 (255*255) when driver torque idx <= 32.
- counts per idx = 2^22/65025/4 = 16.12574 (computed). CONFIRMED.
- Max idx: cmd=+15360 -> (15360*65025>>16)>>6 = 238 ; cmd=-15360 -> -239 (arithmetic-shift floor asymmetry; wire sign +raw gives cmd<0 => 239).
  Claimed 238 correct for one sign, 239 for the other. Top reachable sp on slot 7: idx238 -> 952, idx239 -> 956 (not 960; X[9]=240 never reached). Cosmetic.
- Map Y-in (0xE502C): X 0,12,20,24,32,64,96,128,160,240 ; Y 0,48,80,96,128,256,384,512,640,960 = 4*X exactly (EVIDENCE: byte read of built image).
  Pointer table 0xC9A88 unchanged vs stock. All 28 records: X unchanged, Y monotone, max Y 960 (<32768, so mulh/ld.hu/st.h safe).
- "2x slope": TRUE only in segment 1 (idx<=12). Ratio built/stock Y per knot: 2.0,1.9,1.92,2.06,2.56,3.05,3.3,3.9,5.6. The reference
  scale chain is not what makes it 2x (map X knots and idx formation are untouched), so a wrong idx scale could not falsify it. p50 idx=5 (inherited), so mass sees ~2x.

## (2) Setpoint / feedback units  -- CONFIRMED (the 8 counts/deg/s is inherited EVIDENCE, not re-measured here)
- 0x28F4C..0x28FA4 (disasm, controlled): x=ld.h gp-0x6a56 (bail |x|>12000) ; a=ld.h 0xC63E8=923 ; b=ld.hu 0xC63EA=1560 ;
  inc = (s*a>>10)+(x*b>>10) ; st.w inc -> gp-0x3d30 ; r26 = s + inc  (two-sample sum). DC: I=b*x/(1024-a)=15.446x ; out=2I=30.891 per raw count. CONFIRMED (2*1560/101).
- 0x29D76 shl 5 : E = 32*sp - r26 (32-bit sub). Balance 32 sp = 30.891 x  =>  x = 1.0360 sp raw = 0.1295 sp deg/s at 8 ct/deg/s
  (0.125 deg/s per 0x18F LSB: memory accord-the-ring-is-16-rate-lsb-not-sub-lsb-unit-trap.md, BELIEF here: wire log not re-read).
  stock top 172 -> 22.27 deg/s ; V37A 952..960 -> 123.7..124.3 deg/s. Arithmetic confirmed.
- Lag pole 923/1024 at 1 kHz = 16.5 Hz (computed).

## (3) The clamp 0xC62E6  -- CLEAN
Readers (raw LE scan of built image, hw2==0x72E7 for ld.hu tp+0x72E6; control: finds the three known sites):
  0x28F96 (e56f e772) ld.hu -> r13 ; 0x28F9C (e577 e772) ld.hu -> r14 ; 0x28FB8 (e5d7 e772) ld.hu -> r26.  All opcode field 0x3F, hw2 bit0=1 => ld.hu, UNSIGNED.
  Adjudicated extra raw hits: 0x61824 and 0x618D4 = 6-byte `ld.hu -0x9f52,r0,r14` (base r0, absolute peripheral address) -> NOT tp, not this cell (Ghidra dry-run).
  hw2==0x72E6 (st/ld.h forms): none. Odd-aligned 72E6/7: none. imm32 0xC62E6: none. movea/addi tp+0x72xx: none. 6-byte form (hw3==0x00E5): none.
  (Residual: no known 6-byte tp-load exists to positive-control the 6-byte scan; all three real reads are 4-byte. BELIEF-level, low risk.)
Arms (disasm 0x28FA6..0x28FBC): cmp r13,r26 ; ble -> negative arm ; else r26=r14 (=+C zero-extended, 32-bit positive for 42865).
  negative arm: r14=-C (subr r0) ; cmp r14,r26 ; bge keep ; else ld.hu again, subr r0 -> r26=-C.  All 32-bit signed compares of a zero-extended C; no sxh/zxh on the result.
  Consistent with unsigned 42865. (46080 already flew in V282 through the same code.)
Wide reads: ld.w tp+0x72E4 (opcode 0x39) : none. 0xC62E4 (=4, I-deadband) readers all ld.hu (0x29D6E,29D84,29D8C,29D96,2AC62,2AC76,2AC88). 0xC62E8 (=12800) read ld.hu at 0x28EB6 (speed bound).
Downstream of the clamp: r26 only feeds the floor32/rectify -> gp-0x6a34 (st.h, <=1339, readers only in 0x2A0C6 mode + 0x2AFAE twin island; gp-0x680a has no store hits) and E at 0x29D78. No other r26 reader 0x28FBE..0x29D78. Range: |r26|<=42865, E<=73585, E*Kp<=5.1e7, dE*Kd<=1.9e7: no 32-bit overflow ; E-prev sentinel window is +-768000. FUN_000428d4 (oscillation detector) reads gp-0x6c2c, not fb/E.
Consequence of the STOCK clamp 7680 with the new reference: fb freezes at x=248.6 raw = 31.1 deg/s (E = 32sp-7680 >= 0 for sp>=240); above 31 deg/s neither P nor D sees rate => no damping. With 42865: fb live to 1388 raw = 173.5 deg/s; top 32*960=30720 -> ratio 1.39535 matches 7680/(32*172). [B] is needed and correct.

## (4) GATE 2
[A] changes only sp (map Y). Kp (0xE5378: 248,512,645,696,696 on X 0,68,112,136,208) and Kd (0xE511C: 128 flat) are byte-identical to stock; their keys idx are untouched. Pole cells 0xC63E8/EA, Ki 0xC63E6=0, 0xC646C=891, 0xC61B2/B4=512 equal stock. [B] only moves a saturation. Linear loop L = [Kp/256 + (Kd/8)(1-z^-1)] * plant * F(z) is the stock one; margins = stock (EVIDENCE: structure + byte equality; margin NUMBERS not recomputed here).
The one way [B] changes dynamics: |fb|>7680 (|x|>248.6 raw, 31 deg/s), which stock clamped and V37A no longer does. Not a gain change.
Damping fraction sign(E)!=sign(fb) (BELIEF, qualitative): E<0 needs fb>32 sp. K=2 at low idx: threshold doubles, so a ring of given amplitude spends fewer samples with reversed E; at the x5.6 top, fb must exceed ~124 deg/s so E never reverses and damping appears only as P desaturating (never a braking sign), as in V278r3.

## DEFECTS (none block, ordered by severity)
D1 medium  P clamp 0xC61BC=15360 binds at |E|=5650 (= sp 176.6, slot-7 idx 44, ~p88 of engaged demand). Above it the loop is torque-saturated until fb is within 183 raw (23 deg/s) of target: the x5.6 reference raises authority, not necessarily rate. S clamp 0xC61BE=15360 same. Stock top 172 sat just under this. Linear gain unchanged, linear range shrinks relative to reference.
D2 medium-high  Fault sentinel gp-0x69ae=0x7FFF (FUN_00052676) -> LIM-clamped to +15360 -> idx 238 -> sp 952 (stock 172). Same code path/guard as stock (code bytes identical), but the commanded rate under a delivered sentinel pulse goes 22 -> 124 deg/s with P at its clamp. Whether the pulse reaches the lane on V37A depends on the 0x29A50/0x29A56 guard (not re-verified here; see agent memory on 0xE4 sentinel). Orchestrator should adjudicate.
D3 low-medium  Setpoint kick: D = dE*Kd>>3 (0x29EE4 mul, sar 3) with dE=32*dsp. A 123-count/frame slew step (7.63 idx, cap is fork-side, BELIEF) gives dsp 30.5 -> D 15,632, clamped at 0xC61B6=10240; stock 7,826 unclamped. One-tick spike per 100 Hz frame, ~2x larger.
D4 info  Built image still carries V37-base deltas vs stock: override thresholds 0xC61C0..C5 -> 0xFFFF, 0xC64B4..B8 -> 0xFF (bypass level 112 disabled), 0xC64DE 17->27, 0xC659B/9F/AF/B3, 0xC65C6.., 0xC674F.., 0xC675B.., 0xC6769.., version text at 0x13109/0x14120. Outside the three claimed edits; the "cal-only vs stock" statement is only true relative to V37. Combined with a x5.6 reference, override gating is looser: flag for the arithmetic/interlock lenses.
D5 cosmetic  Max idx 238 (+) / 239 (-); top sp 952/956, not 960.

Method: GhidraMCP decompile (FUN_00028ea6, FUN_00052676, FUN_000428d4) then disassembly; Python LE scans on _v37a image. No file modified except this report.
