# ADV-ARITHMETIC — V299 rev 2 (two-level A3 cap, freeze 1229, asymmetric bound) — built image

**Adversary:** ARITHMETIC (subagent, build round). **Job:** make the BUILT image FAIL. **Verdict: PASS_WITH_DEFECTS.**
DO_NOT_FLASH was reachable: the criteria were written first (`FAIL-CRITERIA-arithmetic-V299.md`). No arithmetic finding reached them.
Nothing flashed, no CAN sent, no git touched, no Ghidra program saved. **Classifier interruptions: 0.**

- **Image:** `accord-firmwares/analysis-2020accord/_v299_V299-ANGLELOOP…A3-2LVL.4096.6144.V2880.FRZ1229…A16B_plain_image.bin`.
  I re-hashed it: sha256 `30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08`. The brief left the image path and sha
  blank, so I found the file by its name and checked the hash against the spec's.
- **Method (independent of the build script and the spec):**
  1. Ghidra decompile, then a dry-run listing of **my own disasm-only import** (`/v299advarith/V299_ADVARITH_DISASM_ONLY.bin`, not saved).
  2. **My own minimal V850E2 interpreter** (`arith/v850_mini.py`). It was written from the encoding rules, not from the kit's `Cpu2`. It
     raises on any opcode it does not model and on any store.
  3. **My own integer mirror**, transcribed line by line from the decode (`arith/a1_mirror_vs_bytes.py::mirror99`).
  4. Python LE reads of every constant and cal used.

  The Honda integrator after the hook comes from the V298 listing at 0x29D7A..0x29DE4. Those bytes are identical in V299: the image
  diff is confined to the 67 bytes. Scripts are in `adversarial/arith/` (`a1`..`a4`, each with its `.out.txt`); every one ran in < 4 s.

---

## Results against the FAIL criteria

