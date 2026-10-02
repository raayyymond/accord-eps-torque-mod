# ADV UNIT / SCALE-CHAIN on the BUILT V298 image — 2026-10-01

**Author:** the UNIT/SCALE-CHAIN adversary, a SUBAGENT of orchestrator `main`. Read-only: nothing built, flashed
or sent; the fork was not touched. Ghidra `disassemble_bytes dry_run:true` / `decompile_function` only, on the
open stock `code.bin`, the V294 program (code-identical to V295), and the V298 copy `ADVIG_V298_177abf04.bin`
(byte-verified identical to the flight image at `0xC4C00..0xC4D08` this session). Python = `bin_decompile` env.

**TARGET:** `_v298_...SP69AE.A16A_plain_image.bin` sha256 `177abf04...2066` ·
`.rwd` `...V298-...-0x13000-0x100000.rwd` sha256 `1a69b927...` (both re-hashed at start and end, unchanged).

**FAIL criteria written first:** `ADV-unit-scale-V298-FAIL-CRITERIA.md` (U1–U9, DO_NOT_FLASH reachable), supersedes
the truncated `FAIL-CRITERIA-unit-scale-V298.md`.

## VERDICT: **PASS_WITH_DEFECTS**

Every link of the angle-loop unit/scale chain was re-derived from the V298 bytes (independent decoder + Ghidra
dry-run), cross-checked on the route-71 wire, and agrees with design `DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md`
§1–§3 within tolerance. **No U-criterion fired; DO_NOT_FLASH not reached.** The defects are two inherited
BELIEF-grade premises and a build-vs-design cave-size note, none of which changes a safety sign/scale conclusion.

| crit | subject | result |
|---|---|---|
| U1 sign | E = 16·(θ_sp−θ), negative feedback | **clear** — derived below; wire sign-agreement confirms frames |
| U2 frame ≥1.25× | sp<<2 vs r26 both 160 counts/deg | **clear** — exact integer match, factor 1.000 |
| U3 speed key | G(v) on gp-0x6a5e, 64 cnt/km/h | **clear** — knots decode to the design's m/s; EVIDENCE from the `<<6` writer |
| U4 Q-format | G Q8 (`sar 8`), Kp `sar 8`, Ki `sar 5`+`sar 3`/`sar 7` | **clear** — all shifts read from bytes |
| U5 wrap | E·G, P, I, D, r26 | **clear** — no reachable 32-bit wrap; r26 saturates (designed), no sign flip |
| U6 D sign/operand | D on fresh gp-0x6abe, a wheel-angle rate | operand **clear**; **sign is pol-dependent, on-car-only (declared H-pol)** |
| U7 freeze unit | 300/512 raw vs noise floor | **clear** — 293/500 wire; fires 9.4%/4.5% of engaged frames, above noise, below a fight |
| U8 integral bound | shl4/shl6 +1250, knee 12.5, cap 4096<6 m/s | **clear** — slopes 26/102 lane-cnt/deg, knee & cap decode exactly |
| U9 rail/clamp | 5346/32768, OCL 3072 | **clear** — read from bytes; "rail 2461" is the observed peak, OCL is the hard clamp |

## 1. The chain, END TO END, from the V298 bytes (EVIDENCE; `us01`,`us05`, Ghidra dry-run)