| # | criterion (DO_NOT_FLASH if shown) | result | EVIDENCE (method) |
|---|---|---|---|
| F1 | Cap fails to cap; shl overflow/wrap; negative r9 into the unsigned `cmovh` | **PASS** | Exhaustive over **all 65 536 θ × sgn(E′) ∈ {−,0,+}** at 15 v-edge words (a2). The bound is always ≥ 1250. It is ≤ 4096 for v ≤ 1382 and ≤ 6144 for 1383..2880. Above 2880 it is uncapped, max 2 098 338. r9 is clamped ≥ 0 before the shift, so `cmovh` (unsigned) sees only positives. Max r9 = 32768≪6 + 1250 does not wrap. A sweep over all 65 536 v words gives exactly three regimes: {≤1382: 4096}, {1383..2880: 6144}, {≥2881: 64\|θ\|+1250}. |
| F2 | Hard freeze reads the wrong cell, width or sign; imm16 mis-extended | **PASS** | `ld.hu -0x4f68[gp]` @0xC4C5E; `movea 0x4cd` = +1229 (bit 15 clear, so no sign trap); `bh`, unsigned. Python census found exactly **one writer**, `st.h r14` @0x7FECA (positive control: the cave's own read @0xC4C5E and `st.h r16,-0x6a32` @0x29D72 were found). Its function FUN_0007f3f8 is byte-identical to stock. The decompile gives `gp-0x4f68 = min(\|s16 gp-0x4f60\|, 0xFFFE)`, a **magnitude**, so the freeze is sign-symmetric. Raw −32768 gives 32768, which freezes. Edge: 1229 winds and 1230 holds (a3 S7). |
| F3 | Asymmetric clause takes sgn(E′) from the wrong or a clobbered register | **PASS** | r16 = E′ after `mul`/`sar 8` @0xC4C54/58. Nothing writes r16 between there and `cmp r0,r16` @0xC4C6E or the second use @0xC4CB2. The Honda increment (0x29D7A `mov r16,r6; sar 5`) uses the same register. Because G ≥ 559 > 0 and `sar` floors, sgn(E′) = sgn(E) exactly. Opposing sign gives a bound of **exactly 1250** at every v edge, for all θ ≠ 0 (a2). Unwinding is never blocked, because t = −(I≫10) < 0 < bound. |
| F4 | Winding compare has the wrong signedness or direction; compounding floor bias | **PASS (1-LSB asymmetry, conservative)** | `cmp r9,r13; bge`, signed, means t ≥ bound freezes. The `sar 0xa` floor makes the negative side stop at \|I8\| = 4 193 280 (4095.000 counts) versus 4 194 296 (4095.992) on the positive side, at bound 4096 (a3 S6). That is one count, on the conservative side, and it does not compound. |
| F5 | Edge pathology at 1382/2880 under jitter: latched FRZ, or an ICL-scale step | **PASS_WITH_DEFECT D1** | No latch: when E′ reverses, the integrator always unwinds (a3 S3: 8182 → 3680 in 0.5 s). The cap is a **winding stop**, though, not a clamp. See D1. |
| F6 | ICL below the cap (vacuous); >>10 overflow at the ICL | **PASS** | ICL tp+0x71BA = 8192, above both caps, so each cap is live. I is clamped to ±8192·128 = ±1 048 576 before `shl 3`, giving I8 ≤ 8 388 608 and t ≤ 8192 with no wrap (a3 S5 at the rail error: S = 8192 exactly). |
| F7 | Diff ≠ 67; CRC; branch into the span from outside; a store; a live register clobbered | **PASS** | Diff vs V298 = **67 bytes**: 60 in-span, 2 imm16 @0xC4C64, 1 F181 @0x1310D (41→42), 4 trailer. crc32[0x13000,0xC4FFC) = `95 3b dd 70` = the trailer. Cave sha `e22193b9…`. Whole-image Format-V census into the cave finds only `jarl` @0x29D76. Short-bcond census into [0xC4C6A,0xC4CAC) finds 5 targets, all from inside the span (a4). The interpreter traps any store and none occurred. Over 30 000 cases, every register except r6/r8/r9/r13/r16/r26 is unchanged. r8/r9/r13 are written before they are read in the Honda code after 0x29D7A, so they are dead at exit. r10 (deadband) is preserved. |
| — | **Mirror = bytes** | **0 / 30 000** | My interpreter on the built cave vs my mirror: exit pc, r16, r26, r6, r9 and the non-scratch registers. The set covers random cases plus targeted ones (v ∈ {0,714,1381..1383,2879..2881,6198,65535}, I8 straddling ±1250/4096/6144/8192·1024, a4f68 ∈ {1228..1231, 32768}, θ ∈ {±177/178, ±306/307, ±32767/−32768}). Exit mix: 23 242 FRZ, 5 011 DONE, 1 747 SKIP. **Negative control:** V298 bytes vs the V299 mirror gives **282 / 3000** mismatches, so the check can fail. |

Supporting arithmetic (EVIDENCE, a2):
- **E·G cannot wrap.** \|E\| ≤ 4·32768 + 65535 = 196 607. The r26 clamp ±C uses tp+0x72E6 = 65535 @0x28FA6; the feedback is r26 = 8θ + 8θ_prev (a = tp+0x73EA = 8192, b = tp+0x73E8 = 0). G over **all** v is in [559, 2188] (no G ≤ 0). The maximum product is 4.30e8, below 2³¹.
- **Relative to V298:** across every θ, sign and regime, **max(bound_V299 − bound_V298) = 0**. V299 never admits more winding than the flown V298. The authority gains are only the two freeze changes (512 → 1229, and the deleted |hand| > 300 opposing-sign freeze). Against a hand ≤ raw 1229, I now winds up to the bound where V298 froze. That is the design's ruling (i); its plant consequence is not arithmetic and not mine to judge.

---

## Defects (none is DO_NOT_FLASH)

### D1 — MEDIUM, a design-coverage gap (inherited structure, not a regression): the two-level cap is a winding stop on the instantaneous v-word
The cap only decides **whether this tick may wind further**. A frozen integrator **holds**: r6 = 0, so I is unchanged and never bleeds toward the
current cap. Open-loop arithmetic, θ 60° held with a 10° same-sign error (a3; the E scaling is BELIEF, the arithmetic is exact):
- **Deceleration carry:** v 3500 → 600 with the error persisting ends at **S = I≫7 = 8192 at v = 600, where the cap is 4096.** That is twice the
  cap the design kept at ≤ 6 m/s. The design kept it because ≥ 5120 trips F4 at 3–4 m/s (spec §1.2).
- **Jitter ratchet at the 1382 edge:** one tick in 50 at 1383 takes S from 4099 to **4633 in 3 s**. It keeps climbing toward 6144, because every
  1383 tick admits one increment and nothing removes it. Alternating every tick gives 6153. At 2880: one in 50 at 2881 gives 6309, and
  alternating gives 8192 (ICL).
- **Why not a FAIL:** V298 has the identical structure with an **uncapped** mid band, and V299's bound is ≤ V298's everywhere. The carried state is
  therefore ≤ what V298 (flown, route 79) could carry. The ceiling is ICL 8192 in both builds. V298's adversary bounded the sustained worst
  case, with I wound to ICL, at |T| 2482 < OCL 3072.
- **What is wrong:** spec §1.2's line "≤ 6 m/s byte-for-byte V298's" is true of the **bytes**, not of the **delivered integral state**. Its
  evidence table is fixed-speed turn-ins only (`rev_cap_size.py`), so **braking into a turn**, the ordinary way to reach 3–6 m/s in a turn,
  is untested.
- **Fix (do not apply here):** state on the page and the drive card that the cap is a winding stop. Add a decel-through-a-held-turn row (e.g.
  12 → 3 m/s) to the S2/RSN sims before reading F4 at low speed. If ever needed, a bleed/clamp of I toward the cap is a new cave term, with
  bytes and its own gates.

### D2 — LOW, inherited: the bound is tested before the increment, so the integrator overshoots it by one tick
Overshoot in output counts (I≫7) = ((E′≫5)·40≫3)/128:

| error | overshoot at G = 560 | overshoot at G = 2188 |
|---|---|---|
| 10° | 4.3 | 16.7 |
| 90° | 38 | 150 |
| rail \|E\| | — | 2051 |

The overshoot is then held (a3 S4: 4095 → 4180 at 90°, bound 4096). It is bounded by ICL 8192 in all cases. Large-error ticks are limited
upstream by the fork's error clip (BELIEF; fork side, not verified here). Fix: none needed. Note it on the page.

### D3 — LOW, documentation: "freeze ⇔ wire ≥ 1201 ⇔ steeringPressed" (spec §1.1) is off by one raw count on one sign
The frame builder FUN_00055C42 (byte-identical to stock) sends `wire = −(raw·125 ≫ 7)`. `sar` floors, so **raw = −1229 gives wire +1201**:
openpilot's `steeringPressed` is true while |raw| = 1229 does **not** freeze. raw = +1229 gives wire −1200 (not pressed). This is a one-count
window, negligible in effect. Fix: reword to "≈" or "raw > 1229". (That steeringPressed means |wire| > 1200 is BELIEF from openpilot.)

### D4 — INFO
- The sar-10 floor gives a one-count sign asymmetry at the bound, on the conservative side (F4).
- The asymmetric clause at E′ = 0 treats E′ as ≥ 0. It is inert there, because e5 = 0 means no increment.
- The v-word is read twice per call (0xC4C18 for G, 0xC4C7A for the regime). An interrupt-time update between the two reads would only mix
  two consecutive samples (BELIEF; harmless).

---

## Delivered-surface arithmetic of the cave, re-derived (my mirror, every line validated 0/30 000 against the bytes)
```
E   = s32((sp<<2) - r26)                         # 0xC4C00/02      r26 = clamp(8θ+8θprev, ±65535) @0x28F86..FBC
op  = s16(gp-0x6abe); u32(op+13000) > 26000 -> 0x2A164 (I:=0)          # 0xC4C04..14
G   = walk(0xC4CDA, v) in [559, 2188];  Ep = s32(E*G) >> 8              # 0xC4C18..58 (no wrap: |E*G| <= 4.30e8)
r25 == 0            -> 0x29D7E, r16=r26=0, r6 = -(I8>>6)  (decay)       # 0xC4C5A/CC8..D4
u16 gp-0x4f68 > 1229 -> 0x29D7E, r6 = 0 (I held; P and D still run)     # 0xC4C5E..68, 4f68 = |raw hand|
r9 = max(θ·sgn(Ep), 0)                                                  # 0xC4C6A..78
bound = v>2880 ? 64·r9+1250 : min_u(16·r9+1250, v<=1382 ? 4096 : 6144)  # 0xC4C7A..A8
t = ±(I8>>10) (sign of Ep);  t >= bound -> hold;  ramp bit15 clear -> hold;  else DONE   # 0xC4CAC..D8
Honda: I = clamp((I8>>3) + ((Ep>>5)*40 >> 3), ±1 048 576);  I8 = I<<3   # 0x29D7A..DE4, st.w @0x2A190 (deadband 0, Ki 40, ICL 8192)
```

**Out of ARITHMETIC scope**, for the other lenses:
- The F4 consequence of D1's carried integral (stability lens).
- raw ↔ wire units and the v-word ↔ m/s scale (unit lens).
- The assertion census (build audit).
- The consumers of the extra authority (interlocks).