```
0xE4 STEER_TORQUE raw  (bytes 0-1 BE s16, FUN_00021724 -> gp-0x1428/27)
 FUN_00052676: sp = FUN_00049a90(raw*-4, -0x4000, +0x4000)   [0x49A90 = symmetric clamp]
   => gp-0x69ae = clamp(-4*raw, +-16384)                     U2 factor-4: CONFIRMED (sVar1*-4)
0x29D6A (E4)  ld.h -0x69ae[gp],r16   => r16 = sp
0xC4C00 cave  shl 0x2,r16            => r16 = 4*sp
0xC4C02       sub r26,r16            => E = 4*sp - r26        (r26 = the angle-filter sum on entry)
 fb filter 0x28F4C..0x28FBE: E1 ld.h -0x6a00,r7 (theta, 0.1deg) ; s_new=(b*theta>>10), b=8192 => 8*theta
   E2 add r9,r26 (SUM) ; a=0 ; clamp +-C, C=65535   => r26 = 8*theta[n]+8*theta[n-1], DC = 16*theta
 => E = 4*clamp(-4*raw) - 16*theta = -16*(raw+theta) = 16*(theta_sp - theta),  theta_sp := -raw   (0.1deg counts)
    both operands are 160 counts/deg  (4*sp = 160*theta_sp_deg ; 16*theta = 160*theta_deg)  -> U2 factor 1.000
0xC4C04       ld.h -0x6abe[gp],r26   => r26 reloaded with the FRESH 1 kHz motor rate (for D only)
0xC4C14       op-skip: bnh CONT ; jr 0x2A164   if (gp-0x6abe+13000) u> 26000  (invalid rate -> Honda epilogue)
0xC4C48/4C    mul r13,r8 ; sar 0xc   => G walk slope term  (table at cave+0xDA, GB-P)
0xC4C54/58    mul r8,r16 ; sar 0x8   => E' = (E*G) >> 8     U4: G is Q8 (256 = 1.0)  CONFIRMED (sar 8)
0xC4C5A/5C    cmp r0,r25 ; be CAM    => CAMERA GATE: run iff gp-0x6803==2 (r25), else inert (E':=0, op:=0)
0xC4C5E..     hard freeze |gp-0x4f68|>512 ; opposing freeze >300 AND sign(gp-0x4f60)!=sign(E')
0xC4C7A..CA   A3 bound: (|gp-0x6a00|<<sh)+1250 ; sh=4 if vw<=2880 else 6 ; cap 4096 if vw<=1382
Honda tail 0x29D7A..: e5 = E'>>5 (sar 5) ; I = clip((I8>>3)+(e5*Ki>>3), +-((ICL<<10)>>3)) ; I8=I<<3 ; I->S = I>>7
  P = clip((E'*Kp)>>8, +-PCL)           Kp=112 PCL=15360
  D = clip((Kd*op)>>3, +-DCL)           Kd=48  DCL=10240  op = fresh gp-0x6abe
  S = (I>>7) + P + D ; fade (fA*fB>>8) ; SCL 15360 ; output lag ; yr=y*ramp>>15 ; T=clip((yr*pol*5346)>>15,+-OCL)
   pol = gp-0x6752 = -1 (boot-static) ; OCL=3072
```

**U1 SIGN (clear).** E = 16·(θ_sp − θ): a positive angle error (θ_sp > θ, need more left) gives E>0 → E'>0 (G>0)
→ P>0. On the wire (route 71, `us03`/`us06`): gp-0x6a00 = +10·carState angle (left-positive), corr(0x14A angle,
d/dt) with its rate +0.997; the hand-torque cell gp-0x4f60 correlates +0.52…+0.57 with angle (sign-agree 0.86 at
|tq|>1200), so it is in the θ frame and the opposing-freeze `xor` is not inverted. The output sign chain
(pol·5346·OCL, lag, ramp) is **byte-identical to V295**, which flew and delivered correct-direction assist; V298
only replaces the error formation with a true (setpoint − feedback) angle error of the same downstream sign. No
positive-feedback path. (The one residual: the fresh-D sign through pol is **on-car-only**, see §3.)

## 2. Per-band surface, from the BUILT table (EVIDENCE `us05`) — agrees with design §1.3/§3

GB-P table at `cave+0xDA`, read verbatim: `(714,1178,1041)(1843,1465,−6264)(2304,760,−2033)(2707,560,1570)
(4032,1068,2118)(6198,2188,0)(65535,2188,0)` — **byte-for-byte the design §1.3 table and the build assertion.**
Walk **min G = 559 @ 11.75 m/s** (design says 559; the knot is 560, the walk lands one count below at the knot) —
CONFIRMED. Knots decode to 3.10 / 8.00 / 10.0 / 11.75 / 17.5 / 26.9 m/s at 64 counts/km/h — the design's speeds.

Kp_eff = Kp·G/2^16 (torque-count per E-count); E = 160 counts/deg; P-rail = PCL(15360) / Kp_eff / 160:

| v (m/s) | G | Kp_eff /E | T-count/deg | P-rail (deg err) |
|---|---|---|---|---|
| 3.1 | 1178 | 2.01 | 322 | 47.7 |
| 8.0 | 1464 | 2.50 | 400 | 38.4 |
| 10.0 | 759 | 1.30 | 208 | 74.0 |
| 11.75 (min) | 559 | 0.96 | 153 | 100.5 |
| 15.0 | 847 | 1.45 | 232 | 66.3 |
| 22.0 | 1604 | 2.74 | 439 | 35.0 |
| 26.9 | 2188 | 3.74 | 598 | 25.7 |

A3 integral bound (design §1.3 "~26 T/deg / ~102 T/deg"): `shl 4`=×16 and `shl 6`=×64 on |θ| (0.1-deg counts) =
160 / 640 S-counts/deg; through the 5346/32768 = 0.163 output gain that is **26.1 / 104 lane-counts/deg** —
matches the page's 26 / 102 within rounding. Knee `vw<=2880` = 45 km/h = **12.5 m/s**; low-speed cap 4096 when
`vw<=1382` = **6.0 m/s**. ICL 8192 → max integral S-contribution = (8192<<10>>3)>>7 = **8192** (design: "ICL 8192,
below V295's 10240"). All EVIDENCE.

## 3. Defects (PASS_WITH_DEFECTS — none a unit/scale sign or factor error)

- **D-D1 (U6, inherited):** the fresh-D sign depends on `pol = gp-0x6752 = −1` and on sign(gp-0x6abe) vs the
  angle rate. The operand is proven a rate of the same wheel angle (gp-0x6a56 is derived from gp-0x6abe via
  `48·1159>>15` at 0x3F794, and gp-0x6a56 is +8.00 counts/(deg/s) on the wire, `us03`). The **sign that makes D
  damp is not provable from bytes alone** — it is the design's declared H-pol item, caught by the flight
  instrument R1 ("c_D aiding ω → abort") on drive 1. BELIEF, instrument-covered, not a unit error.
- **D-D2 (U3, inherited):** 64 counts/km/h for gp-0x6a5e is EVIDENCE from the fallback writer `(gp-0x6753)<<6`
  (FUN_000522fe/534DA) and self-consistent with the firmware's own 50–130 km/h axis at /64; the DBC 0.01 km/h bus
  unit behind it is BELIEF. Does not change any band.
- **D-D3 (build-vs-design, not a unit error):** the IMAGE carries the **260 B camera-gated cave** (merged
  primary 240 B + the `cmp r0,r25 ; be CAM` gate, +20 B), i.e. the C3-rev2-P-**cam** variant the design offers as
  non-default and ESCALATES (§0.3.4). The camera-arm fade `fadeB2@0xE54FC` is neutralized to `fadeB@0xE564C`
  (same i682f=|tq|>>5 key unit — unit-consistent). This belongs to the interlocks adversary; flagged here only
  because the unit chain I verified is the camera-gated one.
- **Designed saturations (documented, not defects):** r26 clamps at C=65535 so the angle feedback saturates
  past |θ|≈409.6° wheel (design §1.3); no sign flip at the clamp (both E operands bounded). The GB dip min G 559
  is one count under the 560 knot by the walk index — the page already states 559.

## 4. What a FAIL would have been, and why it was reachable but not hit

DO_NOT_FLASH was structurally reachable: each U-criterion is decided by a byte read + a named decode in the
BUILT image, none pinned to PASS. A `sar 7`/`sar 9` instead of `sar 8` on G, a `sub` left as `subr` (rate not
angle), sp not `×−4`, the speed key off by a factor, or sign(E) reversed would each have fired. All decoded as
the design states. The nearest thing to a stop — the fresh-D sign — is pol-dependent and is the design's own
pre-declared on-car check, not a byte error.

## 5. Methods / artifacts
`unit_scale/us01_read_image.py` (bytes, diff), `us02_gp_access_scan.py` (gp-access scan, positive-controlled on
gp-0x67a2/gp-0x6803), `us03_wire_frames.py` (route-71 frames: angle-rate +0.997, 0x18F/0x14A rate slope 7.995,
freeze-threshold distribution), `us04_680a_writer_hunt.py` (the dead-damper flag has 0 writers — control found
the 4 gp-0x6803 writers), `us05_table_and_units.py` (G table + per-band gains), `us06_hand_frame_and_selector.py`
(hand-torque frame; per-selector Kp/Kd — only selector 7 is modified). V298 image + .rwd re-hashed, unchanged.
